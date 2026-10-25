# 🤖 Autonomous Audiobook & Visual Pipeline: Universal Agent Replication Manual

> **Scope:** A general, portable specification for an autonomous AI agent to set up the software environment, directory hierarchy, configuration files, specialist sub-agent prompts, and production scripts on **any machine** without hardcoded paths.

---

## 📑 Table of Contents
1. [Conventions & Environment Placeholders](#1-conventions--environment-placeholders)
2. [Hardware Baseline & System Requirements](#2-hardware-baseline--system-requirements)
3. [Software & Runtime Installation](#3-software--runtime-installation)
4. [ComfyUI & Local AI Model Checkpoints](#4-comfyui--local-ai-model-checkpoints)
5. [Universal Directory Hierarchy](#5-universal-directory-hierarchy)
6. [Configuration Files & Data Schemas](#6-configuration-files--data-schemas)
7. [Specialist Sub-Agent Specifications (`.md` Prompts)](#7-specialist-sub-agent-specifications-md-prompts)
8. [Production Scripts Architecture](#8-production-scripts-architecture)
9. [Programmatic Video Engine Setup (Remotion)](#9-programmatic-video-engine-setup-remotion)
10. [End-to-End Execution Protocol](#10-end-to-end-execution-protocol)

---

## 1. Conventions & Environment Placeholders

In this guide, all paths are relative or use standard variables:
- `<WORKSPACE_ROOT>`: The root directory of the pipeline workspace (e.g., `./` or `/path/to/drst`).
- `<COMFYUI_DIR>`: The installation path for ComfyUI.
- `<BOOK_TITLE>`: The name/slug of the input book being processed (e.g., `the_return_of_sherlock_holmes`).
- `<PROJECT_DIR>`: Relative path to the active book directory: `<WORKSPACE_ROOT>/project/<BOOK_TITLE>`.

---

## 2. Hardware Baseline & System Requirements

- **GPU:** NVIDIA GPU with $\ge 8\text{ GB}$ VRAM (Engineered for consumer cards: RTX 3060 Ti / RTX 4060 / RTX 3080).
- **RAM:** $\ge 16\text{ GB}$ system RAM (32 GB recommended for Mixture-of-Experts RAM offloading).
- **Disk:** $\approx 40\text{ GB}$ free SSD space for model weights, cache, and rendered video.
- **OS Support:** Windows 10/11, Ubuntu 22.04+ LTS, or Linux with CUDA 12.x drivers.

---

## 3. Software & Runtime Installation

An agent must ensure the following runtimes and CLI tools are installed and accessible in the system `PATH`:

### 3.1 Core Runtimes & Dependencies
- **Python 3.10 – 3.12:**
  ```bash
  # Python packages required by the pipeline
  pip install --upgrade pip
  pip install requests toml pillow soundfile scipy numpy
  ```

- **FFmpeg (with `libx264`, `aac`, and `libass` support):**
  - *Windows:* `winget install Gyan.FFmpeg`
  - *Linux (Ubuntu/Debian):* `sudo apt-get install -y ffmpeg`
  - *macOS:* `brew install ffmpeg`

- **Node.js (v20+ or v24 LTS) & npm:**
  - *Windows:* `winget install OpenJS.NodeJS.LTS`
  - *Linux:* `sudo apt-get install -y nodejs npm`

- **Git:**
  - Standard git CLI for cloning ComfyUI custom nodes.

---

## 4. ComfyUI & Local AI Model Checkpoints

The pipeline uses a local ComfyUI instance as the backend worker for both text-to-speech (Fish Drama 3) and image generation (Qwen-Image 2.1).

### 4.1 ComfyUI Setup
```bash
# Clone or install ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git <COMFYUI_DIR>
cd <COMFYUI_DIR>
pip install -r requirements.txt

# Install Fish Drama 3 Custom Node
cd <COMFYUI_DIR>/custom_nodes
git clone https://github.com/fishaudio/ComfyUI-Drama3.git
cd ComfyUI-Drama3
pip install -r requirements.txt
```

### 4.2 Required Model Files & Relative Placement
To prevent CUDA Out-Of-Memory errors on 8 GB VRAM cards:
- **Fish Drama 3 TTS:** Uses `w4a8` quantized weights and runs with `experts="in RAM"` (offloading Mixture-of-Experts weights to system memory). VRAM footprint: $\approx 4.2\text{ GB}$.
- **Qwen-Image 2.1:** Uses 8-bit quantized weights (`int8_convrot`) with Qwen3-VL CLIP. VRAM footprint: $\approx 6.8\text{ GB}$.

Place model weights into `<COMFYUI_DIR>`:
```
<COMFYUI_DIR>/
└── models/
    ├── diffusion_models/
    │   ├── drama3_w4a8experts_bf16.safetensors    # Fish Drama 3 TTS Diffusion
    │   └── qwen_image_2.1_int8_convrot.safetensors # Qwen-Image 2.1 Diffusion UNET
    ├── clip/
    │   └── qwen3vl_8b_w4a8.safetensors            # Qwen3-VL CLIP Tokenizer
    └── vae/
        ├── drama3_codec.safetensors               # Fish Drama 3 Audio Codec
        └── qwen_image_2.1_vae_bf16.safetensors    # Qwen Image VAE
```

*Narrator Voice Profile:*
- Place `<narrator_voice>.safetensors` inside `<PROJECT_DIR>/bible/refs/` or link to `<COMFYUI_DIR>/models/voices/`.

---

## 5. Universal Directory Hierarchy

The agent should create the following relative folder structure inside `<WORKSPACE_ROOT>`:

```
<WORKSPACE_ROOT>/
├── config.toml                             # Central pipeline parameters
├── agent.md                                # Master state machine orchestrator instructions
├── agents/                                 # Specialist sub-agent instructions
│   ├── 01_loremaster.md                    # Ingestion & World Bible entity extractor
│   ├── 02_scene_finder.md                  # Narrative boundary & scene slicer
│   ├── 03_audio_master.md                  # Drama 3 voice direction & acting tags
│   ├── 04_image_creator.md                 # Visual composition & ComfyUI prompter
│   └── 05_judge.md                         # Multimodal QA (hands, likeness, audio)
├── scripts/                                # Production execution scripts
│   ├── phase0_ingest.py                    # Book text cleaner
│   ├── build_chapter_scene_graph.py        # Narrative scene graph parser
│   ├── generate_scene_audio.py             # Single-pass Drama 3 audio renderer
│   ├── generate_scene_images.py            # Multi-reference ComfyUI prompter
│   ├── generate_scene_subtitles.py         # Victorian ASS/SRT generator
│   ├── render_scene_video.py               # Ken Burns motion & subtitle burn-in
│   └── concatenate_scenes.py               # Lossless chapter movie concatenation
└── project/
    └── <BOOK_TITLE>/                       # Dedicated workspace for each book
        ├── input/                          # Raw book files (.xhtml, .html, .txt)
        ├── book_clean.txt                  # Normalized plain text
        ├── project_state.json              # State machine cursor tracking
        ├── execution.log                   # Step-by-step audit log
        ├── bible/
        │   ├── registry.json               # Canonical entity IDs & prompt baselines
        │   └── refs/                       # Standardized 4-view model sheets
        └── scenes/
            └── scene_0001/ ... scene_XXXX/ # Generated scene assets
```

---

## 6. Configuration Files & Data Schemas

### 6.1 `config.toml` (Relative & Portable)
```toml
# Relative path to active project directory
project_dir = "project/<BOOK_TITLE>"

# Local ComfyUI API endpoint
comfy_url = "http://127.0.0.1:8188"

# Fish Drama 3 Audio Generation Parameters
audio_model_name = "drama3_w4a8experts_bf16.safetensors"
audio_codec_name = "drama3_codec.safetensors"
narrator_voice_path = "bible/refs/narrator_voice.safetensors"
audio_temperature = 0.88
audio_top_p = 0.85
audio_top_k = 0
audio_max_frames = 600
audio_split_long_text = true

# Voice style & dynamic instructions (0 = none, 1 = sparse, 2 = normal, 3 = maximal)
speaker_seed = 42
speaker_dynamic = 2
speaker_instructions = "deep voice, professional book reader"

# Maximum time (seconds) a single still image can stay on screen
picture_change_time = 10

# Alternative scenes (0 for single narrative path)
number_of_scene_alternatives = 0

# Quality acceptance thresholds (1 - 10)
quality_audio = 7
quality_image = 7
retry_limit = 2

# Text slicing window (in characters)
min_length = 1500
extend = 500
max_extend = 2

# Global visual art style prompt
image_style_prompt = "digital art, pastel marker illustration"
```

### 6.2 `project_state.json` (State Machine Tracker)
Initial state before running:
```json
{
  "bible_completed": false,
  "current_char_cursor": 0,
  "total_chars": 0,
  "current_scene_index": 1
}
```

### 6.3 `bible/registry.json` (World Bible Schema)
```json
{
  "characters": {
    "<character_id>": {
      "display_name": "Character Name",
      "aliases": ["Alias 1", "Alias 2"],
      "base_description": "Physical attributes, age, facial structure, default attire.",
      "states": {
        "<character_id>_front": {
          "file": "bible/refs/<character_id>_front.png",
          "description": "Standardized eye-level portrait close-up."
        },
        "<character_id>_threequarter": {
          "file": "bible/refs/<character_id>_threequarter.png",
          "description": "3/4 medium angle torso shot."
        },
        "<character_id>_profile": {
          "file": "bible/refs/<character_id>_profile.png",
          "description": "Side profile view."
        },
        "<character_id>_costume_props": {
          "file": "bible/refs/<character_id>_costume_props.png",
          "description": "Full period attire and signature props."
        }
      }
    }
  },
  "locations": {
    "<location_id>": {
      "display_name": "Location Name",
      "aliases": ["Room", "House"],
      "base_description": "Architectural details, lighting, mood, key furniture.",
      "states": {
        "<location_id>_basic": {
          "file": "bible/refs/<location_id>_basic.png",
          "description": "Establishing wide perspective under neutral/gaslight mood."
        }
      }
    }
  }
}
```

### 6.4 `scenes/scene_XXXX/manifest.json` (Scene Metadata Schema)
```json
{
  "scene_index": 1,
  "char_start": 0,
  "char_end": 1640,
  "audio_file": "audio_full.wav",
  "audio_duration_sec": 38.4,
  "audio_score": 8.5,
  "images_required": 4,
  "images": [
    { "id": "img_01.png", "prompt": "...", "score": 8.0, "status": "PASSED" },
    { "id": "img_02.png", "prompt": "...", "score": 8.5, "status": "PASSED" },
    { "id": "img_03.png", "prompt": "...", "score": 7.5, "status": "PASSED" },
    { "id": "img_04.png", "prompt": "...", "score": 9.0, "status": "PASSED" }
  ],
  "subtitles": {
    "ass": "subtitles.ass",
    "srt": "subtitles.srt"
  },
  "video_output": "scene_0001_ambient.mp4"
}
```

---

## 7. Specialist Sub-Agent Specifications (`.md` Prompts)

Create each specialist agent markdown prompt inside `agents/`:

### 7.1 `agents/01_loremaster.md`
```markdown
# Role: Loremaster (Continuity Architect & Entity Extractor)

Your goal is to parse `book_clean.txt` before production begins and generate `bible/registry.json`.

1. Entity Extraction:
   - Identify all recurring characters (characters appearing in >1 scene).
   - Identify recurring locations and key narrative objects.
   - Disambiguate duplicate or similar names with explicit snake_case IDs.
2. Canonical Descriptions:
   - Formulate detailed, self-contained visual descriptions adhering to `image_style_prompt`.
3. Standard 4-View Model Sheets:
   - For every recurring character, generate and verify 4 standardized reference sheets in `bible/refs/`:
     - `<character>_front.png`
     - `<character>_threequarter.png`
     - `<character>_profile.png`
     - `<character>_costume_props.png`
4. Register all reference file paths in `bible/registry.json`.
```

### 7.2 `agents/02_scene_finder.md`
```markdown
# Role: Scene Finder (Narrative Boundary Specialist)

Given text starting at `current_char_cursor` with length `min_length` (extended up to the next full stop `.`, `!`, `?`):
1. Detect natural dramatic scene boundaries (change in setting, passage of time, end of conversation).
2. If text cuts off in mid-climax, respond with:
   `{ "status": "SCENE_INCOMPLETE", "needed_extension": 500 }`
3. When complete, output:
   {
     "status": "SCENE_COMPLETE",
     "char_start": <start>,
     "char_end": <end>,
     "scene_summary": "...",
     "primary_characters": ["..."],
     "location_id": "..."
   }
```

### 7.3 `agents/03_audio_master.md`
```markdown
# Role: Audio Master (Drama 3 Voice Director)

Given `scene_text`:
1. Performance Direction:
   - Analyze dramatic context and embed acting performance tags:
     - Whispering: `<whisper: true>`
     - Dramatic pauses: `[pause: 1.0s]`
     - Tension/Excitement: `<excitement: 8/10, pitch: tense>`
2. Audio Synthesis:
   - Invoke `scripts/generate_scene_audio.py` using `watson_narrator_english.safetensors` with `experts="in RAM"`.
3. Verification:
   - Validate word accuracy, natural cadence, and absence of audio clipping.
   - Record `audio_duration_sec` into `manifest.json`.
```

### 7.4 `agents/04_image_creator.md`
```markdown
# Role: Image Creator (Visual Storyboarder & Reference Binder)

Given `scene_text`, `audio_duration_sec`, and `picture_change_time`:
1. Required Image Count:
   $$\text{Count} = \left\lceil \frac{\text{audio\_duration\_sec}}{\text{picture\_change\_time}} \right\rceil$$
2. Shot Progression:
   - Beat 1: Establishing wide shot of the environment.
   - Beat 2: Medium dialogue/action shot.
   - Beat 3: Close-up tension/reaction or signature item shot.
3. Reference Injection:
   - In ComfyUI workflow, link `<character>_front.png` from `bible/refs/` to lock identity and art style.
4. Output: Render and save to `scenes/scene_<XXXX>/img_01.png` ... `img_XX.png`.
```

### 7.5 `agents/05_judge.md`
```markdown
# Role: Multimodal Quality Gatekeeper

Evaluate generated media against strict acceptance criteria:

Audio Criteria:
- Score: 1 - 10. Pass threshold: `quality_audio` in `config.toml`.
- Hard-Fail: Robotic clipping, static hiss, or truncated words.

Image Criteria:
- Score: 1 - 10. Pass threshold: `quality_image` in `config.toml`.
- Hard-Fail:
  - Hands clipping through objects or hands with != 5 fingers.
  - Facial features deviating from the reference model sheet in `bible/refs/`.
  - Style deviating from `image_style_prompt`.
- If failed and `retries < retry_limit`:
  Provide `suggested_fix` (e.g., adjust camera angle, pose seed) and trigger re-render.
```

### 7.6 `agent.md` (Master Orchestrator Instructions)
```markdown
# Role: Master Pipeline Orchestrator State Machine

You coordinate the specialist sub-agents, enforce parameters in `config.toml`, and maintain `project_state.json`:

1. Initialization:
   - Load `config.toml`. Read or create `project_state.json`.
   - If only raw HTML/XHTML exists in `input/`, run `scripts/phase0_ingest.py` to create `book_clean.txt`.
2. Phase 1: World Bible:
   - If `bible_completed == false`, run `01_loremaster.md` to build `registry.json` and 4-view model sheets.
   - Set `bible_completed = true`.
3. Phase 2: Main Scene Loop (while `current_char_cursor < total_chars`):
   - Step A: Call `02_scene_finder.md` on text slice. Create `scenes/scene_<XXXX>/`.
   - Step B: Call `03_audio_master.md` to render `audio_full.wav`. Judge with `05_judge.md`.
   - Step C: Call `04_image_creator.md` to render frames based on audio duration. Judge with `05_judge.md`.
   - Step D: Advance `current_char_cursor = char_end` and increment `current_scene_index`.
4. Phase 3: Video Assembly:
   - Call `scripts/generate_scene_subtitles.py` to build styled `.ass` subtitles.
   - Call `scripts/render_scene_video.py` to composite 1080p ambient video with burned-in subtitles.
   - Call `scripts/concatenate_scenes.py` to build complete chapter movie.
```

---

## 8. Production Scripts Architecture

Each script in `scripts/` should follow these deterministic input/output signatures:

| Script | Input Arguments | Output Result |
| :--- | :--- | :--- |
| `phase0_ingest.py` | `--input <file>` `--output <book_clean.txt>` | Clean UTF-8 text with normalized paragraph breaks. |
| `build_chapter_scene_graph.py` | `--text <file>` `--registry <registry.json>` | `scene_graph.json` with entity and beat mappings. |
| `generate_scene_audio.py` | `--scene-dir <path>` `--voice <path>` | `audio_full.wav` (44.1 kHz, single-pass Drama 3). |
| `generate_scene_images.py` | `--scene-dir <path>` `--config <config.toml>` | `img_01.png` ... `img_XX.png` via ComfyUI API. |
| `generate_scene_subtitles.py` | `--scene-dir <path>` `--style <victorian>` | Styled `subtitles.ass` and `subtitles.srt`. |
| `render_scene_video.py` | `--scene-dir <path>` `--layout <ambient>` | Full HD 1080p MP4 video with Ken Burns motion. |
| `concatenate_scenes.py` | `--project-dir <path>` `--output <full_movie.mp4>` | Merged full chapter/story video without re-encoding. |

---

## 9. Programmatic Video Engine Setup (Remotion)

To create explainer, presentation, or motion-graphic video overviews of the pipeline:

### 9.1 Setup
```bash
mkdir -p remotion
cd remotion

# Initialize package.json
cat << 'EOF' > package.json
{
  "name": "ai-video-engine",
  "version": "1.0.0",
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "@remotion/player": "^4.0.0",
    "@remotion/media-utils": "^4.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "remotion": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "typescript": "^5.4.5"
  }
}
EOF

npm install
```

### 9.2 Rendering Commands
- **Interactive Preview:** `npx remotion preview`
- **Render Single Still Frame:** `npx remotion still src/index.ts <CompositionName> output/frame.png --frame <N>`
- **Render 1080p MP4 Video:** `npx remotion render src/index.ts <CompositionName> output/video.mp4 --concurrency 8`

---

## 10. End-to-End Execution Protocol

When an autonomous agent boots up on a fresh machine:

1. **Verify Software Environment:**
   Run `ffmpeg -version`, `python --version`, and `node -v` to ensure all tools exist in `PATH`.
2. **Start Backend ComfyUI Service:**
   Launch ComfyUI in the background on `http://127.0.0.1:8188`. Verify endpoint responsiveness with a `GET http://127.0.0.1:8188/system_stats`.
3. **Initialize Book Workspace:**
   Create `<PROJECT_DIR>/input/`, deposit raw book file, and write initial `project_state.json`.
4. **Phase 0 Ingestion:**
   Execute `scripts/phase0_ingest.py` to create `book_clean.txt`. Set `total_chars` in `project_state.json`.
5. **Phase 1 World Bible:**
   Execute `agents/01_loremaster.md` to populate `registry.json` and generate baseline model sheets in `bible/refs/`.
6. **Phase 2 Scene Loop:**
   Iterate until `current_char_cursor >= total_chars`:
   - Detect scene boundary with `02_scene_finder.md`.
   - Synthesize narration with `03_audio_master.md` $\to$ verify with `05_judge.md`.
   - Synthesize frames with `04_image_creator.md` $\to$ verify with `05_judge.md`.
   - Advance cursor in `project_state.json`.
7. **Phase 3 Video Production:**
   Render Victorian subtitles $\to$ encode 1080p scene videos with ambient pan/zoom $\to$ concatenate into full story movie.
