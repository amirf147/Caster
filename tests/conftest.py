import sys
from pathlib import Path
from dragonfly import get_engine
from appdirs import user_data_dir

get_engine("text")

# Ensure Caster user directory and plugins directory are in sys.path for direct bare-module imports
user_dir = user_data_dir(appname="caster", appauthor=False)
if user_dir not in sys.path and Path(user_dir).exists():
    sys.path.insert(0, user_dir)
user_plugins = str(Path(user_dir) / "caster_user_content" / "plugins")
if user_plugins not in sys.path and Path(user_plugins).exists():
    sys.path.insert(0, user_plugins)
