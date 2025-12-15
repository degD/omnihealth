"""
Live Vosk Testing Script
Tests voice recognition accuracy with a random subset of commands
User speaks into microphone and results are compared against expected commands
"""

import sounddevice as sd
import vosk
import queue
import json
import sys
import random
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

sampleRate = 16_000
modelPath = "vosk-model-small-en-us-0.15"

# All available commands (from speech-pi.py)
ALL_COMMANDS = [
    "hello",
    "turn on one",
    "turn on two",
    "turn on three",
    "turn on one two",
    "turn on one three",
    "turn on two three",
    "turn on one two three",
    "turn off one",
    "turn off two",
    "turn off three",
    "turn off one two",
    "turn off one three",
    "turn off two three",
    "turn off one two three",
    "open door",
    "close door",
    "open window",
    "close window",
    "set door zero percent",
    "set door twenty five percent",
    "set door fifty percent",
    "set door seventy five percent",
    "set door one hundred percent",
    "set window zero percent",
    "set window twenty five percent",
    "set window fifty percent",
    "set window seventy five percent",
    "set window one hundred percent",
    "turn on ac",
    "turn off ac",
    "turn off air conditioning",
    "set air conditioning twenty degrees",
    "set air conditioning twenty five degrees",
    "set air conditioning thirty degrees",
]

# Number of random commands to test
NUM_TEST_COMMANDS = 10

# Recording duration per command (seconds)
RECORDING_DURATION = 6

# ============================================================================
# GLOBAL STATE
# ============================================================================

inputQueue = queue.Queue()
is_recording = False

# ============================================================================
# AUDIO CALLBACK
# ============================================================================

def callback(indata, frames, time_info, status):
    """Callback for audio input stream."""
    if status:
        print(f"Audio status: {status}", file=sys.stderr)
    if is_recording:
        inputQueue.put(bytes(indata))

# ============================================================================
# TESTING FUNCTIONS
# ============================================================================

def record_and_transcribe(recognizer, expected_command, test_number, total_tests):
    """Record audio for specified duration and transcribe."""
    global is_recording
    
    print("\n" + "="*70)
    print(f"TEST {test_number}/{total_tests}")
    print("="*70)
    print(f"\n📢 Please say: \"{expected_command}\"")
    print(f"\nRecording will start in 2 seconds...")
    time.sleep(2)
    
    # Clear the queue
    while not inputQueue.empty():
        inputQueue.get()
    
    print("🎤 Recording... (speak now!)")
    is_recording = True
    
    # Record for specified duration
    start_time = time.time()
    recognized_text = ""
    
    while time.time() - start_time < RECORDING_DURATION:
        try:
            data = inputQueue.get(timeout=0.1)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if result.get("text"):
                    recognized_text = result["text"]
            else:
                partial = json.loads(recognizer.PartialResult())
                if partial.get("text"):
                    # Show partial result
                    print(f"  Partial: {partial['text']}", end='\r')
        except queue.Empty:
            continue
    
    is_recording = False
    
    # Get final result
    final_result = json.loads(recognizer.FinalResult())
    if final_result.get("text"):
        recognized_text = final_result["text"]
    
    print("\n")  # Clear the partial result line
    
    return recognized_text

def compare_results(expected, recognized):
    """Compare expected command with recognized text."""
    expected = expected.lower().strip()
    recognized = recognized.lower().strip()
    
    is_correct = expected == recognized
    
    if is_correct:
        status = "✅ PASS"
    else:
        status = "❌ FAIL"
    
    print(f"Expected:   \"{expected}\"")
    print(f"Recognized: \"{recognized}\"")
    print(f"Result:     {status}")
    
    return is_correct

# ============================================================================
# MAIN TEST LOOP
# ============================================================================

def main():
    """Run live voice recognition tests."""
    print("\n" + "="*70)
    print("LIVE VOSK VOICE RECOGNITION TEST")
    print("="*70)
    print("\nThis test will randomly select commands for you to speak.")
    print("Make sure your microphone is working and positioned correctly.")
    print("Speak clearly and at a normal pace.\n")
    
    # Select random subset of commands
    test_commands = random.sample(ALL_COMMANDS, min(NUM_TEST_COMMANDS, len(ALL_COMMANDS)))
    
    print(f"Selected {len(test_commands)} random commands to test.\n")
    input("Press ENTER to start testing...")
    
    # Initialize Vosk
    print("\nLoading Vosk model...")
    try:
        model = vosk.Model(modelPath)
        recognizer = vosk.KaldiRecognizer(model, sampleRate, json.dumps(ALL_COMMANDS))
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading Vosk model: {e}")
        print(f"Make sure the model exists at: {modelPath}")
        sys.exit(1)
    
    # Test results tracking
    results = []
    
    try:
        with sd.RawInputStream(
            samplerate=sampleRate,
            blocksize=sampleRate // 2,
            dtype="int16",
            channels=1,
            callback=callback
        ):
            # Run tests
            for i, command in enumerate(test_commands, 1):
                recognized = record_and_transcribe(recognizer, command, i, len(test_commands))
                is_correct = compare_results(command, recognized)
                
                results.append({
                    "expected": command,
                    "recognized": recognized,
                    "correct": is_correct
                })
                
                # Reset recognizer for next test
                recognizer = vosk.KaldiRecognizer(model, sampleRate, json.dumps(ALL_COMMANDS))
                
                if i < len(test_commands):
                    print("\nGet ready for the next command...")
                    time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError during testing: {e}")
    
    # Display summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["correct"])
    failed_tests = total_tests - passed_tests
    accuracy = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTotal tests:  {total_tests}")
    print(f"Passed:       {passed_tests} ✅")
    print(f"Failed:       {failed_tests} ❌")
    print(f"Accuracy:     {accuracy:.1f}%")
    
    # Show failed tests
    if failed_tests > 0:
        print("\n" + "-"*70)
        print("FAILED TESTS:")
        print("-"*70)
        for i, r in enumerate(results, 1):
            if not r["correct"]:
                print(f"\nTest {i}:")
                print(f"  Expected:   \"{r['expected']}\"")
                print(f"  Recognized: \"{r['recognized']}\"")
    
    print("\n" + "="*70)
    print("Testing complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
