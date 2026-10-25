### 2.2 Qwen-Image 2.1

Qwen-Image 2.1 is the premier choice for complex compositional reasoning, multi-reference image blending, localized inpainting, and text-guided adjustments.
https://qwen.ai/blog?id=qwen-image-2.1


**Installed Models:**
  * Diffusion: `models/diffusion_models/qwen_image_2.1_int8_convrot.safetensors`

  * Text Encoder: `models/text_encoders/qwen3vl_8b_w4a8.safetensors` or `Qwen3-4B-UD-Q6_K_XL.gguf`

  * VAE: `models/vae/qwen_image_2.1_vae_bf16.safetensors`

**Custom Nodes:**
  * `TextEncodeQwenImage21`: Supports input slots for `<image1>`, `<image2>`, prompt, negative prompt, and resolution.

  * `QwenImage21Cache`: Caches KV representations to accelerate consecutive prompts.

**Execution Parameters:**
  * Steps: **25 steps**

  * Sampler: `Euler` | Scheduler: `Simple` | CFG: `2.5 – 3.5`

  * Generation Time: **~48 – 72 seconds**

**Template Reference:**
  * Clean API JSON: `C:\MathKnight\math-knight\assets\prototypes\comfy_api_template.json`