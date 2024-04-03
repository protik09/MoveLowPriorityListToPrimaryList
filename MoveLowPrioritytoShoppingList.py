"""
Script to move low priority shopping list items to primary shopping list, if they're ticked.

Author:
    Protik Banerji <protik09@gmail.com>
"""
import os
import gkeepapi
import keyring
import maskpass
import re
try:
    import simplejson as json
except ImportError:
    import json
from time import perf_counter as timer, sleep
if os.name == 'nt':
    from infi.systray import SysTrayIcon
else:
    pass

try:
    if os.name == 'nt':
        from infi.systray import SysTrayIcon
except ImportError:
    pass
# Define constants at the top of your file
GOOGLE_KEEP_MASTER_TOKEN = 'Google Keep Master Token'
# Define the base directory for your application
BASE_DIR = os.path.abspath(os.getcwd())
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
# Adjust the path for keep_notes.json
KEEP_NOTES_PATH = os.path.join(BASE_DIR, 'keep_notes.json')



def first_run() -> bool:
    """
    Check if this is the first run of the program.

    Args:
        None

    Returns: 
        bool: 'True' if first run, 'False' if not.
    """
    return not os.path.isfile(CONFIG_FILE)  # The 'not' is there to flip the return value of isfile


def load_settings() -> dict:
    """
    Load settings from config.json

    Returns: 
        dict: Dictionary of settings
    """
    try:
        with open(CONFIG_FILE, 'r') as openfile:
            # Reading the settings from json file
            settings = json.load(openfile)
            # The Google Master Token is stored on the system keyring and extracted from there
            settings['master_token'] = keyring.get_password(
                GOOGLE_KEEP_MASTER_TOKEN, settings['username'])
            return settings
    except FileNotFoundError:
        print(f"{CONFIG_FILE} not found.")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}


def check_username(username: str) -> None:
    """
    Check if the username is a valid email address.

    Args:
        username (str): Email address of user

    Returns:
        None
    """
    assert username != "", f"Username is empty"
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    assert re.match(
        email_regex, username), f"Invalid email address: {'username'}"
    return None


def check_token(token: str) -> None:
    """
    Checks to ensure token is not empty or too short. 
    * I'm just guessing about the minimum length of a token though. 
    * If you run into issues, feel free to change it and send a pull request.

    Args:
        token (str): Google Keep Master Token

    Returns:
        None
    """
    assert token != "", f"Master token is empty, got: {token}"
    assert len(
        token) > 100, f"Master token is too short, got: {len(token)} characters"

    return None


def check_list_names(keep: object, primary_list: list, low_priority_list: list) -> None:
    """
    Check that the primary and low priority list names are not empty or non-existent in the keep object.

    Args:
        keep (obj): Google Keep object
        primary_list (list): Names of primary lists
        low_priority_list (list): Names of low priority lists

    Returns:
        None
    """
    assert primary_list != [], f"Primary list name is empty"
    for list_name in primary_list:
        assert list_name != "", f"Invalid Primary list name: {list_name}"
    assert low_priority_list != [], f"Low priority list name is empty"
    for list_name in low_priority_list:
        assert list_name != "", f"Invalid Low priority list name: {list_name}"
    # Check if the list names exist in the keep object
    for list_name in primary_list:
        assert keep.list(list_name) is not None, f"Primary list does not exist: {list_name}"
    for list_name in low_priority_list:
        assert keep.list(list_name) is not None, f"Low priority list does not exist: {list_name}"
    return None


def check_low_priority_items(keep: object, low_priority_list: str) -> list:
    """
    Check the low priority list for items that are ticked.

    Args:
        keep (obj): Google Keep object
        low_priority_list (str): Name of low priority list

    Returns:
        list: List of items to move
    """
    items_to_move = []
    for note in keep.all():
        if low_priority_list in note.title:
            checked_items = note.checked
            for item in checked_items:
                items_to_move.append(item)
                # delete item from note
                item.delete()
    return items_to_move


def check_num_sets(num_sets: int) -> None:
    """
    Check that the number of sets is greater than 0.

    Args:
        num_sets (int): Number of sets

    Returns:
        None
    """
    assert num_sets > 0, f"Number of sets must be greater than 0, got: {num_sets}"
    return None


def check_settings(keep: object, config: dict) -> None:
    """
    Check that the settings file is not broken.

    Args:
        keep (obj): Google Keep object
        config (dict): Dictionary of settings

    Returns:
        bool: 'True' if settings are valid, 'False' if not
    """
    assert config != {}, f"{CONFIG_FILE} is empty"  # Check that config is not empty
    assert config['first_run_flag'] == "True", f"{CONFIG_FILE} maybe corrupted"
    check_token(config['master_token'])
    check_username(config["username"])
    check_num_sets(config['num_sets'])
    # Check to see that there are no empty elements or empty strings in the primary and low prioritylist
    check_list_names(keep, config['primary_list'], config['low_priority_list'])
    print(f'Loaded settings. Username: {config["username"]}')

    return None


def move_items_to_primary_list(keep: object, primary_list: str, items_to_move: list) -> None:
    """
    Move ticked items from low priority list to primary list.

    Args:
        keep (obj): Google Keep object
        primary_list (str): Name of primary list
        items_to_move (list): List of items to move

    Returns:
        None
    """
    for note in keep.all():
        if primary_list in note.title:
            for item in items_to_move:
                # Add the item to the top of the primary list unticked
                note.add(item.text, False,
                         gkeepapi.node.NewListItemPlacementValue.Top)
    return None

def delete_ticked_items_from_primary_list(keep: object, primary_list: str) -> None:
    """
    Delete ticked items from primary list.
    
    Args:
        keep (obj): Google Keep object
        primary_list (str): Name of primary list
        
    Returns:
        None
    """
    for note in keep.all():
        if primary_list in note.title:
            for item in note:
                if item.checked:
                    item.delete()
                    
    return None

def loop(keep: object, config: dict) -> None:
    """
        Synchronize the changes to the Google Keep server and continuously move low priority items to the primary list.

        Args:
            keep (object): The object representing the Google Keep instance.
            config (dict): The dictionary containing the configuration settings.

        Returns:
            None
    """
    while True:
        # Syc the changes to the Google Keep server
        keep.sync()
        items_to_move = check_low_priority_items(
            keep, config['low_priority_list'])

        # if no items to move, return to check for low priority items
        if items_to_move == []:
            # print('No items to move')
            pass
        else:
            move_items_to_primary_list(
                keep, config['primary_list'], items_to_move)
            print(
                f'Moved {len(items_to_move)} items to {config["primary_list"]}')
            items_to_move = []
            # Dump Keep Notes to disk for caching
            with open("keep_notes.json", "w") as outfile:
                json.dump(keep.dump(), outfile)
        # Rate restriction to prevent API ban from Google
        sleep(0.5)


def main():
    # start_time = timer()
    if first_run():
        print("First run")
        username = input("Google Keep Username: ")
        check_username(username)
        master_token = maskpass.askpass(
            "Google Keep Master Token (Use the included DockerFile to get one): ")
        check_token(master_token)
        # Load all Keep Notes
        try:
            keep = gkeepapi.Keep()
            keep.resume(username, master_token)
        except Exception as e:
            print(f"Username or master token is invalid: {e}")
            exit(-1)
        # If the login above is successful, write the master token to system keyring
        keyring.set_password("Google Keep Master Token",
                             username, master_token)
        num_sets = int(
            input('Number of Sets of Lists (1 Set contains two Lists ): '))
        check_num_sets(num_sets)

        primary_lists = []
        low_priority_lists = []
        for i in range(int(num_sets)):
            primary_list = input(f'Name of Primary List {i+1}: ')
            low_priority_list = input(f'Name of Low Priority List {i+1}: ')
            primary_lists.append(primary_list)
            low_priority_lists.append(low_priority_list)
            check_list_names(primary_lists, low_priority_lists)
            # Master token is stored on the system keyring so deliberately empty
            config = {
                "first_run_flag": "True",
                "username": username,
                "master_token": "",
                "num_sets": num_sets,
                "primary_list": primary_lists,
                "low_priority_list": low_priority_lists
            }
            json_object = json.dumps(config, indent=4)

            # Writing config.json
            with open("config.json", "w") as outfile:
                outfile.write(json_object)
            config["master_token"] = master_token

        # Before loading the Google Keep object check the settings
        if check_settings(keep, config):
            pass
        else:
            raise Exception("Settings are not valid")

        # Dump Keep Notes to disk for caching
        with open("keep_notes.json", "w") as outfile:
            json.dump(keep.dump(), outfile)

    else:
        config = load_settings()
        check_settings(config)
        # Restore notes from database or online
        keep.resume(config['username'], config['master_token'],
                    state=json.load(open("keep_notes.json")))

    # end_time = timer()
    # print(f'Time to initialize: {(end_time - start_time)}s')

    # Start SysTray Icon if running on Windows, do nothing if on Linux
    if os.name == 'nt':
        hover_text = "Move Low Priority Items to Primary List in Google Keep"
        sysTrayIcon = SysTrayIcon("keep_notes_automation.ico", hover_text,
                                  default_menu_index=1)
        try:
            sysTrayIcon.start()
        except KeyboardInterrupt:
            sysTrayIcon.shutdown()
    else:
        pass
    loop(keep, config)


if __name__ == '__main__':
    main()
