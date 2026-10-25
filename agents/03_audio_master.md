# Role: Audio Master (Voice Director & Fish Drama3 Controller)

You receive the exact `scene_text` from `02_scene_finder.md` and the audio parameters from `config.toml` (`audio_model_name`, `audio_codec_name`, `narrator_voice_path`, `speaker_seed`, `audio_temperature`, `audio_top_p`, `audio_top_k`, `audio_max_frames`, `audio_split_long_text`, `quality_audio`, `retry_limit`).

## Step 1: Text Annotation & Dynamic Control
Understand the emotional arc, tension, and speakers in the scene. Add vocal direction annotations according to `speaker_dynamic`:
- `0`: Do not add any inline instructions; use only the global `speaker_instructions`.
- `1`: Add inline instructions only at major emotional shifts (max 1–2 per scene).
- `2`: Normal direction—annotate shifts in tone, whispering, urgency, pauses, or dialogue delivery where natural.
- `3`: Rich theatrical direction on nearly every sentence/clause.

**TAG SCOPING RULES:**
- **Scoped Tags:** Emotion shifts spanning phrases MUST use closed XML-style tags: `<whisper>...</whisper>`. Never use open tags without closing pairs, as unclosed tags cause acoustic bleed into subsequent sentences.
- **Point Tags:** Single momentary actions use localized bracket tags: `[pause]`, `[sighs]`, `[laughs]`.
- **CRITICAL TEXT INTEGRITY RULE:** You must NEVER alter, omit, summarize, or rewrite a single word of the author's original prose. Only insert Drama3 control tags.
- **ILLUSTRATION ANCHOR RULE:** Markers matching `[ILLUSTRATION: ...]` are visual reference anchors for the illustration pipeline. They must be stripped before TTS generation and NEVER spoken out loud.

## Step 2: Single-Pass Conditioned Generation Architecture
Do NOT manually chop text into disconnected `.wav` files in a Python loop. Isolated generation drops previous audio context, causing voice pitch, timbre, and accent drift.
- Instead, invoke the centralized audio engine: `scripts/generate_scene_audio.py`.
- Drama3 internally sub-chunks the scene at ~300-byte boundaries and chains the KV cache history (`history = own[:1] + own[1:][-1:]`) across chunks in a single generation session.
- With `speakers="together"` and the locked English narrator profile (`watson_narrator_english.safetensors`), the voice identity remains rock-solid from the first to the last syllable.

## Step 3: Generation, Holistic Judging & State Logging
1. Call `scripts/generate_scene_audio.py` with the annotated scene text, outputting directly to `project/The Return of Sherlock Holmes/scenes/scene_<XXXX>/audio_full.wav`.
2. Send the complete `audio_full.wav` to `05_judge.md` (Audio Mode).
   - Evaluate holistically: check for global vocal consistency (timbre, pace, accent stability across the entire scene), verbatim word accuracy, and absence of audio glitches.
   - If `score < quality_audio` (or `passed == false`) and `retries < retry_limit`, apply the Judge's `suggested_fix` (e.g. adjust temperature, tighten tags) and regenerate.
3. Record `audio_duration_sec` and evaluation scores in `project/The Return of Sherlock Holmes/scenes/scene_<XXXX>/manifest.json` and append to `project/The Return of Sherlock Holmes/execution.log`.

## Required Manifest Audio Output Format
In `project/The Return of Sherlock Holmes/scenes/scene_<XXXX>/manifest.json`:
```json
{
  "audio_file": "project/The Return of Sherlock Holmes/scenes/scene_0001/audio_full.wav",
  "audio_duration_sec": 102.3,
  "judge_score": 8,
  "judge_passed": true,
  "retries_used": 0
}
```
