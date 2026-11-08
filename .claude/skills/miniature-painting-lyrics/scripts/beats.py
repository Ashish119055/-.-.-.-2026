#!/usr/bin/env python3
"""Find beats (and strong beats) in a music MP3 with librosa.

usage: python3 beats.py MUSIC.mp3 OUT.json
needs: pip install librosa
"""
import json, sys
import numpy as np, librosa

audio, out = sys.argv[1:3]
y, sr = librosa.load(audio, sr=22050, mono=True)
tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
onset = librosa.onset.onset_strength(y=y, sr=sr)
times = librosa.frames_to_time(frames, sr=sr)
strength = onset[np.clip(frames, 0, len(onset) - 1)]
cut = np.percentile(strength, 75) if len(strength) else 0
beats = [{"t": round(float(t), 3), "strong": bool(s >= cut)} for t, s in zip(times, strength)]
res = {"duration": round(len(y) / sr, 3), "tempo": round(float(np.atleast_1d(tempo)[0]), 1), "beats": beats}
json.dump(res, open(out, "w"), indent=2)
print(f'tempo {res["tempo"]} bpm, {len(beats)} beats, duration {res["duration"]} s')
print("strong beats:", [b["t"] for b in beats if b["strong"]])
