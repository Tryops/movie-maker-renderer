import os
import os.path
import subprocess
from fontTools import ttLib
import datetime

def get_volume(video_clip_info): # returns volume of video clip as a float factor
    for bool_property in video_clip_info['BoundProperties']['BoundPropertyBool']: # when 'Mute' property is set to 'true' the volume is 0
        if(bool_property['@Name'] == 'Mute' and bool_property['@Value'] == 'true'):
            return 0.0 # return type is always float
    for float_property in video_clip_info['BoundProperties']['BoundPropertyFloat']: # otherwise the volume float value is returned
        if(float_property['@Name'] == 'Volume'):
            return float(float_property['@Value'])
    return 1.0 # when not property is set the volume remains unaltered

def get_rotation_steps(video_clip_info): # returns rotation steps of video clip, multiply with 90 for degrees 
    for int_property in video_clip_info['BoundProperties']['BoundPropertyInt']:
        if(int_property['@Name'] == 'rotateStepNinety'):
            return int(int_property['@Value']) # rotated in steps of 90 degrees
    return 0

def play_notification_sound():
    print('\007', end='') # play the bell/error notification sound e.g. to know when rendering is finished, also dont print a newline

def check_file_exists(file):
    if(not os.path.isfile(file)):
        raise FileNotFoundError(f'File "{file}" was not found')
    
def get_extent(extent_id, media_extents):
    return next(filter(lambda extent: extent['@extentID'] == extent_id, media_extents))

def is_even(integer):
    return integer % 2 == 0

def open_explorer_on_file(filepath):
    subprocess.Popen(f'explorer /select,"{filepath}"')

def find_font_file(font_name): # only works with TrueType/OpenType fonts
    font_dir_system = 'C:\\Windows\\Fonts\\'
    font_dir_user = os.environ['USERPROFILE'] + '\\AppData\\Local\\Microsoft\\Windows\\Fonts\\'
    font_paths_system = list(map(lambda filename: os.path.join(font_dir_system, filename), os.listdir(font_dir_system)))
    font_paths_user = list(map(lambda filename: os.path.join(font_dir_user, filename), os.listdir(font_dir_user)))
    
    font_paths_filtered = list(filter(lambda filepath: os.path.isfile(filepath) and (os.path.splitext(filepath)[1] == '.ttf' or os.path.splitext(filepath)[1] == '.otf'), font_paths_system + font_paths_user)) # only allow ttf/otf fonts
    for font_path in font_paths_filtered:
        font = ttLib.TTFont(font_path)
        font_family_name = font['name'].getDebugName(1)
        font_full_name = font['name'].getDebugName(4)
        if font_name == font_family_name or font_name == font_full_name:
            return font_path
    raise Exception(f'Font file (TrueType/OpenType) for font "{font_name}" was not found!')


def get_current_datetime():
    return datetime.datetime.now()

def prevent_file_overwrite(filepath):
    if os.path.exists(filepath):
        while True:
            response = input(f'File "{filepath}" already exists. Overwrite? (Y/n): ').strip().lower()
            if response in ('', 'y'):  # default to 'y' on enter
                print(f'File "{filepath}" will be overwritten. ')
                return filepath
            elif response == 'n':
                print('Rendering aborted. No file was written. ')
                exit()
            else:
                print('Invalid input. Please type "y", "n", or press Enter for "y"')

def print_banner():
    print('+------------------------------------+')
    print('|        Movie Maker Renderer        |')
    print('+------------------------------------+')