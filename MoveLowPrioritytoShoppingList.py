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
import json

# from time import perf_counter as timer
from time import sleep

if os.name == "nt":
    from infi.systray import SysTrayIcon
else:
    pass

# Define constants at the top of your file
KEYRING_NAME: str = "Google Keep Master Token"
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


def loadConfig(_config_file: str) -> dict:
    """
    Load settings from config.json

    Returns:
        dict: Dictionary of settings
    """
    try:
        with open(_config_file, "r") as openfile:
            # Reading the settings from json file
            config = json.load(openfile)
            # The Google Master Token is stored on the system keyring and extracted from there
            try:
                config["master_token"] = keyring.get_password(
                    KEYRING_NAME, config["username"]
                )
            except Exception as e:
                raise Exception(
                    f"""Error loading master token from keyring.
                    You might not have the necessary permissions: {e}"""
                )
            return config
    except FileNotFoundError:
        raise FileNotFoundError(f"{_config_file} not found.")
    except Exception as e:
        raise Exception(f"An unknown error occurred: {e}")


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


class KeepListObj:

    def __init__(
        self, keep_notes: gkeepapi.Keep, primary_list: str, secondary_list: str
    ) -> None:
        self.primary_list: str = primary_list
        self.secondary_list: str = secondary_list
        self.keep_notes: object = keep_notes

    def checkListNames(self) -> bool:
        """
        Check that the primary and low priority list names are not empty
        or non-existent in the keep object.

        Raises:
            ValueError: If any of the lists are empty or list names are invalid.
            LookupError: If a list name does not exist in the keep object.

        Returns:
            True if all checks pass.
        """
        if not self.primary_list:
            raise ValueError("Primary list name is empty")
        if not self.secondary_list:
            raise ValueError("Low priority list is empty")
        for list_name in [
            self.secondary_list,
            self.primary_list,
        ]:  # Check if title exists using keep.find()
            if not self.keep_notes.find(
                query=list_name
            ):  # If the list name is not found in the keep object
                raise LookupError(f"List - {list_name} does not exist.")
        return True

    def moveItemsToPrimaryList(self, items_to_move: list) -> None:
        """
        Move ticked items from low priority list to primary list.

        Args:
            items_to_move (list): List of items to move

        Returns:
            None
        """
        # Find the note matching primary_list in the keep notes object
        for note in self.keep_notes.find(query=self.primary_list):
            for item in items_to_move:
                # Add the item to the top of the primary list unticked
                note.add(
                    item.text,
                    False,
                    gkeepapi.node.NewListItemPlacementValue.Top,
                )
        return None

    def deleteTickedItems(self, ticked_list_del: str) -> list:
        """
        Delete ticked items from _ticked_list_del.

        Args:
            _ticked_list_del (str): Name of list to delete ticked items from

        Returns:
            List of items deleted
        """
        _items_deleted = []
        for note in self.keep_notes.find(query=ticked_list_del):
            # Check through all the ticked items in the given note
            for item in note:
                if item.checked:
                    _items_deleted.append(item)
                    item.delete()
        return _items_deleted

    def checkIfLowPriorityTicked(self) -> list:
        """
        Check the low priority list for items that are ticked.
        If ticked, add them to a list to be moved to the primary list.
        Then delete the ticked items from the low priority list.

        Returns:
            list: List of items to move
        """
        _items_to_move = []
        for note in self.keep_notes.find(query=self.secondary_list):
            if self.secondary_list in note.title:
                for item in note.checked:
                    _items_to_move.append(item)
                    # delete item from note
                    item.delete()
        return _items_to_move


def getConfigFromUser() -> tuple[gkeepapi.Keep, dict]:
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
    _username = input("Google Keep Username: ")
    checkUsername(_username)
    _master_token = maskpass.askpass(
        "Google Keep Master Token (Use the included DockerFile to get one): "
    )
    checkToken(_master_token)
    # Load all Keep Notes
    try:
        _keep = gkeepapi.Keep()
        _keep.authenticate(_username, _master_token)
    except Exception as e:
        raise Exception(f"Username or master token is invalid: {e}")
    # If the login above is successful, write the master token to system keyring
    try:
        keyring.set_password(KEYRING_NAME, _username, _master_token)
    except Exception as e:
        raise Exception(
            f"""Error saving master token to keyring.
            You might not have the necessary permissions: {e}"""
        )
    num_sets = int(input("Number of Sets of Lists (1 Set contains two Lists ): "))
    checkNumSets(num_sets)

    _primary_lists = []
    _secondary_lists = []
    _list_sets_obj = []
    for i in range(int(num_sets)):
        _primary_list = input(f"Name of Primary List {i+1}: ")
        _secondary_list = input(f"Name of Low Priority List {i+1}: ")
        _x: KeepListObj = KeepListObj(_keep, _primary_list, _secondary_list)

        _list_sets_obj.append(_x)
        _primary_lists.append(_primary_list)
        _secondary_lists.append(_secondary_list)
        _x.checkListNames()
    # Serialize KeepListObj objects to JSON
    _list_sets_serialized = json.dumps([vars(_y) for _y in _list_sets_obj])

    # Master token is stored on the system keyring so deliberately empty
    _config = {
        "first_run_flag": "True",
        "username": _username,
        "master_token": "",
        "num_sets": num_sets,
        "list_sets": _list_sets_serialized,
    }
    _config_serialized = json.dumps(_config, indent=4)

    # Writing config.json only after all checks have passed
    with open(CONFIG_FILE, "w") as outfile:
        outfile.write(_config_serialized)
    _config["master_token"] = _master_token

    return (_keep, _config)


def checkConfig(config: dict) -> bool:
    """
    Check that the settings file is not broken.

    Args:
        config (dict): Dictionary of settings

    Returns:
        bool: 'True' if settings are valid, 'False' if not

    Raises:
        ValueError: If the config file is empty.
        ValueError: If the first run flag is not set.
        ValueError: If the username is invalid.
        ValueError: If the number of sets is less than 1.
        ValueError: If the master token is invalid.
        ValueError: If the list names are invalid.
        FileNotFoundError: If the config file is not found.
        Exception: If an unknown error occurs.
    """
    if not config:
        raise ValueError(f"{CONFIG_FILE} is empty")
    if not config["first_run_flag"] == "True":  # Check that the first run flag is set
        raise ValueError(f"{CONFIG_FILE} maybe corrupted")
    checkToken(config["master_token"])
    checkUsername(config["username"])
    checkNumSets(config["num_sets"])
    # Deserialize KeepListObj objects from config
    _keep_list = [
        KeepListObj(**list_set) for list_set in json.loads(config["list_sets"])
    ]
    for _list_objs in _keep_list:
        _list_objs.checkListNames()

    print(f'Loaded settings. Username: {config["username"]}')

    return True


def programLoop(keep: gkeepapi.Keep, config: dict) -> None:
    """
    Synchronize the changes to the Google Keep server and continuously move
    low priority items to the primary list using deserialized KeepListObj objects,
    which are extracted from the config (dict).

    Args:
        keep (object): The object representing the Google Keep instance.
        config (dict): The dictionary containing the configuration settings.

    Returns:
        None

    Raises:
        KeyboardInterrupt: If the user interrupts the program.
        Exception: If an unknown error occurs.
    """
    # Deserialize KeepListObj objects from config
    _keep_list = [
        KeepListObj(**list_set) for list_set in json.loads(config["list_sets"])
    ]

    try:
        while True:
            # Sync the changes to the Google Keep server
            keep.sync()

            for _keep_obj in _keep_list:
                _items_to_move = _keep_obj.checkIfLowPriorityTicked()

                # if no items to move, return to check for low priority items
                if _items_to_move:
                    _keep_obj.moveItemsToPrimaryList(_items_to_move)
                    print(
                        f"Moved {len(_items_to_move)} items to {_keep_obj.primary_list}"
                    )
                    _items_to_move.clear()

                    # Dump Keep Notes to disk for caching
                    with open(KEEP_NOTES_PATH, "w") as outfile:
                        json.dump(keep.dump(), outfile)
                else:
                    pass

            # Rate restriction to prevent API ban from Google
            sleep(1)

    except KeyboardInterrupt:
        print("Program interrupted by user.")
        return 0
    except Exception as e:
        print(f"An unknown error occurred: {e}")
        return -2


def main():
    # Check for input config files
    parser = argparse.ArgumentParser(
        description="Move Low Priority Items to Primary List in Google Keep"
    )
    parser.add_argument("--config", "-c", default="", help="Input config file path")
    args = parser.parse_args()

    # If supplied an external config file use that instead of anything else
    if args.config:
        config_file = args.config
        print(f"Using config file: {config_file}")
        config = loadConfig(config_file)
    else:
        # If no external config file specified, check if first run
        if firstRun():
            print("First run")
            keep, config = getConfigFromUser()
            # Before loading the Google Keep object check the settings
            if checkConfig(config):
                pass
            else:
                raise Exception("Settings are not valid")

            # Dump Keep Notes to disk for caching
            with open(KEEP_NOTES_PATH, "w") as outfile:
                json.dump(keep.dump(), outfile)
        else:
            # Load default config.json, if custom one not specified, and its not the first run
            config = loadConfig(CONFIG_FILE)
    # Load all Keep Notes
    try:
        keep = gkeepapi.Keep()
        keep.authenticate(config["username"], config["master_token"])
    except Exception as e:
        raise Exception(f"Username or master token is invalid: {e}")
    checkConfig(config)
    # Restore notes from database or online
    try:  # Try to load notes from disk
        keep.authenticate(
            config["username"],
            config["master_token"],
            state=json.load(open(KEEP_NOTES_PATH)),
        )
    except FileNotFoundError:  # If the file is not found, load notes from online
        keep.authenticate(config["username"], config["master_token"])
    except Exception as e:
        raise Exception(f"Error restoring notes: {e}")

    # # Start SysTray Icon if running on Windows, do nothing if on Linux
    # if os.name == "nt":
    #     hover_text = "Move Low Priority Items to Primary List in Google Keep"
    #     sysTrayIcon = SysTrayIcon(
    #         "keep_notes_automation.ico", hover_text, default_menu_index=1
    #     )
    #     try:
    #         sysTrayIcon.start()
    #     except KeyboardInterrupt:
    #         sysTrayIcon.shutdown()
    #         raise KeyboardInterrupt("SysTrayIcon shutdown.")
    #     except Exception as e:
    #         raise Exception(f"Error: {e}")
    # else:
    #     pass

    # Run the program loop and return any exceptions
    return programLoop(keep, config)


if __name__ == "__main__":
    main()
