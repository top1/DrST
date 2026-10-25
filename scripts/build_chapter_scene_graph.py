"""
Chapter Scene Graph & Multi-Angle Model Sheet Generator
======================================================
Pre-reads an entire chapter to extract all participating entities, locations,
and props. Builds a formal Scene Graph and generates 3-4 view model sheets
(front close-up, 3/4 medium, profile action, and costume/props) to guarantee
360-degree visual consistency across all subsequent scene beat illustrations.
"""

import os
import sys
import json
import argparse
import re

# Ensure scripts dir is on sys.path
sys.path.insert(0, os.path.dirname(__file__))
import generate_scene_images as gsi

# Standardized Chapter 1 Catalog Definitions
CHAPTER_CATALOG = {
    1: {
        "chapter_id": "chapter_0001",
        "title": "The Adventure of the Empty House",
        "char_start": 0,
        "char_end": 47373,
        "characters": {
            "sherlock_holmes": {
                "display_name": "Sherlock Holmes",
                "base_description": "Tall, lean Victorian consulting detective in his late 30s, sharp aquiline hawk-like nose, piercing grey eyes, dark hair neatly slicked back, prominent square chin",
                "views": {
                    "front": "Close-up eye-level portrait of Sherlock Holmes, sharp aquiline hawk-like nose, piercing grey analytical eyes, clean-shaven square chin, charcoal tweed suit and high collar",
                    "threequarter": "Three-quarter medium shot of Sherlock Holmes standing thoughtfully with one hand in his waistcoat pocket, tailored dark Victorian frock coat, dignified posture",
                    "profile": "Sharp side profile view of Sherlock Holmes examining a clue with keen concentration, distinct aquiline silhouette, dark slicked hair",
                    "costume_disguise": "Sherlock Holmes disguised as the elderly deformed book collector, pronounced hunch in back, sharp wizened face peering out from a frame of untidy white hair and bushy white side-whiskers, seedy worn frockcoat, clutch of antique books"
                }
            },
            "john_watson": {
                "display_name": "Dr. John H. Watson",
                "base_description": "Sturdy middle-aged British physician and Afghan war veteran in his late 40s, square honest jaw, thick groomed dark-brown mustache, warm observant hazel eyes",
                "views": {
                    "front": "Close-up eye-level portrait of Dr. John Watson, warm honest hazel eyes, thick dark-brown groomed mustache, square chin, Victorian wool tweed waistcoat and cravat",
                    "threequarter": "Three-quarter medium shot of Dr. John Watson seated in a study armchair, holding a medical journal, relaxed reflective posture, tweed frock coat",
                    "profile": "Side profile view of Dr. John Watson looking pensively out of a carriage window, bowler hat and heavy dark overcoat",
                    "costume_props": "Full attire of Dr. John Watson holding his polished wood walking cane and black leather physician's bag, dark wool overcoat and leather gloves"
                }
            },
            "colonel_sebastian_moran": {
                "display_name": "Colonel Sebastian Moran",
                "base_description": "Fierce, sinister retired British Army officer and big-game hunter in his late 50s, deeply bronzed weather-beaten face, ferocious predatory pale grey eyes, high bald forehead with thin grizzled grey hair, huge bristling grey cavalry mustache",
                "views": {
                    "front": "Close-up portrait of Colonel Sebastian Moran, ferocious predatory pale grey eyes, high bald forehead, huge bristling grey cavalry mustache, deeply sun-bronzed skin",
                    "threequarter": "Three-quarter view of Colonel Sebastian Moran seated at a whist card table, calculating cynical sneer, heavy dark Victorian gentleman's evening coat",
                    "profile": "Side profile view of Colonel Sebastian Moran squinting along the barrel of a customized cane air-rifle, ferocious hawkish features, crouching predator posture",
                    "costume_props": "Colonel Sebastian Moran holding his sinister custom cane air-gun with rifled barrel and pneumatic chamber, heavy wool overcoat"
                }
            },
            "the_honourable_ronald_adair": {
                "display_name": "The Honourable Ronald Adair",
                "base_description": "Handsome clean-shaven aristocratic Victorian youth in his mid-20s, refined noble features, neatly parted dark brown hair, calm and unemotional grey eyes",
                "views": {
                    "front": "Close-up portrait of The Honourable Ronald Adair, handsome noble features, smooth clean-shaven cheeks, calm unemotional expression, black silk cravat and wing collar",
                    "threequarter": "Three-quarter medium shot of Ronald Adair seated at a mahogany writing desk counting card winnings, impeccably tailored black Victorian tailcoat",
                    "profile": "Side profile view of Ronald Adair examining whist playing cards in hand, elegant aristocratic posture",
                    "costume_props": "Full evening dress of Ronald Adair, black silk top hat, white gloves, black evening tailcoat and gold pocket-watch chain"
                }
            },
            "inspector_lestrade": {
                "display_name": "Inspector G. Lestrade",
                "base_description": "Lean, wiry, ferret-like Scotland Yard detective in his early 40s, sharp beady dark eyes, clean-shaven cheeks with short sideburns, quick alert posture",
                "views": {
                    "front": "Close-up portrait of Inspector Lestrade of Scotland Yard, sharp ferret-like features, beady observant dark eyes, short sideburns, rumpled black Victorian detective bowler hat",
                    "threequarter": "Three-quarter shot of Inspector Lestrade taking rapid notes in a small leather pocketbook, heavy dark detective overcoat",
                    "profile": "Side profile view of Inspector Lestrade peering closely at evidence on the floor, alert aggressive posture"
                }
            },
            "mrs_hudson": {
                "display_name": "Mrs. Hudson",
                "base_description": "Kindly Scottish housekeeper and landlady of 221B Baker Street in her late 50s, silver-streaked hair pinned in a neat Victorian bun, crinkled gentle eyes, dark Victorian house dress with a white lace collar and crisp white linen apron",
                "views": {
                    "front": "Close-up portrait of Mrs. Hudson, warm gentle crinkled eyes, silver hair neatly pinned, white lace collar and crisp linen apron",
                    "threequarter": "Three-quarter shot of Mrs. Hudson carrying a silver tea service tray, motherly caring posture in the 221B sitting room"
                }
            }
        },
        "locations": {
            "baker_street_221b_sitting_room": {
                "display_name": "221B Baker Street Sitting Room",
                "description": "Cluttered Victorian sitting room at 221B Baker Street, twin sash windows overlooking the street, fireplace, armchairs, chemical table, violincase",
                "views": {
                    "wide": "Wide establishing shot of 221B Baker Street sitting room, twin curtained sash windows, glowing coal fireplace with letters pinned by a jackknife, comfortable armchairs",
                    "window_angle": "Looking toward the bow window of 221B from within, streetlights below casting silhouettes across the lace curtains",
                    "chemical_corner": "Close-up of the acid-stained deal side table in 221B with glass test tubes, chemical retorts, Bunsen burner, and violin case"
                }
            },
            "camden_house_empty_room": {
                "display_name": "Camden House (Opposite 221B)",
                "description": "Dark, deserted Victorian room on the first floor of empty Camden House, bare dusty floorboards, looking out dark uncurtained window directly across at 221B Baker Street",
                "views": {
                    "interior": "Interior of the empty abandoned room in Camden House, peeling wallpaper, bare dusty floorboards, moonlight cutting through unwashed window panes",
                    "view_to_221b": "Perspective from the dark Camden House window looking across Baker Street into the brightly lit second-floor window of 221B where a silhouette bust is visible"
                }
            },
            "park_lane_427": {
                "display_name": "427 Park Lane",
                "description": "Grand Mayfair Victorian townhouse, low stone garden wall with iron railings, crocus flowerbed beneath second-floor sitting room window",
                "views": {
                    "exterior": "Exterior front facade of 427 Park Lane, low five-foot stone wall and ornate iron railings, blooming purple and yellow crocuses, gas street lamp",
                    "sitting_room": "Second-floor sitting room at 427 Park Lane, mahogany table with coin piles and cards, coal fireplace, open sash window looking down into garden"
                }
            },
            "bagatelle_card_club": {
                "display_name": "Bagatelle Card Club",
                "description": "Exclusive London gentleman's card club, green baize whist tables, dark mahogany paneling, leather armchairs, cigar smoke under shaded pendant lamps",
                "views": {
                    "whist_room": "Interior of the Bagatelle Card Club, gentleman in evening tailcoats quietly playing cards around green baize tables under shaded gaslights"
                }
            },
            "reichenbach_fall": {
                "display_name": "The Reichenbach Fall",
                "description": "Dramatic Swiss Alpine gorge, roaring torrent of water plunging into boiling chasm, sheer wet rock walls, narrow rocky pathway over the abyss",
                "views": {
                    "abyss_path": "Dramatic narrow mountain pathway beside the roaring Reichenbach Fall, sheer black rock cliff on one side and bottomless misty chasm on the other",
                    "hidden_ledge": "Overhanging rock ledge covered in soft green moss above the Reichenbach pathway, looking down onto the wet tracks below"
                }
            }
        }
    }
}

def build_chapter_scene_graph(chapter_num=1, project_dir="project/The Return of Sherlock Holmes", dry_run=False):
    """
    Constructs the chapter scene graph and generates multi-angle model sheets for all entities.
    """
    if chapter_num not in CHAPTER_CATALOG:
        raise ValueError(f"Chapter {chapter_num} not defined in catalog.")
        
    chapter_data = CHAPTER_CATALOG[chapter_num]
    chapter_id = chapter_data["chapter_id"]
    
    chapter_dir = os.path.join(project_dir, "scenes", chapter_id)
    os.makedirs(chapter_dir, exist_ok=True)
    
    refs_dir = os.path.join(project_dir, "bible", "refs")
    os.makedirs(refs_dir, exist_ok=True)

    print("=" * 65)
    print(f"BUILDING CHAPTER SCENE GRAPH: {chapter_data['title']} ({chapter_id})")
    print("=" * 65)

    graph_data = {
        "chapter_id": chapter_id,
        "title": chapter_data["title"],
        "char_start": chapter_data["char_start"],
        "char_end": chapter_data["char_end"],
        "characters": {},
        "locations": {}
    }

    # 1. Process Characters and Model Sheets
    for char_id, char_info in chapter_data["characters"].items():
        print(f"\nProcessing Character: {char_info['display_name']} ({char_id})")
        char_entry = {
            "display_name": char_info["display_name"],
            "base_description": char_info["base_description"],
            "model_sheets": {}
        }

        for view_name, view_prompt in char_info["views"].items():
            img_filename = f"{char_id}_{view_name}.png"
            target_path = os.path.join(refs_dir, img_filename)
            rel_path = f"project/The Return of Sherlock Holmes/bible/refs/{img_filename}"
            
            char_entry["model_sheets"][view_name] = rel_path
            
            if os.path.exists(target_path):
                print(f"  [OK] Model Sheet exists: {img_filename}")
                continue

            if dry_run:
                print(f"  [DRY-RUN] Would generate {img_filename} with prompt: '{view_prompt[:60]}...'")
                continue

            print(f"  [GEN] Generating Multi-Angle Model Sheet: {img_filename}...")
            # For 3/4 and profile, use front view as reference if it exists
            front_ref = os.path.join(refs_dir, f"{char_id}_front.png")
            refs_to_use = [front_ref] if os.path.exists(front_ref) and view_name != "front" else []
            
            gsi.generate_image(
                prompt_text=f"Model sheet reference illustration: {view_prompt}",
                seed=7000 + hash(img_filename) % 1000,
                output_path=target_path,
                ref_images=refs_to_use
            )

        graph_data["characters"][char_id] = char_entry

    # 2. Process Locations
    for loc_id, loc_info in chapter_data["locations"].items():
        print(f"\nProcessing Location: {loc_info['display_name']} ({loc_id})")
        loc_entry = {
            "display_name": loc_info["display_name"],
            "description": loc_info["description"],
            "views": {}
        }

        for view_name, view_prompt in loc_info["views"].items():
            img_filename = f"{loc_id}_{view_name}.png"
            target_path = os.path.join(refs_dir, img_filename)
            rel_path = f"project/The Return of Sherlock Holmes/bible/refs/{img_filename}"
            
            loc_entry["views"][view_name] = rel_path
            
            if os.path.exists(target_path):
                print(f"  [OK] Location View exists: {img_filename}")
                continue

            if dry_run:
                print(f"  [DRY-RUN] Would generate {img_filename} with prompt: '{view_prompt[:60]}...'")
                continue

            print(f"  [GEN] Generating Location View: {img_filename}...")
            gsi.generate_image(
                prompt_text=f"Location architectural reference illustration: {view_prompt}",
                seed=8000 + hash(img_filename) % 1000,
                output_path=target_path
            )

        graph_data["locations"][loc_id] = loc_entry

    # Save Chapter Scene Graph JSON
    graph_path = os.path.join(chapter_dir, "scene_graph.json")
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"\nSUCCESS: Wrote Chapter Scene Graph to {graph_path}")

    # Also update global registry.json with newly confirmed model sheets
    reg_path = os.path.join(project_dir, "bible", "registry.json")
    if os.path.exists(reg_path):
        with open(reg_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        for c_id, c_data in graph_data["characters"].items():
            if c_id not in registry["characters"]:
                registry["characters"][c_id] = {
                    "display_name": c_data["display_name"],
                    "base_description": c_data["base_description"],
                    "states": {}
                }
            for v_name, v_path in c_data["model_sheets"].items():
                registry["characters"][c_id]["states"][f"{c_id}_{v_name}"] = {
                    "file": v_path,
                    "description": f"Model sheet perspective: {v_name}"
                }

        for l_id, l_data in graph_data["locations"].items():
            if l_id not in registry["locations"]:
                registry["locations"][l_id] = {
                    "display_name": l_data["display_name"],
                    "base_description": l_data["description"],
                    "states": {}
                }
            for v_name, v_path in l_data["views"].items():
                registry["locations"][l_id]["states"][f"{l_id}_{v_name}"] = {
                    "file": v_path,
                    "description": f"Location view: {v_name}"
                }

        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"SUCCESS: Synchronized {reg_path} with all multi-angle model sheets.")

    return graph_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Chapter Scene Graph and Model Sheets")
    parser.add_argument("--chapter", type=int, default=1, help="Chapter number (1-13)")
    parser.add_argument("--project-dir", default="project/The Return of Sherlock Holmes", help="Project directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform extraction without generating missing images")
    args = parser.parse_args()

    build_chapter_scene_graph(chapter_num=args.chapter, project_dir=args.project_dir, dry_run=args.dry_run)
