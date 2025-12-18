# Speech-Command Recognition Demo with Vosk

## Project Overview

This project is a voice-controlled home automation system built with Raspberry Pi, Vosk speech recognition, and ESP32 integration. It enables hands-free control of lights, a servo (window), and air conditioning through natural language voice commands.

### Key Features
- **Offline Speech Recognition**: Uses Vosk for fast, accurate, offline voice recognition.
- **GPIO Control**: Controls 3 LEDs, 1 servo (window), and a status LED via Raspberry Pi GPIO.
- **ESP32 Integration**: Sends command strings via UART serial communication to ESP32 for mobile app integration.
- **Real-time Feedback**: Status LED provides visual feedback (solid when waiting, blinking during transcription).
- **Extensive Testing**: Includes hardware simulation and live voice recognition testing scripts.

## Setup Instructions

### Prerequisites
- **Raspberry Pi**: Any model with GPIO support (tested on Raspberry Pi 4).
- **Python**: Version 3.7 or higher.
- **Microphone**: USB or built-in microphone for voice input.
- **Hardware**: LEDs, resistors, servos, breadboard, and jumper wires (see Parts List).

### Installation Steps

1. **Clone or download the project**:
   ```bash
   cd ~/projects
   git clone https://gitlab.com/den.ege.der/gomulu-speech
   cd gomolu-speech
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   - On Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```
   - On Windows:
     ```bash
     .venv\Scripts\activate
     ```

4. **Install required packages**:
   ```bash
   pip install vosk sounddevice scipy gpiozero pyserial
   ```

5. **Download the Vosk model**:
   ```bash
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   ```

6. **Set up hardware connections** (see Parts, Connections, and Pins section).

7. **Enable UART on Raspberry Pi** (for ESP32 communication):
   - Edit `/boot/config.txt` and add:
     ```
     enable_uart=1
     ```
   - Disable serial console in `raspi-config`: `Interface Options → Serial Port → No (login shell) → Yes (serial hardware)`.
   - Reboot the Raspberry Pi.

## Usage Instructions

### Running the Main Script

1. **Activate the virtual environment** (if not already activated):
   ```bash
   source .venv/bin/activate
   ```

2. **Run the main script**:
   ```bash
   python speech-pi.py
   ```

3. **Speak commands**: The system will start listening for voice commands. Speak clearly into the microphone.

4. **Monitor status**: The status LED will be solid when waiting and blink rapidly during transcription.

5. **Stop the script**: Press `Ctrl+C` to stop the script and clean up GPIO resources.

### Running Test Scripts

#### Hardware Simulation Test
```bash
python test_speech_pi.py
```
This script validates command processing and string message generation without requiring hardware.

#### Live Voice Recognition Test
```bash
python test_vosk_live.py
```
This script tests live voice recognition accuracy with a random subset of commands. Follow the on-screen prompts to speak commands.

## Troubleshooting

### Microphone Not Working
- **Check device**: Run `python -m sounddevice` to list available audio devices.
- **Select device**: Set the default input device in your system settings or specify it in the script.
- **Test input**: Use `arecord -l` (Linux) or system settings to verify microphone input.

### Low Recognition Accuracy
- **Quiet environment**: Minimize background noise for better accuracy.
- **Clear pronunciation**: Speak clearly and at a moderate pace.
- **Microphone position**: Position the microphone close to your mouth (10-20 cm).
- **Adjust recording time**: Increase the recording duration in `test_vosk_live.py` if needed.

### GPIO Errors
- **Permissions**: Ensure you have permissions to access GPIO. Run with `sudo` if necessary or add user to `gpio` group:
  ```bash
  sudo usermod -a -G gpio $USER
  ```
- **Pin conflicts**: Verify no other processes are using the GPIO pins.
- **Wiring**: Double-check all connections match the wiring guide.

### Serial Communication Issues
- **UART not enabled**: Ensure UART is enabled in `/boot/config.txt` and serial console is disabled.
- **Port access**: Check permissions for `/dev/ttyAMA0` or run with `sudo`.
- **Baud rate mismatch**: Ensure ESP32 is configured for 115200 baud rate.
- **Test connection**: Use `screen /dev/ttyAMA0 115200` to test serial communication manually.

### Servo Issues
- **Power supply**: If servos jitter or don't move smoothly, use an external 5V power supply (2A or higher).
- **Common ground**: Ensure all grounds (RPi, servos, external power) are connected.
- **Angle limits**: Verify servo angle mappings in the script match your servo specifications.

## Parts, Connections, and Pins

### Parts List
- **LEDs**: 3x standard LEDs (any color)
- **Resistors**: 4x 220Ω resistors (for LEDs)
- **Servos**: 1x standard servo (window)
- **Status LED**: 1x standard LED (any color)
- **Raspberry Pi**: Any model with GPIO support
- **Breadboard**: For connections
- **Wires**: Jumper wires for connections

### Connections

#### LEDs
- **Light 1**: GPIO 17 → 220Ω resistor → LED anode (+) → LED cathode (-) → GND
- **Light 2**: GPIO 27 → 220Ω resistor → LED anode (+) → LED cathode (-) → GND
- **Light 3**: GPIO 22 → 220Ω resistor → LED anode (+) → LED cathode (-) → GND

#### Servos
- **Window Servo**:
  - Signal: GPIO 19
  - Power: 5V (RPi 5V pin)
  - Ground: GND

#### Status LED
- GPIO 23 → 220Ω resistor → LED anode (+) → LED cathode (-) → GND

### Notes
- Use a common GND rail on the breadboard for all GND connections.
- For servos, consider using an external 5V power supply for stability, especially if experiencing voltage drops.

## Commands and Documentation

### Supported Commands
The system supports the following voice commands:

#### Light Control
- **"turn on one"**: Turns on Light 1.
- **"turn on two"**: Turns on Light 2.
- **"turn on three"**: Turns on Light 3.
- **"turn on one two three"**: Turns on all lights.
- **"turn off one"**: Turns off Light 1.
- **"turn off two"**: Turns off Light 2.
- **"turn off three"**: Turns off Light 3.
- **"turn off one two three"**: Turns off all lights.

#### Window Control
- **"open window"**: Fully opens the window.
- **"close window"**: Fully closes the window.
- **"set window [percentage] percent"**: Sets the window to a specific percentage (e.g., "set window seventy five percent").

#### Air Conditioning Control
- **"turn on ac"**: Turns on the air conditioning.
- **"turn off ac"**: Turns off the air conditioning.
- **"set air conditioning [temperature] degrees"**: Sets the air conditioning to a specific temperature (e.g., "set air conditioning twenty five degrees").

### Notes
- Commands are case-insensitive.
- Ensure clear pronunciation for accurate recognition.
-- Percentages for window control must be in increments of 25% (0%, 25%, 50%, 75%, 100%).

## Testing

### Test Scripts

#### `test_speech_pi.py`
- **Purpose**: Simulates hardware and validates string message generation.
- **Features**:
  - Mock objects for LEDs, servos, and serial communication.
  - Tests command processing logic without requiring Raspberry Pi hardware.
  - Ensures correct command strings are generated for ESP32 communication.

#### `test_vosk_live.py`
- **Purpose**: Tests live voice recognition accuracy.
- **Features**:
  - Uses a random subset of predefined commands for testing.
  - Compares spoken commands against expected results.
  - Measures recognition accuracy and identifies potential issues.

### Notes
- Ensure the Vosk model (`vosk-model-small-en-us-0.15`) is downloaded and extracted before running `test_vosk_live.py`.
- Use a quiet environment for live voice testing to improve accuracy.
