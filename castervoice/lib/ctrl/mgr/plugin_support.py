"""
Caster Plugin Support Module

Provides helper functions for in-process voice management of Caster plugins,
including listing, hot-loading, hot-unloading, reloading, and installing.
"""

import os
from pathlib import Path

from castervoice.lib import printer
from castervoice.lib.ctrl.mgr.plugin_manager import get_plugin_manager
from castervoice.bin.plugin_cli import (
    get_user_plugins_dir,
    get_builtin_plugins_dir,
    load_settings_toml,
    set_plugin_enabled,
    fetch_registry,
    cmd_install,
    DEFAULT_REGISTRY_URL,
)


def get_configured_registry_source():
    """
    Resolves the registry source (local file or remote URL) with user settings priority.
    """
    # 1. Environment variable override
    if os.getenv("CASTER_PLUGIN_REGISTRY"):
        return os.getenv("CASTER_PLUGIN_REGISTRY")

    # 2. Check settings.toml / SETTINGS
    try:
        from castervoice.lib import settings
        cfg = settings.SETTINGS.get("plugins_config", {})
        local_p = cfg.get("local_registry_path")
        if local_p and os.path.exists(local_p):
            return local_p
        if cfg.get("registry_url"):
            return cfg.get("registry_url")
    except Exception:
        pass

    # 3. Automatic detection of local repo if present
    default_local = Path.home() / "Documents" / "repos" / "caster-plugins" / "manifest.json"
    if default_local.is_file():
        return str(default_local)

    # 4. Default remote repository URL
    return DEFAULT_REGISTRY_URL


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
                is_enabled = bool(plugins_cfg.get(name, False))
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
            lines.append("  {} {:<16} [{}]".format(sym, name, status))
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
        _print("@ [Plugin] Started: {}".format(name))
    else:
        _print("# [Plugin] Error: {}".format(msg))


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
        _print("@ [Plugin] Stopped: {}".format(name))
    else:
        _print("# [Plugin] Error: {}".format(msg))


def reload_plugins():
    """Reloads all plugins from configuration."""
    pm = get_plugin_manager()
    success, msg = pm.reload_all()
    _print("@ [Plugin] {}".format(msg))


def install_plugin(plugin_name):
    """Installs a plugin from the configured registry and starts it."""
    if not plugin_name:
        return
    name = str(plugin_name).strip()
    reg_source = get_configured_registry_source()

    class Args:
        registry = reg_source
        force = True

    setattr(Args, "name", name)
    setattr(Args, "source", None)

    try:
        cmd_install(Args)
        pm = get_plugin_manager()
        pm.load_plugin(name)
        _print("@ [Plugin] Installed and started: {}".format(name))
    except Exception as ex:
        _print("# [Plugin] Install error: {}".format(ex))


def get_plugin_choices():
    """Generates phonetic and literal choices for plugin voice commands."""
    choices = {
        "taskbar hud": "taskbar_hud",
        "taskbar": "taskbar_hud",
        "themed hud": "themed_hud",
        "themes hud": "themed_hud",
        "adce": "adce",
        "a d c e": "adce",
        "context engine": "adce",
    }
    try:
        u_dir = get_user_plugins_dir()
        if u_dir.is_dir():
            for p in u_dir.iterdir():
                if p.is_dir() and not p.name.startswith((".", "_")):
                    name = p.name
                    spoken = name.replace("_", " ")
                    choices[spoken] = name
                    choices[name] = name
    except Exception:
        pass
    return choices
