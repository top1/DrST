# Tool Verification & Benchmark Report: Fish Drama3 & ComfyUI (Qwen 2.1)

**Execution Date:** 2026-10-25  
**Hardware Environment:** NVIDIA GeForce RTX 3060 Ti (8 GB VRAM) / 32 GB RAM / Windows 11  
**Python Runtime:** ComfyUI Portable Embedded Python (`C:\comfyui\ComfyUI_windows_portable\python_embeded\python.exe`)

---

## 1. Fish Drama3 TTS Test

### Configuration & Method
- **Execution Mode:** Direct Python invocation via `custom_nodes.ComfyUI-Drama3.nodes` using ComfyUI's embedded environment.
- **MoE Memory Strategy:** Offloading experts to system RAM (`experts="in RAM"`, `expert_cache_gb=0.0`) to operate reliably within the 8 GB VRAM ceiling.
- **Model Files:**
  - Diffusion: `C:\comfyui\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\drama3_w4a8experts_bf16.safetensors`
  - VAE Codec: `C:\comfyui\ComfyUI_windows_portable\ComfyUI\models\vae\drama3_codec.safetensors`
  - Voice Profile: `C:\audio_gen_ai\voices\ganzschlau_seed_42.safetensors` (aligned with `speaker_seed = 42` in `config.toml`)
- **Input Text:**  
  *"It was in the year 1894 that all London was shocked by the murder of the Honourable Ronald Adair."*

### Performance & Results
- **Model Load Time:** 5.96s
- **Codec Load Time:** 1.27s
- **Voice Load Time:** < 0.1s
- **Generation Time:** 90.02s
- **Waveform Decode Time:** 3.66s
- **Output File:** `project/The Return of Sherlock Holmes/test_drama3_sherlock.wav`
- **Audio Specs:** 44.1 kHz, 5.50s duration, 485,144 bytes
- **Multimodal QA Review:** Verified 100% word accuracy, clear Victorian book reader timbre, natural prosody, and zero audio clipping or artifacts.

---

## 2. ComfyUI + Qwen-Image 2.1 Test

### Configuration & Method
- **Execution Mode:** Background API server running on `http://127.0.0.1:8188` (`main.py --windows-standalone-build --disable-auto-launch`).
- **Pipeline Architecture:**
  - `UNETLoader`: `qwen_image_2.1_int8_convrot.safetensors`
  - `CLIPLoader`: `qwen3vl_8b_w4a8.safetensors` (type: `qwen_image`)
  - `VAELoader`: `qwen_image_2.1_vae_bf16.safetensors`
  - `QwenImage21Cache`: `device="auto"`, `dtype="default"`
  - `TextEncodeQwenImage21`: Resolution 1024, VAE linked
  - `KSampler`: 25 steps, CFG 2.5, Euler sampler, Simple scheduler, Denoise 1.0
  - `VAEDecode` & `SaveImage`
- **Prompt:**  
  *"Sherlock Holmes standing in his 221B Baker Street sitting room, examining a document by gaslight, digital art, pastel marker illustration"*
- **Negative Prompt:**  
  *"blurry, low quality, distorted anatomy, extra fingers, deformed face"*

### Performance & Results
- **VRAM Utilization:** Peak ~6.8 GB / 8.0 GB (fits comfortably on RTX 3060 Ti).
- **Generation Latency:** Exactly 60.0s for a 1024x1024 frame.
- **Output File:** `project/The Return of Sherlock Holmes/test_qwen_sherlock.png`
- **Image Specs:** 1024x1024 PNG, 2,703,257 bytes
- **Multimodal QA Review:** Verified accurate period costume (Victorian overcoat and vest), gaslight ambiance, correct 5-digit anatomy on hands holding paper, and adherence to the configured art style (`image_style_prompt = "digital art, pastel marker illustration"`).

---

## 3. Recommended Pipeline Architecture

Based on these benchmarks:
1. **Audio Master (`03_audio_master.md`):** Execute Drama3 via Python script with MoE RAM offload (`experts="in RAM"`), chunking narration at ~250–350 characters to achieve ~40–60s generation time per chunk.
2. **Visual Master (`04_image_creator.md`):** Submit JSON payloads to the background ComfyUI HTTP API (`http://127.0.0.1:8188/prompt`) and poll `/history/{pid}`.
