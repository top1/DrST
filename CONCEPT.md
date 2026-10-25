This pipeline is an **autonomous, multi-agent audiobook and visual studio** orchestrated in Google Antigravity using **Gemini Flash 3.8** as both the director and multimodal quality reviewer, paired with **Fish Drama3** for local text-to-speech (TTS), **Qwen 2.1 (via ComfyUI)** for multi-reference image generation, and **FFmpeg** for final video assembly.  
Its goal is to take a raw book file (such as *The Return of Sherlock Holmes* in `.xhtml` / `.html`), understand its characters and settings before generating a single frame, and turn the entire text into a synced, narrated video where characters, outfits, injuries, and rooms remain visually consistent from chapter to chapter.

## **1. What the Pipeline Can Do (Core Capabilities)**

* **Whole-Book Continuity & Disambiguation:** Scans the entire book first to build a structured "world bible" (`registry.json`), separating similarly named characters into unique IDs and generating baseline reference portraits (`_basic.png`) before scene production starts.  
* **Stateful Visual Evolution:** Tracks when a character or room changes over the story. Instead of generating from scratch, it chains Qwen 2.1 reference images to evolve states (e.g., `character_basic` → `character_red_dress` → `character_red_dress_injured`) while locking in the character's core facial identity and applying the global `image_style_prompt` ("digital art, pastel marker illustration").  
* **Adaptive Scene Boundary Detection:** Reads the book using a sliding character window starting at `min_length` (1500 characters up to the next full stop). If a complete, drawable scene isn't finished yet, it extends the window by `extend` (500 characters) up to `max_extend` (2 times) to find a clean narrative cut.  
* **Expressive, Consistent Single-Pass Narration:** Annotates raw prose with vocal acting cues using scoped XML tags (`<whisper>...</whisper>`) and localized tags (`[sighs]`, `[pause]`) governed by `speaker_dynamic` (0 = none to 3 = maximum, configured at 2) and `narrator_voice_path` (`watson_narrator_english.safetensors`). Generates the entire scene in a single conditioned pass using Fish Drama3's built-in ~300-byte chunker and prompt history chaining (`history = own[:1] + own[1:][-1:]`) with tuned hyperparameters (`audio_temperature = 0.88`, `audio_top_p = 0.85`, `audio_top_k = 0`), completely preventing voice timbre drift.  
* **Audio-First Visual Pacing:** Eliminates audio/video sync headaches by generating the scene's audio *first*, measuring its exact length in seconds, and dividing by `picture_change_time` (10 seconds). If a single conversation lasts 28 seconds, the pipeline automatically plans 3 distinct visual beats (e.g., wide establishing shot, close-up on speaker, reaction shot) so an image never sits frozen on screen for more than 10 seconds.  
* **Multimodal Self-Correction (The Judge Loop):** Every generated `.wav` chunk and `.png` image is inspected directly by Gemini Flash 3.8 against `quality_audio` (7/10) and `quality_image` (7/10). If an audio clip skips a word or an image has a mutated hand or wrong outfit, the Judge rejects it and passes a specific fix back to the generator for up to `retry_limit` (2 retries).  
* **Crash-Proof State Recovery:** Every finished step is saved to disk inside `project/<Book Name>/scenes/scene_XXXX/manifest.json` and `project_state.json`. If ComfyUI or your PC stops halfway through the book, restarting the pipeline resumes from the exact character offset and sub-step where it left off.

## **2. System Architecture & The 6 Agent Roles**

| Component / File | Role | Primary Responsibility |
| :---- | :---- | :---- |
| **config.toml** | Configuration | Stores global parameters: `project_dir`, voice seed (42), acting dynamics (2), image pacing (10s), quality thresholds (7), text slice lengths (1500 + 500 × 2), and art style. |
| **agent.md** | Master Orchestrator | State machine that reads config.toml, tracks the text cursor (`current_char_cursor`), dispatches tasks to sub-agents with isolated context, and logs progress. |
| **01_loremaster.md** | World Builder | Reads the full book in Pass 1, extracts recurring characters/locations/objects, resolves name collisions, and builds `bible/registry.json` + baseline `_basic.png` files. |
| **02_scene_finder.md** | Boundary Slicer | Analyzes the current text window (1500–2500 chars) to find a complete visual scene (action, dialogue, or abstract mood) and outputs the exact `char_end` offset and `scene_text`. |
| **03_audio_master.md** | Voice Director | Injects scoped vocal delivery tags (`<whisper>...</whisper>`) based on `speaker_dynamic`, executes single-pass conditioned generation via Fish Drama3 preserving prompt history, and decodes unified `audio_full.wav`. |
| **04_image_creator.md** | Visual Director | Calculates required image count from audio length and `picture_change_time`, selects or evolves Qwen 2.1 reference states in `bible/refs/`, and drives ComfyUI. |
| **05_judge.md** | Multimodal QA | Uses Flash 3.8's native audio and vision capabilities to score every `.wav` and `.png` from 1–10 against `quality_audio` and `quality_image`, issuing actionable retry instructions on failure. |

## **3. How It Works End-to-End (The 4 Execution Phases)**

### **Phase 0: Book Ingestion & Normalization**

> 1. `agent.md` checks `project/The Return of Sherlock Holmes/`.  
> 2. It converts the raw `.xhtml` / `.html` book into a clean, UTF-8 `book_clean.txt` by stripping HTML/XML tags, CSS, and publisher boilerplate, normalizing all paragraphs so character offsets (`char_start`, `char_end`) are 100% deterministic.

### **Phase 1: The Bible Pass (First Pass Research)**

> 1. `01_loremaster.md` scans `book_clean.txt` to identify every recurring character (e.g., `sherlock_holmes`, `john_watson`), key location (`baker_street_study`), and plot object.  
> 2. It writes `project/The Return of Sherlock Holmes/bible/registry.json` with detailed physical descriptions.  
> 3. It calls ComfyUI (Qwen 2.1) to generate the baseline reference images (`bible/refs/sherlock_holmes_basic.png`, `bible/refs/baker_street_study_basic.png`), which `05_judge.md` verifies before locking them in as the visual ground truth.

### **Phase 2: The Main Scene Production Loop**

For every scene from character 0 to the end of `book_clean.txt`, `agent.md` executes this four-step sequence:

> 1. **Slice & Isolate Scene (`02_scene_finder.md`):**  
   * Slices 1500 characters (`min_length`) up to the next full stop.  
   * Checks if a complete visual scene exists. If the text cuts off mid-moment, it appends 500 characters (`extend`) up to 2 times (`max_extend`).  
   * Outputs the exact sentence and character offset where the scene ends (`char_end`), verbatim `scene_text`, plus the list of characters/locations present. The next scene loop will start cleanly at `char_end`.  
> 2. **Direct, Generate & Judge Audio (`03_audio_master.md` + `05_judge.md`):**  
   * Adds Fish Drama3 scoped emotion and pacing annotations (`<whisper>...</whisper>`, `[pause]`, `[sighs]`) according to `speaker_dynamic = 2` without altering the prose.  
   * Executes a single-pass conditioned generation using `scripts/generate_scene_audio.py` (`split_long_text = true`, `audio_temperature = 0.88`, `audio_top_p = 0.85`, `audio_top_k = 0`), leveraging Drama3's internal KV prompt chaining to preserve vocal timbre across all takes.  
   * `05_judge.md` evaluates the entire `audio_full.wav` holistically. If word accuracy or voice quality fails (`score < 7`), retries with targeted fixes up to 2 times (`retry_limit`).  
   * Exact duration (e.g., 85.4 seconds) is written to `manifest.json` and `execution.log`.  
> 3. **Resolve References & Evolve States (`04_image_creator.md`):**  
   * Computes required images: $\lceil 24.6 / 10 \rceil = 3$ images (`picture_change_time = 10`).  
   * Searches `bible/registry.json` for the characters and location in the scene.  
   * **If existing states match:** Pulls their `.png` paths (e.g., `sherlock_holmes_basic.png` + `baker_street_study_basic.png`).  
   * **If a character/location changed** (e.g., Sherlock puts on a disguise or gets injured): First generates a new reference sheet (`sherlock_holmes_disguised.png`) using `sherlock_holmes_basic.png` as the identity anchor, registers the new state in `registry.json`, and uses it for the scene.  
> 4. **Generate & Judge Scene Images (`04_image_creator.md` + `05_judge.md`):**  
   * Generates `img_01.png`, `img_02.png`, and `img_03.png` in ComfyUI using Qwen 2.1 multi-reference inputs and `image_style_prompt`, varying camera angles across the 3 beats.  
   * `05_judge.md` compares each generated image side-by-side against the reference `.png` files and prompt. Any image scoring below 7 (`quality_image`) is regenerated using the Judge's fix up to 2 times (`retry_limit`).

### **Phase 3: Deterministic Video Assembly (`video_creator`)**

Once all scene folders (`scene_0001`, `scene_0002`, ...) have their approved `audio_full.wav` and `img_XX.png` files logged in `manifest.json`:

> 1. A deterministic Python + FFmpeg script reads each `manifest.json`.  
> 2. For each scene, it displays each image for its exact slice of `audio_duration_sec` (applying a subtle pan/zoom and crossfade so the video feels alive) and muxes it with `audio_full.wav` into `scene_XXXX.mp4`.  
> 3. Finally, it concatenates all `scene_XXXX.mp4` files into the finished audiobook movie, guaranteeing zero audio drift from start to finish.

## **4. Workspace & File Layout**

```text
root/  
├── config.toml                                 <-- Global settings & target book path  
├── agent.md                                    <-- Master state-machine orchestrator  
├── agents.md                                   <-- Synchronized copy for Antigravity rules  
├── video_creator.py                            <-- Deterministic FFmpeg compiler  
├── agents/  
│   ├── 01_loremaster.md                        <-- Pass 1: Entity extraction & base refs  
│   ├── 02_scene_finder.md                      <-- Pass 2: Sliding window boundary slicer  
│   ├── 03_audio_master.md                      <-- Pass 2: Fish Drama3 TTS director & stitcher  
│   ├── 04_image_creator.md                     <-- Pass 2: Qwen 2.1 multi-ref & angle director  
│   └── 05_judge.md                             <-- Pass 1 & 2: Multimodal QA reviewer  
└── project/  
    └── The Return of Sherlock Holmes/  
        ├── input/
        │   └── The Return of Sherlock Holmes.xhtml <-- Raw input book  
        ├── book_clean.txt                      <-- Stripped, character-indexed text  
        ├── project_state.json                  <-- Cursor & crash-recovery checkpoint  
        ├── execution.log                       <-- Chronological audit log  
        ├── bible/  
        │   ├── registry.json                   <-- Master database of entities & state descriptions  
        │   └── refs/                           <-- Reference PNGs (e.g., sherlock_holmes_basic.png)  
        └── scenes/  
            ├── scene_0001/  
            │   ├── manifest.json               <-- Offsets, text, audio length, image timings, scores  
            │   ├── audio_full.wav              <-- Stitched narration for Scene 1  
            │   ├── img_01.png                  <-- Beat 1 (0.0s - 8.2s)  
            │   ├── img_02.png                  <-- Beat 2 (8.2s - 16.4s)  
            │   ├── img_03.png                  <-- Beat 3 (16.4s - 24.6s)  
            │   └── scene_0001.mp4              <-- Rendered scene video clip  
            └── scene_0002/  
                └── ...
```
