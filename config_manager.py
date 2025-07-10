import configparser
import os

# Get the absolute path to the directory where this script is located
_PROJ_PATH = os.path.dirname(os.path.abspath(__file__))
# Build the absolute path to the config.ini file
_CONFIG_PATH = os.path.join(_PROJ_PATH, 'config.ini')

# Create a single, pre-loaded config object for the whole app
config = configparser.ConfigParser()
config.read(_CONFIG_PATH)

def get_config(section, key):
    """
    Reads a value from the pre-loaded config object.
    """
    return config.get(section, key)