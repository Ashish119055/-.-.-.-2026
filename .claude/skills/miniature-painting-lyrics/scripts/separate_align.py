#!/usr/bin/env python3
"""Separate the vocals with demucs, then force-align every lyric word on the vocal track (torchaudio MMS_FA).

usage: python3 separate_align.py SONG.mp3 LYRICS.txt OUT_timing.json [--lang hin] [--vocals VOCALS.wav]
needs: pip install demucs soundfile torch torchaudio uroman   (ffmpeg on PATH)
LYRICS.txt: one sung line per text line, exactly as the user wrote them (Devanagari). Blank lines ignored.
Output words carry their line index, so cards can refer to them. Never edit the timings by hand.
"""
import json, os, re, subprocess, sys
import torch, torchaudio
import uroman as ur

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
song, lyrics, out = args[:3]
lang = opt("--lang", "hin")
vocals = opt("--vocals")
if not vocals:
    sep = os.path.join(os.path.dirname(os.path.abspath(out)), "separated")
    subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", sep, song], check=True)
    vocals = os.path.join(sep, "htdemucs", os.path.splitext(os.path.basename(song))[0], "vocals.wav")
print("vocals:", vocals)

bundle = torchaudio.pipelines.MMS_FA
sr = bundle.sample_rate
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", vocals, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
wave = torch.frombuffer(bytearray(raw), dtype=torch.float32).unsqueeze(0)

rom = ur.Uroman()
items = []  # (line_idx, word, roman)
lines = [l.strip() for l in open(lyrics, encoding="utf-8") if l.strip()]
for li, line in enumerate(lines):
    for w in line.split():
        r = re.sub(r"[^a-z']", "", rom.romanize_string(w, lcode=lang).lower())
        if r:
            items.append((li, w, r))
if not items:
    sys.exit("no alignable words in lyrics")

model = bundle.get_model(with_star=False)
tok, aligner = bundle.get_tokenizer(), bundle.get_aligner()
with torch.inference_mode():
    emission, _ = model(wave)
    spans = aligner(emission[0], tok([r for _, _, r in items]))
ratio = wave.size(1) / emission.size(1) / sr
res = {"duration": round(wave.size(1) / sr, 3), "lines": lines, "words": []}
for i, ((li, w, r), s) in enumerate(zip(items, spans)):
    res["words"].append({"i": i, "line": li, "word": w, "roman": r,
                         "start": round(s[0].start * ratio, 3), "end": round(s[-1].end * ratio, 3),
                         "score": round(sum(t.score * len(t) for t in s) / sum(len(t) for t in s), 3)})
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
low = [x for x in res["words"] if x["score"] < 0.3]
for x in res["words"]:
    print(f'#{x["i"]:3d} L{x["line"]:2d} {x["start"]:7.2f}–{x["end"]:7.2f}  {x["word"]}  ({x["score"]})')
if low:
    print(f"WARNING: {len(low)} low-confidence words — check the lyrics match what is sung:", [x["word"] for x in low])
