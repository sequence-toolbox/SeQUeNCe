import os
import json

CONFIG = {}
USER_CONFIG_PATH = os.getenv("config_path", None)

if USER_CONFIG_PATH and os.path.exists(USER_CONFIG_PATH):
    with open(USER_CONFIG_PATH, 'r') as f:
        CONFIG = json.load(f)

if CONFIG.get("plugin_path", None):
    import sys
    sys.path.append(CONFIG["plugin_path"])