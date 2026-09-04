import glob
import os
import re
import shutil

# ============================================================
# Constants (originally from Utility_functions.py)
# ============================================================

min_empty_size = 10240
min_page_no = 5
v2_valid_ext = ['.png','.jpg','.jpeg','.gif','.webp']

exception_list_folder_empty = ['^000','^zzz']

list_source = "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2"
list_dest = "/storage/emulated/0/Vere2/TempD"

source_zzz = ['/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 Zzz',
              '/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 Cc']
dest_zzz = "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 Zzz e"
dest_zzz_inc = "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 CC inc"

source_s = ['/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 S']
dest_s = "/storage/emulated/0/Vere2/Vere/NewFolder/Vere2/000 S e"

# ============================================================
# Utility functions (originally from Utility_functions.py)
# ============================================================

def check_valid_vere2(folder_name, exception_list_re):
    for ele_2 in exception_list_re:
        if re.search(ele_2, folder_name.lower()):
            return False
    return True

def empty_folder_02(path_01):
    total_size = 0
    flag1 = True
    for path, dirs, files in os.walk(path_01):
        if flag1 == False:
            break
        for f in files:
            fp = os.path.join(path, f)
            total_size += os.path.getsize(fp)
            if total_size > min_empty_size:
                flag1 = False
                break
    return flag1

def extract_numbers(file_name):
    return re.findall(r'\d+', file_name)

def empty_folder_continue_02(path_01):
    files_list = []
    Flag = False
    for path, dirs, files in os.walk(path_01):
        for f in files:
            fp = os.path.join(path, f)
            if os.path.isfile(fp) and os.path.splitext(f)[1].lower() in v2_valid_ext:
                num = extract_numbers(f)
                if num:
                    files_list.extend(extract_numbers(f))
    unique_sorted_numbers = sorted(set(int(num) for num in files_list))
    if len(unique_sorted_numbers) > 0:
        Flag = unique_sorted_numbers[0] > min_page_no
    return Flag

def move_files_2(original, target):
    print("."*30)
    print("MOVING :")
    print(original)
    print("-"*13, " to ", "-"*13)
    print(target)
    shutil.move(original,target)

def remove_dir_2(dir_path, Name):
    try:
        os.rmdir(dir_path)
        print("Directory '% s' has been removed successfully" % Name)
    except OSError as error:
        print(error)
        print("Directory '% s' can not be removed" % Name)

# ============================================================
# Main script
# ============================================================

dict_output = {}
empty_folder_dict = {}

if os.path.exists(list_source):
    for filename2 in glob.iglob(list_source + f'{os.sep}*', recursive=False):
        Name = str(os.path.basename(filename2))
        if not check_valid_vere2(Name, exception_list_folder_empty):
            continue
        for filename in glob.iglob(filename2 + f'{os.sep}*', recursive=False):
            if not os.path.isdir(filename):
                continue
            mystring = os.path.basename(filename)
            if empty_folder_02(filename):
                target_dest = list_dest + os.sep + Name + os.sep + mystring
                dict_output[mystring] = {"Original_Path":filename, "New_Path": target_dest}
                print("."*30)
                print(filename, "\n", "-"*30, "\n", target_dest)
                print("."*30)

for root_dir in source_zzz:
    if not os.path.exists(root_dir):
        continue
    for filename in glob.iglob(root_dir + f'{os.sep}*', recursive=False):
        if os.path.isdir(filename):
            mystring = os.path.basename(filename)
            if empty_folder_02(filename):
                target_dest = dest_zzz + os.sep + mystring
                dict_output[mystring] = {"Original_Path":filename, "New_Path": target_dest}
                print("."*30)
                print(filename, "\n", "-"*30, "\n", target_dest)
                print("."*30)
            elif empty_folder_continue_02(filename):
                target_dest = dest_zzz_inc + os.sep + mystring
                dict_output[mystring] = {"Original_Path":filename, "New_Path": target_dest}
                print("."*30)
                print(filename, "\n", "-"*30, "\n", target_dest)
                print("."*30)

for root_dir in source_s:
    if not os.path.exists(root_dir):
        continue
    for filename in glob.iglob(root_dir + f'{os.sep}*', recursive=False):
        if os.path.isdir(filename):
            mystring = os.path.basename(filename)
            if empty_folder_02(filename):
                target_dest = dest_s + os.sep + mystring
                dict_output[mystring] = {"Original_Path":filename, "New_Path": target_dest}
                print("."*30)
                print(filename, "\n", "-"*30, "\n", target_dest)
                print("."*30)

print(len(dict_output))
print("."*30)
var = input("Move? (y/n): ")
if var.lower() == 'y':
    for name in dict_output:
        original = dict_output[name]["Original_Path"]
        target = dict_output[name]["New_Path"]
        move_files_2(original,target)

print("-"*30)
print("="*10, "Folders to Delete", "="*10)
print("-"*30)

if os.path.exists(list_source):
    for filename2 in glob.iglob(list_source + f'{os.sep}*', recursive=False):
        Name = str(os.path.basename(filename2))
        if not os.path.isdir(filename2):
            continue
        if not check_valid_vere2(Name, exception_list_folder_empty):
            continue
        if empty_folder_02(filename2):
            empty_folder_dict[Name] = filename2
            print("."*30)
            print(Name)
            print("."*30)

print(len(empty_folder_dict))
print("."*30)
var = input("Remove Empty Folders? (y/n): ")
if var.lower() == 'y':
    for name in empty_folder_dict:
        remove_dir_2(empty_folder_dict[name], name)
