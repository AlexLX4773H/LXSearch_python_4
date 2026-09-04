#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Move_From_Source_standalone.py

Cross-platform standalone script to match and move releases from source folders
into series destination folders based on circle/parody brackets and ComicInfo metadata.

Features:
- Pure Python standard library: no external dependencies.
- Cross-platform: works on Linux, Windows, Android (Termux/Pydroid), and macOS.
- Extracts series/parody candidates from folder names (circle brackets).
- Extracts metadata from ComicInfo files (ComicInfo.xml, ComicInfo.json) in loose folders,
  subdirectories, and inside CBZ / ZIP archives.
- Matches candidate names against output_list_name.json.
- Supports CLI arguments (--source, --dest, --dry-run, --yes) as well as default paths.
"""

import os
import sys
import re
import json
import shutil
import argparse
import zipfile
import xml.etree.ElementTree as ET

# Ensure UTF-8 output encoding across platforms
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# -------------------------------------------------------------------------
# Configuration & Path Resolution
# -------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
DEFAULT_INPUT_DIR = os.path.join(SCRIPT_DIR, "input")

# Candidate destination directories across Android, Windows, and Linux/WSL
CANDIDATE_DESTINATIONS = [
    "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2",
]

# Candidate source directories across Android, Windows, and Linux/WSL
CANDIDATE_SOURCES = [
    # Android ( Mihon / Vere2)
    "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 new",
    "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 S",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/NineHentai (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/NHentai (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/nHentai.com (unoriginal) (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/E-Hentai (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/Hennojin (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/HentaiHand (ALL)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/HentaiHand (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/AsmHentai (EN)",
    "/storage/emulated/0/Vere2/Vere/Mihon/downloads/NHentai.xxx (EN)",
]

# Patterns for extracting bracketed tokens
PATTERN_SQUARE = re.compile(r"(\[([^\]]+)\])")
PATTERN_CIRCLE = re.compile(r"(\(([^\)]+)\))")

# Case-insensitive ComicInfo filenames
VALID_COMICINFO_NAMES = {'comicinfo.xml', 'comic_info.xml', 'comicinfo.json', 'comic_info.json'}

# Regex patterns for summary/description line matching
PARODIES_PAT = re.compile(r'^\s*(?:\*\*)?\s*parod(?:ies|y)\s*(?:\*\*)?\s*:\s*(.+)$', re.IGNORECASE)
SERIES_PAT = re.compile(r'^\s*(?:\*\*)?\s*series\s*(?:\*\*)?\s*:\s*(.+)$', re.IGNORECASE)
GROUPS_PAT = re.compile(r'^\s*(?:\*\*)?\s*(?:groups?|circles?)\s*(?:\*\*)?\s*:\s*(.+)$', re.IGNORECASE)


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def deduplicate_list(items):
    """Preserves order while removing duplicates."""
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def check_valid_regex(text, regex_list):
    """Returns True if text does NOT match any regex pattern in regex_list."""
    lower_text = text.lower()
    for pattern in regex_list:
        try:
            if re.search(pattern, lower_text):
                return False
        except Exception:
            pass
    return True


def load_exclusions(input_dir=None):
    """Loads exclude_in_brackets.txt and exclude_in_brackets_re.txt safely."""
    input_dir = input_dir or DEFAULT_INPUT_DIR
    exclude_brackets = set()
    exclude_brackets_re = []

    file_txt = os.path.join(input_dir, "exclude_in_brackets.txt")
    if os.path.exists(file_txt):
        try:
            with open(file_txt, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    s = line.strip().lower()
                    if s:
                        exclude_brackets.add(s)
        except Exception as e:
            print(f"Warning reading {file_txt}: {e}")

    file_re = os.path.join(input_dir, "exclude_in_brackets_re.txt")
    if os.path.exists(file_re):
        try:
            with open(file_re, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    s = line.strip()
                    if s:
                        exclude_brackets_re.append(s)
        except Exception as e:
            print(f"Warning reading {file_re}: {e}")

    return exclude_brackets, exclude_brackets_re


def load_json_mapping(json_path=None):
    """Loads output_list_name.json and builds a mapping dictionary."""
    if not json_path:
        json_path = os.path.join(DEFAULT_OUTPUT_DIR, "output_list_name.json")

    if not os.path.exists(json_path):
        print(f"Error: JSON mapping file not found: {json_path}")
        return [], {}

    try:
        with open(json_path, "r", encoding="utf-8", errors="replace") as f:
            list_dict_data = json.load(f)
    except Exception as e:
        print(f"Error reading {json_path}: {e}")
        return [], {}

    # Build fast lookup dictionary: lower_key -> Canonical Name
    mapping = {}
    for item in list_dict_data:
        canonical_name = item.get("Name")
        if not canonical_name:
            continue
        # Also map canonical name itself
        name_lower = canonical_name.strip().lower()
        if name_lower not in mapping:
            mapping[name_lower] = canonical_name
        for alias in item.get("List", []):
            alias_lower = str(alias).strip().lower()
            if alias_lower and alias_lower not in mapping:
                mapping[alias_lower] = canonical_name

    return list_dict_data, mapping


# -------------------------------------------------------------------------
# Bracket Extraction Logic
# -------------------------------------------------------------------------
def extract_folder_circles(folder_name, exclude_brackets, exclude_brackets_re):
    """
    Extracts circle bracket items (...) from folder name.
    Square brackets [...] are removed first to prevent author info contamination.
    Returns cleaned, lowercase, filtered items in reversed order (matching Move_From_Source.py).
    """
    # 1. Remove all square brackets and their contents
    squares = PATTERN_SQUARE.findall(folder_name)
    without_squares = folder_name
    for sq in squares:
        without_squares = without_squares.replace(sq[0], '')

    # 2. Extract circle brackets
    circles = PATTERN_CIRCLE.findall(without_squares)
    circle_items = [c[1].strip().lower() for c in circles if c[1].strip()]

    # 3. Filter using exclusions and regex list
    filtered_items = []
    for item in circle_items:
        if item in exclude_brackets:
            continue
        if not check_valid_regex(item, exclude_brackets_re):
            continue
        filtered_items.append(item)

    # Deduplicate and reverse order (last circle bracket first)
    deduped = deduplicate_list(filtered_items)
    deduped.reverse()
    return deduped


# -------------------------------------------------------------------------
# ComicInfo Extraction Logic
# -------------------------------------------------------------------------
def _parse_comicinfo_content(content, is_json=False):
    """
    Extracts raw parodies, series, and groups strings from XML or JSON text/bytes.
    Never raises an exception.
    """
    parody_raw = ''
    series_raw = ''
    group_raw = ''

    try:
        if is_json:
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            data = json.loads(content)
            parody_raw = str(data.get('parodies') or data.get('parody') or '')
            series_raw = str(data.get('series') or '')
            group_raw = str(data.get('groups') or data.get('group') or data.get('circle') or data.get('circles') or '')
            summary = str(data.get('summary') or data.get('description') or data.get('notes') or '')
            if summary:
                for line in summary.splitlines():
                    line = line.strip()
                    if not parody_raw:
                        m_par = PARODIES_PAT.match(line)
                        if m_par:
                            parody_raw = m_par.group(1).strip()
                    if not series_raw:
                        m_ser = SERIES_PAT.match(line)
                        if m_ser:
                            series_raw = m_ser.group(1).strip()
                    if not group_raw:
                        m_grp = GROUPS_PAT.match(line)
                        if m_grp:
                            group_raw = m_grp.group(1).strip()
        else:
            # Parse XML
            if isinstance(content, str):
                content_bytes = content.encode('utf-8', errors='replace')
            else:
                content_bytes = content

            root = ET.fromstring(content_bytes)

            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1].lower()
                text = (elem.text or '').strip()
                if not text:
                    continue
                if tag_name in ('parodies', 'parody') and not parody_raw:
                    parody_raw = text
                elif tag_name == 'series' and not series_raw:
                    series_raw = text
                elif tag_name in ('groups', 'group', 'circle', 'circles', 'teams', 'team') and not group_raw:
                    group_raw = text
                elif tag_name in ('summary', 'description', 'notes'):
                    for line in text.splitlines():
                        line = line.strip()
                        if not parody_raw:
                            m_par = PARODIES_PAT.match(line)
                            if m_par:
                                parody_raw = m_par.group(1).strip()
                        if not series_raw:
                            m_ser = SERIES_PAT.match(line)
                            if m_ser:
                                series_raw = m_ser.group(1).strip()
                        if not group_raw:
                            m_grp = GROUPS_PAT.match(line)
                            if m_grp:
                                group_raw = m_grp.group(1).strip()
    except Exception:
        pass

    return parody_raw, series_raw, group_raw


def get_comicinfo_from_folder(folder_path):
    """
    Finds ComicInfo file content inside folder or immediate subdirectories.
    Case-insensitive search for Linux compatibility.
    """
    try:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return None, False

        # 1. Direct folder check
        for f in os.listdir(folder_path):
            f_lower = f.lower()
            if f_lower in VALID_COMICINFO_NAMES:
                fp = os.path.join(folder_path, f)
                with open(fp, 'rb') as fp_obj:
                    return fp_obj.read(), f_lower.endswith('.json')

        # 2. Immediate subdirectories (e.g. Chapter folder)
        for sub in os.listdir(folder_path):
            sub_path = os.path.join(folder_path, sub)
            if os.path.isdir(sub_path):
                for sub_file in os.listdir(sub_path):
                    sub_lower = sub_file.lower()
                    if sub_lower in VALID_COMICINFO_NAMES:
                        fp = os.path.join(sub_path, sub_file)
                        with open(fp, 'rb') as fp_obj:
                            return fp_obj.read(), sub_lower.endswith('.json')

        # 3. Check if there is an inner .cbz or .zip in the folder
        for f in os.listdir(folder_path):
            if f.lower().endswith(('.cbz', '.zip')):
                archive_path = os.path.join(folder_path, f)
                content, is_json = get_comicinfo_from_archive(archive_path)
                if content:
                    return content, is_json
    except Exception:
        pass

    return None, False


def get_comicinfo_from_archive(archive_path):
    """Reads ComicInfo directly from a .cbz or .zip file in memory."""
    try:
        if not os.path.isfile(archive_path) or not zipfile.is_zipfile(archive_path):
            return None, False

        with zipfile.ZipFile(archive_path, 'r') as zf:
            for name in zf.namelist():
                base_lower = os.path.basename(name).lower()
                if base_lower in VALID_COMICINFO_NAMES:
                    return zf.read(name), base_lower.endswith('.json')
    except Exception:
        pass

    return None, False


def extract_comicinfo_candidates(path, exclude_brackets, exclude_brackets_re):
    """
    Extracts candidate series/parody/group names from ComicInfo metadata.
    Supports directories, CBZ/ZIP files, and sub-folders.
    """
    content = None
    is_json = False

    if os.path.isfile(path):
        content, is_json = get_comicinfo_from_archive(path)
    elif os.path.isdir(path):
        content, is_json = get_comicinfo_from_folder(path)

    if not content:
        return []

    parody_raw, series_raw, group_raw = _parse_comicinfo_content(content, is_json=is_json)

    # Process all extracted strings in priority order: Parody -> Series -> Group
    candidates = []
    for raw_str in [parody_raw, series_raw, group_raw]:
        if not raw_str or not isinstance(raw_str, str):
            continue
        # Split tokens by common delimiters: comma, pipe, slash, semicolon
        parts = re.split(r'[,|/;]+', raw_str)
        for part in parts:
            clean = part.strip().lower()
            if not clean:
                continue
            if clean in exclude_brackets:
                continue
            if not check_valid_regex(clean, exclude_brackets_re):
                continue
            candidates.append(clean)

    return deduplicate_list(candidates)


# -------------------------------------------------------------------------
# Matching Logic
# -------------------------------------------------------------------------
def find_match(folder_name, full_path, exclude_brackets, exclude_brackets_re, list_dict_data, mapping):
    """
    Matches candidate identifiers against output_list_name.json.
    Prioritizes:
      1. Folder circle brackets (reversed, so last circle bracket is checked first)
      2. ComicInfo metadata (Parodies / Series / Groups)
    Returns: (matched_series_name, matched_token, match_source) or (None, None, None)
    """
    # 1. Extract from folder name
    bracket_items = extract_folder_circles(folder_name, exclude_brackets, exclude_brackets_re)

    # 2. Extract from ComicInfo
    comicinfo_items = extract_comicinfo_candidates(full_path, exclude_brackets, exclude_brackets_re)

    # Build candidates with provenance
    candidate_sources = []
    for item in bracket_items:
        candidate_sources.append((item, "Folder Bracket"))

    for item in comicinfo_items:
        # Avoid duplicate tags if already covered by folder bracket
        if not any(item == c[0] for c in candidate_sources):
            candidate_sources.append((item, "ComicInfo"))

    # Check candidates in order
    for candidate, source in candidate_sources:
        # 1. Check in fast hash mapping
        if candidate in mapping:
            return mapping[candidate], candidate, source

        # 2. Fallback check directly in list_dict_data (matches check_in_json exactly)
        for json_item in list_dict_data:
            for ele in json_item.get("List", []):
                if candidate == ele:
                    return json_item["Name"], candidate, source

    return None, None, None


# -------------------------------------------------------------------------
# Directory Resolution
# -------------------------------------------------------------------------
def get_resolved_destination(custom_dest=None):
    """Resolves destination root folder with fallbacks."""
    if custom_dest:
        return custom_dest

    env_dest = os.environ.get("VERE2_DEST") or os.environ.get("DEST_DIR")
    if env_dest and os.path.exists(env_dest):
        return env_dest

    for p in CANDIDATE_DESTINATIONS:
        if os.path.exists(p):
            return p

    return CANDIDATE_DESTINATIONS[0]


def get_resolved_sources(custom_sources=None):
    """Resolves list of source directories to scan."""
    if custom_sources:
        return [s for s in custom_sources if s]

    env_sources = os.environ.get("VERE2_SOURCES") or os.environ.get("SOURCE_DIRS")
    if env_sources:
        paths = [s.strip() for s in env_sources.split(os.pathsep) if s.strip()]
        if paths:
            return paths

    existing = [s for s in CANDIDATE_SOURCES if os.path.exists(s)]
    return existing if existing else CANDIDATE_SOURCES


# -------------------------------------------------------------------------
# Main Routine
# -------------------------------------------------------------------------
def run_move_from_source(sources=None, destination=None, json_path=None, dry_run=False, auto_yes=False):
    dest_dir = get_resolved_destination(destination)
    source_dirs = get_resolved_sources(sources)

    print(f"Destination: {dest_dir}")
    print(f"Sources to scan ({len(source_dirs)}):")
    for s in source_dirs:
        status = "exists" if os.path.exists(s) else "not found"
        print(f"  - {s} [{status}]")
    print("-" * 50)

    # Load exclusions and JSON mapping
    exclude_brackets, exclude_brackets_re = load_exclusions()
    list_dict_data, mapping = load_json_mapping(json_path)

    if not mapping and not list_dict_data:
        print("Error: No valid mapping data found. Exiting.")
        return {}

    dict_output = {}

    for root_dir in source_dirs:
        if not os.path.exists(root_dir):
            continue

        try:
            entries = sorted(os.listdir(root_dir))
        except Exception as e:
            print(f"Error reading directory {root_dir}: {e}")
            continue

        for entry_name in entries:
            if not entry_name or entry_name.isspace():
                continue

            item_path = os.path.join(root_dir, entry_name)

            # Match against mapping using both folder name and ComicInfo
            matched_name, matched_token, match_source = find_match(
                entry_name, item_path, exclude_brackets, exclude_brackets_re, list_dict_data, mapping
            )

            if not matched_name:
                continue

            target_path = os.path.join(dest_dir, matched_name, entry_name)
            dict_output[entry_name] = {
                "Original_Path": item_path,
                "New_Path": target_path,
                "Series": matched_name,
                "Matched_Token": matched_token,
                "Source": match_source,
            }

            print("." * 30)
            print(f"{entry_name}\n{'-' * 30}\n{matched_name}  [{match_source}: '{matched_token}']")
            print("." * 30)

    print(f"Total matching items found: {len(dict_output)}")
    print("." * 30)

    if not dict_output:
        print("No items to move.")
        return dict_output

    if dry_run:
        print("[DRY RUN] Preview completed. No files were moved.")
        return dict_output

    # Confirm move
    if auto_yes:
        do_move = True
    else:
        var = input("Move? (y/n): ")
        do_move = (var.strip().lower() == 'y')

    if do_move:
        moved_count = 0
        for name in dict_output:
            original = dict_output[name]["Original_Path"]
            target = dict_output[name]["New_Path"]

            # Ensure destination directory exists
            target_parent = os.path.dirname(target)
            os.makedirs(target_parent, exist_ok=True)

            print("." * 30)
            print("MOVING :")
            print(original)
            print("-" * 13, " to ", "-" * 13)
            print(target)

            try:
                shutil.move(original, target)
                moved_count += 1
            except Exception as err:
                print(f"Error moving {original} -> {target}: {err}")

        print("." * 30)
        print(f"Successfully moved {moved_count} of {len(dict_output)} item(s).")
    else:
        print("Move cancelled by user.")

    return dict_output


# -------------------------------------------------------------------------
# CLI Entrypoint
# -------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Move releases from source directories to series destination folders matching circle/parody names and ComicInfo metadata."
    )
    parser.add_argument(
        "-s", "--source", action="append", dest="sources",
        help="Source directory to scan. Can be specified multiple times for multiple sources."
    )
    parser.add_argument(
        "-d", "--dest", dest="destination",
        help="Destination root directory (default: Vere2 candidate directory)."
    )
    parser.add_argument(
        "-j", "--json", dest="json_path",
        help="Path to output_list_name.json (default: output/output_list_name.json)."
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", dest="auto_yes",
        help="Automatically confirm moves without prompt."
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Preview matched files and targets without moving anything."
    )

    args = parser.parse_args()
    run_move_from_source(
        sources=args.sources,
        destination=args.destination,
        json_path=args.json_path,
        dry_run=args.dry_run,
        auto_yes=args.auto_yes,
    )


if __name__ == "__main__":
    main()
