import sys
import torch
import soundfile as sf
import comfy.utils
import comfy.model_management
import importlib

# 1. ComfyUI-Root registrieren
sys.path.insert(0, r"C:\comfyui\ComfyUI_windows_portable\ComfyUI")
comfy.model_management.DISABLE_PINNED_MEMORY = True

# 2. Drama 3 Nodes laden
drama3 = importlib.import_module("custom_nodes.ComfyUI-Drama3.nodes")
Drama3Loader = drama3.Drama3Loader
Drama3CodecLoader = drama3.Drama3CodecLoader
Drama3Generate = drama3.Drama3Generate
Drama3Decode = drama3.Drama3Decode

# 3. Modell & Codec initialisieren (MoE-Experten im RAM halten für 8GB VRAM)
model = Drama3Loader.execute(
    model_name="drama3_w4a8experts_bf16.safetensors",
    experts="in RAM",
    expert_cache_gb=0.0
)[0]
codec = Drama3CodecLoader.execute(codec_name="drama3_codec.safetensors")[0]

# 4. Optional: Gespeicherte Stimme / Voice-Clone laden (.safetensors)
tensors, metadata = comfy.utils.load_torch_file(
    r"C:\audio_gen_ai\voices\ganzschlau_male_88.safetensors", 
    return_metadata=True
)
voice = {
    "transcript": metadata.get("transcript", "Hallo!"),
    "codes": tensors["codes"].long()
}

# 5. Generieren
with torch.inference_mode():
    codes = Drama3Generate.execute(
        model=model,
        text="Willkommen in meinem neuen Projekt! [excited] Das funktioniert super.",
        voices={"voice0": voice},
        seed=42,
        temperature=0.95,
        top_p=0.9,
        top_k=0,
        max_frames=300
    )[0]

    audio_dict = Drama3Decode.execute(codec=codec, codes=codes, shorten_long_pauses=True)[0]

# 6. Als WAV speichern (44.1 kHz)
waveform = audio_dict["waveform"][0, 0].cpu().float().numpy()
sf.write("output.wav", waveform, audio_dict["sample_rate"])