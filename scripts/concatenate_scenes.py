"""
Scene Concatenator for Sherlock Holmes Video Pipeline
=====================================================
Losslessly stitches multiple rendered scene videos into a full chapter or story MP4.
"""

import os
import glob
import argparse
import subprocess

def concatenate_scenes(project_dir, video_name="video_ambient.mp4", output_path=None):
    scenes_root = os.path.join(project_dir, "scenes")
    if not os.path.exists(scenes_root):
        raise FileNotFoundError(f"Scenes root not found: {scenes_root}")

    # Find all scene folders sorted
    scene_dirs = sorted(glob.glob(os.path.join(scenes_root, "scene_*")))
    valid_videos = []
    
    for s_dir in scene_dirs:
        # Check for specified video_name or fallback to video.mp4
        target_vid = os.path.join(s_dir, video_name)
        if not os.path.exists(target_vid):
            alt_vid = os.path.join(s_dir, "video.mp4")
            if os.path.exists(alt_vid):
                target_vid = alt_vid
            else:
                continue
        valid_videos.append(target_vid)

    if not valid_videos:
        raise FileNotFoundError(f"No rendered '{video_name}' files found in {scenes_root}")

    print(f"\nFound {len(valid_videos)} scene videos to concatenate:")
    for v in valid_videos:
        print(f"  + {v} ({os.path.getsize(v) / (1024*1024):.2f} MB)")

    if not output_path:
        story_name = os.path.basename(os.path.abspath(project_dir)).replace(" ", "_")
        output_path = os.path.join(project_dir, f"{story_name}_combined.mp4")

    # Write concat list
    concat_list = os.path.join(project_dir, "concat_scenes.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for v in valid_videos:
            clean = os.path.abspath(v).replace("\\", "/")
            f.write(f"file '{clean}'\n")

    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", "-y", output_path
    ]
    print(f"\nConcatenating {len(valid_videos)} scenes into {output_path}...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Concatenation error: {res.stderr}")

    # Cleanup list
    if os.path.exists(concat_list):
        os.remove(concat_list)

    file_size = os.path.getsize(output_path)
    print(f"\nSUCCESS: Created combined video: {output_path}")
    print(f"Total Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatenate scene videos into full chapter MP4")
    parser.add_argument("--project-dir", default="project/The Return of Sherlock Holmes", help="Project directory")
    parser.add_argument("--video-name", default="video_ambient.mp4", help="Video filename in each scene dir")
    parser.add_argument("--output", help="Optional output path")
    args = parser.parse_args()

    concatenate_scenes(args.project_dir, video_name=args.video_name, output_path=args.output)
