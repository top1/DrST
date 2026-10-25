import xml.etree.ElementTree as ET
import urllib.parse
import subprocess
import shutil
import json
import re
import os

import argparse

def find_chrome():
    candidates = [
        os.environ.get("CHROME_PATH", ""),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "chrome"

parser = argparse.ArgumentParser(description="Phase 0: Book Ingestion & Canonical Illustration Extraction")
parser.add_argument("--project-dir", default=r"project/The Return of Sherlock Holmes", help="Target project directory")
args, _ = parser.parse_known_args()

PROJECT_DIR = args.project_dir
XHTML_PATH = os.path.join(PROJECT_DIR, "input", "The Return of Sherlock Holmes.xhtml")
ILLUST_DIR = os.path.join(PROJECT_DIR, "illustrations")
REFS_DIR = os.path.join(PROJECT_DIR, "bible", "refs")
BOOK_CLEAN_PATH = os.path.join(PROJECT_DIR, "book_clean.txt")
MANIFEST_PATH = os.path.join(ILLUST_DIR, "illustrations_manifest.json")
STATE_PATH = os.path.join(PROJECT_DIR, "project_state.json")
LOG_PATH = os.path.join(PROJECT_DIR, "execution.log")
CHROME_PATH = find_chrome()

os.makedirs(ILLUST_DIR, exist_ok=True)
os.makedirs(REFS_DIR, exist_ok=True)

print("=" * 60)
print("PHASE 0: BOOK INGESTION & CANONICAL ILLUSTRATION EXTRACTION")
print("=" * 60)

tree = ET.parse(XHTML_PATH)
root = tree.getroot()

articles = root.findall('.//{http://www.w3.org/1999/xhtml}article')
print(f"Loaded XHTML document: Found {len(articles)} short stories.")

# Systematic descriptive IDs for the 15 story illustrations
story_illust_metadata_map = {
    0: ("dancing_men_note_1", "figure", "A page torn from a notebook with fifteen dancing men figures"),
    1: ("dancing_men_note_2", "figure", "Second set of hieroglyphics with nine dancing men figures"),
    2: ("dancing_men_note_3", "figure", "Third set of hieroglyphics with nine dancing men and flag"),
    3: ("dancing_men_note_4", "figure", "Fourth set of hieroglyphics with five dancing men figures"),
    4: ("dancing_men_note_5", "figure", "Fifth set of hieroglyphics with two lines of dancing men"),
    5: ("dancing_man_symbol_e1", "inline_symbol", "Dancing man symbol with arms in arm and legs apart representing E"),
    6: ("dancing_man_symbol_e2", "inline_symbol", "Dancing man symbol with arms in arm and legs apart representing E"),
    7: ("dancing_man_symbol_n", "inline_symbol", "Dancing man symbol with one arm in air and one on hip representing N"),
    8: ("dancing_man_symbol_v", "inline_symbol", "Dancing man symbol with arms by side and leg straight representing V"),
    9: ("dancing_man_symbol_r", "inline_symbol", "Dancing man symbol with arms in air and leg straight representing R"),
    10: ("dancing_men_note_6", "figure", "Sixth set of hieroglyphics with fourteen dancing men and upside-down figure"),
    11: ("map_moor_priory_school", "figure", "Map of the moor and the Priory School"),
    12: ("sketch_plan_study_house", "figure", "Sketch floor plan of professor's study where Smith's body was found"),
    13: ("blotting_paper_strip", "figure", "Strip of blotting-paper with ink marks and reversed writing"),
    14: ("blotting_paper_reverse", "figure", "Reverse side of blotting-paper strip showing mirror text")
}

# Also extract titlepage ornament
titlepage_sec = root.find('.//{http://www.w3.org/1999/xhtml}section[@id="titlepage"]')
titlepage_img = titlepage_sec.find('.//{http://www.w3.org/1999/xhtml}img') if titlepage_sec is not None else None
if titlepage_img is not None and titlepage_img.attrib.get('src', '').startswith('data:'):
    t_src = titlepage_img.attrib.get('src', '')
    t_svg = urllib.parse.unquote(t_src.split(',', 1)[1])
    t_svg_path = os.path.join(ILLUST_DIR, "titlepage_ornament.svg")
    t_png_path = os.path.join(ILLUST_DIR, "titlepage_ornament.png")
    with open(t_svg_path, 'w', encoding='utf-8') as f:
        f.write(t_svg)
    # Render with chrome
    t_html = f"<!DOCTYPE html><html><body style='margin:0;padding:20px;background:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'>{t_svg}</body></html>"
    t_temp_html = os.path.join(ILLUST_DIR, "temp_titlepage.html")
    with open(t_temp_html, 'w', encoding='utf-8') as f:
        f.write(t_html)
    subprocess.run([CHROME_PATH, "--headless", "--disable-gpu", f"--screenshot={os.path.abspath(t_png_path)}", "--window-size=600,400", "--hide-scrollbars", os.path.abspath(t_temp_html)], capture_output=True)
    if os.path.exists(t_temp_html):
        os.remove(t_temp_html)
    print("Extracted titlepage ornament illustration.")

def render_svg_file(svg_content, png_dest, width=1024, height=600):
    temp_html = png_dest + ".temp.html"
    html_markup = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    margin: 0;
    padding: 24px;
    background: #ffffff;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    box-sizing: border-box;
  }}
  svg {{
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
  }}
</style>
</head>
<body>
{svg_content}
</body>
</html>
"""
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_markup)
        
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        f"--screenshot={os.path.abspath(png_dest)}",
        f"--window-size={width},{height}",
        "--hide-scrollbars",
        os.path.abspath(temp_html)
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(temp_html):
        os.remove(temp_html)

story_illust_idx = 0
illustrations_manifest = []
clean_text_segments = []
current_char_offset = 0

for art_idx, art in enumerate(articles):
    art_id = art.attrib.get('id', '')
    h2 = art.find('.//{http://www.w3.org/1999/xhtml}h2')
    story_title = "".join(h2.itertext()).strip() if h2 is not None else art_id
    
    header_block = f"{story_title.upper()}\n\n"
    clean_text_segments.append(header_block)
    current_char_offset += len(header_block)
    
    for child in art:
        tag = child.tag.split('}')[-1]
        
        if tag == 'figure':
            img = child.find('.//{http://www.w3.org/1999/xhtml}img')
            if img is not None:
                src = img.attrib.get('src', '')
                alt = img.attrib.get('alt', '').strip()
                if src.startswith('data:'):
                    svg_xml = urllib.parse.unquote(src.split(',', 1)[1])
                    svg_title_m = re.search(r'<title>(.*?)</title>', svg_xml)
                    svg_title = svg_title_m.group(1).strip() if svg_title_m else alt
                    
                    id_base, illust_type, def_desc = story_illust_metadata_map.get(
                        story_illust_idx,
                        (f"illustration_{story_illust_idx+1:02d}", "figure", alt)
                    )
                    full_id = f"illustration_{story_illust_idx+1:02d}_{id_base}"
                    
                    svg_fn = f"{full_id}.svg"
                    png_fn = f"{full_id}.png"
                    ref_fn = f"{full_id}_basic.png"
                    
                    svg_path = os.path.join(ILLUST_DIR, svg_fn)
                    png_path = os.path.join(ILLUST_DIR, png_fn)
                    ref_path = os.path.join(REFS_DIR, ref_fn)
                    
                    with open(svg_path, 'w', encoding='utf-8') as f:
                        f.write(svg_xml)
                        
                    # Calculate render dimensions from viewBox
                    vb_m = re.search(r'viewBox=[\'"]([^\'"]*)[\'"]', svg_xml)
                    w, h = 1024, 600
                    if vb_m:
                        parts = vb_m.group(1).split()
                        if len(parts) == 4:
                            try:
                                vb_w, vb_h = float(parts[2]), float(parts[3])
                                ratio = vb_h / max(vb_w, 1.0)
                                if vb_w < 500:
                                    w = 800
                                    h = max(200, int(800 * ratio) + 48)
                                else:
                                    w = 1200
                                    h = max(300, int(1200 * ratio) + 48)
                            except Exception:
                                pass
                                
                    render_svg_file(svg_xml, png_path, width=w, height=h)
                    if os.path.exists(png_path):
                        shutil.copy2(png_path, ref_path)
                        
                    marker = f"[ILLUSTRATION: {full_id} | Title: \"{svg_title}\" | Alt: \"{alt}\"]\n\n"
                    m_start = current_char_offset
                    m_end = m_start + len(marker)
                    
                    illustrations_manifest.append({
                        "id": full_id,
                        "index": story_illust_idx + 1,
                        "type": illust_type,
                        "story_id": art_id,
                        "story_title": story_title,
                        "title": svg_title,
                        "alt": alt,
                        "description": def_desc,
                        "svg_file": f"project/The Return of Sherlock Holmes/illustrations/{svg_fn}",
                        "png_file": f"project/The Return of Sherlock Holmes/illustrations/{png_fn}",
                        "ref_file": f"project/The Return of Sherlock Holmes/bible/refs/{ref_fn}",
                        "char_start": m_start,
                        "char_end": m_end
                    })
                    
                    clean_text_segments.append(marker)
                    current_char_offset += len(marker)
                    story_illust_idx += 1
                    print(f"  [{story_illust_idx:02d}/15] Rendered figure: {full_id} ({w}x{h})")
                    
        elif tag in ['p', 'blockquote']:
            parts = []
            if child.text:
                parts.append(child.text)
                
            for sub in child:
                sub_tag = sub.tag.split('}')[-1]
                if sub_tag == 'img':
                    src = sub.attrib.get('src', '')
                    alt = sub.attrib.get('alt', '').strip()
                    if src.startswith('data:'):
                        svg_xml = urllib.parse.unquote(src.split(',', 1)[1])
                        svg_title_m = re.search(r'<title>(.*?)</title>', svg_xml)
                        svg_title = svg_title_m.group(1).strip() if svg_title_m else alt
                        
                        id_base, illust_type, def_desc = story_illust_metadata_map.get(
                            story_illust_idx,
                            (f"illustration_{story_illust_idx+1:02d}", "inline_symbol", alt)
                        )
                        full_id = f"illustration_{story_illust_idx+1:02d}_{id_base}"
                        
                        svg_fn = f"{full_id}.svg"
                        png_fn = f"{full_id}.png"
                        ref_fn = f"{full_id}_basic.png"
                        
                        svg_path = os.path.join(ILLUST_DIR, svg_fn)
                        png_path = os.path.join(ILLUST_DIR, png_fn)
                        ref_path = os.path.join(REFS_DIR, ref_fn)
                        
                        with open(svg_path, 'w', encoding='utf-8') as f:
                            f.write(svg_xml)
                            
                        render_svg_file(svg_xml, png_path, width=400, height=300)
                        if os.path.exists(png_path):
                            shutil.copy2(png_path, ref_path)
                            
                        marker = f" [ILLUSTRATION: {full_id}] "
                        parts.append(marker)
                        
                        illustrations_manifest.append({
                            "id": full_id,
                            "index": story_illust_idx + 1,
                            "type": illust_type,
                            "story_id": art_id,
                            "story_title": story_title,
                            "title": svg_title,
                            "alt": alt,
                            "description": def_desc,
                            "svg_file": f"project/The Return of Sherlock Holmes/illustrations/{svg_fn}",
                            "png_file": f"project/The Return of Sherlock Holmes/illustrations/{png_fn}",
                            "ref_file": f"project/The Return of Sherlock Holmes/bible/refs/{ref_fn}",
                            "char_start": current_char_offset,
                            "char_end": current_char_offset + len(marker)
                        })
                        story_illust_idx += 1
                        print(f"  [{story_illust_idx:02d}/15] Rendered symbol: {full_id}")
                else:
                    parts.append("".join(sub.itertext()))
                    
                if sub.tail:
                    parts.append(sub.tail)
                    
            p_text = re.sub(r'[ \t]+', ' ', "".join(parts)).strip()
            if p_text:
                para_block = f"{p_text}\n\n"
                clean_text_segments.append(para_block)
                current_char_offset += len(para_block)
                
        elif tag == 'hr':
            divider = "* * *\n\n"
            clean_text_segments.append(divider)
            current_char_offset += len(divider)

full_book_clean = "".join(clean_text_segments).strip() + "\n"
total_chars = len(full_book_clean)
print(f"\nCompleted text normalization.")
print(f"Total book_clean.txt characters: {total_chars:,}")
print(f"Total illustrations cataloged: {len(illustrations_manifest)}")

with open(BOOK_CLEAN_PATH, 'w', encoding='utf-8') as f:
    f.write(full_book_clean)
print(f"Wrote clean book to: {BOOK_CLEAN_PATH}")

with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
    json.dump({
        "book": "The Return of Sherlock Holmes",
        "author": "Arthur Conan Doyle",
        "total_illustrations": len(illustrations_manifest),
        "illustrations": illustrations_manifest
    }, f, indent=2)
print(f"Wrote illustrations manifest to: {MANIFEST_PATH}")

# Initialize project_state.json
state = {
    "bible_completed": False,
    "current_char_cursor": 0,
    "total_chars": total_chars,
    "current_scene_index": 1,
    "illustrations_extracted": len(illustrations_manifest)
}
with open(STATE_PATH, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2)
print(f"Initialized state: {STATE_PATH}")

# Append to execution.log
log_msg = f"[PHASE 0] Completed book ingestion. Extracted {len(articles)} stories, {total_chars:,} characters, and {len(illustrations_manifest)} canonical illustrations with baseline PNG references.\n"
with open(LOG_PATH, 'a', encoding='utf-8') as f:
    f.write(log_msg)
print(f"Appended log: {LOG_PATH}")
print("Phase 0 complete!")
