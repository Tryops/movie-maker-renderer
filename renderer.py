from moviepy import *
import xmltodict
from pprint import pprint
from utils import *

debug = False
if(debug is True):
    # set custom ffmpeg binaries:
    # import os
    # os.environ["FFMPEG_BINARY"] = "C:/Program Files/ffmpeg/bin/ffmpeg.exe"
    # os.environ["FFPLAY_BINARY"] = "C:/Program Files/ffmpeg/bin/ffplay.exe"
    from moviepy.config import check
    check()

def log(text):
    print(f'[{str(get_current_datetime())}] {text}')

def render(project_file: str, output_file: str, output_width: int, output_height: int, output_fps: int, overwrite_existing_file=False):
    output_settings = {
        'width': int(output_width),
        'height': int(output_height),
        'fps': int(output_fps)
    }

    log('Rendering with the following settings:')
    log('--------------------------------------')
    log(f'Project file: "{project_file}"')
    log(f'Output file: "{output_file}"')
    log(f'Output width: {output_width} px')
    log(f'Output height: {output_height} px')
    log(f'Output fps: {output_file}')
    log(f'Overwrite pre-existing output file: {overwrite_existing_file}')
    log('--------------------------------------')

    # TODO fix font scaling with resolution
    # TODO add image rendering

    log('Start time: ' + str(get_current_datetime()) + '\n')

    if not overwrite_existing_file:
        prevent_file_overwrite(output_file)
    elif os.path.exists(output_file):
        log(f'File "{output_file}" already exists and will be overwritten (--overwrite-existing-file)')

    movie_maker_file = project_file
    with open(movie_maker_file, 'r', encoding='utf-8') as file:
        xml_string = file.read()
    log('Reading project file done!')

    movie_maker_dict = xmltodict.parse(xml_string, force_list=('BoundPropertyBool', 'BoundPropertyFloat', 'BoundPropertyInt', 'BoundPropertyString', 'BoundPropertyFloatSet', 'BoundPropertyStringSet', 'BoundPropertyStringElement', 'ExtentRef', 'TitleClip', 'VideoClip', 'AudioClip'))
    log('Parsing project file done!')

    media_items_array = movie_maker_dict['Project']['MediaItems']['MediaItem']
    media_items = {} # using dict instead of array because there can be number gaps in media items
    for media_item in media_items_array:
        file = media_item['@filePath']
        media_items[media_item['@id']] = file

    # read order of clips from the movie maker file:

    # read under which ids the orders are stored in the movie maker file: 
    bound_placeholders = movie_maker_dict['Project']['BoundPlaceholders']['BoundPlaceholder']
    placeholder_ids = {     # structure of dict is { 'placeholderID': 'extentID', ... }
        'Main': None,       # 'Main' BoundPlaceholder contains order of video and background color clips
        'SoundTrack': None, # 'SoundTrack' BoundPlaceholder contains only audio clips
        'Text': None        # 'Text' BoundPlaceholder contains only text clips that are above video/background color clips
    }
    for placeholder_id in placeholder_ids:
        try:
            placeholder_ids[placeholder_id] = next(filter(lambda bound_placeholder: bound_placeholder['@placeholderID'] == placeholder_id, bound_placeholders))['@extentID']
            # print(placeholder_id, placeholder_ids[placeholder_id])
        except StopIteration as e:
            print(f"Error: extentID for placeholderID '{placeholder_id}' was not found in Movie Maker file! " + repr(e))
            exit()

    # then read the order of the clips in each category ('Main', 'SoundTrack', 'Text'):
    extent_selectors = movie_maker_dict['Project']['Extents']['ExtentSelector']
    for placeholder_id, extent_id in placeholder_ids.items():
        media_extent_ids = [] # empty by default
        extent_refs = next(filter(lambda extent_selector: extent_selector['@extentID'] == extent_id, extent_selectors))['ExtentRefs']
        if(extent_refs is not None):
            media_extent_ids = extent_refs['ExtentRef']
            media_extent_ids = list(map(lambda id: id['@id'], media_extent_ids))
        else:
            print(f"Info: Clip category '{placeholder_id}' has no entries. ")
        placeholder_ids[placeholder_id] = media_extent_ids
        # not try catch here because entry for referenced extent is always in the file (probably)

    log('Reading order of video/title/audio clips done!')

    # prepare extent categories for later:
    title_extents = movie_maker_dict['Project']['Extents'].get('TitleClip', []) # empty if key not present in extents
    video_extents = movie_maker_dict['Project']['Extents'].get('VideoClip', [])
    audio_extents = movie_maker_dict['Project']['Extents'].get('AudioClip', [])

    log('Start building video clips.')
    # then build main video sequence:
    video_clips = []
    previous_clip_end = 0.0
    for i, extent_id in enumerate(placeholder_ids['Main']):
        log(f'Adding video/title clip {i+1}/{len(placeholder_ids["Main"])} (ID {extent_id}):')
        is_title_clip = any(extent['@extentID'] == extent_id for extent in title_extents)
        if(is_title_clip): # when its a title clip then it must be a background color clip because movie maker saves these under title clips for some reason
            title_extent = get_extent(extent_id, title_extents)
            colors = next(filter(lambda entry: entry['@Name'] == 'diffuseColor', title_extent['BoundProperties']['BoundPropertyFloatSet']))['BoundPropertyFloatElement'] # get rgb color entries
            colors = list(map(lambda entry: int(round(float(entry['@Value']) * 255)), colors)) # parse rgb color entries to 0 - 255 values
            duration = int(title_extent['@duration'])
            color_clip = (
                ColorClip(size=(output_settings['width'], output_settings['height']), color=colors)
                    .with_start(previous_clip_end)
                    .with_duration(duration)
                    .with_audio(AudioClip(lambda t: 0, duration=duration, fps=44100)) # add "null" audio to color clip to avoid audio compositing error later on # TODO less fps possible?
            )
            video_clips.append(color_clip)
            previous_clip_end += color_clip.duration # always append next video/color clip to end of previous one
            log(f'Added color clip (ID {extent_id})!')
        else: # must be video extent
            video_extent = get_extent(extent_id, video_extents)
            crop_start = float(video_extent['@inTime'])
            crop_end = float(video_extent['@outTime'])

            crossfade_duration = 0
            crossfade_effects = []
            if video_extent['Transitions'] is not None: # called 'Transitions' but every clip can only have one transition
                # for simplicity make every transition into a cross fade transiton with the given duration
                crossfade_duration = float(next(iter(video_extent['Transitions'].values()))['@duration'])
                crossfade_effects = [vfx.CrossFadeIn(duration=crossfade_duration)] if crossfade_duration > 0 else [] # prevent division by zero error in moviepy

            audiofade_effects = []
            if video_extent['Effects'] and video_extent['Effects']['AudioEffect'] and video_extent['Effects']['AudioEffect']['@effectTemplateID'] == 'AudioFadeEffectTemplate': # if has correct audio effect
                fade_duration_entries = video_extent['Effects']['AudioEffect']['BoundProperties']['BoundPropertyFloat']
                fade_in_duration = float(next(filter(lambda entry: entry['@Name'] == 'AudioFadeInDuration', fade_duration_entries))['@Value'])
                fade_out_duration = float(next(filter(lambda entry: entry['@Name'] == 'AudioFadeOutDuration', fade_duration_entries))['@Value'])
                if fade_in_duration > 0: # prevent division by zero error in moviepy
                    audiofade_effects.append(afx.AudioFadeIn(fade_in_duration))
                if fade_out_duration > 0:
                    audiofade_effects.append(afx.AudioFadeOut(fade_out_duration))

            file = media_items[video_extent['@mediaItemID']]
            check_file_exists(file) # check if media file exists to avoid strange moviepy errors later on when rendering
            log(f'Preloading video clip "{file}" (ID {extent_id})...')
            video_clip = VideoFileClip(file) # on seperate line so video duration/end attributes can be read
            video_clip = (
                video_clip
                    .with_start(previous_clip_end - crossfade_duration) # shift clip into previous one for transition effect
                    .subclipped(crop_start, crop_end if crop_end != 0 else video_clip.end) # when clip was not cropped in movie maker then crop_start and crop_end are both zero but as soon as crop_start is modified in movie maker, crop_end is set to the duration of the clip (if not changed manually to a different value); so manually set to clip end in the case of crop_end is zero
                    .with_effects([
                        vfx.MultiplySpeed(float(video_extent['@speed'])),
                        *crossfade_effects,
                        *audiofade_effects
                    ])
                    # .with_speed_scaled(float(video_extent['@speed'])) # TODO use this instead of speed effect
                    .with_volume_scaled(get_volume(video_extent))
                    .rotated(get_rotation_steps(video_extent) * 90)
                    .resized(width=output_settings["width"]) # always scale to width of render setting, aspect ratio is maintained
                    # .with_fps(output_settings['fps']) # necessary if given in write_videofile?
            )
            video_clips.append(video_clip)
            previous_clip_end += video_clip.duration - crossfade_duration # always append next video/color clip to end of previous one
            log(f'Added video clip "{file}" (ID {extent_id})!')

    total_video_duration = previous_clip_end # renamed for better understanding in audio part
    log('Building video clips done!')

    log('Start building audio clips.')
    # then build audio clips (similar to video clips):
    audio_clips = []
    previous_clip_end = 0.0
    for i, extent_id in enumerate(placeholder_ids['SoundTrack']): # also access to index to detect last element
        log(f'Adding audio clip {i+1}/{len(placeholder_ids["SoundTrack"])} (ID {extent_id}):')
        audio_extent = get_extent(extent_id, audio_extents)

        file = media_items[audio_extent['@mediaItemID']]
        check_file_exists(file) # check if media file exists to avoid moviepy errors when rendering
        log(f'Preloading audio clip "{file}" (ID {extent_id})...')
        audio_clip = AudioFileClip(file) # on seperate line so video duration/end attributes can be read

        gap_before = float(audio_extent['@gapBefore']) # can be negative
        crop_start = float(audio_extent['@inTime'])
        crop_end = float(audio_extent['@outTime'])
        crop_end = crop_end if crop_end != 0 else audio_clip.end # make value length of clip when it is zero

        is_last = i == len(placeholder_ids['SoundTrack']) - 1
        if is_last: # cut end of audio clip so that audio does not go on beyond video
            crop_end = crop_end - (previous_clip_end + (crop_end - crop_start) - total_video_duration)
        else:
            next_extent_id = placeholder_ids['SoundTrack'][i + 1]
            next_audio_extent = get_extent(next_extent_id, audio_extents)
            next_gap_before = float(next_audio_extent['@gapBefore']) # when negative crop end of current clip, because next clip cuts it off
            if next_gap_before < 0:
                crop_end = crop_end + next_gap_before

        audiofade_effects = []
        if audio_extent['Effects'] and audio_extent['Effects']['AudioEffect'] and audio_extent['Effects']['AudioEffect']['@effectTemplateID'] == 'AudioFadeEffectTemplate': # if has correct audio effect
            fade_duration_entries = audio_extent['Effects']['AudioEffect']['BoundProperties']['BoundPropertyFloat']
            fade_in_duration = float(next(filter(lambda entry: entry['@Name'] == 'AudioFadeInDuration', fade_duration_entries))['@Value'])
            fade_out_duration = float(next(filter(lambda entry: entry['@Name'] == 'AudioFadeOutDuration', fade_duration_entries))['@Value'])
            if fade_in_duration > 0: # prevent division by zero error in moviepy
                audiofade_effects.append(afx.AudioFadeIn(fade_in_duration))
            if fade_out_duration > 0:
                audiofade_effects.append(afx.AudioFadeOut(fade_out_duration))

        audio_clip = (
            audio_clip
                .with_start(previous_clip_end + max(0, gap_before)) # audio clips can have a pause before they start (in contrast to video clips), when gapBefore is negative it was already subtracted from the previous clip end in the previous iteration of the loop so make zero here; the first audio clip cant (should not) have a negative gapBefore
                .subclipped(crop_start, crop_end) # same as with video clips
                .with_effects([
                    vfx.MultiplySpeed(float(audio_extent['@speed'])),
                    *audiofade_effects
                ])
                # .with_speed_scaled(float(v['@speed'])) # TODO use this instead of speed effect
                .with_volume_scaled(get_volume(audio_extent))
        )

        # print(crop_start, crop_end, gap_before, audio_clip.duration)
        audio_clips.append(audio_clip)
        previous_clip_end += audio_clip.duration + max(0, gap_before) # always append next audio clip to end of previous one with added (positive) gapBefore
        log(f'Added audio clip "{file}" (ID {extent_id})!')

    log('Building audio clips done!')

    log('Start building title clips.')
    # then build title/text clips (are rendered transparently above main video clips)
    title_clips = []
    previous_clip_end = 0.0
    for i, extent_id in enumerate(placeholder_ids['Text']):
        log(f'Adding title clip {i+1}/{len(placeholder_ids["Text"])} (ID {extent_id}):')
        title_extent = get_extent(extent_id, title_extents)
        gap_before = float(title_extent['@gapBefore'])
        duration = float(title_extent['@duration'])

        text_color = next(filter(lambda entry: entry['@Name'] == 'color', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyFloatSet']))['BoundPropertyFloatElement'] # get rgb color entries
        text_color = list(map(lambda entry: int(round(float(entry['@Value']) * 255)), text_color)) # parse rgb color entries to 0 - 255 values
        
        text_outline_color = next(filter(lambda entry: entry['@Name'] == 'outlineColor', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyFloatSet']))['BoundPropertyFloatElement'] # get rgb color entries
        text_outline_color = list(map(lambda entry: int(round(float(entry['@Value']) * 255)), text_outline_color)) # parse rgb color entries to 0 - 255 values

        text_outline_size = next(filter(lambda entry: entry['@Name'] == 'outlineSizeIndex', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyInt'])) # get text outline size index
        text_outline_size = int(text_outline_size['@Value']) * 4 # convert outline index value to pixels, must be integer!

        font_family = next(filter(lambda entry: entry['@Name'] == 'family', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyStringSet']))['BoundPropertyStringElement'] # get font family entries (array but only 1 element)
        font_family = font_family[0]['@Value'] # parse font family string from first entry (only 1 entry)

        text_align = next(filter(lambda entry: entry['@Name'] == 'justify', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyStringSet']))['BoundPropertyStringElement'] # get text align entries (array but only 1 element)
        text_align = text_align[0]['@Value'] # parse text align string from first entry (only 1 entry)
        text_align = {'MIDDLE': 'center', 'BEGIN': 'left', 'END': 'right'}.get(text_align, 'center') # map movie maker names to moviepy names, 'center' is default

        text_strings = next(filter(lambda entry: entry['@Name'] == 'string', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyStringSet']))['BoundPropertyStringElement'] # get string entries
        text_string = '\n'.join(list(map(lambda entry: entry['@Value'], text_strings))) # concat text string entries to string with line breaks

        font_size = next(filter(lambda entry: entry['@Name'] == 'size', title_extent['Effects']['TextEffect']['BoundProperties']['BoundPropertyFloat'])) # get font size entry
        font_size = int(float(font_size['@Value']) * 60) # calculate approximate font size in point unit, factor is approx 60, but could also be 64 or similar

        # OPTIONAL: add text transparency

        # pprint(title_extent)
        # continue
        # exit()

        should_scroll = title_extent['Effects'] and title_extent['Effects']['TextEffect'] and title_extent['Effects']['TextEffect']['@effectTemplateID'] == 'TextEffectScrollTemplate' # default other effect: 'TextEffectFadeZoomTemplate'

        # title clips can be shifted into each other like audio clips, so make sure they dont overlap:
        is_last = i == len(placeholder_ids['Text']) - 1
        if not is_last:
            next_extent_id = placeholder_ids['Text'][i + 1]
            next_title_extent = get_extent(next_extent_id, title_extents)
            next_gap_before = float(next_title_extent['@gapBefore'])
            if next_gap_before < 0: # when negative crop end of current title clip, because next title would overlap
                duration = duration + next_gap_before

        title_clip_size_tolerance_margin = 50 # tolerance margin for calculated title clip size e.g. if scrolled text is slighly cut off how many pixels the clip should be bigger on the y-axis
        title_clip_size = ( # tuple (x, y) for title clip size
            output_settings['width'], 
            output_settings['height'] if not should_scroll 
            else TextClip(
                font=find_font_file(font_family), 
                text=text_string, font_size=font_size, 
                stroke_color=tuple(text_outline_color), 
                stroke_width=int(text_outline_size), 
                text_align=text_align
            ).size[1] + title_clip_size_tolerance_margin # calculate title clip height when scrolling to not cut off text
        )
        
        log(f'Preloading title clip (ID {extent_id})...')
        title_clip = (
            TextClip(font=find_font_file(font_family), 
                    text=text_string, 
                    font_size=font_size, 
                    size=title_clip_size, 
                    method='caption', 
                    color=tuple(text_color), 
                    stroke_color=tuple(text_outline_color), 
                    stroke_width=int(text_outline_size), 
                    text_align=text_align, 
                    horizontal_align='center', 
                    vertical_align='center', 
                    duration=duration
            )
            .with_start(previous_clip_end +  max(0, gap_before))
            .with_effects([
                vfx.CrossFadeIn(duration=1.5), # the default title texts in movie maker have a fade transition
                vfx.CrossFadeOut(duration=1.5)
            ] if not should_scroll else []) # only fade when not scrolling
            .with_fps(output_settings['fps'])
        )

        if should_scroll:
            scroll_speed = (title_clip_size[1] + output_settings['height'])/duration # optimal scroll speed so that all text is displayed within duration
            title_clip = title_clip.with_position(lambda t: (0, output_settings['height'] - scroll_speed*t)) # add scroll effect

        title_clips.append(title_clip)

        previous_clip_end += title_clip.duration + max(0, gap_before)
        log(f'Added title clip (ID {extent_id})!')

    log('Building title clips done!')


    log('Compositing video/title clips...')
    # video_composited = CompositeVideoClip([TextClip(font='segoeui.ttf', text="Test", duration=5, font_size=30).with_fps(30).with_duration(10)])
    video_composited = CompositeVideoClip(video_clips + title_clips) # put title clips on top of video clips
    log('Compositing video/title clips done!')
    log('Compositing audio clips...')
    audio_composited = CompositeAudioClip(list(map(lambda v: v.audio, video_clips)) + audio_clips)
    log('Compositing audio clips done!')
    video_composited.audio = audio_composited

    log('Start writing video file...')
    # Write the result to a file (many options available!)
    video_composited.write_videofile(output_file, fps=output_settings['fps']) # optional: set e.g. threads=4 for better performance, but ffmpeg normally detects optimal number automatically
    log('Writing video file done!')

    log('Opening explorer...')
    open_explorer_on_file(output_file)
    log('Opening explorer done!')

    log('Playing sound...')
    play_notification_sound()
    log('Playing sound done!')
    # TODO at end open explorer with rendered file selected

    log('Rendering finished!')
    print('\nEnd time: ' + str(get_current_datetime()) + '\n')