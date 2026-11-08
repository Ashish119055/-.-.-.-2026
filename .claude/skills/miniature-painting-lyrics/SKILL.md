---
name: miniature-painting-lyrics
description: Make a seamless 16:9 lyric video in the style of the "Khat" (Navjot Ahuja) video — an Indian miniature painting that comes alive, flowing from paper flowers to a diya, a pop-up blue house, her eye, a field of blue flowers and a flying letter with no visible cuts, with Hindi lyrics that move with their meaning. Use when the user runs /miniature-painting-lyrics or attaches a song MP3 with Devanagari lyrics, a title and an artist name for a living-miniature lyric video.
argument-hint: "[song.mp3] [lyrics in Devanagari] [title] [artist]"
---

# Living miniature-painting lyric video (16:9)

Input from the user: **a song MP3 (a 60–75 s cut works), its lyrics in Devanagari, the song title and the artist name.**
Output: a 1920×1080 @ 30 fps MP4 with the original song audio + a 1280×720 copy under 20 MB for WhatsApp.

The user makes every image and clip from your prompts (Gemini, Google Flow / Veo). **You** do the rest in code:
alignment, cutting, re-timing, joins, lyrics, render — an HTML canvas rendered frame by frame in headless Chromium
(Playwright, pre-installed) and encoded with ffmpeg. Scripts are in `scripts/` next to this file
(`${CLAUDE_SKILL_DIR}/scripts`; if empty use `.claude/skills/miniature-painting-lyrics/scripts`).

## Hard rules (every run)

1. **Only the user's generated images/clips go in the video.** No stock, no generating images or clips yourself, no drawn stand-ins.
2. **Time every word with forced alignment (torchaudio MMS_FA) on the separated vocals. Never guess or hand-type timings.**
3. **Missing input → ask.** A missing sheet, frame or clip, unreadable audio, or missing lyrics/title/artist: ask for it.
   **Never use a placeholder**, test pattern, freeze-frame or solid colour in its place.
4. **Contact sheet of stills before the full render**, then wait for an OK.
5. **Ask before overwriting files.** The scripts refuse to overwrite; pass `--force` only after the user agrees.
6. Render **the MP4 with the original audio, plus a 720p copy under 20 MB for WhatsApp.**
7. If the song isn't the user's own, mention once that posting it publicly may need the rights holder's permission.

## Workspace

`videos/miniature-painting-lyrics/<song-slug>/` in the repo (ask before reusing an existing folder):
```
song.mp3 lyrics.txt timing.json beats.json
sheets/sheet-1.png sheet-2.png sheet-3.png   frames/A.png … L.png   frames/r2-*.png
clips/clip1.mp4 … clip4.mp4 (round 1)   clips/x1.mp4 … x4.mp4 (round 2)
edl.json plan.json base.mp4 base.timing.json stills/ overlay/ contact_sheet.png
<slug>.mp4  <slug>_whatsapp720.mp4
```
Python deps on first use: `pip install demucs soundfile torch torchaudio uroman librosa`.

---

## Step 1 — Vocals, word timing, beats, story

1. Save the lyrics **exactly as the user wrote them**, one sung line per line, as `lyrics.txt`.
2. Separate vocals and align every word on the vocal track:
   ```bash
   python3 scripts/separate_align.py song.mp3 lyrics.txt timing.json      # demucs htdemucs --two-stems=vocals, then MMS_FA
   python3 scripts/beats.py song.mp3 beats.json
   ```
   Words scoring < 0.3 usually mean the lyrics don't match what's sung (a repeat, an ad-lib, a missing line).
   Show those to the user and fix `lyrics.txt` with them — never shift times by hand.
3. Read the lyrics, write **the story in one line**, then a table: lyric line (with aligned start–end) → picture
   (which frame letters / clip) → planned text effect. Show it and continue.

## Step 2 — Gemini sheets → frames A–L

Give the 3 Gemini prompts below. The user makes each at the highest quality and saves `sheet-1.png`, `sheet-2.png`,
`sheet-3.png`. All people are on sheet 1, so they stay consistent without separate character images.

**For "Khat", give the prompts word for word. For any other song keep the style lines, the 2×2 grid and the
two-part clip structure; change only the people, places and objects to fit the lyrics.**

Cut each sheet along its grid into four 1920×1080 frames:
```bash
python3 scripts/cut_grid.py sheets/sheet-1.png frames --names CFHI
python3 scripts/cut_grid.py sheets/sheet-2.png frames --names BEGJ
python3 scripts/cut_grid.py sheets/sheet-3.png frames --names ADKL
```
Check each printed aspect is ≈ 1.778. If a divider was missed, there's text in a panel, or the two people don't match
the descriptions, show it and ask for a regenerated sheet.

### GEMINI IMAGE PROMPTS (3 images, each a 2×2 grid = 12 frames)

**Sheet 1, the people** (TOP LEFT = C, TOP RIGHT = F, BOTTOM LEFT = H, BOTTOM RIGHT = I):
```
One wide 16:9 image divided into a 2x2 grid of four separate paintings. Each panel is its own full 16:9 scene, all four the same size, separated only by a thin straight black line. No outer margin. No text, numbers, labels, letters or signatures anywhere. All four panels share one style: Traditional Indian miniature painting, Rajasthani-Mughal gouache on handmade paper, fine brush outlines, soft paper grain, jewel colours of ultramarine blue, rose pink and marigold yellow with cream highlights, strong colour contrast, tender emotional mood.
The same two people appear across the panels. He is a gentle young Indian man in his early 20s with soft curly black hair and kind tired eyes, in a pale yellow cotton kurta with rolled sleeves and a thin red thread on his right wrist. She is a young Indian woman in her early 20s with a long black braid, a small bindi and a warm bright smile, in a deep blue cotton salwar suit, rose pink dupatta, small silver jhumkas and glass bangles.
TOP LEFT: Night. He sits cross-legged at a low wooden desk in a small room with deep indigo walls, writing a letter with a reed pen. Folded pink and yellow paper flowers lie around him. On the right, an arched window shows yellow stars and a distant white temple spire, with a small lit clay diya in the window niche. The letter shows only faint wavy lines.
TOP RIGHT: Bright morning. He is seen from three-quarter back in an empty unfinished room, holding a wide brush. The left third of the white wall is painted wet ultramarine blue. A paint pot and ladder stand nearby. Yellow sunlight and pink bougainvillea come through an open doorway.
BOTTOM LEFT: Pink and gold evening on a rooftop terrace. She sits on a low parapet, laughing, holding out one small blue flower, her pink dupatta lifting in the breeze. Behind her are yellow marigold garlands, pots of blue flowers and a distant old town.
BOTTOM RIGHT: Extreme close-up of her eye filling the panel: fine lashes, kajal, warm brown iris, with a tiny field of blue flowers reflected in the iris.
```

**Sheet 2, the covers** (TOP LEFT = B, TOP RIGHT = E, BOTTOM LEFT = G, BOTTOM RIGHT = J):
```
One wide 16:9 image divided into a 2x2 grid of four separate paintings. Each panel is its own full 16:9 scene, all four the same size, separated only by a thin straight black line. No outer margin. No text, numbers, labels, letters or signatures anywhere. All four panels share one style: Traditional Indian miniature painting, Rajasthani-Mughal gouache on handmade paper, fine brush outlines, soft paper grain, jewel colours of ultramarine blue, rose pink and marigold yellow with cream highlights, strong colour contrast, tender emotional mood.
Each panel is filled completely edge to edge, with no background, no people and no other objects.
TOP LEFT: Hundreds of folded paper flowers packed tightly together, in rose pink and marigold yellow with a few ultramarine ones.
TOP RIGHT: Pure warm white-gold light with only a faint paper texture.
BOTTOM LEFT: Wet ultramarine blue paint with soft visible brush strokes and a slight shine.
BOTTOM RIGHT: Close-up delicate ultramarine and sky blue five-petal flowers with yellow centres, packed tightly with no sky and no ground.
```

**Sheet 3, the objects** (TOP LEFT = A, TOP RIGHT = D, BOTTOM LEFT = K, BOTTOM RIGHT = L):
```
One wide 16:9 image divided into a 2x2 grid of four separate paintings. Each panel is its own full 16:9 scene, all four the same size, separated only by a thin straight black line. No outer margin. No text, numbers, labels, letters or signatures anywhere. All four panels share one style: Traditional Indian miniature painting, Rajasthani-Mughal gouache on handmade paper, fine brush outlines, soft paper grain, jewel colours of ultramarine blue, rose pink and marigold yellow with cream highlights, strong colour contrast, tender emotional mood.
TOP LEFT: A single sheet of handmade cream paper fills the panel, softly lit, with faint fibres. One small folded rose pink paper flower and one marigold yellow paper flower rest near the centre. Nothing else.
TOP RIGHT: Extreme close-up of one small clay diya with a single large golden flame in the exact centre, against deep indigo darkness with a soft warm glow.
BOTTOM LEFT: Dense indigo night sky with gold stars and curling miniature-style clouds. One small folded cream letter tied with pink thread, a single blue flower tucked under the thread, floats in the exact centre.
BOTTOM RIGHT: Dawn. A small house with an ultramarine blue wall and an open wooden door, pink bougainvillea above, yellow marigolds along the path. At the threshold, a woman's hand with glass bangles lifts a folded letter tied with pink thread, a blue flower on it. Only her hand, forearm and the edge of a rose pink dupatta are visible. A thin painted floral border in blue, pink and yellow runs around this panel on handmade cream paper.
```

## Step 3 — Round 1 Flow clips (one at a time)

Tell the user: Google Flow → **Frames to Video**, **16:9**, **2 outputs**, a Veo model that takes a first and last
frame. **Run clip 3 first** — it's the hardest and shows quickly whether two scenes fit in one clip. **Re-roll if a face
melts, a hard cut appears or text shows up.** Give one prompt at a time with its two frames; save as `clips/clip1.mp4` … `clip4.mp4`.

**Clip 1 — first frame A, last frame D:**
```
Hand-painted Indian miniature painting coming gently to life. Two parts in one continuous shot, with no hard cuts. Slow, soft, dreamlike movement. Keep the painted paper texture and colours. No text, no speech, no music. Part 1: gentle hands in pale yellow sleeves fold paper flowers on the page, and more flowers gather until they fill the whole frame. Part 2: the flowers fall away to reveal a young man in a yellow kurta from behind, writing at a low desk at night. The camera glides past him to a window niche and pushes in until the diya flame fills the frame.
```

**Clip 2 — first frame D, last frame G:**
```
Hand-painted Indian miniature painting coming gently to life. Two parts in one continuous shot, with no hard cuts. Slow, soft, dreamlike movement. Keep the painted paper texture and colours. No text, no speech, no music. Part 1: the flame flickers and the camera pulls back to two cupped hands in yellow sleeves folded in prayer around the diya, then the flame brightens until warm light fills the frame. Part 2: the light settles into a bright empty room where the young man, seen from behind, paints a white wall with long strokes. The blue spreads and the camera pushes in until wet blue paint fills the whole frame.
```

**Clip 3 — first frame H, last frame J:**
```
Hand-painted Indian miniature painting coming gently to life. Two parts in one continuous shot, with no hard cuts. Slow, soft, dreamlike movement. Keep the painted paper texture and colours. No text, no speech, no music. Part 1: she laughs and speaks softly, tucks a strand of hair behind her ear, and the camera slowly pushes into her eye until it fills the frame. Part 2: her eye blinks once, the reflected blue flowers grow, and the camera passes through the iris into a swaying field of blue flowers until they fill the whole frame.
```

**Clip 4 — first frame J, last frame L:**
```
Hand-painted Indian miniature painting coming gently to life. Two parts in one continuous shot, with no hard cuts. Slow, soft, dreamlike movement. Keep the painted paper texture and colours. No text, no speech, no music. Part 1: the flowers part from the centre to reveal a folded letter tied with pink thread. A breeze lifts it and it drifts up into a starry indigo night. Part 2: the letter drifts down as the sky brightens to pink dawn and lands at the door of a blue house. The door opens and a hand with glass bangles lifts the letter.
```

(Round 1 uses A, D, G, H, J and L as first/last frames. B, C, E, F, I and K are the in-between scenes each clip's
"Part 1 → Part 2" passes through: use them to check the clip hit the right look, and as first/last frames if a
two-part clip keeps failing and must be split into two single-part clips.)

## Step 4 — Watch round 1, then round 2 Flow clips

When the 4 clips are back, check each (`ffprobe`; a strip of stills:
`ffmpeg -i clips/clip1.mp4 -vf "fps=2,scale=320:-1,tile=8x2" strips/clip1.png`) and **say where it feels slow or empty**.
Then cut the first/last frames for round 2 at the listed times (adjust to the user's actual clips only if the moment
moved — say so):
```bash
ffmpeg -ss 6.4 -i clips/clip1.mp4 -frames:v 1 -vf scale=1920:1080 frames/r2-1-first.png   # and 8.4 -> r2-1-last.png
```
Same for clip 2 at 4.6 / 5.6 s, clip 3 at 2.4 / 4.8 s, clip 4 at 4.4 / 6.8 s. Give the prompts one at a time; save as `clips/x1.mp4` … `x4.mp4`.
These add the big moments: the ink vine to the temple, the pop-up house, the couple together, the letter over the town.

### FLOW VIDEO PROMPTS, ROUND 2

**Extra clip 1, Pen to temple and back** (frames from clip 1 at 6.4 s and 8.4 s):
```
Hand-painted Indian miniature painting coming to life, matching the style, paper texture and colours of the first frame. One continuous, flowing camera move with no hard cuts. Confident and fast, but graceful. No text, no speech, no music. The camera swoops down to his pen nib. Blue ink flows off the page as a living vine with small blue flowers, races across the desk, up the wall and out of the window into the night. The camera follows it over dark rooftops to a white temple spire under yellow stars, then turns away and glides back through the window to the lit diya in its wall niche.
```

**Extra clip 2, The house builds itself** (frames from clip 2 at 4.6 s and 5.6 s):
```
Hand-painted Indian miniature painting coming to life, matching the style, paper texture and colours of the first frame. One continuous, flowing camera move with no hard cuts. Confident and fast, but graceful. No text, no speech, no music. The light flares to pure white, then settles on a sheet of cream paper. A small blue house folds itself up from the paper like a pop-up book: walls rise, shutters open, the roof lands, pink bougainvillea climbs over it. The camera flies fast toward the open door and through it into a bright empty room, where the man stands with his brush.
```

**Extra clip 3, The memory together** (frames from clip 3 at 2.4 s and 4.8 s):
```
Hand-painted Indian miniature painting coming to life, matching the style, paper texture and colours of the first frame. One continuous, flowing camera move with no hard cuts. Confident and fast, but graceful. No text, no speech, no music. She laughs and turns, pointing at something. The camera sweeps back to reveal a rose pink evening terrace with pots of blue flowers, and a young man in a yellow kurta beside her, seen from behind, watching her. A blue petal floats past. The camera then rushes smoothly back to her face and into her eye until it fills the frame.
```

**Extra clip 4, The letter's journey** (frames from clip 4 at 4.4 s and 6.8 s):
```
Hand-painted Indian miniature painting coming to life, matching the style, paper texture and colours of the first frame. One continuous, flowing camera move with no hard cuts. Confident and fast, but graceful. No text, no speech, no music. The letter dives and the camera chases it as it swoops over a sleeping old town, past windows glowing with diyas, along a river of floating diyas and through a drifting cloud of paper flowers. It climbs again as the sky turns from indigo to pink dawn, arriving above a blue roof.
```

## Step 5 — Re-cut 8 clips into ~11 shots

Write `edl.json` (format in `scripts/assemble.py`): about 11 shots from the 8 clips, in story order, each timed so
its lyric line falls inside it and its joins land on beats or between lines.
- **Close to real speed:** `speed` 0.9–1.1 (the script warns outside 0.85–1.15). Nothing should look stretched.
- **Flow doesn't always land on the exact last frame:** drop any part where a person's look changes (face, clothes,
  hair, bangles) — check the strips frame by frame and set `in`/`out` before it.
- **Hide every join** (`join` on the outgoing shot): `zoom` (zoom through an object — eye, door, flame),
  `glow` (light from the flame), `fade` (soft fade) or `bloom` (watercolour bloom spreading across the frame).
- Story: open on the hands folding flowers (title over it) … end on the hand lifting the letter at the blue door.
- The picture length must match the song cut (± 0.5 s); `end_fade` ≈ 1.5 s fades to black at the end.
```bash
python3 scripts/assemble.py base edl.json base.mp4      # mutes all Flow audio, writes base.timing.json
```

## Step 6 — Lyrics plan

Write `plan.json` (format at the top of `scripts/render_overlay.js`). Rules:
- **Devanagari in Tiro Devanagari Hindi** (`"font": "serif"`); **Kalam** for handwritten words (`"font": "hand"`,
  automatic for `write` and `envelope`). Fonts load from Google Fonts; if one fails the renderer stops — never fall back.
- **A few words at a time** (a card is ≤ 6 words), placed **in the empty part of each shot** (look at the stills).
- **Each word appears exactly when it is sung** — the renderer reads start times from `timing.json`; cards only
  reference word indices.
- **An effect that matches the line's meaning:**

  | Meaning | `effect` | What it does |
  |---|---|---|
  | writing / letters | `write` | written on stroke by stroke in Kalam: outline drawn by a moving pen nib, then the ink fills |
  | prayer | `rise` | rises out of the diya flame (`source` = flame position) with embers |
  | the house | `fold` | folds up from its baseline like the pop-up house |
  | blue paint | `drybrush` | revealed with a dry ultramarine brush stroke |
  | flowers / wind | `wind` | blows in on the wind with petals |
  | the khat | `envelope` | written on the envelope and moves with it (`path` keyframes follow the letter) |
  | anything else | `ink` | soft ink bleed-in |
- Put `"slip": true` (torn paper slip) behind any card on a busy shot so it stays readable.
- **Title:** song title in Caladea with the artist name small below it, over the hands folding flowers; it must
  fade out before the first sung word (the renderer enforces this).
- **End** on the hand lifting the letter at the blue door, then fade out (`end_fade`). Light paper grain is in `base`.

## Step 7 — Contact sheet, then render

```bash
node scripts/render_overlay.js plan.json timing.json base.timing.json stills --times <title, each card mid + end, each join, last 2 s>
python3 scripts/assemble.py sheet base.mp4 stills contact_sheet.png
```
Check it yourself first (Devanagari shaping — matras, nukta, conjuncts; text in empty space; slips on busy shots;
no face changes; joins hidden), then **show it and wait for OK**. Then:
```bash
node scripts/render_overlay.js plan.json timing.json base.timing.json overlay
python3 scripts/assemble.py final base.mp4 overlay song.mp3 <slug>.mp4
```
→ `<slug>.mp4` (1920×1080, 30 fps, H.264 High, AAC 192k, original song) and `<slug>_whatsapp720.mp4` (1280×720, < 20 MB).
Verify with `ffprobe`, look at 3 frames, then send both files with sizes and durations.

## Done checklist
- [ ] Vocals separated, every word force-aligned; one-line story + lyric→picture table shown
- [ ] 3 Gemini prompts given; sheets cut to frames A–L at 1920×1080
- [ ] 4 round-1 Flow prompts one at a time (clip 3 first, re-roll rules); 4 round-2 prompts with frames cut at the listed times
- [ ] ~11 shots near real speed, Flow audio muted, no look changes, joins hidden (zoom / glow / fade / bloom)
- [ ] Lyrics word-exact, a few words at a time, meaning-matched effects, slips on busy shots; title in Caladea; end fade
- [ ] Contact sheet approved; nothing overwritten without asking
- [ ] 1080p MP4 with original audio + 720p WhatsApp copy < 20 MB delivered
