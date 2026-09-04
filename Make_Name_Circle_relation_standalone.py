import os
import sys
import re
import csv
import json
import xml.etree.ElementTree as ET

# Ensure UTF-8 output encoding for consoles across platforms
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# -------------------------------------------------------------------------
# Configuration & Constants (Standalone - no external utility functions needed)
# -------------------------------------------------------------------------
list_csv_delimiter = '╥'

# Resolve input/output directories relative to this script for cross-platform portability
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
folder_name_output = os.path.join(SCRIPT_DIR, "output")
folder_name_input = os.path.join(SCRIPT_DIR, "input")

# Candidate directories to scan across Windows, Android/Linux, and WSL/Linux
default_root_dirs = [
    "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2",
    "/storage/emulated/0/Vere2/TempD",
]

# Folders to skip at root level
exception_list_folder_start = [r'^000', r'^original', r'^zzz', r'^various']

# Bracket patterns
pattern_square = r"(\[([^\]]+)\])"
pattern_circle = r"(\(([^\)]+)\))"

# Valid ComicInfo filenames (checked case-insensitively for Linux compatibility)
valid_xml_names = {'comicinfo.xml', 'comic_info.xml', 'comicinfo.json', 'comic_info.json'}
parodies_pat = re.compile(r'^\s*(?:\*\*)?\s*parod(?:ies|y)\s*(?:\*\*)?\s*:\s*(.+)$', re.IGNORECASE)


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def get_resolved_root_dirs(custom_dirs=None):
    """
    Resolves the list of root directories to scan.
    Prioritizes:
      1. Explicit arguments passed to function or CLI (sys.argv[1:])
      2. Environment variable VERE2_PATH
      3. Existing directories from default_root_dirs
      4. Fallback to default_root_dirs if none exist yet
    """
    if custom_dirs:
        return [d for d in custom_dirs if d]

    env_path = os.environ.get("VERE2_PATH")
    if env_path and os.path.exists(env_path):
        return [env_path]

    existing = [p for p in default_root_dirs if os.path.exists(p)]
    return existing if existing else default_root_dirs


def deduplicate_list(items):
    """Preserves order while removing duplicates."""
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def check_valid(string_to_check, regex_list):
    """Returns True if string does NOT match any pattern in regex_list."""
    for pattern in regex_list:
        if re.search(pattern, string_to_check.lower()):
            return False
    return True


def load_exclusions():
    """Loads exclusion lists from input folder safely."""
    exclude_brackets = set()
    exclude_brackets_re = []

    file_txt = os.path.join(folder_name_input, "exclude_in_brackets.txt")
    if os.path.exists(file_txt):
        try:
            with open(file_txt, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    s = line.strip().lower()
                    if s:
                        exclude_brackets.add(s)
        except Exception as e:
            print(f"Warning reading {file_txt}: {e}")

    file_re = os.path.join(folder_name_input, "exclude_in_brackets_re.txt")
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


def extract_brackets_parody(folder_name, exclude_brackets, exclude_brackets_re):
    """
    Extracts parody name from circle brackets (...) in folder name.
    Square brackets [...] are removed first to avoid author details leaking in.
    """
    # 1. Remove all square brackets and their contents
    find_squares = re.findall(pattern_square, folder_name)
    without_squares = folder_name
    for sq in find_squares:
        without_squares = without_squares.replace(sq[0], '')

    # 2. Extract all circle brackets
    find_circles = re.findall(pattern_circle, without_squares)
    circle_items = [c[1].strip().lower() for c in find_circles if c[1].strip()]

    # 3. Filter using exclusions
    valid_items = []
    for item in circle_items:
        if item in exclude_brackets:
            continue
        if not check_valid(item, exclude_brackets_re):
            continue
        valid_items.append(item)

    # In original convention, the last circle bracket is the parody/series name
    return [valid_items[-1]] if valid_items else []


def get_comicinfo_file(folder_path):
    """
    Finds ComicInfo.xml or ComicInfo.json in folder or immediate subdirectories.
    Performs case-insensitive filename comparison for Linux compatibility.
    Never raises an exception.
    """
    try:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return None

        # Check direct folder
        for f in os.listdir(folder_path):
            if f.lower() in valid_xml_names:
                return os.path.join(folder_path, f)

        # Check immediate subdirectories (e.g. Chapter folder)
        for sub in os.listdir(folder_path):
            sub_path = os.path.join(folder_path, sub)
            if os.path.isdir(sub_path):
                for sub_file in os.listdir(sub_path):
                    if sub_file.lower() in valid_xml_names:
                        return os.path.join(sub_path, sub_file)
    except Exception:
        pass
    return None


def extract_comicinfo_parody(folder_path, exclude_brackets, exclude_brackets_re):
    """
    Extracts 'Parodies' from ComicInfo.xml / comicinfo.json if available.
    Falls back gracefully without failing if missing, empty, or unparseable.
    """
    xml_path = get_comicinfo_file(folder_path)
    if not xml_path:
        return []

    parody_raw = ''
    try:
        # Support JSON ComicInfo if present
        if xml_path.lower().endswith('.json'):
            with open(xml_path, 'r', encoding='utf-8', errors='replace') as fp:
                data = json.load(fp)
            parody_raw = data.get('parodies') or data.get('parody') or ''
        else:
            # Parse XML
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
            except Exception:
                with open(xml_path, 'r', encoding='utf-8', errors='replace') as fp:
                    content = fp.read()
                root = ET.fromstring(content)

            # 1. Direct XML tag
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1].lower()
                if tag_name in ('parodies', 'parody'):
                    parody_raw = elem.text or ''
                    break

            # 2. Fallback to Summary / Description / Notes
            if not parody_raw:
                for elem in root.iter():
                    tag_name = elem.tag.split('}')[-1].lower()
                    if tag_name in ('summary', 'description', 'notes'):
                        summary_text = elem.text or ''
                        for line in summary_text.splitlines():
                            m = parodies_pat.match(line.strip())
                            if m:
                                parody_raw = m.group(1).strip()
                                break
                        if parody_raw:
                            break
    except Exception:
        # Must not fail if comic info parsing encounters any issue
        return []

    if not parody_raw or not isinstance(parody_raw, str):
        return []

    # Split parodies if multiple separated by |, ,, /, or ;
    parts = re.split(r'[,|/;]+', parody_raw)
    valid_parodies = []
    for part in parts:
        clean_part = part.strip().lower()
        if not clean_part:
            continue
        if clean_part in exclude_brackets:
            continue
        if not check_valid(clean_part, exclude_brackets_re):
            continue
        valid_parodies.append(clean_part)

    return valid_parodies


# -------------------------------------------------------------------------
# Main Execution Logic
# -------------------------------------------------------------------------
def make_name_circle_relation(root_dirs=None):
    root_dirs = get_resolved_root_dirs(root_dirs)

    os.makedirs(folder_name_output, exist_ok=True)
    exclude_brackets, exclude_brackets_re = load_exclusions()

    print("Reading Data...")
    output_dict = {}

    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            print(f"Directory not found: {root_dir}")
            continue

        print(f"Scanning directory: {root_dir}")
        try:
            series_folders = sorted(os.listdir(root_dir))
        except Exception as e:
            print(f"Error accessing {root_dir}: {e}")
            continue

        for series_name in series_folders:
            series_path = os.path.join(root_dir, series_name)
            if not os.path.isdir(series_path):
                continue

            # Skip folders matching exception patterns (e.g. ^000, ^zzz, etc.)
            if not check_valid(series_name, exception_list_folder_start):
                continue

            series_elements = []

            # Read book/release folders inside this series
            try:
                book_folders = os.listdir(series_path)
            except Exception:
                continue

            for book_name in book_folders:
                book_path = os.path.join(series_path, book_name)
                if not os.path.isdir(book_path):
                    continue

                # 1. Extract from brackets in folder name
                bracket_parodies = extract_brackets_parody(book_name, exclude_brackets, exclude_brackets_re)
                series_elements.extend(bracket_parodies)

                # 2. Extract from ComicInfo.xml if available
                comicinfo_parodies = extract_comicinfo_parody(book_path, exclude_brackets, exclude_brackets_re)
                series_elements.extend(comicinfo_parodies)

            # Deduplicate items for this series
            deduped_elements = deduplicate_list(series_elements)

            if series_name in output_dict:
                output_dict[series_name] = deduplicate_list(output_dict[series_name] + deduped_elements)
            else:
                output_dict[series_name] = deduped_elements

    # Prepare output data
    output_list = [{"Name": k, "List": output_dict[k]} for k in output_dict]

    print("Writing Data...")

    # 1. JSON output
    json_path = os.path.join(folder_name_output, "output_list_name.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_list, f, indent=4, ensure_ascii=False)
    print(f"Written: {json_path}")

    # 2. Duplicate detection
    count_dup = 0
    dup_path = os.path.join(folder_name_output, "output_duplicate.txt")
    with open(dup_path, "w", encoding="utf-8") as f:
        fill_list_tmp = set()
        for item in output_dict:
            intersection = fill_list_tmp.intersection(set(output_dict[item]))
            if len(intersection) != 0:
                for i in intersection:
                    f.write(str(i) + "\n")
                    count_dup += 1
            fill_list_tmp = fill_list_tmp.union(output_dict[item])

    print("Count of Duplicates : ", count_dup)
    print(f"Written: {dup_path}")

    # 3. CSV output
    output_list_csv = [["Name", "Element"]]
    for item_name in output_dict:
        for item_ele in output_dict[item_name]:
            output_list_csv.append([item_name, item_ele])

    csv_path = os.path.join(folder_name_output, "output_list_name.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=list_csv_delimiter)
        csv_writer.writerows(output_list_csv)
    print(f"Written: {csv_path}")

    print(f"Done! Processed {len(output_dict)} series.")
    return output_dict


if __name__ == "__main__":
    # Support CLI arguments for custom directory paths (e.g. python script.py /linux/path)
    cli_dirs = sys.argv[1:] if len(sys.argv) > 1 else None
    make_name_circle_relation(cli_dirs)
