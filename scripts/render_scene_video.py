"""
Centralized Scene Video Renderer for Sherlock Holmes Video Pipeline
===================================================================
Renders modern 16:9 (1920x1080) Full HD video synchronized with audio master
and visual beats from manifest.json, supporting Ambient Blur, Ken Burns pan/zoom,
and Victorian styled subtitles.
"""

import os
import sys
import json
import shutil
import tempfile
import argparse
import subprocess

# Ensure scripts dir is on sys.path to import generate_scene_subtitles
sys.path.insert(0, os.path.dirname(__file__))
import generate_scene_subtitles as gss

def check_nvenc():
    """Check if h264_nvenc encoder is available and working."""
    try:
        res = subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return res.returncode == 0
    except Exception:
        return False

def render_beat_ambient(img_path, duration_sec, out_path, fps=30, encoder="h264_nvenc"):
    """Renders a single beat using ambient blurred background + crisp centered foreground."""
    filter_graph = (
        "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=25:5,eq=brightness=-0.25[bg];"
        "[0:v]scale=-1:960[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-loop", "1", "-t", f"{duration_sec:.3f}", "-i", img_path,
        "-filter_complex", filter_graph,
        "-r", str(fps), "-c:v", encoder
    ]
    if encoder == "h264_nvenc":
        cmd.extend(["-preset", "p4", "-cq", "22"])
    else:
        cmd.extend(["-preset", "medium", "-crf", "22"])
    cmd.extend(["-y", out_path])
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error rendering ambient beat {img_path}: {res.stderr}")

def render_beat_kenburns(img_path, duration_sec, out_path, beat_idx=1, fps=30, encoder="h264_nvenc"):
    """Renders a single beat using dynamic Ken Burns slow pan and zoom."""
    frames = max(int(duration_sec * fps), 1)
    
    # Alternate pan/zoom directions based on beat index
    mode = beat_idx % 4
    if mode == 1:
        # Slow zoom in toward center
        zoom_expr = "min(zoom+0.0004,1.15)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 2:
        # Slow zoom out from center
        zoom_expr = "max(1.15-0.0004*on,1.0)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 3:
        # Pan slightly upward with gentle zoom
        zoom_expr = "min(zoom+0.0003,1.12)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"(ih/2-(ih/zoom/2))-((on/{frames})*25)"
    else:
        # Pan slightly downward with gentle zoom
        zoom_expr = "min(zoom+0.0003,1.12)"
        x_expr = f"(iw/2-(iw/zoom/2))+((on/{frames})*20)"
        y_expr = f"(ih/2-(ih/zoom/2))+((on/{frames})*20)"

    vf = f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s=1920x1080:fps={fps},format=yuv420p"
    
    cmd = [
        "ffmpeg", "-framerate", str(fps), "-i", img_path,
        "-vf", vf,
        "-c:v", encoder
    ]
    if encoder == "h264_nvenc":
        cmd.extend(["-preset", "p4", "-cq", "22"])
    else:
        cmd.extend(["-preset", "medium", "-crf", "22"])
    cmd.extend(["-y", out_path])

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error rendering Ken Burns beat {img_path}: {res.stderr}")

def render_beat_pillarbox(img_path, duration_sec, out_path, fps=30, encoder="h264_nvenc"):
    """Renders a single beat centered on 1920x1080 black matte."""
    vf = "scale=-1:1080,pad=1920:1080:(ow-iw)/2:0:black,format=yuv420p"
    cmd = [
        "ffmpeg", "-loop", "1", "-t", f"{duration_sec:.3f}", "-i", img_path,
        "-vf", vf,
        "-r", str(fps), "-c:v", encoder
    ]
    if encoder == "h264_nvenc":
        cmd.extend(["-preset", "p4", "-cq", "22"])
    else:
        cmd.extend(["-preset", "medium", "-crf", "22"])
    cmd.extend(["-y", out_path])

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error rendering pillarbox beat {img_path}: {res.stderr}")

def render_scene_video(scene_dir, layout="ambient", subtitles=True, output_path=None, fps=30, encoder=None):
    """
    Renders complete scene video with matching audio, 1080p layout, and subtitles.
    """
    manifest_path = os.path.join(scene_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"manifest.json not found in {scene_dir}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Audio master
    audio_file = manifest.get("audio", {}).get("file", "audio_full.wav")
    audio_path = os.path.join(scene_dir, audio_file)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    total_audio_sec = manifest["audio"]["duration_sec"]
    images = manifest.get("visuals", {}).get("images", [])
    if not images:
        raise ValueError(f"No visual images found in manifest for {scene_dir}")

    # Determine encoder
    if not encoder:
        encoder = "h264_nvenc" if check_nvenc() else "libx264"
    print(f"\n========================================================", flush=True)
    print(f"RENDERING SCENE VIDEO: {os.path.basename(scene_dir)}", flush=True)
    print(f"========================================================", flush=True)
    print(f"Layout Mode: {layout.upper()}", flush=True)
    print(f"Subtitles: {'ENABLED' if subtitles else 'DISABLED'}", flush=True)
    print(f"Encoder: {encoder}", flush=True)
    print(f"Audio Duration: {total_audio_sec:.2f}s | Beats: {len(images)}", flush=True)

    # Ensure subtitles exist
    ass_path = os.path.join(scene_dir, "subtitles.ass")
    if subtitles and not os.path.exists(ass_path):
        print("Generating scene subtitles...", flush=True)
        gss.generate_subtitles(scene_dir)

    # Output path
    if not output_path:
        output_path = os.path.join(scene_dir, "video.mp4")

    # Temporary directory for beat clips
    temp_dir = tempfile.mkdtemp(prefix="sh_scene_")
    try:
        beat_files = []
        for idx, img_info in enumerate(images, start=1):
            img_rel = img_info["file"]
            img_path = os.path.join(scene_dir, img_rel)
            dur = img_info.get("duration_sec", total_audio_sec / len(images))
            
            beat_out = os.path.join(temp_dir, f"beat_{idx:03d}.mp4")
            print(f"Rendering beat {idx:02d}/{len(images):02d} ({img_rel}, {dur:.2f}s)...", flush=True)
            
            if layout == "kenburns":
                render_beat_kenburns(img_path, dur, beat_out, beat_idx=idx, fps=fps, encoder=encoder)
            elif layout == "pillarbox":
                render_beat_pillarbox(img_path, dur, beat_out, fps=fps, encoder=encoder)
            else:
                render_beat_ambient(img_path, dur, beat_out, fps=fps, encoder=encoder)
                
            beat_files.append(beat_out)

        # Create concat demuxer file
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for bf in beat_files:
                clean_path = bf.replace("\\", "/")
                f.write(f"file '{clean_path}'\n")

        print("\nConcatenating beats and multiplexing audio...", flush=True)
        combined_video = os.path.join(temp_dir, "combined_video.mp4")
        concat_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-c", "copy", "-y", combined_video
        ]
        res = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Concat error: {res.stderr}")

        # Step 2: Multiplex audio and apply subtitles (if enabled)
        final_cmd = [
            "ffmpeg", "-i", combined_video, "-i", audio_path
        ]
        
        if subtitles and os.path.exists(ass_path):
            clean_ass = ass_path.replace("\\", "/")
            if len(clean_ass) > 2 and clean_ass[1] == ":":
                clean_ass = clean_ass[0] + "\\:" + clean_ass[2:]
            final_cmd.extend(["-vf", f"ass='{clean_ass}'"])
            final_cmd.extend(["-c:v", encoder])
            if encoder == "h264_nvenc":
                final_cmd.extend(["-preset", "p4", "-cq", "20"])
            else:
                final_cmd.extend(["-preset", "medium", "-crf", "20"])
        else:
            final_cmd.extend(["-c:v", "copy"])

        final_cmd.extend([
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-y", output_path
        ])

        print(f"Muxing master video: {output_path}...", flush=True)
        res = subprocess.run(final_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Final muxing error: {res.stderr}")

        file_size = os.path.getsize(output_path)
        print(f"\nSUCCESS: Rendered scene video: {output_path}", flush=True)
        print(f"Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)", flush=True)
        return output_path

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render 1080p video from scene assets")
    parser.add_argument("--scene-dir", required=True, help="Path to scene directory")
    parser.add_argument("--layout", default="ambient", choices=["ambient", "kenburns", "pillarbox"], help="Visual layout mode")
    parser.add_argument("--subtitles", action="store_true", default=True, help="Burn in Victorian subtitles")
    parser.add_argument("--no-subtitles", dest="subtitles", action="store_false", help="Disable subtitles")
    parser.add_argument("--output", help="Optional output MP4 path")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--encoder", choices=["h264_nvenc", "libx264"], help="Video encoder override")
    args = parser.parse_args()

    render_scene_video(
        scene_dir=args.scene_dir,
        layout=args.layout,
        subtitles=args.subtitles,
        output_path=args.output,
        fps=args.fps,
        encoder=args.encoder
    )
