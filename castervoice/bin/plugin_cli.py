"""
Caster Plugin Management CLI

Enables listing, installation, updating, enabling, disabling, and removal
of Caster plugins from user space and remote plugin registries.

Usage:
    py -3.10 -m castervoice.bin.plugin_cli list
    py -3.10 -m castervoice.bin.plugin_cli install <name>
    py -3.10 -m castervoice.bin.plugin_cli update [name|all]
    py -3.10 -m castervoice.bin.plugin_cli enable <name>
    py -3.10 -m castervoice.bin.plugin_cli disable <name>
    py -3.10 -m castervoice.bin.plugin_cli remove <name> [--purge]
    py -3.10 -m castervoice.bin.plugin_cli info <name>
"""

import argparse
import platform
import shutil
import sys
from pathlib import Path

from castervoice.lib.ctrl.mgr.plugin_support import (
    DEFAULT_REGISTRY_URL,
    fetch_registry,
    get_builtin_plugins_dir,
    get_configured_registry_source,
    get_user_plugins_dir,
    install_plugin_package,
    load_settings_toml,
    set_plugin_enabled,
)


def _get_current_platform():
    """Returns normalized platform identifier: 'windows', 'linux', or 'darwin'."""
    return platform.system().lower()


def cmd_list(args):
    """Lists installed and available plugins across local space and remote registry."""
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
    print("-" * 75)
    print(f"{'Plugin Name':<22} {'Scope':<15} {'Status':<12} {'Path'}")
    print("-" * 75)
    if not installed:
        print("  (No plugins found)")
    else:
        for name, info in sorted(installed.items()):
            val = plugins_cfg.get(name, False)
            is_enabled = bool(val.get("enabled", False)) if isinstance(val, dict) else bool(val)
            status = "enabled" if is_enabled else "disabled"
            print(f"{name:<22} {info['scope']:<15} {status:<12} {info['path']}")

    # Registry check
    print("\nAvailable in Plugin Registry:")
    print("-" * 75)
    registry = fetch_registry(args.registry)
    current_os = _get_current_platform()
    if not registry or "plugins" not in registry:
        print(f"  (Registry at '{args.registry}' unreachable or empty)")
    else:
        for name, details in sorted(registry["plugins"].items()):
            inst_status = "installed" if name in installed else "available"
            version = details.get("version", "unknown")
            desc = details.get("description", "")
            supported_platforms = details.get("platforms", ["any"])
            if isinstance(supported_platforms, str):
                supported_platforms = [supported_platforms]

            plat_note = ""
            if "any" not in supported_platforms and current_os not in supported_platforms:
                plat_note = f" (requires {','.join(supported_platforms)})"

            print(f"  * {name:<18} v{version:<6} [{inst_status:<9}] {desc}{plat_note}")
    print()


def cmd_install(args):
    """Installs a plugin into user space and enables it."""
    plugin_name = args.name.strip()
    registry_source = args.registry
    source_path = getattr(args, "source", None)
    force = getattr(args, "force", False)

    # Optional platform warning check
    registry = fetch_registry(registry_source)
    if registry and "plugins" in registry and plugin_name in registry["plugins"]:
        details = registry["plugins"][plugin_name]
        platforms = details.get("platforms", ["any"])
        if isinstance(platforms, str):
            platforms = [platforms]
        current_os = _get_current_platform()
        if "any" not in platforms and current_os not in platforms:
            print(f"Warning: Plugin '{plugin_name}' specifies support for {platforms}, but current platform is {current_os}.")

    success, msg = install_plugin_package(
        plugin_name,
        registry_url=registry_source,
        source_path=source_path,
        force=force,
    )
    if success:
        print(f"Success: {msg}")
    else:
        print(f"Error: {msg}")
        sys.exit(1)


def cmd_update(args):
    """Updates installed plugins from local repository or remote registry while preserving settings."""
    target_name = getattr(args, "name", None)
    registry = fetch_registry(args.registry)
    if not registry or "plugins" not in registry:
        print(f"Error: Registry at '{args.registry}' unreachable or empty.")
        sys.exit(1)

    doc = load_settings_toml()
    plugins_cfg = doc.get("plugins", {})

    plugins_to_update = []
    if target_name and target_name.lower() not in ("all", "--all"):
        if target_name not in registry["plugins"]:
            print(f"Error: Plugin '{target_name}' not found in registry {args.registry}.")
            sys.exit(1)
        plugins_to_update.append(target_name)
    else:
        user_dir = get_user_plugins_dir()
        for p_name in registry["plugins"]:
            if (user_dir / p_name).exists() or (user_dir / f"{p_name}.py").exists():
                plugins_to_update.append(p_name)
        if not plugins_to_update:
            print("No user-space plugins currently installed to update.")
            return

    for plugin_name in plugins_to_update:
        val = plugins_cfg.get(plugin_name, False)
        was_enabled = bool(val.get("enabled", False)) if isinstance(val, dict) else bool(val)
        print(f"\n--- Updating '{plugin_name}' (currently {'enabled' if was_enabled else 'disabled'}) ---")

        success, msg = install_plugin_package(
            plugin_name,
            registry_url=args.registry,
            source_path=getattr(args, "source", None),
            force=True,
        )
        if success:
            print(f"Success: {msg}")
            if not was_enabled:
                set_plugin_enabled(plugin_name, False)
                print(f"Preserved '{plugin_name} = false' in settings.toml.")
        else:
            print(f"Error updating '{plugin_name}': {msg}")


def cmd_enable(args):
    """Enables an installed plugin in settings.toml."""
    plugin_name = args.name.strip()
    set_plugin_enabled(plugin_name, True)
    print(f"Enabled plugin '{plugin_name}' in settings.toml.")


def cmd_disable(args):
    """Disables an installed plugin in settings.toml."""
    plugin_name = args.name.strip()
    set_plugin_enabled(plugin_name, False)
    print(f"Disabled plugin '{plugin_name}' in settings.toml.")


def cmd_remove(args):
    """Disables and removes a plugin from user space."""
    plugin_name = args.name.strip()
    target_dir = get_user_plugins_dir() / plugin_name
    target_file = get_user_plugins_dir() / f"{plugin_name}.py"

    set_plugin_enabled(plugin_name, False)
    print(f"Disabled '{plugin_name}' in settings.toml.")

    found = False
    if target_dir.exists():
        found = True
        if args.purge:
            shutil.rmtree(target_dir, ignore_errors=True)
            print(f"Removed directory: {target_dir}")
        else:
            print(f"Retained directory: {target_dir} (use --purge to delete).")

    if target_file.exists():
        found = True
        if args.purge:
            target_file.unlink(missing_ok=True)
            print(f"Removed file: {target_file}")
        else:
            print(f"Retained file: {target_file} (use --purge to delete).")

    if not found:
        print(f"Note: '{plugin_name}' is not in user plugins directory.")


def cmd_info(args):
    """Displays detailed metadata and configuration for a plugin."""
    plugin_name = args.name.strip()
    doc = load_settings_toml()
    plugins_cfg = doc.get("plugins", {})
    user_dir = get_user_plugins_dir()
    builtin_dir = get_builtin_plugins_dir()

    is_builtin = (builtin_dir / plugin_name).exists() or (builtin_dir / f"{plugin_name}.py").exists()
    is_user = (user_dir / plugin_name).exists() or (user_dir / f"{plugin_name}.py").exists()

    val = plugins_cfg.get(plugin_name, None)
    if val is None:
        status = "not configured (disabled by default)"
    elif isinstance(val, dict):
        status = "enabled" if val.get("enabled", False) else "disabled"
    else:
        status = "enabled" if val else "disabled"

    print(f"\nPlugin Information: {plugin_name}")
    print("-" * 50)
    print(f"Status in settings.toml : {status}")
    if is_builtin:
        print(f"Installed Location      : Built-in ({builtin_dir / plugin_name})")
    elif is_user:
        print(f"Installed Location      : User-space ({user_dir / plugin_name})")
    else:
        print(f"Installed Location      : Not installed locally")

    registry = fetch_registry(args.registry)
    if registry and "plugins" in registry and plugin_name in registry["plugins"]:
        details = registry["plugins"][plugin_name]
        print(f"Registry Version        : {details.get('version', 'N/A')}")
        print(f"Author                  : {details.get('author', 'N/A')}")
        print(f"Platforms               : {', '.join(details.get('platforms', ['any']))}")
        print(f"Description             : {details.get('description', 'N/A')}")
        if "dependencies" in details:
            print(f"Dependencies            : {', '.join(details['dependencies'])}")
        if "config" in details:
            print(f"Configuration Options   : {details['config']}")
    else:
        print(f"Registry Availability   : Not found in registry {args.registry}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Caster Plugin Manager CLI")
    parser.add_argument(
        "--registry",
        default=None,
        help="URL or local path to plugin registry manifest JSON (defaults to settings/local repo)",
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

    # update
    p_upd = subparsers.add_parser("update", help="Update installed plugins from registry or local repo")
    p_upd.add_argument("name", nargs="?", default="all", help="Plugin name to update (or 'all' for all installed)")
    p_upd.add_argument("--source", help="Optional local path of plugin to install from")

    # enable
    p_en = subparsers.add_parser("enable", help="Enable an installed plugin in settings.toml")
    p_en.add_argument("name", help="Name of plugin to enable")

    # disable
    p_dis = subparsers.add_parser("disable", help="Disable an installed plugin in settings.toml")
    p_dis.add_argument("name", help="Name of plugin to disable")

    # remove
    p_rem = subparsers.add_parser("remove", help="Disable and remove a plugin")
    p_rem.add_argument("name", help="Name of plugin to remove")
    p_rem.add_argument(
        "--purge", action="store_true", help="Delete plugin files from disk"
    )

    # info
    p_info = subparsers.add_parser("info", help="Display details about a plugin")
    p_info.add_argument("name", help="Name of plugin")

    args = parser.parse_args()
    if not getattr(args, "registry", None):
        args.registry = get_configured_registry_source()

    commands = {
        "list": cmd_list,
        "install": cmd_install,
        "update": cmd_update,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "remove": cmd_remove,
        "info": cmd_info,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)


if __name__ == "__main__":
    main()
