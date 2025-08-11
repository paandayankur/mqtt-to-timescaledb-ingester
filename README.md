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


2. Usage
The script can be run in two ways: interactively or with command-line arguments.

Interactive Mode (Recommended for first-time use)
Simply run the script without any arguments. It will prompt you to enter the necessary credentials.

Bash

python generator.py
You will be asked for your Wi-Fi SSID/password and MQTT broker details. A new file, like esphome-device-a1b2c3d4e5f6.yaml, will be created, and the default config action will be run.

Command-Line Mode (For automation and power users)
You can provide all credentials and specify an action directly via command-line flags. This is useful for scripting deployments.

Bash

python generator.py \
  --wifi-ssid "YourWiFi_SSID" \
  --wifi-password "YourWiFiPassword" \
  --mqtt-broker "192.168.1.100" \
  --mqtt-port "1883" \
  --mqtt-user "mqtt_username" \
  --mqtt-pass "mqtt_password" \
  --action "run"
Available Actions (--action flag)
config (Default): Creates the YAML file and validates it with esphome config.

compile: Creates the YAML file and compiles the firmware with esphome compile.

run: Creates the YAML file, compiles, and uploads it to the device with esphome run.

⚙️ Customization
This script is built around a specific hardware configuration defined in the generate_yaml_config function. If your hardware is different (e.g., different GPIO pins, another type of sensor, or a different board), you can easily customize it.

Open generator.py in your favorite editor.

Navigate to the generate_yaml_config function.

Modify the YAML f-string:

Change board: esp32-s3-devkitc-1 to match your board.

Update the pin numbers for your GPIO switches or UART configuration.

Add or remove components (sensors, switches, etc.) as needed.

Remember to generate unique IDs using generate_safe_name() for any new entities you add!

📄 License
This project is licensed under the MIT License. See the LICENSE file for details.
