from ctypes import *
import win32clipboard
import win32ui
import os
import shutil
from time import gmtime, strftime
from sys import stdout
from tkinter import *
from tkinter.ttk import *
import webbrowser
import getpass
import keyboard
import time
import threading


# Load config file
def load_config(config_file="duckhunt.conf"):
    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse key = value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.split('#')[0].strip()  # Remove inline comments
                    
                    # Remove quotes from strings
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # Convert to appropriate types
                    elif value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    
                    config[key] = value
        return config
    except FileNotFoundError:
        print("ERROR: duckhunt.conf file not found!")
        exit(1)
    except Exception as e:
        print(f"ERROR loading config file: {e}")
        exit(1)

# Load configuration
config = load_config()

# Create a simple object to mimic the module behavior
class DuckHuntConfig:
    pass

duckhunt = DuckHuntConfig()
duckhunt.threshold = config.get('threshold', 30)
duckhunt.size = config.get('size', 25)
duckhunt.policy = config.get('policy', 'normal').lower()
duckhunt.password = config.get('password', 'quack')
duckhunt.allow_auto_type_software = config.get('allow_auto_type_software', True)
duckhunt.randdrop = config.get('randdrop', 6)
duckhunt.filename = config.get('filename', 'log.txt')
duckhunt.blacklist = config.get('blacklist', '')

##### NOTES #####
#
# 1. Understanding Protection Policy:
#   - Paranoid: When an attack is detected, lock down any further keypresses until the correct password is entered. (set password in .conf file). Attack will also be logged.
#   - Normal: When an attack is detected, keyboard input will temporarily be disallowed. (After it is deemed that the threat is over, keyboard input will be allowed again). Attack will also be logged.
#   - Sneaky: When an attack is detected, a few keys will be dropped (enough to break any attack, make it look as if the attacker messed up.) Attack will also be logged.
#   - LogOnly: When an attack is detected, simply log the attack and in no way stop it. 

# 2. How To Use
#   - Modify the user configurable vars in duckhunt.conf
#   - Turn the program into a .pyw to run it as windowless script.
#   - (Opt) Use PyInstaller to build an .exe
#
#################


threshold = duckhunt.threshold  # Speed Threshold
size = duckhunt.size  # Size of history array
policy = duckhunt.policy  # Designate Policy Type
password = duckhunt.password  # Password used in Paranoid Mode
allow_auto_type_software = duckhunt.allow_auto_type_software  # Allow AutoType Software
################################################################################
pcounter = 0  # Password Counter (If using password)
speed = 0  # Current Average Keystroke Speed
prevTime = -1  # Previous Keypress Timestamp
i = 0  # History Array Timeslot
intrusion = False  # Boolean Flag to be raised in case of intrusion detection
history = [threshold + 1] * size  # Array for keeping track of average speeds across the last n keypresses
randdrop = duckhunt.randdrop  # How often should one drop a letter (in Sneaky mode)
prevWindow = ""  # What was the previous window
filename = duckhunt.filename  # Filename to save attacks
blacklist = duckhunt.blacklist  # Program Blacklist
block_keyboard = False  # Flag to block all keyboard input
password_buffer = ""  # Buffer for password input in paranoid mode


# Get active window title
def get_active_window():
    try:
        import win32gui
        window = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(window)
    except:
        return "Unknown Window"


# Logging the Attack
def log(key_name):
    global prevWindow

    current_window = get_active_window()
    x = open(filename, "a+")
    if (prevWindow != current_window):
        x.write("\n[ %s ]\n" % (current_window))
        prevWindow = current_window
    
    x.write("[%s]" % key_name)
    x.close()
    return


def caught(key_name):
    global intrusion, policy, randdrop, block_keyboard
    print("Quack! Quack! -- Time to go Duckhunting!")
    intrusion = True
    log(key_name)

    # Paranoid Policy
    if policy == "paranoid":
        block_keyboard = True
        threading.Thread(target=show_paranoid_alert, daemon=True).start()
        return True  # Block this key
    
    # Sneaky Policy
    elif policy == "sneaky":
        randdrop += 1
        # Drop every 7th letter
        if randdrop == 7:
            randdrop = 0
            return True  # Block this key
        else:
            return False  # Allow this key

    # Logging Only Policy
    elif policy == "log":
        return False  # Allow key

    # Normal Policy - block during intrusion
    block_keyboard = True
    threading.Thread(target=show_normal_alert, daemon=True).start()
    return True  # Block this key


def show_paranoid_alert():
    win32ui.MessageBox(
        "Someone might be trying to inject keystrokes into your computer.\nPlease check your ports or any strange programs running.\nEnter your Password to unlock keyboard.",
        "KeyInjection Detected", 4096)


def show_normal_alert():
    global block_keyboard, intrusion
    win32ui.MessageBox(
        "KeyInjection Attack Detected!\nKeyboard input has been blocked temporarily.",
        "KeyInjection Detected", 4096)
    # After closing the alert, wait to see if threat continues
    time.sleep(2)
    block_keyboard = False


# This is triggered every time a key is pressed
def on_key_event(event):
    global threshold, policy, password, pcounter, password_buffer
    global speed, prevTime, i, history, intrusion, blacklist, block_keyboard

    key_name = event.name
    current_time = time.time() * 1000  # Convert to milliseconds
    current_window = get_active_window()

    print(f"Key: {key_name}")

    # Handle Paranoid mode password entry
    if policy == "paranoid" and block_keyboard:
        if key_name == "backspace" and password_buffer:
            password_buffer = password_buffer[:-1]
        elif len(key_name) == 1:  # Single character
            password_buffer += key_name
            
        print(f"Password buffer: {password_buffer}")
        
        if password_buffer == password:
            print("Correct Password!")
            win32ui.MessageBox("Correct Password! Keyboard Unlocked.", "Access Granted", 4096)
            block_keyboard = False
            intrusion = False
            password_buffer = ""
            pcounter = 0
        
        return True  # Block all keys during paranoid mode

    # Normal/Sneaky mode blocking during intrusion
    if block_keyboard and policy == "normal":
        return True  # Block key

    # Initial Condition
    if prevTime == -1:
        prevTime = current_time
        return False  # Allow key

    if i >= len(history):
        i = 0

    # TypeSpeed = NewKeyTime - OldKeyTime
    history[i] = current_time - prevTime
    print(f"{current_time} - {prevTime} = {history[i]}")
    prevTime = current_time
    speed = sum(history) / float(len(history))
    i = i + 1

    print(f"Average Speed: {speed}")

    # Blacklisting
    for window in blacklist.split(","):
        if window.strip() and window.strip() in current_window:
            should_block = caught(key_name)
            return should_block

    # Intrusion detected
    if speed < threshold:
        should_block = caught(key_name)
        return should_block
    else:
        intrusion = False
        block_keyboard = False
    
    # Allow key
    return False


def start_keyboard_hook():
    print("DuckHunt started! Monitoring keyboard...")
    # Hook all keyboard events
    keyboard.hook(on_key_event, suppress=True)
    keyboard.wait()  # Keep the hook running


def window():
    main_window = Tk()
    
    def StopScript():
        keyboard.unhook_all()
        exit(0)

    def About():
        webbrowser.open_new(r"https://github.com/pmsosa/duckhunt/blob/master/README.md")
    
    def WindowStarted():
        def HideWindow():
            window1.destroy()
            
        def add_to_startup(file_path=dir_path):
            if file_path == "":
                file_path = os.path.dirname(os.path.realpath(__file__))
            bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % USER_NAME
            with open(bat_path + '\\' + "duckhunt.bat", "w+") as bat_file:
                bat_file.write(r'start "" "%s\builds\duckhunt.0.9.exe"' % file_path)
        
        def FullScreen():
            window1.attributes('-fullscreen', True)
            window1.bind('<Escape>', lambda e: window1.destroy())
            
        def HideTitleBar():
            window1.overrideredirect(True)
        
        window1 = Tk()
        window1.title("DuckHunter")
        try:
            window1.iconbitmap('favicon.ico')
        except:
            pass
        window1.geometry('310x45')
        window1.resizable(False, False)
        window1.geometry("+300+300")
        window1.attributes("-topmost", True)
        menu = Menu(window1)
        new_item = Menu(menu)
        new_item.add_command(label='STOP SCRIPT', command=StopScript)
        new_item.add_command(label='CLOSE WINDOW', command=HideWindow)
        new_item.add_separator()
        new_item.add_command(label='ABOUT', command=About)
        menu.add_cascade(label='Menu', menu=new_item)
        window1.config(menu=menu) 
        btn = Button(window1, text="Stop Script", command=StopScript)
        btn1 = Button(window1, text="Close Window", command=HideWindow)
        btn2 = Button(window1, text="RUN SCRIPT ON STARTUP", command=add_to_startup)
        new_item2 = Menu(menu)
        new_item2.add_command(label='RUN SCRIPT ON STARTUP', command=add_to_startup)
        new_item2.add_command(label='FULLSCREEN', command=FullScreen)
        new_item2.add_command(label='HIDE TITLE BAR', command=HideTitleBar)
        menu.add_cascade(label='Settings', menu=new_item2)
        btn2.grid(column=3, row=0)
        btn.grid(column=1, row=0)
        btn1.grid(column=2, row=0)

        window1.mainloop()
        
    def start():
        main_window.destroy()
        # Start keyboard hook in a separate thread
        hook_thread = threading.Thread(target=start_keyboard_hook, daemon=True)
        hook_thread.start()
        WindowStarted()
    
    USER_NAME = getpass.getuser()
    dir_path = os.path.dirname(os.path.realpath(__file__))

    def FullScreen():
        main_window.attributes('-fullscreen', True)
        main_window.bind('<Escape>', lambda e: main_window.destroy())
    
    def HideTitleBar():
        main_window.overrideredirect(True)
        
    def add_to_startup(file_path=dir_path):
        if file_path == "":
            file_path = os.path.dirname(os.path.realpath(__file__))
        bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % USER_NAME
        with open(bat_path + '\\' + "duckhunt.bat", "w+") as bat_file:
            bat_file.write(r'start "" "%s\AutoRunDuckHunt.exe"' % file_path)

    main_window.title("DuckHunter")
    try:
        main_window.iconbitmap('favicon.ico')
    except:
        pass
    main_window.resizable(False, False)
    main_window.geometry('300x45')
    main_window.geometry("+300+300")
    main_window.attributes("-topmost", True)
    menu = Menu(main_window)
    new_item = Menu(menu)
    new_item.add_command(label='START', command=start)
    new_item.add_command(label='CLOSE', command=StopScript)
    new_item.add_separator()
    new_item.add_command(label='ABOUT', command=About)
    menu.add_cascade(label='Menu', menu=new_item)
    new_item2 = Menu(menu)
    new_item2.add_command(label='RUN SCRIPT ON STARTUP', command=add_to_startup)
    new_item2.add_command(label='FULLSCREEN', command=FullScreen)
    new_item2.add_command(label='HIDE TITLE BAR', command=HideTitleBar)
    menu.add_cascade(label='Settings', menu=new_item2)
    main_window.config(menu=menu)
    btn = Button(main_window, text="Start", command=start)
    btn.grid(column=1, row=0)
    btn = Button(main_window, text="Close", command=StopScript)
    btn.grid(column=2, row=0)
    btn = Button(main_window, text="RUN SCRIPT ON STARTUP", command=add_to_startup)
    btn.grid(column=3, row=0)

    main_window.mainloop()


# Main execution
if __name__ == "__main__":
    window()