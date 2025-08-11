# ESPHome MQTT to TimescaleDB Ingestor

A robust Python service that listens for ESPHome data on an MQTT broker and persists it into a structured, multi-table TimescaleDB database.

This project is designed to work with the standard ESPHome and Home Assistant discovery protocols, handling various message types including device discovery, entity configurations, real-time state updates, and commands.

## Features

* Connects to an MQTT broker and subscribes to all relevant ESPHome and Home Assistant topics.
* Intelligently processes and stores five distinct types of messages.
* Automatically creates the necessary database tables on the first run.
* Uses a multi-threaded, queue-based architecture for high performance and resilience.
* Supports intelligent batch processing for efficient database writes.

## Installation

Install the package directly from PyPI:

```bash
pip install esphome-mqtt-timescaledb-ingestor
```

## Usage

This package includes an interactive command-line interface (CLI) to help you get started.

### 1. Initial Configuration

After installing the package, run the `configure` command. This will launch an interactive setup wizard that will ask for your MQTT and database credentials and save them to a configuration file.

```bash
mqtt-ingestor configure
```

You will be prompted for the following:
-   MQTT Broker Host
-   MQTT Broker Port
-   MQTT Username & Password
-   Database Host
-   Database Port
-   Database Name
-   Database User & Password

### 2. Start the Ingestor Service

Once you have configured your credentials, you can start the ingestor service:

```bash
mqtt-ingestor start
```

The service will load your saved configuration and begin listening for messages.

## Testing

To run the tests, clone the repository, install the development dependencies, and run pytest:

```bash
git clone [https://github.com/paandayankur/mqtt-to-timescaledb-ingester.git](https://github.com/paandayankur/mqtt-to-timescaledb-ingester.git)
cd mqtt-to-timescaledb-ingester
poetry install --with dev
poetry run pytest
```

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
