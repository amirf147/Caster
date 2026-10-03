"""
Caster Plugin Support Module

Provides helper functions for in-process voice management of Caster plugins,
settings persistence, registry fetching, and package installation.
"""

import io
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import tomlkit
from appdirs import user_data_dir

from castervoice.lib import printer
from castervoice.lib.ctrl.mgr.plugin_manager import get_plugin_manager

DEFAULT_REGISTRY_URL = (
    "https://raw.githubusercontent.com/amirf147/caster-plugins/master/manifest.json"
)


def get_user_dir():
    """Returns the authoritative Caster user directory across Windows, Linux, and macOS."""
    if os.getenv("CASTER_USER_DIR"):
        return Path(os.getenv("CASTER_USER_DIR"))
    try:
        from castervoice.lib import settings
        if getattr(settings, "_USER_DIR", None):
            return Path(settings._USER_DIR)
        u = settings.settings(["paths", "USER_DIR"])
        if u:
            return Path(u)
    except Exception:
        pass
    return Path(user_data_dir(appname="caster", appauthor=False))


def get_user_plugins_dir():
    """Returns the user plugins directory."""
    plugins_dir = get_user_dir() / "caster_user_content" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir


def get_builtin_plugins_dir():
    """Returns the in-tree Caster core plugins directory."""
    try:
        import castervoice
        base_dir = Path(castervoice.__file__).resolve().parent
    except Exception:
        base_dir = Path(__file__).resolve().parents[3]
    return base_dir / "plugins"


def get_settings_path():
    """Returns the path to settings.toml in user space."""
    return get_user_dir() / "settings" / "settings.toml"


def load_settings_toml():
    """Loads settings.toml as a tomlkit document."""
    path = get_settings_path()
    if path.is_file():
        with io.open(str(path), "rt", encoding="utf-8") as f:
            return tomlkit.loads(f.read())
    return tomlkit.document()


def save_settings_toml(doc):
    """Saves tomlkit document to settings.toml."""
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))


def set_plugin_enabled(plugin_name, enabled=True):
    """Updates the [plugins] table in settings.toml while preserving dictionary configs."""
    doc = load_settings_toml()
    if "plugins" not in doc:
        doc["plugins"] = tomlkit.table()

    current = doc["plugins"].get(plugin_name)
    if isinstance(current, dict):
        current["enabled"] = bool(enabled)
    else:
        doc["plugins"][plugin_name] = bool(enabled)
    save_settings_toml(doc)


def get_configured_registry_source():
    """Resolves the registry source (local file or remote URL) with user settings priority."""
    if os.getenv("CASTER_PLUGIN_REGISTRY"):
        return os.getenv("CASTER_PLUGIN_REGISTRY")
    try:
        from castervoice.lib import settings
        cfg = settings.SETTINGS.get("plugins_config", {})
        local_p = cfg.get("local_registry_path")
        if local_p and os.path.exists(local_p):
            return str(local_p)
        if cfg.get("registry_url"):
            return str(cfg.get("registry_url"))
    except Exception:
        pass
    try:
        doc = load_settings_toml()
        cfg = doc.get("plugins_config", {})
        local_p = cfg.get("local_registry_path")
        if local_p and os.path.exists(local_p):
            return str(local_p)
        if cfg.get("registry_url"):
            return str(cfg.get("registry_url"))
    except Exception:
        pass
    return DEFAULT_REGISTRY_URL


def fetch_registry(registry_url=None):
    """Fetches and parses the plugin manifest JSON from a local path or remote URL."""
    if not registry_url:
        registry_url = get_configured_registry_source()
    try:
        p = Path(registry_url)
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        if p.is_dir() and (p / "manifest.json").is_file():
            with open(p / "manifest.json", "r", encoding="utf-8") as f:
                return json.load(f)

        req = urllib.request.Request(
            registry_url, headers={"User-Agent": "Caster-Plugin-Manager/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception:
        return None


def install_plugin_package(plugin_name, registry_url=None, source_path=None, force=False):
    """
    Installs a plugin into user space and enables it in settings.toml.
    Returns (success: bool, message: str).
    """
    plugin_name = plugin_name.strip()
    target_dir = get_user_plugins_dir() / plugin_name

    if target_dir.exists() and not force:
        set_plugin_enabled(plugin_name, True)
        return True, f"Plugin '{plugin_name}' already installed; ensured enabled in settings.toml."

    # 1. Direct local source path override
    source_dir = None
    if source_path:
        cand = Path(source_path)
        if cand.exists():
            source_dir = cand

    # 2. Check registry
    registry = fetch_registry(registry_url)
    if not source_dir:
        if not registry or "plugins" not in registry or plugin_name not in registry["plugins"]:
            return False, f"Plugin '{plugin_name}' not found in registry."

        details = registry["plugins"][plugin_name]
        subpath = details.get("path", f"plugins/{plugin_name}")

        # Check if registry was a local file/dir
        reg_str = registry_url or get_configured_registry_source()
        reg_p = Path(reg_str)
        reg_base = reg_p.parent if reg_p.is_file() else reg_p
        if (reg_base / subpath).exists():
            source_dir = reg_base / subpath

    if source_dir and source_dir.exists():
        if source_dir.is_dir():
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_dir, target_dir)
    else:
        # Remote download handling
        download_url = None
        if registry and plugin_name in registry.get("plugins", {}):
            details = registry["plugins"][plugin_name]
            download_url = details.get("download_url")

        if download_url:
            try:
                import tempfile
                req = urllib.request.Request(
                    download_url, headers={"User-Agent": "Caster-Plugin-Manager/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp, tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(resp.read())
                    tmp_path = tmp.name

                if zipfile.is_zipfile(tmp_path):
                    with zipfile.ZipFile(tmp_path, "r") as zf:
                        zf.extractall(target_dir)
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(tmp_path, target_dir / "__init__.py")
                Path(tmp_path).unlink(missing_ok=True)
            except Exception as dl_err:
                return False, f"Failed to download plugin archive: {dl_err}"
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            init_file = target_dir / "__init__.py"
            if not init_file.exists():
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write(f'"""Plugin {plugin_name}"""\n')

    set_plugin_enabled(plugin_name, True)
    return True, f"Plugin '{plugin_name}' installed and enabled successfully."


def _print(msg):
    print(msg)
    printer.out(msg)


def list_plugins():
    """Prints a structured summary of installed and running plugins to HUD/log."""
    pm = get_plugin_manager()
    doc = load_settings_toml()
    plugins_cfg = doc.get("plugins", {})

    user_dir = get_user_plugins_dir()
    installed = []

    if user_dir.is_dir():
        for entry in sorted(user_dir.iterdir()):
            if entry.name.startswith((".", "_")):
                continue
            if entry.is_dir() or entry.suffix == ".py":
                name = entry.stem if entry.is_file() else entry.name
                val = plugins_cfg.get(name, False)
                is_enabled = bool(val.get("enabled", False)) if isinstance(val, dict) else bool(val)
                is_running = pm.get_plugin(name) is not None and pm.get_plugin(name).is_running
                status = "running" if is_running else ("enabled" if is_enabled else "disabled")
                installed.append((name, status))

    reg_source = get_configured_registry_source()
    reg = fetch_registry(reg_source)
    available = []
    if reg and "plugins" in reg:
        inst_names = {x[0] for x in installed}
        for name in sorted(reg["plugins"].keys()):
            if name not in inst_names:
                available.append(name)

    lines = ["@ Caster Plugins:"]
    if installed:
        lines.append("# Installed:")
        for name, status in installed:
            sym = "+" if status == "running" else ("o" if status == "enabled" else "-")
            lines.append(f"  {sym} {name:<16} [{status}]")
    else:
        lines.append("# Installed: (None)")

    if available:
        lines.append("# Available in Registry:")
        lines.append("  " + ", ".join(available))

    _print("\n".join(lines))


def load_plugin(plugin_name):
    """Loads and starts a plugin dynamically on the fly."""
    if not plugin_name:
        return
    name = str(plugin_name).strip()
    pm = get_plugin_manager()
    success, msg = pm.load_plugin(name)
    if success:
        try:
            set_plugin_enabled(name, True)
        except Exception:
            pass
        _print(f"@ [Plugin] Started: {name}")
    else:
        _print(f"# [Plugin] Error: {msg}")


def unload_plugin(plugin_name):
    """Stops and unloads a plugin dynamically on the fly."""
    if not plugin_name:
        return
    name = str(plugin_name).strip()
    pm = get_plugin_manager()
    success, msg = pm.unload_plugin(name)
    if success:
        try:
            set_plugin_enabled(name, False)
        except Exception:
            pass
        _print(f"@ [Plugin] Stopped: {name}")
    else:
        _print(f"# [Plugin] Error: {msg}")


def reload_plugins():
    """Reloads all plugins from configuration."""
    pm = get_plugin_manager()
    success, msg = pm.reload_all()
    _print(f"@ [Plugin] {msg}")


def install_plugin(plugin_name):
    """Installs a plugin from the configured registry and starts it."""
    if not plugin_name:
        return
    name = str(plugin_name).strip()
    reg_source = get_configured_registry_source()

    success, msg = install_plugin_package(name, registry_url=reg_source, force=True)
    if success:
        pm = get_plugin_manager()
        pm.load_plugin(name)
        _print(f"@ [Plugin] Installed and started: {name}")
    else:
        _print(f"# [Plugin] Install error: {msg}")


def get_plugin_choices():
    """
    Generates phonetic and literal choices for plugin voice commands dynamically.
    Discovers available plugins and aliases from active plugins, plugin directories,
    and user configuration without hardcoded names.
    """
    choices = {}

    def _add_choice(raw_name, target):
        if not raw_name or not target:
            return
        clean_spoken = str(raw_name).strip().lower()
        if clean_spoken:
            choices[clean_spoken] = str(target)

    # 1. Inspect loaded plugins in PluginManager
    try:
        pm = get_plugin_manager()
        for p in pm.get_loaded_plugins():
            p_name = getattr(p, "name", None)
            if p_name:
                _add_choice(p_name, p_name)
                _add_choice(p_name.replace("_", " "), p_name)
                _add_choice(p_name.replace("-", " "), p_name)
                for alias in getattr(p, "aliases", []):
                    _add_choice(alias, p_name)
    except Exception:
        pass

    # 2. Inspect built-in and user plugin directories
    search_dirs = []
    try:
        b_dir = get_builtin_plugins_dir()
        if b_dir and b_dir.is_dir():
            search_dirs.append(b_dir)
    except Exception:
        pass
    try:
        u_dir = get_user_plugins_dir()
        if u_dir and u_dir.is_dir():
            search_dirs.append(u_dir)
    except Exception:
        pass

    for p_dir in search_dirs:
        try:
            for entry in p_dir.iterdir():
                if entry.name.startswith((".", "_")):
                    continue
                if entry.is_dir() or entry.suffix == ".py":
                    name = entry.stem if entry.is_file() else entry.name
                    _add_choice(name, name)
                    _add_choice(name.replace("_", " "), name)
                    _add_choice(name.replace("-", " "), name)
        except Exception:
            pass

    # 3. Inspect settings.toml for configured plugins and custom user aliases
    try:
        doc = load_settings_toml()
        plugins_cfg = doc.get("plugins", {})
        for name, val in plugins_cfg.items():
            if name.startswith((".", "_")):
                continue
            _add_choice(name, name)
            _add_choice(name.replace("_", " "), name)
            _add_choice(name.replace("-", " "), name)
            if isinstance(val, dict):
                aliases = val.get("aliases", [])
                if isinstance(aliases, (list, tuple)):
                    for alias in aliases:
                        _add_choice(alias, name)
    except Exception:
        pass

    # 4. Fallback to prevent Dragonfly Choice initialization failure if no plugins exist
    if not choices:
        choices["plugin"] = "plugin"

    return choices
