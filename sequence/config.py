# This file is responsible for loading the configuration file and making it available as a dictionary globally across SeQUeNCe
# simply by importing it from this file.
# It serves two purposes:
# 1. It allows the configuration file to be loaded once and used throughout the codebase
# 2. It allows the dynamic loading of plugins by specifying the path to the plugins in the configuration file.

import os
import json
import sys

# Defining the global CONFIG dictionary
CONFIG = {}
# Reading the configuration file path from environment variable "config_path"
USER_CONFIG_PATH = os.getenv("config_path", None)

# If the environment variable is set and the file exists, load the configuration dictionary from the file
if USER_CONFIG_PATH and os.path.exists(USER_CONFIG_PATH):
    with open(USER_CONFIG_PATH, 'r') as f:
        CONFIG = json.load(f)

# Check to see if the configuration file has a "plugin_path" field. If it does, add the path to sys.path. 
# This facilitates importing the plugins from anywhere on the host machine.
if CONFIG.get("plugin_path", None):
    sys.path.append(CONFIG["plugin_path"])