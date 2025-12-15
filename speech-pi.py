import sounddevice as sd
import vosk
import queue
import json
import sys
import re
import threading
import time
from gpiozero import LED, Servo

# ============================================================================
# WIRING GUIDE
# ============================================================================
#
# LIGHTS (LEDs) - 3x devices
# ─────────────────────────────────────────────────────────────────────────
# Each LED connection:
#   GPIO Pin ──[220Ω resistor]──[LED anode (+, longer leg)]
#   [LED cathode (-, shorter leg)] ──[GND]
#
#   Light 1: GPIO 17 ──[220Ω]──LED+ | LED- ──GND
#   Light 2: GPIO 27 ──[220Ω]──LED+ | LED- ──GND
#   Light 3: GPIO 22 ──[220Ω]──LED+ | LED- ──GND
#
# SERVOS - 2x devices
# ─────────────────────────────────────────────────────────────────────────
# Each servo connection (3 wires):
#   Servo Signal (yellow/orange) ──> GPIO Pin (PWM)
#   Servo Power (red)            ──> 5V (RPi 5V pin)
#   Servo Ground (brown/black)   ──> GND (common ground)
#
#   Door Servo:   Signal ──GPIO 18 | Power ──5V | GND ──GND
#   Window Servo: Signal ──GPIO 19 | Power ──5V | GND ──GND
#
# NOTE: Using RPi's 5V pin is acceptable for demo/short-term use, but
# for stability and reliability, a separate 5V power supply (≥2A) is
# STRONGLY RECOMMENDED. Servos draw ~500mA each and can cause voltage
# drops that affect RPi stability. If experiencing crashes or reboots,
# switch to external 5V supply and ensure common GND between supplies.
#
# STATUS LED - 1x device
# ─────────────────────────────────────────────────────────────────────────
# Status LED connection:
#   GPIO Pin ──[220Ω resistor]──[LED anode (+, longer leg)]
#   [LED cathode (-, shorter leg)] ──[GND]
#
#   Status LED: GPIO 23 ──[220Ω]──LED+ | LED- ──GND
#
# GND CONNECTIONS (Common Ground)
# ─────────────────────────────────────────────────────────────────────────
# Connect all GND paths to a common GND rail on breadboard:
#   - All LED cathodes
#   - All servo GND wires
#   - Status LED cathode
#   - RPi GND pin (GPIO pin 6, 9, 14, 20, 25, 30, or 34)
#
# 5V CONNECTIONS
# ─────────────────────────────────────────────────────────────────────────
# RPi 5V pin (pin 2 or 4) supplies:
#   - Servo power (both Door and Window servos)
#   - Consider adding 470µF capacitor across servo power for stability
#

# ============================================================================
# GPIO PIN CONSTANTS
# ============================================================================

# Lights (LEDs)
PIN_LIGHT_1 = 17
PIN_LIGHT_2 = 27
PIN_LIGHT_3 = 22

# Servos
PIN_SERVO_DOOR = 18
PIN_SERVO_WINDOW = 19

# Status LED
PIN_STATUS_LED = 23

# ============================================================================
# DEVICE CONFIGURATION CONSTANTS
# ============================================================================

# Servo angle mappings (percentage to actual angle)
DOOR_MAX_ANGLE = 100  # 100% = 100 degrees
WINDOW_MAX_ANGLE = 60  # 100% = 60 degrees

# ============================================================================
# AUDIO CONFIGURATION
# ============================================================================

inputQueue = queue.Queue()
sampleRate = 16_000
modelPath = "vosk-model-small-en-us-0.15"

# Predefined commands for Vosk
commands = [
  "hello",
  "turn on 1",
  "turn on 2",
  "turn on 3",
  "turn on 1 2",
  "turn on 1 3",
  "turn on 2 3",
  "turn on 1 2 3",
  "turn off 1",
  "turn off 2",
  "turn off 3",
  "turn off 1 2",
  "turn off 1 3",
  "turn off 2 3",
  "turn off 1 2 3",
  "open door",
  "close door",
  "open window",
  "close window",
  "set door 0 percent",
  "set door 25 percent",
  "set door 50 percent",
  "set door 75 percent",
  "set door 100 percent",
  "set window 0 percent",
  "set window 25 percent",
  "set window 50 percent",
  "set window 75 percent",
  "set window 100 percent",
  "turn on ac",
  "turn off ac",
  "turn off air conditioning",
  "set air conditioning 20 degrees",
  "set air conditioning 25 degrees",
  "set air conditioning 30 degrees",
]

# ============================================================================
# GLOBAL STATE
# ============================================================================

status_led = None
lights = {}
servos = {}
current_state = "waiting"  # "waiting" or "transcribing"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def initialize_gpio():
    """Initialize all GPIO devices."""
    global status_led, lights, servos
    
    status_led = LED(PIN_STATUS_LED)
    lights = {
        1: LED(PIN_LIGHT_1),
        2: LED(PIN_LIGHT_2),
        3: LED(PIN_LIGHT_3),
    }
    servos = {
        "door": Servo(PIN_SERVO_DOOR),
        "window": Servo(PIN_SERVO_WINDOW),
    }
    
    print("GPIO devices initialized")
    status_led.on()

def cleanup_gpio():
    """Cleanup all GPIO devices."""
    if status_led:
        status_led.off()
    for light in lights.values():
        light.off()
    for servo in servos.values():
        servo.mid()
    print("GPIO cleanup complete")

def set_status_led_state(new_state):
    """Update status LED state (waiting or transcribing)."""
    global current_state
    current_state = new_state
    
    if new_state == "waiting":
        status_led.on()
    elif new_state == "transcribing":
        # Start blinking in background
        blink_thread = threading.Thread(target=blink_status_led, daemon=True)
        blink_thread.start()

def blink_status_led():
    """Blink status LED rapidly (300ms interval) during transcription."""
    while current_state == "transcribing":
        status_led.toggle()
        time.sleep(0.15)
    status_led.on()  # Ensure it's on after transcribing

def extract_light_ids(command):
    """Extract light IDs from command like 'turn on 1 2 3' or 'turn off 1'."""
    numbers = re.findall(r'\d+', command)
    # Remove duplicates and filter for valid light IDs (1-3)
    light_ids = set(int(n) for n in numbers if int(n) in [1, 2, 3])
    return sorted(list(light_ids))

def extract_percentage(command):
    """Extract percentage value from command like 'set door 45 percent'."""
    match = re.search(r'(\d+)\s+percent', command)
    if match:
        return int(match.group(1))
    return None

def extract_temperature(command):
    """Extract temperature value from command like 'set air conditioning 30 degrees'."""
    match = re.search(r'(\d+)\s+degrees', command)
    if match:
        return int(match.group(1))
    return None

# ============================================================================
# DEVICE CONTROL FUNCTIONS
# ============================================================================

def control_lights(light_ids, state):
    """Turn lights on or off."""
    for light_id in light_ids:
        if light_id in lights:
            if state == "on":
                lights[light_id].on()
                print(f"Light {light_id} turned ON")
            elif state == "off":
                lights[light_id].off()
                print(f"Light {light_id} turned OFF")

def control_servo(servo_name, action, percentage=None):
    """Control servo (door or window)."""
    if servo_name not in servos:
        return
    
    servo = servos[servo_name]
    
    if action == "open":
        servo.max()
        print(f"{servo_name.capitalize()} opened (100%)")
    elif action == "close":
        servo.min()
        print(f"{servo_name.capitalize()} closed (0%)")
    elif action == "set" and percentage is not None:
        # Map percentage (0-100) to servo angle range (-90 to 90 in gpiozero)
        if servo_name == "door":
            angle = (percentage / 100) * DOOR_MAX_ANGLE - 90
        else:  # window
            angle = (percentage / 100) * WINDOW_MAX_ANGLE - 90
        
        servo.value = angle / 90  # gpiozero uses -1 to 1 range
        print(f"{servo_name.capitalize()} set to {percentage}%")

def control_ac(action, temperature=None):
    """Control air conditioning (dummy - just print)."""
    if action == "on":
        print("AC turned ON")
    elif action == "off":
        print("AC turned OFF")
    elif action == "set" and temperature is not None:
        print(f"AC set to {temperature} degrees")

# ============================================================================
# COMMAND PROCESSING
# ============================================================================

def process_command(command):
    """Parse and execute a recognized command."""
    command = command.lower().strip()
    
    if command == "hello":
        print("Hello! How can I help?")
    
    # Light commands
    elif command.startswith("turn on"):
        light_ids = extract_light_ids(command)
        if light_ids:
            control_lights(light_ids, "on")
    
    elif command.startswith("turn off"):
        light_ids = extract_light_ids(command)
        if light_ids:
            control_lights(light_ids, "off")
    
    # Door commands
    elif command == "open door":
        control_servo("door", "open")
    elif command == "close door":
        control_servo("door", "close")
    elif command.startswith("set door"):
        percentage = extract_percentage(command)
        if percentage is not None:
            control_servo("door", "set", percentage)
    
    # Window commands
    elif command == "open window":
        control_servo("window", "open")
    elif command == "close window":
        control_servo("window", "close")
    elif command.startswith("set window"):
        percentage = extract_percentage(command)
        if percentage is not None:
            control_servo("window", "set", percentage)
    
    # AC commands
    elif "air conditioning" in command or "ac" in command:
        if "turn on" in command:
            control_ac("on")
        elif "turn off" in command:
            control_ac("off")
        elif "set" in command:
            temperature = extract_temperature(command)
            if temperature is not None:
                control_ac("set", temperature)

# ============================================================================
# AUDIO CALLBACK
# ============================================================================

def callback(indata, frames, time, status):
    """Callback for audio input stream."""
    if status:
        print(status, file=sys.stderr)
    inputQueue.put(bytes(indata))

# ============================================================================
# MAIN LOOP
# ============================================================================

try:
    initialize_gpio()
    
    model = vosk.Model(modelPath)
    recognizer = vosk.KaldiRecognizer(model, sampleRate, json.dumps(commands))
    
    with sd.RawInputStream(
        samplerate=sampleRate,
        blocksize=sampleRate // 2,
        dtype="int16",
        channels=1,
        callback=callback
    ):
        
        print("\nStarting voice recognition...")
        print("Listening for commands...\n")
        set_status_led_state("waiting")
        
        while True:
            data = inputQueue.get()
            set_status_led_state("transcribing")
            
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if result.get("text"):
                    recognized_command = result["text"]
                    print(f"Recognized: {recognized_command}")
                    process_command(recognized_command)
            else:
                partial = json.loads(recognizer.PartialResult())
                if partial.get("text") and partial["text"] in commands:
                    recognized_command = partial["text"]
                    print(f"Recognized: {recognized_command}")
                    process_command(recognized_command)
            
            set_status_led_state("waiting")

except KeyboardInterrupt:
    print("\n\nStopping...")
    set_status_led_state("waiting")
    cleanup_gpio()
    sys.exit(0)
except Exception as e:
    print(f"An error occurred: {e}")
    cleanup_gpio()
    sys.exit(1)
