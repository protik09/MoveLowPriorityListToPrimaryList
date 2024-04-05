# Google Keep Shopping List Organizer

This Python script automates the management of shopping lists in Google Keep by moving ticked items from low-priority lists to a primary shopping list.

## Features

- **Automated List Management:** Automatically moves ticked items from specified low-priority lists to a primary list in Google Keep.
- **First Run Setup:** Guides new users through initial setup, including Google Keep authentication and list configuration.
- **Configurable List Sets:** Supports multiple sets of primary and low-priority lists.
- **Local Caching:** Caches Google Keep notes locally to reduce API calls and speed up operations.
- **Cross-Platform Support:** Works on both Windows and Linux, with additional system tray support on Windows.

## Installation Instructions

1. Ensure you have Python 3.x installed on your system.
2. Clone this repository or download the script to your local machine.
3. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Obtain a Google Keep Master Token. Instructions for obtaining this token can be found in the included DockerFile.

## Usage Examples

To start the script, navigate to the directory containing the script and run:

```bash
python MoveLowPrioritytoShoppingList.py
```

On the first run, the script will prompt you for your Google Keep username and master token, as well as the names of your primary and low-priority shopping lists.

## Configuration Options

The script generates a `config.json` file during the first run, which stores:

- Google Keep username
- Number of list sets
- Names of primary and low-priority lists

You can edit this file directly to change your configuration settings.

## Contribution Guidelines

Contributions are welcome! If you'd like to contribute, please:

1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Commit your changes.
4. Push to the branch.
5. Submit a pull request.

## Testing Instructions

Currently, there are no automated tests for this script. Manual testing can be done by running the script and verifying that items are correctly moved between lists in Google Keep.

## Acknowledgements/Credits

- **Author:** Protik Banerji <protik09@gmail.com>
- Thanks to the developers of `gkeepapi`, `keyring`, `maskpass`, `simplejson`, and `infi.systray` for their excellent libraries that made this project possible.

## Usage

The script will run in the background, checking for changes to the specified shopping lists every 0.5 seconds.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
