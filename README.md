# ESPHome Dynamic YAML Generator 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python script that automates the creation of ESPHome configuration files for a specific hardware setup (ESP32-S3 with a Modbus RTU module). It generates unique device names and entity IDs, injects credentials securely, and integrates directly with the ESPHome command-line interface (CLI) to compile or flash your device.

This tool is perfect for rapidly deploying multiple, similar devices without the tedious process of manually copying, pasting, and editing YAML files.



***

## ✨ Key Features

* **Automatic YAML Generation**: Creates a complete, ready-to-use `.yaml` file from a template.
* **Unique ID Generation**: Uses UUIDs to generate safe, unique names and IDs for the device and all its components (switches, sensors, etc.), preventing conflicts.
* **Interactive Setup**: Prompts the user for Wi-Fi and MQTT credentials, with password fields hidden for security.
* **Command-Line Automation**: All credentials can be passed as command-line arguments, making it ideal for use in automated scripts.
* **Direct ESPHome Integration**: Can automatically trigger `esphome compile`, `esphome run`, or `esphome config` on the newly created file, streamlining the entire workflow.
* **Built for a Specific Stack**: Tailored for an **ESP32-S3** board with a **Modbus RTU D-series module**, including GPIO switches, a buzzer, and more.

***

## 🔧 Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3**: The script is written in Python.
2.  **ESPHome CLI**: The script relies on the `esphome` command to validate, compile, and upload the configuration. You can install it with:
    ```bash
    pip install esphome
    ```

***

## 🚀 Getting Started

### 1. Installation

Clone the repository or download the `generator.py` script to your local machine.

```bash
git clone <your-repository-url>
cd <your-repository-name>
