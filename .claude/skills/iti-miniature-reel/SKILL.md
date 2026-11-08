---
name: iti-miniature-reel
description: Make a 10–15 s 9:16 Instagram reel for Government ITI Maninagar (Mechanic Diesel) in which an Indian miniature painting comes alive with no visible cuts — trainee's hands with a spanner → painted diesel engine → fire in the cylinder → trainee standing proud before a bus — with bold popping Gujarati text. Use when the user runs /iti-miniature-reel or attaches a Gujarati voiceover / music MP3 plus 2–3 Gujarati text lines for this reel.
argument-hint: "[voiceover-or-music.mp3] [Gujarati line 1 | line 2 | CTA]"
---

# ITI miniature reel (Mechanic Diesel, ITI Maninagar)

One continuous painted shot, 10–15 s, 1080×1920 @ 30 fps:
**hands + ring spanner (A) → miniature diesel engine (B) → flame inside the cylinder (C) → trainee proud in front of a GSRTC-style red-and-white bus (D).**

The user generates every image and clip themselves from the prompts below (Gemini, Google Flow / Veo).
**You** do everything else in code: cutting, timing, text, glow, grain, render — HTML canvas in headless
Chromium (Playwright, pre-installed) + ffmpeg. Helper scripts live in `scripts/` next to this file
(`${CLAUDE_SKILL_DIR}/scripts` — resolve it to `.claude/skills/iti-miniature-reel/scripts` if the variable is empty).

## Hard rules (every run)

1. **Only the user's generated images/clips go in the reel.** No stock, no AI generation by you, no drawn stand-ins.
2. **Missing input → stop and ask.** If the audio, the text lines, the voiceover transcript, the Gemini sheet
   (or frames A–D), or either Flow clip is missing/unreadable, ask for it. **Never use a placeholder**, test
   pattern, solid colour or a still in place of a clip.
3. **Contact sheet before the full render.** Show it and wait for an OK.
4. **Ask before overwriting any file.** The scripts refuse to overwrite; only pass `--force` after the user says yes.
5. **Text:** max 3 Gujarati lines; last line is the CTA. Every line scales 60 % → 110 % → settles 100 % with a
   yellow highlight bar sweeping behind it and a symbol beside it (🔧 ⚙️ 🔥 ✅). **Never plain fades.**
   Keep text out of the top 250 px, bottom 420 px and right 150 px.
6. Deliver **the 1080×1920 MP4 plus a 720p copy under 20 MB for WhatsApp.**

## Workspace

Work in `reels/iti-miniature-reel/<YYYY-MM-DD>/` inside the repo (create it; if it already exists, ask whether
to reuse it or make `<date>-2`). Layout:

```
audio.mp3  transcript.txt  timing.json  timeline.json
sheet.png  frames/A.png … D.png
clip1.mp4 (A→B)  clip2.mp4 (C→D)
stills/  overlay/  base.mp4  contact_sheet_frames.png  contact_sheet.png
iti-miniature-reel.mp4  iti-miniature-reel_whatsapp720.mp4
```

Copy the attachments in (ask before replacing an existing file). Install Python deps only when needed:
`pip install librosa` (music) or `pip install torch torchaudio uroman` (voiceover).

---

## Step 1 — Timing, story, table

**Decide the audio type.** If the user didn't say, run `ffprobe` and ask "voiceover or music?" when it isn't obvious.

- **Voiceover:** you need the exact spoken words in Gujarati script. If the attached text lines are not the full
  script, ask for the transcript. Save it as `transcript.txt`, then force-align every word with torchaudio MMS_FA:
  ```bash
  python3 scripts/align_voice.py audio.mp3 transcript.txt timing.json
  ```
  Words with a low score (< 0.3) or a gap that doesn't match listening — tell the user and re-check the transcript.
- **Music:** find the beats with librosa:
  ```bash
  python3 scripts/beats.py audio.mp3 timing.json
  ```

**Pick the duration (10–15 s)**: for voiceover, end 0.5–0.8 s after the last word (if speech runs past 15 s,
ask the user to trim/re-record — don't cut words); for music, end on a strong beat between 10 and 15 s.

**Plan the timeline** (`timeline.json`, used by every later step):

```json
{ "duration": 13.0, "fps": 30, "join": 6.5, "join_style": "flame",
  "lines": [
    {"text": "હાથમાં સ્પેનર, દિલમાં સપનું", "icon": "🔧", "t": 0.8},
    {"text": "એન્જિનની આગ સમજો",        "icon": "🔥", "t": 5.0},
    {"text": "ITI મણિનગર — પ્રવેશ ચાલુ", "icon": "✅", "t": 9.8, "cta": true} ] }
```

- `t` = the line's pop: the aligned start of its first spoken word (voiceover) or the nearest strong beat (music).
- `join` = the hidden seam between clip 1 (ends on B) and clip 2 (starts on C), ≈ the middle; snap it to a
  strong beat or a pause between words. `join_style`: `flame` (default — it lands on the cylinder fire) or `bloom` (watercolour bloom).
- Icons: 🔧 hands/spanner, ⚙️ engine, 🔥 fire, ✅ CTA. Strip a trailing ✅ from the CTA text — the icon carries it.
- If the user gave no CTA, propose `ITI મણિનગર — પ્રવેશ ચાલુ ✅` and confirm.

**Show the user** a one-line story and a table, then continue:

> **Story:** A trainee's hands tighten a bolt, the painting flows into a diesel engine, its cylinder bursts into golden fire, and the light becomes the trainee standing proud as a mechanic before a state bus.

| Second | Picture | Text line |
|---|---|---|
| 0.0–3.2 | A — hands, ring spanner, push-in | 0.8 🔧 line 1 pops |
| 3.2–6.5 | B — miniature diesel engine | 5.0 ⚙️/🔥 line 2 pops |
| 6.5 | flame glow hides the join | — |
| 6.5–9.5 | C — fuel-spray flame → whip pan | — |
| 9.5–13.0 | D — crane up to trainee + bus | 9.8 ✅ CTA pops |

(Fill with the real times.)

## Step 2 — ONE Gemini image prompt, then cut the sheet

Give exactly this prompt (one code block, copy-ready):

```
A single vertical 9:16 image divided into a 2×2 grid of four equal 9:16 panels — A top-left, B top-right, C bottom-left, D bottom-right — separated by thin straight black lines. No text, letters, numbers, captions, logos, labels or watermarks anywhere.
Style for all four panels: traditional Indian miniature painting, Rajasthani-Mughal gouache on handmade paper, fine brush outlines, jewel colours (ultramarine, marigold, rose, cream), soft visible paper grain, flat ornamental perspective. The same young trainee looks identical wherever he appears.
Panel A: close-up of a young Gujarati trainee's hands in a blue ITI uniform holding a ring spanner over handmade paper.
Panel B: a diesel engine painted in miniature style — cylinder block, injector and flywheel clearly visible — in warm workshop light.
Panel C: extreme close-up inside the engine cylinder — the piston at the top of its stroke and a golden fuel-spray flame in the centre against deep indigo.
Panel D: low angle — the same trainee in his blue uniform standing proud in front of a red-and-white Indian state transport bus, sunrise behind him, a marigold ornamental border around this panel.
Highest resolution available. Keep every panel exactly 9:16 and the dividing lines thin and straight.
```

Tell the user to download it at full resolution and attach it. Then:

```bash
python3 scripts/cut_grid.py sheet.png frames      # -> frames/A.png … D.png, 1080×1920 each
```

Check the printout: each panel's aspect should be ≈ 0.5625; if a divider was missed (aspect far off) or the sheet
contains text, tell the user and ask for a regenerated sheet — don't hand-patch it. Look at A–D yourself and flag
anything off-brief (wrong bus colours, extra hands, text). Upscale above ×2.5 will look soft; mention it.

**First contact sheet (frames + text):**
```bash
node scripts/render_overlay.js timeline.json stills --times <each t+0.45>,<join>,<duration-0.3>
python3 scripts/assemble.py sheet timeline.json stills contact_sheet_frames.png --frames frames
```
Show `contact_sheet_frames.png` (cyan box = text-safe area). Fix text/timing if the user asks.

## Step 3 — Two Google Flow prompts (Frames to Video, Veo, 9:16)

Tell the user: Google Flow → **Frames to Video**, aspect **9:16**, upload the first and last frame shown, paste the prompt, generate, download the best take as MP4.

**Clip 1 — first frame `A.png`, last frame `B.png`:**
```
A living Indian miniature painting in Rajasthani-Mughal gouache on handmade paper. The trainee's hands in a blue ITI uniform tighten a bolt with the ring spanner, a firm quarter turn. The camera makes a slow, steady push-in. The painted paper itself flows and unfolds like liquid gouache, the brush lines redrawing themselves until the hands and paper become the miniature diesel engine with cylinder block, injector and flywheel in warm workshop light. Smooth continuous motion, gentle parallax, jewel colours ultramarine, marigold, rose and cream. No text, no speech, no music, keep the painted paper texture, no hard cuts.
```

**Clip 2 — first frame `C.png`, last frame `D.png`:**
```
A living Indian miniature painting in Rajasthani-Mughal gouache on handmade paper. Inside the cylinder the golden fuel-spray flame flares and blooms until it fills the frame with warm golden light. A fast whip pan through the light reveals the trainee in his blue ITI uniform, then the camera cranes up in one smooth move to show him standing proud before the red-and-white state bus against the sunrise, the marigold border settling around the scene. Brush strokes stay visible, jewel colours, continuous motion. No text, no speech, no music, keep the painted paper texture, no hard cuts.
```

## Step 4 — Join the clips (when both are back)

Ask for whichever clip is missing. Check each with `ffprobe` (has video, ≥ the needed length, first/last frames
match A/B and C/D — extract and look). Then:

```bash
python3 scripts/assemble.py base clip1.mp4 clip2.mp4 timeline.json base.mp4
```

This drops all Flow audio, fits clip 1 into `0 → join+0.25 s` and clip 2 into the rest (gentle speed-up up to
×1.33, else trims the tail), dissolves 0.5 s at `join`, scales/crops to 1080×1920 @ 30 fps and adds light paper grain.
The flame glow / watercolour bloom that hides the seam is drawn by the overlay in Step 5. If a clip is too
short the script stops — move `join` or ask for a new take; never freeze-frame to pad.

## Step 5 — Text, glow, contact sheet, render

1. Contact sheet from the real footage (before any full render):
   ```bash
   node scripts/render_overlay.js timeline.json stills --times <each t+0.1>,<each t+0.45>,<join>,<duration-0.3>
   python3 scripts/assemble.py sheet timeline.json stills contact_sheet.png --base base.mp4
   ```
   Look at it yourself first: Gujarati shaping correct (matras, conjuncts like ન્જ), text inside the cyan box,
   readable over the paint, glow covering the seam. Show it to the user and **wait for OK**.
2. Full overlay + render:
   ```bash
   node scripts/render_overlay.js timeline.json overlay
   python3 scripts/assemble.py final base.mp4 overlay audio.mp3 timeline.json iti-miniature-reel.mp4
   ```
   Produces `iti-miniature-reel.mp4` (H.264 High, CRF 18 capped at 16 Mb/s, AAC 192k, faststart) and
   `iti-miniature-reel_whatsapp720.mp4` (720×1280, re-encoded at a capped bitrate if it would exceed 20 MB).
   Audio = the user's MP3 only, trimmed to the duration with a 0.4 s fade-out.
3. Verify with `ffprobe` (1080×1920, 30 fps, duration 10–15 s, one audio stream; WhatsApp copy < 20 MB), pull
   3 frames to eyeball, then send both files to the user with sizes and durations.

### What the overlay does (`scripts/render_overlay.js`)

- Font: **Noto Sans Gujarati Black (900)** from Google Fonts, falling back to **Hind Vadodara Bold**; if neither
  loads, it errors — stop and tell the user (never render Gujarati in a fallback system font).
- Each line: scale 0.6 → 1.1 in 0.22 s (ease-out), settle to 1.0 by 0.40 s; yellow (#FFD21F) rounded bar sweeps
  left → right behind it from 0.06 s to 0.44 s; dark indigo text with a cream outline; emoji symbol on the left.
  Lines stack bottom-up and stay on screen; CTA is the largest. Font size auto-shrinks to fit the safe width.
- Safe area: x 70 → 930, y 250 → 1500 (top 250 / bottom 420 / right 150 kept clear). It errors if text won't fit.
- Join: a radial golden flame glow (or rose-cream watercolour bloom) peaking at `join`, added with `lighter` blending.
- Paper grain is added by ffmpeg in `base` (`noise=alls=6:allf=t`) — keep it light.

## Done checklist

- [ ] Story line + second→picture→text table shown
- [ ] One Gemini prompt; sheet cut to A–D 1080×1920; frames contact sheet shown
- [ ] Two Flow prompts, each ending with the exact required sentence
- [ ] Flow audio muted, 10–15 s, seam hidden by glow/bloom
- [ ] ≤ 3 Gujarati lines, scale-pop + highlight bar + symbol, CTA last, safe area respected
- [ ] Contact sheet approved before render; no file overwritten without asking
- [ ] 1080×1920 30 fps MP4 + 720p WhatsApp copy < 20 MB delivered
