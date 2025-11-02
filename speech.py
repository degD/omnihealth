import sounddevice as sd
import vosk
import queue
import json
import sys

inputQueue = queue.Queue()
sampleRate = 16_000
modelPath = "vosk-model-small-en-us-0.15"

commands = [
  "hello",
  "power on",
  "power off",
  "light one on",
  "light one off",
  "light two on",
  "light two off",
  "light three on",
  "light three off",
  "light all on",
  "light all off",
  "window one open",
  "window one close",
  "window two open",
  "window two close",
]

def callback(indata, frames, time, status):
  if status:
    print(status, file=sys.stderr)
  inputQueue.put(bytes(indata))

try:

  model = vosk.Model(modelPath)
  recognizer = vosk.KaldiRecognizer(model, sampleRate, json.dumps(commands))

  with sd.RawInputStream(
    samplerate=sampleRate, 
    blocksize=sampleRate//2,
    dtype="int16",
    channels=1,
    callback=callback
  ):
    
    print("\nStarting...")
    while True:
      data = inputQueue.get()
      print("Transcribing...")
      if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result())
        if result["text"] in commands:
          print(f"Command: {result['text']}")

        else:
          partial = json.loads(recognizer.PartialResult())
          if partial["text"] in commands:
            print(f"Command: {partial['text']}")

except KeyboardInterrupt:
  print("\nStopping...")
  sys.exit(0)
except Exception as e:
  print(f"An error occured: {e}")
  sys.exit(1)