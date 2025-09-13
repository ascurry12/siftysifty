import tkinter
from tkinter import filedialog as fd
from tkinter import StringVar
from tkinter import messagebox
import webbrowser
import pandas as pd
import pathlib
from send2trash import send2trash
import shutil
from pathlib import Path

# *** ///////// GUI ///////// ***

window = tkinter.Tk()
window.title("SiftySifty")

frame = tkinter.Frame(window)
frame.pack()

game_setting_frame = tkinter.LabelFrame(frame, text="Select Game")
game_setting_frame.grid(row=0, column=0)

v = StringVar(frame, "3") # default; CHANGE TO 2 FOR PROD
u = StringVar(frame, "n") 

set_iters = 5
# *** /////////////////////// ***

# User has a choice between The Sims 3 and 4 (use specific directory based on choice)
GAMES = {"The Sims 3": 1,
         "The Sims 4": 2,
         "Test": 3}

ALLOWED_3 = ('.package')
ALLOWED_4 = ('.package', '.ts4script')

# Define paths
USER = pathlib.Path.home()

print("User", USER)

SIMS_3_MODS_PATH = USER / "Documents" / "Electronic Arts" / "The Sims 3" / "Mods" / "Packages"

SIMS_4_MODS_PATH = USER / "Documents" / "Electronic Arts" / "The Sims 4" / "Mods"

TEST_PATH = USER / "Desktop" / "Mods"

current_mod_path = TEST_PATH # CHANGE TO SIMS_4_MODS_PATH FOR PROD
current_allowed = ALLOWED_4

if v == "1":
    current_mod_path = SIMS_3_MODS_PATH
    current_allowed = ALLOWED_3
elif v == "2":
    current_mod_path = SIMS_4_MODS_PATH
    current_allowed = ALLOWED_4
else:
    current_mod_path = TEST_PATH
    current_allowed = ALLOWED_3

print("Test path", TEST_PATH)

# Define folders

folder_paths = {
    "backup": "",
    "keep": "",
    "active": "",
    "inactive": "",
    "quarantine": ""
}

def create_folders():
    folders = [
        "backup",
        "keep",
        "active",
        "inactive",
        "quarantine"
    ]

    main_folder_path = USER / "Desktop" / "siftysiftydir"

    if not main_folder_path.exists():
        main_folder_path.mkdir()
        print(f"Created folder: {main_folder_path}")
    else:
        print(f"Folder already exists: {main_folder_path}")

    for folder in folders:
        folder_path = main_folder_path / folder
        folder_paths[folder] = folder_path
        if not folder_path.exists():
            folder_path.mkdir()
            print(f"Created folder: {folder_path}")
        else:
            # Clear existing folders (moved to trash for safety, user should clear trash after use, add disclaimer) and create new ones
            print(f"Folder already exists: {folder_path}")
            send2trash(folder_path)
            folder_path.mkdir()
            print(f"Folder cleared: {folder_path}")

    # Copy mods to backup
    copy_mods(current_mod_path , folder_paths["backup"], True)

def clean_folder(folder: pathlib.Path):
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir()

def copy_mods(src: pathlib.Path, dir: pathlib.Path, replace):
    shutil.copytree(src, dir, dirs_exist_ok=replace)

def move_mod(file: pathlib.Path, src, dest):
    relative_path = file.relative_to(src.resolve())
    dest_path = dest / relative_path 
    
    if file.resolve() == dest_path.resolve():
        print(f"Skipping copy — source and destination are the same: {file}")
        return
    
    if src == folder_paths["backup"]:
        shutil.copy2(str(file), str(dest_path))
    else:
        shutil.move(str(file), str(dest_path))

# Disable upload button if Sims 4 is not selected
def update_button_state():
    if v.get() == "2" or v.get() == "3":
        csv_upload_button.config(state="normal")
    else:
        csv_upload_button.config(state="disabled")

# Recursively collect mod files from a directory and sorts them by last modified date.
def sort_mod_files(mod_path: Path):
    # Use pathlib's rglob for recursive search
    mod_files = [f for f in mod_path.rglob("*") if f.suffix.lower() in ALLOWED_4]

    # Sort by last modified time (descending: newest first)
    sorted_mods = sorted(mod_files, key=lambda f: f.stat().st_mtime, reverse=True)

    print(f"Found {len(sorted_mods)} mods")
    for mod in sorted_mods[:5]:  # Preview top 5
        print(f"{mod} — Last modified: {mod.stat().st_mtime}")

    return sorted_mods

# ///////// TO-DO //////////
# (Optional) User can upload most recent mod checker csv from https://scarletsrealm.com/the-mod-list-checker/#instructions
def load_csv():
    file_path = fd.askopenfilename(title="Select file", filetypes=[("Comma-Separated Values", "*.csv")])
    if file_path and "Mod List Checker" in file_path:
        # Filter csv for broken mods 
        df = pd.read_csv(file_path, usecols=['Mod Name', 'Creator', 'Patch Status'])
        filtered_df = df[df['Patch Status'] == "Broken"]

        print("Selected file:", file_path)
        print(filtered_df)

        # Sort mod folder by date (descending)
        sorted_mods = sort_mod_files(TEST_PATH) # CHANGE TO SIMS 4 IN PROD
        print(sorted_mods)
        # Perform check, move broken mods to quarantine folder
        potential_broken = []
        for index, row in filtered_df.iterrows():
                for mod in sorted_mods:
                    not_contained = False
                    substrings = str(row['Mod Name']).lower().split(" ")
                    for substring in substrings:
                        if substring not in str(mod).lower():
                            not_contained = True
                            continue
                    if not not_contained:
                        potential_broken.append(mod)
        for mod in potential_broken:
            move_mod(mod, TEST_PATH, folder_paths["quarantine"])

        # Report potential broken mods via pop-up (total number)
        messagebox.showinfo(title="CSV Check Complete", message=f"{len(potential_broken)} mod{"" if len(potential_broken) == 1 else "s"} moved to quarantine")
        
    else:
        messagebox.showinfo(title="Error", message="Invalid file uploaded")
# ////////////////////////////

def start_fifty_fifty(mod_path):
    mods = sort_mod_files(mod_path)
    print(f"\n Running 50/50 round from: {current_mod_path}")

    if len(mods) <= set_iters:
        print(f"Quarantine triggered — {len(mods)} mod(s) remaining")
        for file in mods:
            move_mod(file, mod_path, folder_paths["quarantine"])
        messagebox.showinfo("Test Complete", "Potential problem mods moved to quarantine. All mods remain in backup folder.")
        return
    
    half = len(mods) // 2
    test_mods = mods[:half]
    inactive_mods = mods[half:]

    # Clean destination folders
    clean_folder(current_mod_path)

    # Move files to Mods (active test batch)
    print(test_mods)
    for file in test_mods:
        move_mod(file, mod_path, current_mod_path)
        shutil.copy2(current_mod_path / file.name, folder_paths["active"] / file.name)

    print(inactive_mods)
    # Move files to HoldMods (not being tested now)
    for file in inactive_mods:
        move_mod(file, mod_path, folder_paths["inactive"])

    print(f"Moved {len(test_mods)} mods to Mods")
    print(f"Held back {len(inactive_mods)} mods in InactiveMods")

    result = messagebox.askyesnocancel(message="Please run your game. Did the problem persist?")

    if not result:
        clean_folder(folder_paths["active"])
        start_fifty_fifty(folder_paths["inactive"])
    elif result:
        clean_folder(folder_paths["inactive"])
        start_fifty_fifty(folder_paths["active"])
    elif result is None:
        messagebox.showinfo("Quit", message="Testing quit")
        return

    """
    if remaining_mods <= set_iters:
        for file in test_mods:
            move_mod(file, mod_path, folder_paths["quarantine"])

        # Move files to HoldMods (not being tested now)
        for file in inactive_mods:
            move_mod(file, mod_path, folder_paths["quarantine"])
        
        messagebox.showinfo("Potential problem mods have been moved to the qurantine file")
   """     

# Initialize folders
create_folders()

# *** ///////// GUI ///////// ***

for (text, value) in GAMES.items():
    tkinter.Radiobutton(game_setting_frame, text=text, value=value, variable=v, command=update_button_state).grid(row=0, column=value-1)

# ///////// Only compatible with The Sims 4 ///////////

csv_upload_frame = tkinter.LabelFrame(frame, text="Mod List File Upload (Sims 4 Compatible)")
csv_upload_frame.grid(row=1, column=0)

csv_upload_tip = tkinter.Message(csv_upload_frame, text="Click here to download the latest mod list file from Scarlet's Realm", fg="blue", cursor="pointinghand")
csv_upload_tip.grid(row=0, column=0)
csv_upload_tip.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://scarletsrealm.com/the-mod-list-checker/"))

csv_upload_button = tkinter.Button(csv_upload_frame, text="Upload File", command=load_csv)
csv_upload_button.grid(row=0, column=1)

# ////////////////////////////////////////////////////

main_test_frame = tkinter.LabelFrame(frame, text="50/50 Tester")
main_test_frame.grid(row=2, column=0)

start_test_button = tkinter.Button(main_test_frame, text="Start Test", command=lambda:start_fifty_fifty(folder_paths["backup"]))
start_test_button.grid(row=0, column=0)

window.mainloop()

# *** ////////////////////////////// ***



# Workflow

# Display .package file count in mod folder


# Prompt user to start game and confirm if problems persist (if yes, prompt to start 50/50 check)

# User starts 50/50 mod check via button click

# Split remaining mods into two folders: active and inactive

# Add active files into mod folder, prompt user to launch game, confirm if problem persists

# If problem persists, continue 50/50 method on active files; if not, move current active files to backup folder and inactive files to active folder

# Once number of remaining files reaches specified number (set by user, 1-10), add to quarantine folder and allow user to manually test