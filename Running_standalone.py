import os
import csv
import ast
import re

# ============================================================
# Constants (originally from Utility_functions.py)
# ============================================================

pattern_square = r"(\[([^\]]+)\])"
pattern_circle = r"(\(([^\)]+)\))"
pattren_curly = r"({([^}]+)})"
pattren_equal = r"(=([^=]+)=)"

input_seperators = ['|','/',';']

list_csv_delimiter = '╥'

list_csv_headers = ["Name","Folder","Extracted Name","Circle List","Curly List","Equal List","Author List","Tag List","Main Titles","Main Titles Pressed","Name Pressed"]
list_csv_headers_that_are_list = ["Circle List","Curly List","Equal List","Author List","Tag List","Main Titles","Main Titles Pressed"]

# ============================================================
# Utility functions (originally from Utility_functions.py)
# ============================================================

def string_press(input_string):
    return re.sub('[^A-Za-z0-9]+', '', input_string).lower()

def string_press_list(input_string_list):
    return [string_press(item) for item in input_string_list]

def remove_list_from_string(string_to_remove, list_to_remove):
    for tmpr in list_to_remove:
        string_to_remove = string_to_remove.replace(tmpr, '')
    return string_to_remove.strip()

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

def parse_input_value(string_to_check):
    for i in input_seperators:
        string_to_check = string_to_check.replace(i, '_')
    extract_output_list = dict(zip(list_csv_headers[2:], extract_brackets(string_to_check)))
    return extract_output_list

def parse_input_value_custom(string_to_check, input_seperators_tmp):
    for i in input_seperators_tmp:
        string_to_check = string_to_check.replace(i, '_')
    extract_output_list = dict(zip(list_csv_headers[2:], extract_brackets(string_to_check)))
    return extract_output_list

def split_string_and_return_1(string_input_values, list_to_split):
    for tmpr in list_to_split:
        string_input_values = [item.lower().split(tmpr)[0].strip() for item in string_input_values]
    return string_input_values

# ============================================================
# Main script
# ============================================================

folder_name_output = "output"
list_dict_data = []

folder_name_input = "input"
f = open(os.path.join(folder_name_input, "exclude_input_chapter_sep.txt"), "r", encoding="utf-8")
exclude_input_chapter_sep = []
for line in f:
    exclude_input_chapter_sep.append(" "+line.strip()+" ")
f.close

with open(os.path.join(folder_name_output, "filename_list.csv"), "r", encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile, delimiter = list_csv_delimiter, skipinitialspace=True)
    headers = next(reader)
    for row in reader:
        line = dict(zip(headers, row))
        for convert_to_list in list_csv_headers_that_are_list:
            line[convert_to_list] = ast.literal_eval(line[convert_to_list])
        list_dict_data.append(line)

def check_list(string_input_values, column_type="Name Pressed"):
    list_set = []
    for string_input_value in string_input_values:
        if len(string_input_value) < 3:
            continue
        for line_dict in list_dict_data:
            if string_input_value.lower() in line_dict[column_type].lower():
                list_set.append(str(line_dict["Name"] + '\t --- \t' + line_dict["Folder"]))
    list_set = set(list_set)
    for ele in list_set:
        print(ele)
        print()
    print("Count ---> ", len(list_set))
    return len(list_set) != 0

print("\n" + "="*30)
print(" COMMAND MENU:")
print(" [text]      : Default Name search")
print(" #<text>     : Exact Name search")
print(" -<text>     : Use '-' as separator")
print(" @<c><text>  : Use <c> as separator")
print(" ~<text>     : Strip ~...~ blocks")
print(" 000         : Exit script")
print("="*30 + "\n")

val = ''
while val != '000':
    print("="*30)
    val = input("Enter: ")
    print("."*30)
    if not val:
        print("Empty input. Please enter a valid value.")
        continue
    if val.startswith('#'):
        vals = [val[1:]]
        print(vals)
        print("-"*30)
        found = check_list(vals, "Folder")
    elif val.startswith('-'):
        vals = parse_input_value_custom(val[1:], input_seperators + ['-'])["Main Titles"]
        vals = split_string_and_return_1(vals, exclude_input_chapter_sep)
        vals = string_press_list(vals)
        vals = [re.sub(r'\d+$', '', item) for item in vals]
        print(vals)
        print("-"*30)
        found = check_list(vals, "Name Pressed")
    elif val.startswith('@'):
        if len(val) > 1:
            vals = parse_input_value_custom(val[2:], input_seperators + val[1])["Main Titles"]
            vals = split_string_and_return_1(vals, exclude_input_chapter_sep)
            vals = string_press_list(vals)
            vals = [re.sub(r'\d+$', '', item) for item in vals]
            print(vals)
            print("-"*30)
            found = check_list(vals, "Name Pressed")
        else:
            print("Invalid format. Please provide a character after '$' to act as the separator.")
            continue
    elif val.startswith('~'):
        working_val = val[1:] # Remove the initial trigger flag
        if working_val.count('~') % 2 != 0:
            print("Invalid format. Missing a closing '~' somewhere in your text.")
            continue
        remaining_val = re.sub(r'~[^~]*~', '', working_val)
        vals = parse_input_value(remaining_val)["Main Titles"]
        vals = split_string_and_return_1(vals, exclude_input_chapter_sep)
        vals = string_press_list(vals)
        vals = [re.sub(r'\d+$', '', item) for item in vals]
        print(vals)
        print("-"*30)
        found = check_list(vals, "Name Pressed")
    elif val == '000':
        break
    else:
        vals = parse_input_value(val)["Main Titles"]
        vals = split_string_and_return_1(vals, exclude_input_chapter_sep)
        vals = string_press_list(vals)
        vals = [re.sub(r'\d+$', '', item) for item in vals]
        print(vals)
        print("-"*30)
        found = check_list(vals, "Name Pressed")
    print("Found : ", found)
