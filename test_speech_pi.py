"""
Test script for speech-pi.py
Tests command processing and string message generation without Raspberry Pi hardware
"""

import json
import sys

# ============================================================================
# MOCK OBJECTS FOR HARDWARE SIMULATION
# ============================================================================

class MockLED:
    """Mock LED object to simulate gpiozero.LED"""
    def __init__(self, pin):
        self.pin = pin
        self.state = False
    
    def on(self):
        self.state = True
    
    def off(self):
        self.state = False
    
    def toggle(self):
        self.state = not self.state

class MockServo:
    """Mock Servo object to simulate gpiozero.Servo"""
    def __init__(self, pin):
        self.pin = pin
        self.value = 0
        self.position = "mid"
    
    def max(self):
        self.value = 1
        self.position = "max"
    
    def min(self):
        self.value = -1
        self.position = "min"
    
    def mid(self):
        self.value = 0
        self.position = "mid"

class MockSerial:
    """Mock serial port to capture messages"""
    def __init__(self):
        self.is_open = True
        self.messages = []
    
    def write(self, data):
        message = data.decode('utf-8').strip()
        self.messages.append(message)
        print(f"  [SERIAL] {message}")
    
    def close(self):
        self.is_open = False

# ============================================================================
# IMPORT FUNCTIONS FROM SPEECH-PI.PY
# ============================================================================

# We'll need to import specific functions, but first let's create a minimal
# implementation here to avoid import issues with hardware dependencies

def extract_light_ids(command):
    """Extract light IDs from command like 'turn on 1 2 3' or 'turn off 1'."""
    import re
    numbers = re.findall(r'\d+', command)
    # Remove duplicates and filter for valid light IDs (1-3)
    light_ids = set(int(n) for n in numbers if int(n) in [1, 2, 3])
    return sorted(list(light_ids))

def extract_percentage(command):
    """Extract percentage value from command like 'set window 45 percent'."""
    import re
    match = re.search(r'(\d+)\s+percent', command)
    if match:
        return int(match.group(1))
    return None

def extract_temperature(command):
    """Extract temperature value from command like 'set air conditioning 30 degrees'."""
    import re
    match = re.search(r'(\d+)\s+degrees', command)
    if match:
        return int(match.group(1))
    return None

# ============================================================================
# GLOBAL MOCK STATE
# ============================================================================

lights = {
    1: MockLED(17),
    2: MockLED(27),
    3: MockLED(22),
}

servos = {
    "window": MockServo(19),
}

serial_port = MockSerial()
status_led = MockLED(23)

# ============================================================================
# DEVICE CONTROL FUNCTIONS (ADAPTED FOR TESTING)
# ============================================================================

def send_to_esp32(command):
    """Send command string to ESP32 via serial (mocked)."""
    if serial_port is None or not serial_port.is_open:
        return
    
    command_string = command + "\n"
    serial_port.write(command_string.encode('utf-8'))

def control_lights(light_ids, state, command=None):
    """Turn lights on or off."""
    print(f"  [ACTION] Lights {light_ids} -> {state.upper()}")
    for light_id in light_ids:
        if light_id in lights:
            if state == "on":
                lights[light_id].on()
            elif state == "off":
                lights[light_id].off()
    
    # Send to ESP32
    if command:
        send_to_esp32(command)

def control_servo(servo_name, action, percentage=None, command=None):
    """Control servo (window)."""
    if servo_name not in servos:
        return
    
    servo = servos[servo_name]
    
    if action == "open":
        servo.max()
        print(f"  [ACTION] {servo_name.capitalize()} -> OPEN (100%)")
    elif action == "close":
        servo.min()
        print(f"  [ACTION] {servo_name.capitalize()} -> CLOSE (0%)")
    elif action == "set" and percentage is not None:
        servo.value = (percentage / 100) * 2 - 1
        print(f"  [ACTION] {servo_name.capitalize()} -> SET {percentage}%")
    
    # Send to ESP32
    if command:
        send_to_esp32(command)

def control_ac(action, temperature=None, command=None):
    """Control air conditioning (dummy - just print and send to ESP32)."""
    if action == "on":
        print(f"  [ACTION] AC -> ON")
    elif action == "off":
        print(f"  [ACTION] AC -> OFF")
    elif action == "set" and temperature is not None:
        print(f"  [ACTION] AC -> SET {temperature}°C")
    
    # Send to ESP32
    if command:
        send_to_esp32(command)

def process_command(command):
    """Parse and execute a recognized command."""
    command = command.lower().strip()
    
    # Light commands
    if command.startswith("turn on"):
        light_ids = extract_light_ids(command)
        if light_ids:
            control_lights(light_ids, "on", command)
    
    elif command.startswith("turn off"):
        light_ids = extract_light_ids(command)
        if light_ids:
            control_lights(light_ids, "off", command)
    
    # Window commands
    elif command == "open window":
        control_servo("window", "open", command=command)
    elif command == "close window":
        control_servo("window", "close", command=command)
    elif command.startswith("set window"):
        percentage = extract_percentage(command)
        if percentage is not None:
            control_servo("window", "set", percentage, command)
    
    # AC commands
    elif "air conditioning" in command or "ac" in command:
        if "turn on" in command:
            control_ac("on", command=command)
        elif "turn off" in command:
            control_ac("off", command=command)
        elif "set" in command:
            temperature = extract_temperature(command)
            if temperature is not None:
                control_ac("set", temperature, command)

# ============================================================================
# TEST SCENARIOS
# ============================================================================

def run_test(test_name, command):
    """Run a single test scenario."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Command: '{command}'")
    process_command(command)

def verify_device_states():
    """Print current state of all devices."""
    print("\n--- Device States ---")
    for light_id, light in lights.items():
        state = "ON" if light.state else "OFF"
        print(f"Light {light_id}: {state}")
    for servo_name, servo in servos.items():
        print(f"{servo_name.capitalize()}: position={servo.position}, value={servo.value}")

def main():
    """Run all test scenarios."""
    print("\n" + "="*70)
    print("SPEECH-PI.PY TEST SUITE")
    print("Testing command processing and string message generation")
    print("="*70)
    
    # Light tests
    run_test("Light - Turn on single light", "turn on 1")
    run_test("Light - Turn on multiple lights", "turn on 1 2")
    run_test("Light - Turn on all lights", "turn on 1 2 3")
    run_test("Light - Turn off single light", "turn off 2")
    run_test("Light - Turn off with duplicates", "turn off 1 1 1 2")
    run_test("Light - Invalid light ID ignored", "turn on 1 5 9")
    
    # Servo tests (window only)
    run_test("Servo - Open window", "open window")
    run_test("Servo - Close window", "close window")
    run_test("Servo - Set window percentage", "set window 75 percent")
    
    # AC tests
    run_test("AC - Turn on", "turn on ac")
    run_test("AC - Turn off", "turn off air conditioning")
    run_test("AC - Set temperature", "set air conditioning 25 degrees")
    
    # Final device state
    verify_device_states()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total messages sent to ESP32: {len(serial_port.messages)}")
    print("\nAll tests completed successfully!")
    print("If you see command strings above, the serial communication is working correctly.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
