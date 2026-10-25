"""
Centralized Scene Image Generator for ComfyUI Qwen 2.1
======================================================
Executes image generation for scene beats, binding multi-angle reference portraits
and locations from the World Bible and Chapter Scene Graph to ensure visual continuity.
Enforces strict Pastel Marker Graphic Novel style lock and anti-artifact negative prompts.
"""

import sys
import os
import time
import json
import shutil
import urllib.request
import urllib.error

COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
COMFY_ROOT = os.environ.get("COMFYUI_PATH", r"C:\comfyui\ComfyUI_windows_portable\ComfyUI")
COMFY_INPUT = os.environ.get("COMFYUI_INPUT", os.path.join(COMFY_ROOT, "input"))
COMFY_OUTPUT = os.environ.get("COMFYUI_OUTPUT", os.path.join(COMFY_ROOT, "output"))

# Strict Style Anchor Constants
STYLE_PREFIX = "Pastel marker illustration, traditional graphic novel art style, clean sepia and ink outlines, muted period watercolor palette, textured paper grain, "
STYLE_SUFFIX = ", 1894 Victorian historical setting, authentic period clothing, clean hand anatomy, architectural perspective, masterpiece graphic novel illustration"

UNIVERSAL_NEGATIVE_PROMPT = (
    "photorealistic, 3d render, CGI, glossy, airbrushed, digital 3d, anime, modern photography, "
    "oversaturated neon, extra fingers, missing fingers, fused fingers, distorted hands, backward hands, "
    "hand clipping through objects, hand passing through door, upside down cards, floating props, "
    "deformed limbs, mutated face, modern clothes, text watermark, logo, blurry, bad anatomy"
)

def format_styled_prompt(prompt_text):
    """Wraps prompt with strict style prefix and suffix while avoiding duplicate keywords."""
    clean_p = prompt_text.strip().rstrip(".,")
    # Strip existing trailing generic style if present
    for generic in ["digital art, pastel marker illustration", "pastel marker illustration", "digital art"]:
        if clean_p.lower().endswith(generic):
            clean_p = clean_p[:-len(generic)].strip().rstrip(".,")
            
    return f"{STYLE_PREFIX}{clean_p}{STYLE_SUFFIX}"

def build_workflow(prompt_text, seed, prefix, ref_images=None):
    """
    Constructs ComfyUI API prompt for Qwen Image 2.1.
    If ref_images is provided (list of paths), copies them to ComfyUI input
    and binds them into TextEncodeQwenImage21.
    """
    os.makedirs(COMFY_INPUT, exist_ok=True)
    
    styled_prompt = format_styled_prompt(prompt_text)
    
    wf = {
        "1": {
            "inputs": {
                "unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                "weight_dtype": "default"
            },
            "class_type": "UNETLoader"
        },
        "2": {
            "inputs": {
                "clip_name": "qwen3vl_8b_w4a8.safetensors",
                "type": "qwen_image"
            },
            "class_type": "CLIPLoader"
        },
        "3": {
            "inputs": {
                "vae_name": "qwen_image_2.1_vae_bf16.safetensors"
            },
            "class_type": "VAELoader"
        },
        "4": {
            "inputs": {
                "model": ["1", 0],
                "device": "auto",
                "dtype": "default"
            },
            "class_type": "QwenImage21Cache"
        },
        "6": {
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "7": {
            "inputs": {
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["5", 1],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": 25,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0
            },
            "class_type": "KSampler"
        },
        "8": {
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 0]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": prefix,
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

    # TextEncode inputs with strict negative prompt
    te_inputs = {
        "clip": ["2", 0],
        "prompt": styled_prompt,
        "negative_prompt": UNIVERSAL_NEGATIVE_PROMPT,
        "resolution": 1024,
        "vae": ["3", 0]
    }

    # Handle multi-angle reference images
    if ref_images:
        for idx, ref_path in enumerate(ref_images, start=1):
            if not os.path.isabs(ref_path):
                ref_path = os.path.abspath(ref_path)
            if os.path.exists(ref_path):
                base_name = os.path.basename(ref_path)
                comfy_in_file = os.path.join(COMFY_INPUT, base_name)
                if not os.path.exists(comfy_in_file):
                    shutil.copy2(ref_path, comfy_in_file)
                
                node_id = f"10{idx}"
                wf[node_id] = {
                    "inputs": {"image": base_name},
                    "class_type": "LoadImage"
                }
                te_inputs[f"images.image_{idx}"] = [node_id, 0]
            else:
                print(f"Warning: Reference image not found: {ref_path}")

    wf["5"] = {
        "inputs": te_inputs,
        "class_type": "TextEncodeQwenImage21"
    }

    return wf

def generate_image(prompt_text, seed, output_path, ref_images=None, timeout=300):
    """Submits workflow to ComfyUI, polls for completion, and moves result to output_path."""
    prefix = os.path.splitext(os.path.basename(output_path))[0]
    wf = build_workflow(prompt_text, seed, prefix, ref_images)
    
    req_data = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        prompt_id = res.get("prompt_id")
        
    print(f"Queued prompt {prompt_id} for {output_path} (seed={seed})...", flush=True)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(3.0)
        try:
            url = f"{COMFY_URL}/history/{prompt_id}"
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if prompt_id in data:
                    status = data[prompt_id].get("status", {})
                    if status.get("status_str") == "error":
                        raise RuntimeError(f"ComfyUI execution error for {output_path}: {status.get('messages')}")
                    outputs = data[prompt_id].get("outputs", {})
                    for nid, nout in outputs.items():
                        imgs = nout.get("images", [])
                        if imgs:
                            fn = imgs[0]["filename"]
                            subfolder = imgs[0].get("subfolder", "")
                            src_img = os.path.join(COMFY_OUTPUT, subfolder, fn)
                            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                            shutil.copy2(src_img, output_path)
                            elapsed = time.time() - start_time
                            print(f"Generated {output_path} in {elapsed:.1f}s ({os.path.getsize(output_path)} bytes)", flush=True)
                            return output_path
        except RuntimeError:
            raise
        except Exception:
            pass
            
    raise TimeoutError(f"Image generation timed out after {timeout}s for {output_path}")

def generate_scene_images(scene_dir, beats):
    """
    Generates all beats for a scene.
    beats: list of dicts with:
      - 'file': filename (e.g. 'img_01.png')
      - 'prompt': text prompt
      - 'seed': integer seed
      - 'refs': list of reference file paths (optional)
    """
    results = []
    for idx, beat in enumerate(beats, 1):
        target_path = os.path.join(scene_dir, beat["file"])
        if os.path.exists(target_path):
            print(f"Beat {idx} already exists: {target_path}", flush=True)
            results.append(target_path)
            continue
            
        print(f"\n--- Generating Scene Beat {idx}/{len(beats)}: {beat['file']} ---", flush=True)
        generate_image(
            prompt_text=beat["prompt"],
            seed=beat.get("seed", 1000 + idx),
            output_path=target_path,
            ref_images=beat.get("refs", [])
        )
        results.append(target_path)
        
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ComfyUI Qwen 2.1 Scene Image Generator")
    parser.add_argument("--scene-dir", required=True, help="Scene directory path")
    parser.add_argument("--plan-file", required=True, help="JSON file with image beats plan")
    args = parser.parse_args()
    
    with open(args.plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)
        
    generate_scene_images(args.scene_dir, plan)
