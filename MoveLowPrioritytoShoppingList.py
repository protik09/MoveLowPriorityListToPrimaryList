"""
Script to move low priority shopping list items to primary shopping list, if they're ticked.

Author:
    Protik Banerji <protik09@gmail.com>
"""
import os
import gkeepapi
import json

from time import perf_counter as timer, sleep


def first_run() -> bool:
    """
    Check if this is the first run of the program.

    Args:
        None

    Returns: 
        bool: 'True' if first run, 'False' if not.
    """
    return not os.path.isfile('config.json')  # The 'not' is there to flip the return value of isfile


def load_settings() -> dict:
    """
    Load settings from config.json

    Returns: 
        dict: Dictionary of settings
    """
    with open('config.json', 'r') as openfile:
        # Reading from json file
        settings = json.load(openfile)
        return settings


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
                note.add(item.text, False, gkeepapi.node.NewListItemPlacementValue.Top)
    return None


def main():
    # start_time = timer()
    keep = gkeepapi.Keep()
    if first_run():
        print("First run")
        username = input("Google Keep Username: ")
        master_token = input(
            "Google Keep Master Token (Use the included DockerFile to get one): ")
        primary_list = input('Name of Primary List: ')
        low_priority_list = input('Name of Low Priority List: ')
        config = {
            "first_run_flag": "True",
            "username": username,
            "master_token": master_token,
            "primary_list": primary_list,
            "low_priority_list": low_priority_list
        }
        json_object = json.dumps(config, indent=4)

        # Writing config.json
        with open("config.json", "w") as outfile:
            outfile.write(json_object)

        # Load all Keep Notes
        keep.resume(username, master_token)

        # Dump Keep Notes to disk for caching
        with open("keep_notes.json", "w") as outfile:
            json.dump(keep.dump(), outfile)

    else:
        config = load_settings()
        print(f'Loaded settings. Username: {config["username"]}')
        assert config['first_run_flag'] == "True"
        # Restore notes from database or online
        keep.resume(config['username'], config['master_token'],
                    state=json.load(open("keep_notes.json")))

    # end_time = timer()
    # print(f'Time to initialize: {(end_time - start_time)}s')
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
            move_items_to_primary_list(keep, config['primary_list'], items_to_move)
            print(f'Moved {len(items_to_move)} items to {config["primary_list"]}')
            items_to_move = []
        sleep(0.5)


if __name__ == '__main__':
    main()
