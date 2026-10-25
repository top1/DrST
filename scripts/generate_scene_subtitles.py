"""
Victorian Subtitle Generator for Sherlock Holmes Video Pipeline
==============================================================
Generates styled Advanced SubStation Alpha (.ass) and SubRip (.srt) subtitles
synchronized to scene audio and manifest beat timestamps.
"""

import os
import re
import json
import argparse

def format_ass_time(seconds):
    """Format seconds into ASS time format: h:mm:ss.cc"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs}:{mins:02d}:{secs:05.2f}"

def format_srt_time(seconds):
    """Format seconds into SRT time format: hh:mm:ss,ms"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def split_into_caption_chunks(text, max_chars=65):
    """Splits prose text into readable caption cards (1-2 lines, 30-65 chars)."""
    chunks = []
    paragraphs = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
    
    for p in paragraphs:
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', p)
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(s) <= max_chars:
                chunks.append(s)
                continue
                
            # Split long sentences on clause punctuation (commas, semicolons, em-dashes)
            clauses = re.split(r'(?<=[,;:\u2014])\s+', s)
            current = ""
            for cl in clauses:
                if not current:
                    current = cl
                elif len(current) + 1 + len(cl) <= max_chars:
                    current += " " + cl
                else:
                    chunks.append(current.strip())
                    current = cl
            if current:
                # If still too long, break on word boundaries
                words = current.split()
                line = ""
                for w in words:
                    if not line:
                        line = w
                    elif len(line) + 1 + len(w) <= max_chars:
                        line += " " + w
                    else:
                        chunks.append(line.strip())
                        line = w
                if line:
                    chunks.append(line.strip())

    # Merge orphaned trailing fragments (< 15 chars) into preceding chunk if total <= 75 chars
    merged = []
    for c in chunks:
        if merged and len(c) < 15 and len(merged[-1]) + 1 + len(c) <= 75:
            merged[-1] += " " + c
        else:
            merged.append(c)
            
    return merged

def generate_subtitles(scene_dir, font_name="Georgia", font_size=32):
    """Reads manifest.json in scene_dir and creates subtitles.ass and subtitles.srt."""
    manifest_path = os.path.join(scene_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"manifest.json not found in {scene_dir}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scene_text = manifest["scene_text"]
    total_duration = manifest["audio"]["duration_sec"]
    
    chunks = split_into_caption_chunks(scene_text)
    total_chars = sum(len(c) for c in chunks)
    
    events = []
    current_time = 0.0
    
    for idx, chunk in enumerate(chunks):
        # Duration proportional to character length with minimum 1.5s
        prop_dur = (len(chunk) / total_chars) * total_duration
        start_t = current_time
        end_t = min(start_t + prop_dur, total_duration)
        if idx == len(chunks) - 1:
            end_t = total_duration
            
        events.append({
            "index": idx + 1,
            "start": start_t,
            "end": end_t,
            "text": chunk
        })
        current_time = end_t

    # Write ASS format
    ass_path = os.path.join(scene_dir, "subtitles.ass")
    ass_content = f"""[Script Info]
Title: Sherlock Holmes - {os.path.basename(scene_dir)}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: VictorianDefault,{font_name},{font_size},&H00F0F6F8,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2.5,2,2,100,100,55,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for ev in events:
        s_str = format_ass_time(ev["start"])
        e_str = format_ass_time(ev["end"])
        text = ev["text"].replace("\n", "\\N")
        ass_content += f"Dialogue: 0,{s_str},{e_str},VictorianDefault,,0,0,0,,{text}\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    # Write SRT format
    srt_path = os.path.join(scene_dir, "subtitles.srt")
    srt_content = ""
    for ev in events:
        s_str = format_srt_time(ev["start"])
        e_str = format_srt_time(ev["end"])
        srt_content += f"{ev['index']}\n{s_str} --> {e_str}\n{ev['text']}\n\n"

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"Generated subtitles for {scene_dir}:")
    print(f"  ASS: {ass_path} ({len(events)} cards)")
    print(f"  SRT: {srt_path}")
    
    return ass_path, srt_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ASS and SRT subtitles for scene")
    parser.add_argument("--scene-dir", required=True, help="Path to scene directory containing manifest.json")
    parser.add_argument("--font", default="Georgia", help="Font name for ASS subtitles")
    parser.add_argument("--size", type=int, default=32, help="Font size in points")
    args = parser.parse_args()

    generate_subtitles(args.scene_dir, font_name=args.font, font_size=args.size)
