# ESPHome MQTT to TimescaleDB Multi-Table Ingestor 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

A robust and high-performance Python service designed to bridge the gap between your ESPHome devices and a powerful TimescaleDB database.

This script listens to a wide array of MQTT topics, intelligently decodes different message types (from device discovery to real-time state changes), and persists them into a structured, multi-table database schema. It's built for reliability and performance, using a multi-threaded, queue-based architecture to handle high volumes of IoT data without missing a beat.

## 🏛️ Architecture Overview

The ingestor acts as a central hub, listening to all communication from your ESPHome devices via an MQTT broker and organizing it neatly into your database.



```text
                                                     ┌──────────────────────────┐
                                                     │   discovery_data         │
                                                     │ (Device Metadata)        │
                                                     ├──────────────────────────┤
                               ┌──────────────────┐  │   entity                 │
                               │                  │  │ (Component Config)       │
┌──────────────┐   MQTT        │  Python Ingestor │  ├──────────────────────────┤
│ ESPHome      ├──────────────►│                  ├─►│   device_status          │
│ Devices      │   Broker      │  (This Script)   │  │ (Online/Offline Log)     │
└──────────────┘               │                  │  ├──────────────────────────┤
                               └──────────────────┘  │   command                │
                                                     │ (Sent Commands Log)      │
                                                     ├──────────────────────────┤
                                                     │   esphome_data (Hypertable)│
                                                     │ (Real-time State)        │
                                                     └──────────────────────────┘
## ✨ Key Features

* **Comprehensive Data Capture**: Ingests five distinct types of MQTT messages for a complete picture of your IoT ecosystem.
* **Structured Multi-Table Storage**: Organizes data logically across five different SQL tables, separating metadata from time-series state data.
* **TimescaleDB Hypertable Support**: Automatically creates and uses a TimescaleDB hypertable for efficient querying of real-time sensor data.
* **High Performance**: Utilizes a multi-threaded, queue-based architecture to decouple message reception from database writing, preventing data loss under high load.
* **Batch Processing**: Intelligently batches time-series data for efficient `INSERT` operations, significantly improving database performance.
* **Automatic Schema Setup**: Creates all necessary tables on its first run, simplifying deployment.
* **Resilient by Design**: Handles database and MQTT connection errors gracefully, with automatic reconnection attempts.
* **Easy Configuration**: All connection details and performance parameters are centralized at the top of the script for easy modification.

***

## 🗃️ Database Schema

The script automatically creates and manages the following five tables:

1.  **`discovery_data`**
    * Stores device metadata when an ESPHome device announces itself on the network.
    * **Columns**: `time`, `device_name` (Primary Key), `ip_address`, `mac_address`, `version`, `platform`, `board`, `network`, `raw_payload`.

2.  **`entity`**
    * Stores the configuration for each component (sensor, switch, etc.) as discovered via the Home Assistant discovery protocol.
    * **Columns**: `time`, `unique_id` (Primary Key), `device_name`, `component_type`, `name`, `state_topic`, `command_topic`, `raw_payload`.

3.  **`device_status`**
    * An audit trail of when devices connect and disconnect from the MQTT broker.
    * **Columns**: `time`, `device_name`, `status` ('online' or 'offline'), `raw_payload`.

4.  **`command`**
    * A log of all commands sent to devices through their MQTT command topics.
    * **Columns**: `time`, `device_id`, `component_id`, `command`, `raw_payload`.

5.  **`esphome_data`** (TimescaleDB Hypertable)
    * The core time-series table storing all real-time state updates from device components.
    * **Columns**: `time`, `device_id`, `sensor_name`, `value`, `attributes`.

***

## 🔧 Prerequisites

Before running the script, ensure you have the following:

1.  **Python 3.7+**
2.  **A running MQTT Broker** (e.g., Mosquitto).
3.  **A running PostgreSQL server with the TimescaleDB extension enabled.**
4.  **Required Python libraries**:
    ```bash
    pip install paho-mqtt psycopg2-binary
    ```

***

## 🚀 Setup & Usage

1.  **Clone the Repository / Download the Script**
    * Save the script as `python_mqtt_to_timescale_multi_table.py` on your server.

2.  **Configure the Script**
    * Open the script and edit the configuration variables at the top of the file to match your environment:
        * `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`
        * `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
    * Adjust `BATCH_SIZE` and `FLUSH_INTERVAL` if needed for performance tuning.

3.  **Set Up Database Permissions**
    * Ensure the `DB_USER` you configured has permissions to `CREATE` tables and `INSERT` data into the `DB_NAME` database.

4.  **Run the Script**
    * Execute the script from your terminal:
    ```bash
    python python_mqtt_to_timescale_multi_table.py
    ```
    * On the first run, it will connect to the database and create the five tables if they don't exist. It will then connect to the MQTT broker and begin ingesting data.

### Running as a Systemd Service (Recommended)

For continuous, reliable operation, it's best to run this script as a systemd service on Linux.

1.  Create a service file:
    ```bash
    sudo nano /etc/systemd/system/mqtt-ingestor.service
    ```

2.  Paste the following configuration, making sure to update the paths and username:
    ```ini
    [Unit]
    Description=MQTT to TimescaleDB Ingestor Service
    After=network.target

    [Service]
    User=your_linux_user
    Group=your_linux_group
    WorkingDirectory=/path/to/your/script
    ExecStart=/usr/bin/python3 /path/to/your/script/python_mqtt_to_timescale_multi_table.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  Enable and start the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable mqtt-ingestor.service
    sudo systemctl start mqtt-ingestor.service
    ```

4.  Check its status:
    ```bash
    sudo systemctl status mqtt-ingestor.service
    ```

***

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.
