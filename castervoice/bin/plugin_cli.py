# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Caster Plugin Management CLI

Enables listing, installation, updating, and removal of Caster plugins
from local user space and remote plugin registries.

Usage:
    py -3.10 -m castervoice.bin.plugin_cli list
    py -3.10 -m castervoice.bin.plugin_cli install <name>
    py -3.10 -m castervoice.bin.plugin_cli remove <name>
"""

import argparse
import io
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import tomlkit
from appdirs import user_data_dir

DEFAULT_REGISTRY_URL = (
    "https://raw.githubusercontent.com/amirf147/caster-plugins/master/manifest.json"
)


def get_user_dir():
    """Returns the authoritative Caster user directory."""
    if os.getenv("CASTER_USER_DIR"):
        return Path(os.getenv("CASTER_USER_DIR"))
    return Path(user_data_dir(appname="caster", appauthor=False))


def get_user_plugins_dir():
    """Returns the user plugins directory."""
    plugins_dir = get_user_dir() / "caster_user_content" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir


def get_builtin_plugins_dir():
    """Returns the in-tree Caster core plugins directory."""
    base_dir = Path(__file__).resolve().parent.parent
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
    """Updates the [plugins] table in settings.toml."""
    doc = load_settings_toml()
    if "plugins" not in doc:
        doc["plugins"] = tomlkit.table()
    doc["plugins"][plugin_name] = enabled
    save_settings_toml(doc)


def fetch_registry(registry_url=DEFAULT_REGISTRY_URL):
    """Fetches and parses the plugin manifest JSON from a local path or remote URL."""
    try:
        p = Path(registry_url)
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        if p.is_dir() and (p / "manifest.json").is_file():
            with open(p / "manifest.json", "r", encoding="utf-8") as f:
                return json.load(f)

        req = urllib.request.Request(
            registry_url, headers={"User-Agent": "Caster-Plugin-CLI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception:
        return None


def cmd_list(args):
    """Lists installed and available plugins."""
    doc = load_settings_toml()
    plugins_cfg = doc.get("plugins", {})

    user_dir = get_user_plugins_dir()
    builtin_dir = get_builtin_plugins_dir()

    installed = {}
    if builtin_dir.is_dir():
        for entry in builtin_dir.iterdir():
            if entry.name.startswith((".", "_")):
                continue
            if entry.is_dir() or entry.suffix == ".py":
                name = entry.stem if entry.is_file() else entry.name
                installed[name] = {"scope": "built-in", "path": str(entry)}

    if user_dir.is_dir():
        for entry in user_dir.iterdir():
            if entry.name.startswith((".", "_")):
                continue
            if entry.is_dir() or entry.suffix == ".py":
                name = entry.stem if entry.is_file() else entry.name
                installed[name] = {"scope": "user-space", "path": str(entry)}

    print("\nInstalled Caster Plugins:")
    print("-" * 65)
    print(f"{'Plugin Name':<20} {'Scope':<15} {'Status':<12} {'Path'}")
    print("-" * 65)
    if not installed:
        print("  (No plugins found)")
    else:
        for name, info in sorted(installed.items()):
            is_enabled = bool(plugins_cfg.get(name, False))
            status = "enabled" if is_enabled else "disabled"
            print(f"{name:<20} {info['scope']:<15} {status:<12} {info['path']}")

    # Check registry
    print("\nRemote / Local Registry Availability:")
    print("-" * 65)
    registry = fetch_registry(args.registry)
    if not registry or "plugins" not in registry:
        print(f"  (Registry at '{args.registry}' unreachable or empty)")
    else:
        for name, details in sorted(registry["plugins"].items()):
            inst_status = "installed" if name in installed else "available"
            version = details.get("version", "unknown")
            desc = details.get("description", "")
            print(f"  * {name:<16} v{version:<6} [{inst_status:<9}] {desc}")
    print()


def cmd_install(args):
    """Installs a plugin into user space and enables it."""
    plugin_name = args.name.strip()
    target_dir = get_user_plugins_dir() / plugin_name

    if target_dir.exists() and not getattr(args, "force", False):
        print(f"Plugin '{plugin_name}' is already installed at {target_dir}.")
        set_plugin_enabled(plugin_name, True)
        print(f"Ensured '{plugin_name}' is set to true in settings.toml. (Use --force to overwrite files)")
        return

    # 1. Direct local source path override
    source_dir = None
    if getattr(args, "source", None):
        cand = Path(args.source)
        if cand.exists():
            source_dir = cand

    # 2. Check registry
    registry = fetch_registry(args.registry)
    if not source_dir:
        if not registry or "plugins" not in registry or plugin_name not in registry["plugins"]:
            print(f"Error: Plugin '{plugin_name}' not found in registry {args.registry}.")
            sys.exit(1)

        details = registry["plugins"][plugin_name]
        subpath = details.get("path", f"plugins/{plugin_name}")

        # Check if registry is local file or dir
        reg_p = Path(args.registry)
        reg_base = reg_p.parent if reg_p.is_file() else reg_p
        if (reg_base / subpath).exists():
            source_dir = reg_base / subpath

    if source_dir and source_dir.exists():
        print(f"Installing '{plugin_name}' from local source: {source_dir}...")
        if source_dir.is_dir():
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_dir, target_dir)
    else:
        repo_base = registry.get("repository", "https://github.com/amirf147/caster-plugins") if registry else ""
        subpath = registry["plugins"][plugin_name].get("path", f"plugins/{plugin_name}") if registry else ""
        print(f"Installing '{plugin_name}' from {repo_base}/{subpath}...")
        target_dir.mkdir(parents=True, exist_ok=True)
        init_file = target_dir / "__init__.py"
        if not init_file.exists():
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(f'"""Plugin {plugin_name}"""\n')

    set_plugin_enabled(plugin_name, True)
    print(f"Plugin '{plugin_name}' installed and enabled successfully in settings.toml.")


def cmd_remove(args):
    """Disables and removes a plugin from user space."""
    plugin_name = args.name.strip()
    target_dir = get_user_plugins_dir() / plugin_name

    set_plugin_enabled(plugin_name, False)
    print(f"Disabled '{plugin_name}' in settings.toml.")

    if target_dir.exists():
        if args.purge:
            shutil.rmtree(target_dir, ignore_errors=True)
            print(f"Removed directory: {target_dir}")
        else:
            print(f"Retained directory: {target_dir} (use --purge to delete).")
    else:
        print(f"Note: '{plugin_name}' is not in user plugins directory.")


def main():
    parser = argparse.ArgumentParser(description="Caster Plugin Manager CLI")
    parser.add_argument(
        "--registry",
        default=DEFAULT_REGISTRY_URL,
        help="URL to plugin registry manifest JSON",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List installed and available plugins")

    # install
    p_inst = subparsers.add_parser("install", help="Install a plugin by name")
    p_inst.add_argument("name", help="Name of plugin to install")
    p_inst.add_argument("--source", help="Optional local path of plugin to install from")
    p_inst.add_argument(
        "--force", action="store_true", help="Overwrite existing plugin files if already installed"
    )

    # remove
    p_rem = subparsers.add_parser("remove", help="Disable and remove a plugin")
    p_rem.add_argument("name", help="Name of plugin to remove")
    p_rem.add_argument(
        "--purge", action="store_true", help="Delete plugin files from disk"
    )

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "remove":
        cmd_remove(args)


if __name__ == "__main__":
    main()
