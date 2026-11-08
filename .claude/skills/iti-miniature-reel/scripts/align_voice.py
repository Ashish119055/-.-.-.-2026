#!/usr/bin/env python3
"""Force-align every Gujarati word of a voiceover with torchaudio MMS_FA.

usage: python3 align_voice.py VOICE.mp3 TRANSCRIPT.txt OUT.json
needs: pip install torch torchaudio uroman   (ffmpeg on PATH)
TRANSCRIPT.txt = exactly what is spoken, in Gujarati script.
"""
import json, re, subprocess, sys
import torch, torchaudio
import uroman as ur

audio, transcript, out = sys.argv[1:4]
bundle = torchaudio.pipelines.MMS_FA
sr = bundle.sample_rate

# decode with ffmpeg -> 16 kHz mono float
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-ac", "1", "-ar", str(sr),
                      "-f", "f32le", "-"], capture_output=True, check=True).stdout
wave = torch.frombuffer(bytearray(raw), dtype=torch.float32).unsqueeze(0)

text = open(transcript, encoding="utf-8").read()
words = [w for w in re.split(r"\s+", text.strip()) if w]
rom = ur.Uroman()
pairs = []
for w in words:
    r = re.sub(r"[^a-z']", "", rom.romanize_string(w, lcode="guj").lower())
    if r:
        pairs.append((w, r))
if not pairs:
    sys.exit("transcript has no alignable words")

model = bundle.get_model(with_star=False)
tokenizer, aligner = bundle.get_tokenizer(), bundle.get_aligner()
with torch.inference_mode():
    emission, _ = model(wave)
    spans = aligner(emission[0], tokenizer([r for _, r in pairs]))

ratio = wave.size(1) / emission.size(1) / sr
result = {"duration": round(wave.size(1) / sr, 3), "words": []}
for (w, r), s in zip(pairs, spans):
    result["words"].append({"word": w, "roman": r,
                            "start": round(s[0].start * ratio, 3),
                            "end": round(s[-1].end * ratio, 3),
                            "score": round(sum(t.score * len(t) for t in s) / sum(len(t) for t in s), 3)})
json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for x in result["words"]:
    print(f'{x["start"]:6.2f}–{x["end"]:6.2f}  {x["word"]}  ({x["score"]})')
