# tts_piper.py — Brazilian Portuguese narration with Piper, in the tools environment.
# Usage: python tts_piper.py job.json   (job: {"model": ".onnx", "length_scale": 1.0, "items": [{"text", "out"}]})
import json
import sys
import wave

from piper import PiperVoice
from piper.config import SynthesisConfig

job = json.loads(open(sys.argv[1], encoding="utf-8").read())
voice = PiperVoice.load(job["model"])
config = SynthesisConfig(length_scale=float(job.get("length_scale", 1.0)))
for item in job["items"]:
    with wave.open(item["out"], "wb") as out:
        voice.synthesize_wav(item["text"], out, syn_config=config)
print(f"{len(job['items'])} trechos")
