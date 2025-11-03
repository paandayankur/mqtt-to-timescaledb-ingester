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
import logging

# --- CLI App Setup ---
app = typer.Typer(help="A robust service to ingest ESPHome MQTT data into TimescaleDB.")
CONFIG_FILE_NAME = "ingestor_config.json"
config_path = Path(typer.get_app_dir("esphome-ingestor")) / CONFIG_FILE_NAME

# --- Global variables that will be loaded from config ---
CONFIG = {}
stop_event = threading.Event()
logger = logging.getLogger(__name__)

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
        logger.error(f"  -> ❌ Database connection failed: {e}")
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
        logger.error(f"  -> ❌ MQTT connection failed: {e}")
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
        logger.info("  -> Testing database connection...")
        if _test_db_connection(db_config):
            logger.info("  -> ✅ Database connection successful!")
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
        logger.info("  -> Testing MQTT connection...")
        if _test_mqtt_connection(mqtt_config):
            logger.info("  -> ✅ MQTT connection successful!")
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
# == LOGGING SETUP
# ==============================================================================
def setup_logging(log_level=logging.INFO):
    """Configures the application's logger."""
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)

    # Configure the logger used by this application
    logger.setLevel(log_level)
    logger.addHandler(stream_handler)

    # You could also configure the root logger, but it's often better to configure your specific logger
    # logging.basicConfig(level=log_level, handlers=[stream_handler])

    logger.info("Logging has been configured.")

# ==============================================================================
# == START SERVICE COMMAND
# ==============================================================================

def setup_database_tables(conn):
    """Creates the necessary tables if they don't exist."""
    with conn.cursor() as cursor:
        logger.info("Ensuring database tables exist...")
        # ... (SQL commands are the same as your original script)
        cursor.execute("CREATE TABLE IF NOT EXISTS discovery_data (time TIMESTAMPTZ NOT NULL, device_name TEXT PRIMARY KEY, ip_address TEXT, mac_address TEXT, version TEXT, platform TEXT, board TEXT, network TEXT, raw_payload JSONB);")
        cursor.execute("CREATE TABLE IF NOT EXISTS entity (time TIMESTAMPTZ NOT NULL, unique_id TEXT PRIMARY KEY, device_name TEXT, component_type TEXT, name TEXT, state_topic TEXT, command_topic TEXT, raw_payload JSONB);")
        cursor.execute("CREATE TABLE IF NOT EXISTS device_status (time TIMESTAMPTZ NOT NULL, device_name TEXT, status TEXT, raw_payload JSONB);")
        cursor.execute("CREATE TABLE IF NOT EXISTS command (time TIMESTAMPTZ NOT NULL, device_id TEXT, component_id TEXT, command TEXT, raw_payload JSONB);")
        # Note: You'll need to add your esphome_data hypertable creation here if needed
        conn.commit()
        logger.info("Database tables are ready.")

def db_writer_thread():
    """Writes batches of data from all queues to the database."""
    conn = None
    logger.info("DB writer thread started.")
    db_config = CONFIG.get('database', {})

    # Data batch lists
    discovery_batch = []
    entity_batch = []
    status_batch = []
    state_batch = []
    command_batch = []

    while not stop_event.is_set():
        try:
            if conn is None or conn.closed:
                logger.info("Attempting to connect to the database...")
                conn = psycopg2.connect(**db_config)
                setup_database_tables(conn)

            # Drain queues into batch lists
            while not discovery_queue.empty():
                discovery_batch.append(discovery_queue.get_nowait())
            while not entity_queue.empty():
                entity_batch.append(entity_queue.get_nowait())
            while not status_queue.empty():
                status_batch.append(status_queue.get_nowait())
            while not state_queue.empty():
                state_batch.append(state_queue.get_nowait())
            while not command_queue.empty():
                command_batch.append(command_queue.get_nowait())

            # Write batches to DB
            with conn.cursor() as cursor:
                if discovery_batch:
                    psycopg2.extras.execute_values(cursor,
                        "INSERT INTO discovery_data (time, device_name, ip_address, mac_address, version, platform, board, network, raw_payload) VALUES %s ON CONFLICT (device_name) DO UPDATE SET time=EXCLUDED.time, ip_address=EXCLUDED.ip_address, mac_address=EXCLUDED.mac_address, version=EXCLUDED.version, platform=EXCLUDED.platform, board=EXCLUDED.board, network=EXCLUDED.network, raw_payload=EXCLUDED.raw_payload;",
                        [(time.strftime('%Y-%m-%d %H:%M:%S%z'), d['name'], d.get('ip'), d.get('mac'), d.get('version'), d.get('platform'), d.get('board'), d.get('network'), json.dumps(d)) for d in discovery_batch]
                    )
                    logger.info(f"Wrote {len(discovery_batch)} discovery messages.")
                    discovery_batch.clear()

                if entity_batch:
                    psycopg2.extras.execute_values(cursor,
                        "INSERT INTO entity (time, unique_id, device_name, component_type, name, state_topic, command_topic, raw_payload) VALUES %s ON CONFLICT (unique_id) DO UPDATE SET time=EXCLUDED.time, device_name=EXCLUDED.device_name, component_type=EXCLUDED.component_type, name=EXCLUDED.name, state_topic=EXCLUDED.state_topic, command_topic=EXCLUDED.command_topic, raw_payload=EXCLUDED.raw_payload;",
                        [(time.strftime('%Y-%m-%d %H:%M:%S%z'), e['unique_id'], e['device']['identifiers'][0], e['component'], e.get('name', 'N/A'), e.get('state_topic'), e.get('command_topic'), json.dumps(e)) for e in entity_batch]
                    )
                    logger.info(f"Wrote {len(entity_batch)} entity messages.")
                    entity_batch.clear()

                if status_batch:
                    psycopg2.extras.execute_values(cursor,
                        "INSERT INTO device_status (time, device_name, status, raw_payload) VALUES %s;",
                        [(time.strftime('%Y-%m-%d %H:%M:%S%z'), topic.split('/')[0], payload, json.dumps({"topic": topic, "payload": payload})) for topic, payload in status_batch]
                    )
                    logger.info(f"Wrote {len(status_batch)} status messages.")
                    status_batch.clear()

                # Handling state messages requires a dynamic table approach
                if state_batch:
                    # Group states by device
                    states_by_table = {}
                    for topic, payload in state_batch:
                        # Assuming topic is like "device/component/id/state"
                        device_name = topic.split('/')[0]
                        table_name = f"esphome_{device_name.replace('-', '_')}"
                        if table_name not in states_by_table:
                            states_by_table[table_name] = []
                        states_by_table[table_name].append((time.strftime('%Y-%m-%d %H:%M:%S%z'), topic, payload, json.dumps({"topic": topic, "payload": payload})))

                    for table_name, values in states_by_table.items():
                        # Ensure hypertable exists for the device
                        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (time TIMESTAMPTZ NOT NULL, topic TEXT, value TEXT, raw_payload JSONB);")
                        cursor.execute(f"SELECT create_hypertable('{table_name}', 'time', if_not_exists => TRUE);")

                        psycopg2.extras.execute_values(cursor,
                            f"INSERT INTO {table_name} (time, topic, value, raw_payload) VALUES %s;",
                            values
                        )
                        logger.info(f"Wrote {len(values)} state messages to {table_name}.")
                    state_batch.clear()


            conn.commit()
            time.sleep(1.0) # Flush interval
        except psycopg2.Error as e:
            logger.error(f"❌ Database error: {e}. Attempting to reconnect...")
            if conn: conn.close()
            conn = None
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred in the DB writer thread: {e}")
            time.sleep(5)

    if conn: conn.close(); logger.info("Database connection closed.")


def on_mqtt_connect(client, userdata, flags, rc):
    """Callback for when the MQTT client connects."""
    if rc == 0:
        client.subscribe("homeassistant/#")
        client.subscribe("esphome/discover/#")
        client.subscribe("+/status")
        client.subscribe("+/+/+/state")
        client.subscribe("+/+/+/command")
        logger.info("✅ Connected to MQTT Broker and subscribed to topics.")
    else:
        logger.error(f"❌ Failed to connect to MQTT, return code {rc}")

def on_mqtt_message(client, userdata, msg):
    """Callback that routes messages to the correct queue based on topic."""
    try:
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")

        if "esphome/discover" in topic:
            discovery_queue.put(json.loads(payload_str))
        elif "homeassistant" in topic and topic.endswith("/config"):
             # Assuming device_name is the first part of the identifier string "device_name-mac"
            entity_data = json.loads(payload_str)
            if 'device' in entity_data and 'identifiers' in entity_data['device']:
                entity_queue.put(entity_data)
        elif topic.endswith("/status"):
            status_queue.put((topic, payload_str))
        elif topic.endswith("/state"):
            state_queue.put((topic, payload_str))
        elif topic.endswith("/command"):
            command_queue.put((topic, payload_str))

    except json.JSONDecodeError:
        logger.warning(f"⚠️ Could not decode JSON from topic {msg.topic}")
    except Exception as e:
        logger.error(f"❌ Error processing message from topic {msg.topic}: {e}")

@app.command()
def start():
    """
    Starts the ingestor service using the saved configuration.
    """
    setup_logging()
    if not config_path.exists():
        logger.error("Configuration file not found!")
        typer.echo(f"Please run 'mqtt-ingestor configure' first.")
        raise typer.Abort()

    global CONFIG
    with open(config_path, "r") as f:
        CONFIG = json.load(f)

    logger.info("--- Starting ESPHome Ingestor Service ---")
    writer = threading.Thread(target=db_writer_thread, daemon=True)
    writer.start()

    mqtt_config = CONFIG.get('mqtt', {})
    mqtt_client = mqtt.Client(client_id=f"python-ingestor-{os.getpid()}")
    mqtt_client.username_pw_set(mqtt_config.get('username'), mqtt_config.get('password'))
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message

    try:
        logger.info("Connecting to MQTT broker...")
        mqtt_client.connect(mqtt_config.get('host'), mqtt_config.get('port'), 60)
        mqtt_client.loop_start()
        # Keep the main thread alive
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down script.")
    except Exception as e:
        logger.error(f"❌ An error occurred with the MQTT client: {e}")
    finally:
        stop_event.set()
        if mqtt_client.is_connected():
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        writer.join()
        logger.info("Script finished.")

if __name__ == "__main__":
    app()
