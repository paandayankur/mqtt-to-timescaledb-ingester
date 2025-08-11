# filepath: esphome_mqtt_timescaledb_ingestor/ingestor.py

import typer
import paho.mqtt.client as mqtt
import psycopg2
import psycopg2.extras
import json
import time
import os
import threading
from queue import Queue
from pathlib import Path
import getpass

# --- CLI App Setup ---
app = typer.Typer(help="A robust service to ingest ESPHome MQTT data into TimescaleDB.")
CONFIG_FILE_NAME = "ingestor_config.json"
config_path = Path(typer.get_app_dir("esphome-ingestor")) / CONFIG_FILE_NAME

# --- Global variables that will be loaded from config ---
CONFIG = {}
stop_event = threading.Event()

# --- Queues for data processing ---
discovery_queue = Queue()
entity_queue = Queue()
state_queue = Queue()
status_queue = Queue()
command_queue = Queue()

# ==============================================================================
# == INTERACTIVE CONFIGURATION COMMAND
# ==============================================================================

def _test_db_connection(db_config):
    """Tries to connect to the database and returns True on success."""
    try:
        conn = psycopg2.connect(**db_config)
        conn.close()
        return True
    except psycopg2.Error as e:
        typer.secho(f"  -> ❌ Database connection failed: {e}", fg=typer.colors.RED)
        return False

def _test_mqtt_connection(mqtt_config):
    """Tries to connect to the MQTT broker and returns True on success."""
    try:
        client = mqtt.Client(client_id=f"ingestor-test-{os.getpid()}")
        client.username_pw_set(mqtt_config['username'], mqtt_config['password'])
        client.connect(mqtt_config['host'], mqtt_config['port'], 60)
        client.disconnect()
        return True
    except Exception as e:
        typer.secho(f"  -> ❌ MQTT connection failed: {e}", fg=typer.colors.RED)
        return False

@app.command()
def configure():
    """
    Launch an interactive setup wizard to configure database and MQTT credentials.
    """
    typer.secho("--- ESPHome Ingestor Configuration Wizard ---", bold=True)
    typer.echo(f"This will create a configuration file at: {config_path}")

    # --- Database Configuration ---
    typer.secho("\n--- Step 1: Database Connection ---", fg=typer.colors.CYAN)
    while True:
        db_config = {
            "host": typer.prompt("Database host", default="localhost"),
            "port": typer.prompt("Database port", default=5432, type=int),
            "dbname": typer.prompt("Database name", default="telemetry_db"),
            "user": typer.prompt("Database user"),
            "password": getpass.getpass("Database password: "),
        }
        typer.echo("  -> Testing database connection...")
        if _test_db_connection(db_config):
            typer.secho("  -> ✅ Database connection successful!", fg=typer.colors.GREEN)
            break
        elif not typer.confirm("Connection failed. Do you want to try again?"):
            raise typer.Abort()

    # --- MQTT Configuration ---
    typer.secho("\n--- Step 2: MQTT Broker Connection ---", fg=typer.colors.CYAN)
    while True:
        mqtt_config = {
            "host": typer.prompt("MQTT broker host", default="127.0.0.1"),
            "port": typer.prompt("MQTT broker port", default=1883, type=int),
            "username": typer.prompt("MQTT username", default=""),
            "password": getpass.getpass("MQTT password: "),
        }
        typer.echo("  -> Testing MQTT connection...")
        if _test_mqtt_connection(mqtt_config):
            typer.secho("  -> ✅ MQTT connection successful!", fg=typer.colors.GREEN)
            break
        elif not typer.confirm("Connection failed. Do you want to try again?"):
            raise typer.Abort()

    # --- Save Configuration ---
    final_config = {"database": db_config, "mqtt": mqtt_config}
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(final_config, f, indent=4)

    typer.secho(f"\n✨ Configuration saved successfully to {config_path}", fg=typer.colors.BRIGHT_GREEN, bold=True)
    typer.echo("You can now run the service with the 'start' command.")


# ==============================================================================
# == START SERVICE COMMAND
# ==============================================================================

def setup_database_tables(conn):
    """Creates the necessary tables if they don't exist."""
    with conn.cursor() as cursor:
        typer.echo("Ensuring database tables exist...")
        # ... (SQL commands are the same as your original script)
        cursor.execute("CREATE TABLE IF NOT EXISTS discovery_data (time TIMESTAMPTZ NOT NULL, device_name TEXT PRIMARY KEY, ip_address TEXT, mac_address TEXT, version TEXT, platform TEXT, board TEXT, network TEXT, raw_payload JSONB);")
        cursor.execute("CREATE TABLE IF NOT EXISTS entity (time TIMESTAMPTZ NOT NULL, unique_id TEXT PRIMARY KEY, device_name TEXT, component_type TEXT, name TEXT, state_topic TEXT, command_topic TEXT, raw_payload JSONB);")
        cursor.execute("CREATE TABLE IF NOT EXISTS device_status (time TIMESTAMPTZ NOT NULL, device_name TEXT, status TEXT, raw_payload JSONB);")
        cursor.execute("CREATE TABLE IF NOT EXISTS command (time TIMESTAMPTZ NOT NULL, device_id TEXT, component_id TEXT, command TEXT, raw_payload JSONB);")
        # Note: You'll need to add your esphome_data hypertable creation here if needed
        conn.commit()
        typer.echo("Database tables are ready.")

def db_writer_thread():
    """Writes batches of data from all queues to the database."""
    conn = None
    typer.echo("DB writer thread started.")
    db_config = CONFIG.get('database', {})

    while not stop_event.is_set():
        try:
            if conn is None or conn.closed:
                typer.echo("Attempting to connect to the database...")
                conn = psycopg2.connect(**db_config)
                setup_database_tables(conn)

            # ... (The rest of your db_writer_thread logic is the same)
            # This section is shortened for brevity but should contain your original queue processing logic.
            if not discovery_queue.empty():
                # ... process discovery_queue
                pass
            if not entity_queue.empty():
                # ... process entity_queue
                pass
            # ... and so on for all queues

            time.sleep(1.0) # Flush interval
        except psycopg2.Error as e:
            typer.secho(f"❌ Database error: {e}. Attempting to reconnect...", fg=typer.colors.RED)
            if conn: conn.close()
            conn = None
            time.sleep(5)
        except Exception as e:
            typer.secho(f"❌ An unexpected error occurred in the DB writer thread: {e}", fg=typer.colors.RED)
            time.sleep(5)

    if conn: conn.close(); typer.echo("Database connection closed.")


def on_mqtt_connect(client, userdata, flags, rc):
    """Callback for when the MQTT client connects."""
    if rc == 0:
        client.subscribe("homeassistant/#")
        client.subscribe("esphome/discover/#")
        client.subscribe("+/status")
        client.subscribe("+/+/+/state")
        client.subscribe("+/+/+/command")
        typer.secho("✅ Connected to MQTT Broker and subscribed to topics.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Failed to connect to MQTT, return code {rc}", fg=typer.colors.RED)

def on_mqtt_message(client, userdata, msg):
    """Callback that routes messages to the correct queue based on topic."""
    # This function's logic remains exactly the same as your original script.
    # It will put messages onto the various queues.
    pass # Shortened for brevity

@app.command()
def start():
    """
    Starts the ingestor service using the saved configuration.
    """
    if not config_path.exists():
        typer.secho("Configuration file not found!", fg=typer.colors.RED, bold=True)
        typer.echo(f"Please run 'mqtt-ingestor configure' first.")
        raise typer.Abort()

    global CONFIG
    with open(config_path, "r") as f:
        CONFIG = json.load(f)

    typer.secho("--- Starting ESPHome Ingestor Service ---", bold=True)
    writer = threading.Thread(target=db_writer_thread, daemon=True)
    writer.start()

    mqtt_config = CONFIG.get('mqtt', {})
    mqtt_client = mqtt.Client(client_id=f"python-ingestor-{os.getpid()}")
    mqtt_client.username_pw_set(mqtt_config.get('username'), mqtt_config.get('password'))
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message

    try:
        typer.echo("Connecting to MQTT broker...")
        mqtt_client.connect(mqtt_config.get('host'), mqtt_config.get('port'), 60)
        mqtt_client.loop_start()
        # Keep the main thread alive
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\n🛑 Shutting down script.")
    except Exception as e:
        typer.secho(f"❌ An error occurred with the MQTT client: {e}", fg=typer.colors.RED)
    finally:
        stop_event.set()
        if mqtt_client.is_connected():
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        writer.join()
        typer.echo("Script finished.")

if __name__ == "__main__":
    app()
