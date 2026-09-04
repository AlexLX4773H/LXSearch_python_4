import glob
import os
import re
import csv
import json
import xml.etree.ElementTree as ET

# -------------------------------------------------------------------------
# Constants (from Utility_functions.py)
# -------------------------------------------------------------------------
pattern_square = r"(\[([^\]]+)\])"
pattern_circle = r"(\(([^\)]+)\))"
pattren_curly = r"({([^}]+)})"
pattren_equal = r"(=([^=]+)=)"

list_csv_delimiter = '╥'

list_csv_headers = ["Name","Folder","Extracted Name","Circle List","Curly List","Equal List","Author List","Tag List","Main Titles","Main Titles Pressed","Name Pressed"] #11

v2_list_summary = ['Parodies','Groups','Characters','Pages','Language','Categories'] #6
v2_list = ['Genre','Writer','Penciller'] #3
v2_summary = 'Summary'
v2_xml_info = 'ComicInfo.xml'
v2_end_items = ["Count Items", "Has Folders", "Total Size", "Count Files", "Average Size"] #5

v2_list_csv_headers = list_csv_headers + v2_list_summary + v2_list + v2_end_items #25 - 11 + 6 + 3 + 5

v2_valid_ext = ['.png','.jpg','.jpeg','.gif','.webp']

read_root_dir_for_folders = [
'/storage/emulated/0/Vere2/TempD',
'/storage/emulated/0/Vere2/TempT',
'/storage/emulated/0/Vere2/Vere/NewFolder',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/NineHentai (EN)',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/NHentai (EN)',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/nHentai.com (unoriginal) (EN)',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/E-Hentai (EN)',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/Hennojin (EN)',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/HentaiHand (ALL)',
'/storage/emulated/0/Vere2/Vere/Tachiyomi/downloads/HentaiHand (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/NineHentai (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/NHentai (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/nHentai.com (unoriginal) (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/E-Hentai (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/Hennojin (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/HentaiHand (ALL)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/HentaiHand (EN)',
'/storage/emulated/0/Vere2/Vere/Mihon/downloads/AsmHentai (EN)',
'storage/emulated/0/Vere2/Vere/Mihon/downloads/NHentai.xxx (EN)']

read_root_dir_for_files = ['/storage/emulated/0/Vere2/TempT',
'/storage/emulated/0/Vere2/Vere/NewFolder/Files']

# -------------------------------------------------------------------------
# Helper Functions (from Utility_functions.py)
# -------------------------------------------------------------------------
def check_re(string_to_check, re_list):
    for ele_1 in re_list:
        if re.fullmatch(ele_1, string_to_check.lower()):
            return True
    return False

def remove_list_from_string(string_to_remove, list_to_remove):
    for tmpr in list_to_remove:
        string_to_remove = string_to_remove.replace(tmpr, '')
    return string_to_remove.strip()

def string_press(input_string):
    return re.sub('[^A-Za-z0-9]+', '', input_string).lower()

def string_press_list(input_string_list):
    return [string_press(item) for item in input_string_list]

def extract_brackets(string_to_check):
    find_squares = re.findall(pattern_square, string_to_check)
    find_squares_remove = [i[0] for i in find_squares]
    find_squares_list = [i[1].strip() for i in find_squares]
    after_remove_square = remove_list_from_string(string_to_check, find_squares_remove)

    find_circle = re.findall(pattern_circle, after_remove_square)
    find_circle_remove = [i[0] for i in find_circle]
    find_circle_list = [i[1].strip() for i in find_circle]
    after_remove_circle = remove_list_from_string(after_remove_square, find_circle_remove)

    find_curly = re.findall(pattren_curly, after_remove_circle)
    find_curly_remove = [i[0] for i in find_curly]
    find_curly_list = [i[1].strip() for i in find_curly]
    after_remove_curly = remove_list_from_string(after_remove_circle, find_curly_remove)

    find_equal_list = []

    if after_remove_curly.count('=')%2 == 0:
        find_equal = re.findall(pattren_equal, after_remove_curly)
        find_equal_remove = [i[0] for i in find_equal]
        find_equal_list = [i[1].strip() for i in find_equal]
        after_remove_equal = remove_list_from_string(after_remove_curly, find_equal_remove)
        final_string = after_remove_equal
    else:
        final_string = after_remove_curly

    if final_string.isspace() or len(final_string) == 0:
        return string_to_check, find_circle_list, find_curly_list, find_equal_list, [], [], [], [], string_press(string_to_check)

    main_titles = final_string.split('_')
    main_titles = [item.strip() for item in main_titles]
    main_titles_pressed = string_press_list(main_titles)

    left_string = string_to_check.split(final_string)[0].strip()
    left_string_squares = re.findall(pattern_square, left_string)
    left_string_list = [i[1] for i in left_string_squares]

    left_author_list = [item for item in find_squares_list if item in left_string_list]
    right_tags_list = [item for item in find_squares_list if item not in left_string_list]

    return final_string, find_circle_list, find_curly_list, find_equal_list, left_author_list, right_tags_list, main_titles, main_titles_pressed, string_press(string_to_check)

def _clean_xml_tag(tag):
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def v2_get_tag_text_xml(tag_name, root_xml):
    if root_xml is None:
        return ''
    if isinstance(tag_name, str):
        tag_names = [tag_name]
    else:
        tag_names = list(tag_name)
    tag_names_lower = [t.lower() for t in tag_names]
    
    # 1. Check direct children first
    for child in root_xml:
        c_tag = _clean_xml_tag(child.tag).lower()
        if c_tag in tag_names_lower:
            return (child.text or '').strip()
            
    # 2. Check all descendants
    for elem in root_xml.iter():
        c_tag = _clean_xml_tag(elem.tag).lower()
        if c_tag in tag_names_lower:
            return (elem.text or '').strip()
    return ''

def v2_get_Summary_items_xml(summary_text, root_xml=None):
    patterns = {
        'Parodies': re.compile(r'^\s*(?:\*\*)?\\s*parod(?:ies|y)\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE),
        'Groups': re.compile(r'^\s*(?:\*\*)?\\s*(?:groups?|circles?)\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE),
        'Characters': re.compile(r'^\s*(?:\*\*)?\\s*characters?\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE),
        'Pages': re.compile(r'^\s*(?:\*\*)?\\s*pages?\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE),
        'Language': re.compile(r'^\s*(?:\*\*)?\\s*languages?\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE),
        'Categories': re.compile(r'^\s*(?:\*\*)?\\s*categor(?:ies|y)\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE),
    }
    series_pat = re.compile(r'^\s*(?:\*\*)?\\s*series\s*(?:\*\*)?\\s*:\s*(.+)$', re.IGNORECASE)
    
    result = {k: '' for k in v2_list_summary}
    series_val = ''
    
    if summary_text and isinstance(summary_text, str):
        for line in summary_text.splitlines():
            line = line.strip()
            if not line:
                continue
            matched = False
            for k, pat in patterns.items():
                if not result[k]:
                    m = pat.match(line)
                    if m:
                        result[k] = m.group(1).strip()
                        matched = True
                        break
            if not matched and not series_val:
                m_ser = series_pat.match(line)
                if m_ser:
                    series_val = m_ser.group(1).strip()
                    
    # Fallback for Parodies from Series in summary if not found
    if not result['Parodies'] and series_val:
        result['Parodies'] = series_val

    # Fallback to direct XML tags if root_xml is provided
    if root_xml is not None:
        tag_fallbacks = [
            ('Parodies', ['Parodies', 'Parody']),
            ('Groups', ['Groups', 'Group', 'Teams', 'Team', 'Circle', 'Circles']),
            ('Characters', ['Characters', 'Character']),
            ('Pages', ['Pages', 'Page', 'PageCount']),
            ('Language', ['Language', 'Languages', 'LanguageISO']),
            ('Categories', ['Categories', 'Category', 'Format']),
        ]
        for key, tags in tag_fallbacks:
            if not result[key]:
                val = v2_get_tag_text_xml(tags, root_xml)
                if val:
                    result[key] = val

    return [str(result[k]) if result[k] is not None else '' for k in v2_list_summary]

def v2_get_items_xml(root_xml):
    if root_xml is None:
        return [''] * 9
    
    # Support dict (e.g. from JSON)
    if isinstance(root_xml, dict):
        parodies = root_xml.get('parodies') or root_xml.get('parody') or ''
        groups = root_xml.get('groups') or root_xml.get('group') or root_xml.get('circle') or ''
        chars = root_xml.get('characters') or root_xml.get('character') or ''
        pages = root_xml.get('pages') or root_xml.get('page_count') or root_xml.get('pageCount') or ''
        lang = root_xml.get('language') or root_xml.get('languages') or ''
        cat = root_xml.get('categories') or root_xml.get('category') or ''
        genre = root_xml.get('genre') or root_xml.get('tags') or ''
        writer = root_xml.get('writer') or root_xml.get('author') or ''
        penciller = root_xml.get('penciller') or root_xml.get('artist') or ''
        return [str(x) if x is not None else '' for x in [parodies, groups, chars, pages, lang, cat, genre, writer, penciller]]

    summary_text = v2_get_tag_text_xml([v2_summary, 'Description', 'Notes'], root_xml)
    item_list = v2_get_Summary_items_xml(summary_text, root_xml)
    
    genre = v2_get_tag_text_xml(['Genre', 'Genres', 'Tags'], root_xml)
    writer = v2_get_tag_text_xml(['Writer', 'Writers', 'Author', 'Authors'], root_xml)
    penciller = v2_get_tag_text_xml(['Penciller', 'Pencillers', 'Artist', 'Artists', 'Illustrator'], root_xml)
    
    item_list.extend([genre, writer, penciller])
    return [str(x) if x is not None else '' for x in item_list]

def v2_parse_comic_info(xml_file_path):
    if not xml_file_path or not os.path.exists(xml_file_path):
        return [''] * 9
    try:
        if xml_file_path.lower().endswith('.json'):
            with open(xml_file_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            return v2_get_items_xml(data)
            
        try:
            tree_root = ET.parse(xml_file_path).getroot()
        except Exception:
            with open(xml_file_path, 'r', encoding='utf-8', errors='replace') as fp:
                content = fp.read()
            tree_root = ET.fromstring(content)
            
        return v2_get_items_xml(tree_root)
    except Exception as e:
        return [''] * 9

def v2_get_ComicInfo_xml_file(folder_path):
    try:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return None
        valid_names = [v2_xml_info.lower(), 'comic_info.xml', 'comicinfo.json', 'comic_info.json']
        # Check direct folder
        for file in os.listdir(folder_path):
            if file.lower() in valid_names:
                return os.path.join(folder_path, file)
        # Check immediate subdirectories (in case ComicInfo is inside a chapter folder)
        for item in os.listdir(folder_path):
            sub_path = os.path.join(folder_path, item)
            if os.path.isdir(sub_path):
                for sub_file in os.listdir(sub_path):
                    if sub_file.lower() in valid_names:
                        return os.path.join(sub_path, sub_file)
    except Exception:
        pass
    return None

def v2_check_directory_exists(path):
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            return True
    return False

def convert_bytes_to_readable_size(size):
    # Define the suffixes for different size units
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']

    # Determine the appropriate size unit
    index = 0
    while size >= 1024 and index < len(suffixes) - 1:
        size /= 1024
        index += 1

    # Format the size with the appropriate unit
    size = round(size, 2)
    size_with_unit = f"{size} {suffixes[index]}"

    return size_with_unit

def v2_get_files_size_and_count_avg(path):
    total_size = 0
    count = 0

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path) and os.path.splitext(item)[1].lower() in v2_valid_ext:
            total_size += os.path.getsize(item_path)
            count += 1

    avg = total_size/count if count > 0 else 0

    return convert_bytes_to_readable_size(total_size), count, convert_bytes_to_readable_size(avg)

# -------------------------------------------------------------------------
# Main Script
# -------------------------------------------------------------------------
count = 0
temp_string = ""
final_list = [v2_list_csv_headers]

folder_name_input = "input"
f = open(os.path.join(folder_name_input, "exclude_folders_chapter_re.txt"), "r", encoding="utf-8")
exclude_chapter_re = []
for line in f:
    exclude_chapter_re.append(line.strip())
f.close

folder_name_output = "output"
os.makedirs(folder_name_output, exist_ok=True)

for root_dir in read_root_dir_for_folders:
    for filename in glob.iglob(root_dir + f'**{os.sep}**', recursive=True):
        if os.path.isdir(filename):
            mystring = os.path.basename(filename)
            mystring = mystring.lower().strip()
            first = re.sub('[^A-Za-z0-9]+', '', mystring)
            if check_re(first, exclude_chapter_re):
                continue
            second = str(filename)
            both = first + " ::: " + second + "\n"
            temp_string += both
            count+=1
            print(first, ' - ', count)

            mystring2 = os.path.basename(filename)
            if mystring2.isspace() or len(mystring2) == 0:
                continue
            xyz = extract_brackets(mystring2)
            final_xyz = [mystring2, second] + list(xyz) #11 fields
            
            xml_file_path = v2_get_ComicInfo_xml_file(filename)
            xml_items = [''] * 9
            if xml_file_path:
                try:
                    tree_root = ET.parse(xml_file_path).getroot()
                    xml_items = v2_get_items_xml(tree_root)
                except Exception:
                    try:
                        xml_items = v2_parse_comic_info(xml_file_path)
                    except Exception:
                        xml_items = [''] * 9

            if len(xml_items) != 9:
                xml_items = (list(xml_items) + [''] * 9)[:9]

            final_xyz_v2 = final_xyz + xml_items + [len(os.listdir(filename)), v2_check_directory_exists(filename)] + list(v2_get_files_size_and_count_avg(filename)) #25 fields
            final_list.append(final_xyz_v2) #25 fields


for root_dir in read_root_dir_for_files:
    for filename in glob.iglob(root_dir + f'**{os.sep}**', recursive=True):
        if os.path.isfile(filename):
            mystring = os.path.basename(filename)
            mystring = mystring.lower().strip()
            first = re.sub('[^A-Za-z0-9]+', '', mystring)
            second = str(filename)
            both = first + " ::: " + second + "\n"
            temp_string += both
            count+=1
            print(first, ' - ', count)

f = open(os.path.join(folder_name_output, "list.txt"), "w", newline="", encoding="utf-8")
f.write(temp_string)
f.close()

f1 = open(os.path.join(folder_name_output, "count.txt"), "w",  newline="", encoding="utf-8")
f1.write(str(count))
f1.close()

with open(os.path.join(folder_name_output, "filename_list_v2.csv"), "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile, delimiter = list_csv_delimiter) #alt 1234
    # Write each row of the list to the CSV file
    csv_writer.writerows(final_list)
