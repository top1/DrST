"""
Centralized Scene Audio Generator for Fish Drama3
=================================================
Executes single-pass conditioned audio generation for audiobook scenes,
leveraging Drama3's internal ~300-byte sub-chunking with prompt history chaining
(history = own[:1] + own[1:][-1:]) to guarantee rock-solid voice continuity.
"""

import sys
import os
import time
import argparse
import tomllib
import soundfile as sf
import torch

# Register ComfyUI portable root
COMFY_ROOT = os.environ.get("COMFYUI_PATH", r"C:\comfyui\ComfyUI_windows_portable\ComfyUI")
sys.path.insert(0, COMFY_ROOT)

import comfy.model_management
import comfy.utils
import importlib

# Disable pinned memory for 8 GB VRAM stability
comfy.model_management.DISABLE_PINNED_MEMORY = True

def load_config(config_path="config.toml"):
    if not os.path.exists(config_path):
        # Check parent dir
        parent_config = os.path.join(os.path.dirname(__file__), "..", config_path)
        if os.path.exists(parent_config):
            config_path = parent_config
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
    with open(config_path, "rb") as f:
        return tomllib.load(f)

def validate_voice_reference(voice_path):
    """Ensure reference voice file exists, is readable, and contains a valid transcript."""
    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"Reference voice profile not found: {voice_path}")
        
    tensors, metadata = comfy.utils.load_torch_file(voice_path, return_metadata=True)
    if "codes" not in tensors:
        raise ValueError(f"Voice safetensors missing 'codes' tensor: {voice_path}")
        
    transcript = metadata.get("transcript", "").strip() if metadata else ""
    if not transcript:
        raise ValueError(f"Voice safetensors missing non-empty 'transcript' metadata: {voice_path}. Drama3 requires a transcript for prompt conditioning.")
        
    print(f"Validated reference voice: {voice_path}")
    print(f"  Transcript: '{transcript}'")
    print(f"  Codes shape: {tensors['codes'].shape}")
    
    return {
        "transcript": transcript,
        "codes": tensors["codes"].long()
    }

def generate_scene_audio(scene_text, output_path, config, voice_override=None, seed_override=None):
    """Executes single-pass conditioned generation of the entire scene."""
    drama3 = importlib.import_module("custom_nodes.ComfyUI-Drama3.nodes")
    Drama3Loader = drama3.Drama3Loader
    Drama3CodecLoader = drama3.Drama3CodecLoader
    Drama3Generate = drama3.Drama3Generate
    Drama3Decode = drama3.Drama3Decode

    # Configuration extraction
    model_name = config.get("audio_model_name", "drama3_w4a8experts_bf16.safetensors")
    codec_name = config.get("audio_codec_name", "drama3_codec.safetensors")
    voice_path = voice_override or config.get("narrator_voice_path", r"project/The Return of Sherlock Holmes/bible/refs/watson_narrator_english.safetensors")
    seed = seed_override if seed_override is not None else config.get("speaker_seed", 42)
    temperature = config.get("audio_temperature", 0.88)
    top_p = config.get("audio_top_p", 0.85)
    top_k = config.get("audio_top_k", 0)
    max_frames = config.get("audio_max_frames", 600)
    split_long_text = config.get("audio_split_long_text", True)

    print("=" * 60)
    print("DRAMA3 AUDIO ENGINE: SINGLE-PASS CONDITIONED GENERATION")
    print("=" * 60)
    print(f"Model: {model_name} (MoE in RAM)")
    print(f"Codec: {codec_name}")
    print(f"Voice: {voice_path}")
    print(f"Sampling: seed={seed}, temp={temperature}, top_p={top_p}, top_k={top_k}, max_frames={max_frames}")

    # Validate voice
    voice = validate_voice_reference(voice_path)
    voices = {"voice0": voice}

    # Format text: ensure each paragraph has a speaker tag for clean line transitions
    clean_text = scene_text.strip()
    import re
    clean_text = re.sub(r'\[ILLUSTRATION:[^\]]*\]', '', clean_text).strip()
    paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]
    formatted_paragraphs = []
    for p in paragraphs:
        if not p.startswith("<|speaker:"):
            formatted_paragraphs.append(f"<|speaker:0|> {p}")
        else:
            formatted_paragraphs.append(p)
    clean_text = "\n\n".join(formatted_paragraphs)

    # Load Model (MoE in RAM for 8GB VRAM)
    t0 = time.time()
    print("\nLoading Drama3 model...")
    model = Drama3Loader.execute(
        model_name=model_name,
        experts="in RAM",
        expert_cache_gb=0.0
    )[0]
    print(f"Loaded model in {time.time() - t0:.2f}s")

    t0 = time.time()
    print("Loading Codec...")
    codec = Drama3CodecLoader.execute(codec_name=codec_name)[0]
    print(f"Loaded codec in {time.time() - t0:.2f}s")

    # Generate full scene in single pass
    print(f"\nGenerating audio for {len(clean_text)} characters using internal chained history...")
    t0 = time.time()
    with torch.inference_mode():
        codes = Drama3Generate.execute(
            model=model,
            text=clean_text,
            voices=voices,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_frames=max_frames,
            split_long_text=split_long_text,
            speakers="together"  # Preserves voice continuity across internal takes
        )[0]
        gen_time = time.time() - t0
        print(f"Generation complete in {gen_time:.1f}s.")

        print("Decoding waveform with pause shortening...")
        t0 = time.time()
        audio_dict = Drama3Decode.execute(codec=codec, codes=codes, shorten_long_pauses=True)[0]
        dec_time = time.time() - t0
        print(f"Decoded waveform in {dec_time:.2f}s.")

    # Save output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    waveform = audio_dict["waveform"][0, 0].cpu().float().numpy()
    sample_rate = audio_dict["sample_rate"]
    sf.write(output_path, waveform, sample_rate)

    duration = len(waveform) / sample_rate
    print(f"\nSUCCESS: Saved master audio: {output_path}")
    print(f"Duration: {duration:.2f}s | Sample Rate: {sample_rate} Hz | Size: {os.path.getsize(output_path)} bytes")

    # Memory cleanup
    del model
    del codec
    del voices
    torch.cuda.empty_cache()
    print("Released Drama3 VRAM and GPU cache.")

    return {
        "output_path": output_path,
        "duration_sec": duration,
        "sample_rate": sample_rate,
        "file_size": os.path.getsize(output_path)
    }

def main():
    parser = argparse.ArgumentParser(description="Single-Pass Conditioned Audio Generator for Fish Drama3")
    parser.add_argument("--text-file", help="Path to text file containing scene text")
    parser.add_argument("--text", help="Direct text string to speak")
    parser.add_argument("--output", required=True, help="Path for output audio .wav")
    parser.add_argument("--config", default="config.toml", help="Path to config.toml")
    parser.add_argument("--voice", help="Path to reference voice .safetensors (overrides config)")
    parser.add_argument("--seed", type=int, help="Seed integer (overrides config)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            scene_text = f.read()
    elif args.text:
        scene_text = args.text
    else:
        raise ValueError("Either --text-file or --text must be provided.")

    generate_scene_audio(scene_text, args.output, config, voice_override=args.voice, seed_override=args.seed)

if __name__ == "__main__":
    main()
