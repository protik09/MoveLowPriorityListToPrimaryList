"""
Script to move low priority shopping list items to primary shopping list, if they're ticked.

Author:
    Protik Banerji <protik09@gmail.com>
"""

import os
import argparse
import gkeepapi
import keyring
import maskpass
import re

try:
    import simplejson as json
except ImportError:
    import json
# from time import perf_counter as timer
from time import sleep

if os.name == "nt":
    from infi.systray import SysTrayIcon
else:
    pass

# Define constants at the top of your file
GOOGLE_KEEP_MASTER_TOKEN: str = "Google Keep Master Token"
# Define the base directory for your application
BASE_DIR: str = os.path.abspath(os.getcwd())
CONFIG_FILE: str = os.path.join(BASE_DIR, "config.json")
# Adjust the path for keep_notes.json
KEEP_NOTES_PATH: str = os.path.join(BASE_DIR, "keep_notes.json")


def firstRun() -> bool:
    """
    Check if this is the first run of the program.

    Args:
        None

    Returns:
        bool: 'True' if first run, 'False' if not.
    """
    return not os.path.isfile(
        CONFIG_FILE
    )  # The 'not' is there to flip the return value of isfile


def loadSettings(config: str = CONFIG_FILE) -> dict:
    """
    Load settings from config.json

    Returns:
        dict: Dictionary of settings
    """
    try:
        with open(CONFIG_FILE, "r") as openfile:
            # Reading the settings from json file
            settings = json.load(openfile)
            # The Google Master Token is stored on the system keyring and extracted from there
            settings["master_token"] = keyring.get_password(
                GOOGLE_KEEP_MASTER_TOKEN, settings["username"]
            )
            return settings
    except FileNotFoundError:
        print(f"{CONFIG_FILE} not found.")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}


def checkUsername(username: str) -> bool:
    """
    Check if the username is a valid email address.

    Args:
        username (str): Email address of user

    Returns:
        Bool: 'True' if valid, 'False' if not.
    """
    if not username:
        raise ValueError("Username is empty")
    email_regex = r"\b[A-Za-z0-9._%+-]+@gmail\.[A-Z|a-z]{2,}\b"
    if not re.match(email_regex, username):
        raise ValueError(f"Invalid email address: {username}. Must be a gmail account.")
    return True


def checkToken(token: str) -> bool:
    """
    Checks to ensure token is not empty or too short.
    * I'm just guessing about the minimum length of a token though.
    * If you run into issues, feel free to change it and send a pull request.

    Args:
        token (str): Google Keep Master Token

    Returns:
        Bool: 'True' if valid, 'False' if not.
    """
    if not token:
        raise ValueError("Master token is empty")
    if len(token) < 100:  # This is a guess
        raise ValueError(f"Master token is too short, got: {len(token)} characters")
    return True


def checkListNames(keep: object, primary_list: list, low_priority_list: list) -> bool:
    """
    Check that the primary and low priority list names are not empty or non-existent in the keep object.

    Args:
        keep (obj): Google Keep object
        primary_list (list): Names of primary lists
        low_priority_list (list): Names of low priority lists

    Raises:
        ValueError: If any of the lists are empty or list names are invalid.
        LookupError: If a list name does not exist in the keep object.

    Returns:
        True if all checks pass.
    """
    if not primary_list:
        raise ValueError("Primary list name is empty")
    for list_name in primary_list:
        if not list_name:
            raise ValueError(f"Invalid Primary list name: {list_name}")
    if not low_priority_list:
        raise ValueError("Low priority list name is empty")
    for list_name in low_priority_list:
        if not list_name:
            raise ValueError(f"Invalid Low priority list name: {list_name}")
    # Check if the list names exist in the keep object
    for list_name in primary_list:
        if keep.list(list_name) is None:
            raise LookupError(f"Primary list does not exist: {list_name}")
    for list_name in low_priority_list:
        if keep.list(list_name) is None:
            raise LookupError(f"Low priority list does not exist: {list_name}")
    return True


def checkLowPriorityItems(keep: object, low_priority_list: str) -> list:
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


def checkNumSets(num_sets: int) -> bool:
    """
    Check that the number of sets is greater than 0.

    Args:
        num_sets (int): Number of sets

    Returns:
        None
    """
    if num_sets < 1:  # Check that the number of sets is greater than 0
        raise ValueError(f"Number of sets must be greater than 0, got: {num_sets}")
    return True


def checkSettings(keep: object, config: dict) -> bool:
    """
    Check that the settings file is not broken.

    Args:
        keep (obj): Google Keep object
        config (dict): Dictionary of settings

    Returns:
        bool: 'True' if settings are valid, 'False' if not
    """
    if not config:
        raise ValueError(f"{CONFIG_FILE} is empty")
    if not config["first_run_flag"] == "True":  # Check that the first run flag is set
        raise ValueError(f"{CONFIG_FILE} maybe corrupted")
    checkToken(config["master_token"])
    checkUsername(config["username"])
    checkNumSets(config["num_sets"])
    # Check to see that there are no empty elements or empty strings in the primary and low prioritylist
    checkListNames(keep, config["primary_list"], config["low_priority_list"])
    print(f'Loaded settings. Username: {config["username"]}')

    return True


def moveItemsToPrimaryList(
    keep: object, primary_list: str, items_to_move: list
) -> None:
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
                note.add(item.text, False, gkeepapi.node.NewListItemPlacementValue.Top)
    return None


def DeleteTickedItemsFromPrimaryList(keep: object, primary_list: str) -> None:
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


def programLoop(keep: object, config: dict) -> None:
    """
    Synchronize the changes to the Google Keep server and continuously move
    low priority items to the primary list.

    Args:
        keep (object): The object representing the Google Keep instance.
        config (dict): The dictionary containing the configuration settings.

    Returns:
        None
    """
    while True:
        # Syc the changes to the Google Keep server
        keep.sync()
        items_to_move: list = checkLowPriorityItems(keep, config["low_priority_list"])

        # if no items to move, return to check for low priority items
        if items_to_move:
            moveItemsToPrimaryList(keep, config["primary_list"], items_to_move)
            print(f'Moved {len(items_to_move)} items to {config["primary_list"]}')
            items_to_move.clear()

            # Dump Keep Notes to disk for caching
            with open(os.path.join(BASE_DIR, "keep_notes.json"), "w") as outfile:
                json.dump(keep.dump(), outfile)
        else:
            pass
        # Rate restriction to prevent API ban from Google
        sleep(1)

        return None


def getConfigFromUser() -> tuple:
    """
    Get the configuration from the user.
    * This function is only called if the config.json file is not found.
    * The config.json file is created by this function.
    * The master token is stored on the system keyring.

    Args:
        None
    Returns:
        tuple: (keep, config)
        keep (obj): Google Keep object
        config (dict): Dictionary of settings
    """
    username = input("Google Keep Username: ")
    checkUsername(username)
    master_token = maskpass.askpass(
        "Google Keep Master Token (Use the included DockerFile to get one): "
    )
    checkToken(master_token)
    # Load all Keep Notes
    try:
        keep = gkeepapi.Keep()
        keep.resume(username, master_token)
    except Exception as e:
        print(f"Username or master token is invalid: {e}")
        exit(-1)
    # If the login above is successful, write the master token to system keyring
    keyring.set_password("Google Keep Master Token", username, master_token)
    num_sets = int(input("Number of Sets of Lists (1 Set contains two Lists ): "))
    checkNumSets(num_sets)

    primary_lists = []
    low_priority_lists = []
    for i in range(int(num_sets)):
        primary_list = input(f"Name of Primary List {i+1}: ")
        low_priority_list = input(f"Name of Low Priority List {i+1}: ")
        primary_lists.append(primary_list)
        low_priority_lists.append(low_priority_list)
        checkListNames(primary_lists, low_priority_lists)
        # Master token is stored on the system keyring so deliberately empty
        config = {
            "first_run_flag": "True",
            "username": username,
            "master_token": "",
            "num_sets": num_sets,
            "primary_list": primary_lists,
            "low_priority_list": low_priority_lists,
        }
        json_serialized = json.dumps(config, indent=4)

        # Writing config.json
        with open("config.json", "w") as outfile:
            outfile.write(json_serialized)
        config["master_token"] = master_token
    return (keep, config)


def main():
    # start_time = timer()
    # Check for input config files
    parser = argparse.ArgumentParser(
        description="Move Low Priority Items to Primary List in Google Keep"
    )
    parser.add_argument("--config", "-c", default="", help="Input config file path")
    args = parser.parse_args()

    if args.config:
        CONFIG_FILE = args.config
        print(f"Using config file: {CONFIG_FILE}")
    else:
        if firstRun():
            print("First run")
            keep, config = getConfigFromUser()
            # Before loading the Google Keep object check the settings
            if checkSettings(keep, config):
                pass
            else:
                raise Exception("Settings are not valid")

            # Dump Keep Notes to disk for caching
            with open("keep_notes.json", "w") as outfile:
                json.dump(keep.dump(), outfile)
        else:
            pass

        config = loadSettings()
        checkSettings(config)
        # Restore notes from database or online
        try:  # Try to load notes from disk
            keep.resume(
                config["username"],
                config["master_token"],
                state=json.load(open("keep_notes.json")),
            )
        except FileNotFoundError:  # If the file is not found, load notes from online
            keep.resume(config["username"], config["master_token"])
    # end_time = timer()
    # print(f'Time to initialize: {(end_time - start_time)}s')

    # Start SysTray Icon if running on Windows, do nothing if on Linux
    if os.name == "nt":
        hover_text = "Move Low Priority Items to Primary List in Google Keep"
        sysTrayIcon = SysTrayIcon(
            "keep_notes_automation.ico", hover_text, default_menu_index=1
        )
        try:
            sysTrayIcon.start()
        except KeyboardInterrupt:
            sysTrayIcon.shutdown()
    else:
        pass
    programLoop(keep, config)


if __name__ == "__main__":
    main()
