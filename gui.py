import tkinter as tk
from tkinter import ttk, filedialog
import os
from renderer import render
from utils import print_banner

print_banner()
print('Choose render settings in gui, then click "Start rendering"...')

root = tk.Tk()
root.title("Movie Maker Renderer")
# root.geometry("300x350")
root.geometry("") # make window resize dynamically
root.resizable(False, False)

resolutions = {
    "HD": (1280, 720),
    "Full HD": (1920, 1080),
    "2K": (2048, 1080),
    "4K": (3840, 2160),
}

default_resolution = "4K" # default selected resolution
project_filepath = "" # stores the path to the movie maker project file

def validate_numeric_input(P): # only allow positive integers or empty string
    return (P.isdigit() and int(P) > 0) or P == ""

def create_label(text, row, column, **kwargs):
    label = tk.Label(root, text=text, font=("Segoe UI", 10), **kwargs)
    label.grid(row=row, column=column, padx=5, pady=5, sticky="e")
    return label

def toggle_custom_fields(*args): # toggles custom width/height fields
    if selected_option.get() == "Custom":
        custom_widgets[0].grid(row=6, column=0, padx=5, pady=5, sticky="e") # width label
        custom_widgets[1].grid(row=6, column=1, padx=5, pady=5, sticky="ew") # width entry
        custom_widgets[2].grid(row=7, column=0, padx=5, pady=5, sticky="e") # height label
        custom_widgets[3].grid(row=7, column=1, padx=5, pady=5, sticky="ew") # height entry
    else:
        for widget in custom_widgets:
            widget.grid_remove()

def choose_project():
    global project_filepath
    filepath = filedialog.askopenfilename(filetypes=[("Windows Movie Maker Projects", "*.wlmp")])
    if filepath:
        project_label_var.set('Project selected: ' + os.path.basename(filepath))
        project_filepath = filepath
        render_button.config(state="normal")

def start_rendering():
    save_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    if save_path:
        root.destroy() # close tkinter window
        try:
            # note: running this file from windows explorer causes a permission denied error from ffmpeg here; to fix this start this script from a batch file instead
            render(project_filepath, save_path, width_entry_var.get(), height_entry_var.get(), fps_entry_var.get(), overwrite_existing_file=True) # overwrite existing file because file chooser already asks user
        except Exception as e:
            print('\n\nError:', e)
        finally:
            print('\nEnd of script, press Enter to exit...')
            input()
            exit()


# make ui layout
title_label = tk.Label(root, text="Movie Maker Renderer", font=("Segoe UI", 20))
title_label.grid(row=0, column=0, columnspan=2, pady=10, padx=20)

ttk.Separator(root, orient="horizontal").grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

create_label("Choose Project:", row=2, column=0)
ttk.Button(root, text="Choose Project", command=choose_project).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

project_label_var = tk.StringVar(value="No project selected")
project_label = tk.Label(root, textvariable=project_label_var, font=("Segoe UI", 10, "italic"), wraplength=250, anchor="center")
project_label.grid(row=3, column=0, columnspan=2, pady=5)

ttk.Separator(root, orient="horizontal").grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")

create_label("Resolution:", row=5, column=0)
options = list(resolutions.keys()) + ["Custom"]
selected_option = tk.StringVar(value=default_resolution)
ttk.Combobox(root, textvariable=selected_option, values=options, state="readonly").grid(row=5, column=1, padx=5, pady=5, sticky="ew")
selected_option.trace_add("write", toggle_custom_fields)

# custom width/height input entries
width_entry_var = tk.StringVar(value=resolutions[default_resolution][0])
height_entry_var = tk.StringVar(value=resolutions[default_resolution][1])
width_entry = ttk.Entry(root, textvariable=width_entry_var, validate="key", validatecommand=(root.register(validate_numeric_input), "%P"))
height_entry = ttk.Entry(root, textvariable=height_entry_var, validate="key", validatecommand=(root.register(validate_numeric_input), "%P"))

custom_widgets = [
    create_label("Custom width:", row=6, column=0),
    width_entry,
    create_label("Custom height:", row=7, column=0),
    height_entry
]
toggle_custom_fields()

create_label("FPS:", row=8, column=0)
fps_entry_var = tk.StringVar(value="30")
fps_entry = ttk.Entry(root, textvariable=fps_entry_var, validate="key", validatecommand=(root.register(validate_numeric_input), "%P"))
fps_entry.grid(row=8, column=1, padx=5, pady=5, sticky="ew")

ttk.Separator(root, orient="horizontal").grid(row=9, column=0, columnspan=2, pady=5, sticky="ew")

render_button_frame = tk.Frame(root)
render_button_frame.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")
render_button_frame.grid_columnconfigure(0, weight=0)
render_button = ttk.Button(render_button_frame, text="▶ Start Rendering!", command=start_rendering, state="disabled", padding=(10, 2))
render_button.pack(pady=(0, 10))

root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

root.mainloop()
