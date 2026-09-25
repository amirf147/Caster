# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Caster Plugin Manager

Discovers, instantiates, initializes, and orchestrates the lifecycle of all
built-in and user-authored Caster plugins according to settings.toml.
"""

import importlib
import inspect
import logging
import os
import sys

from castervoice.lib import printer
from castervoice.lib.plugin import PluginBase

_logger = logging.getLogger("caster.plugin_manager")


class PluginManager(object):
    """
    Manages discovery, initialization, startup, and shutdown of Caster plugins.
    """

    def __init__(self, nexus=None, settings_dict=None):
        self._nexus = nexus
        self._settings = settings_dict or {}
        self._plugins = {}  # name -> PluginBase instance
        self._enabled_names = set()

    def get_plugin(self, name):
        """Returns the loaded plugin instance by name, or None if not loaded."""
        return self._plugins.get(name)

    def get_loaded_plugins(self):
        """Returns a list of all loaded plugin instances."""
        return list(self._plugins.values())

    def load_plugins(self, plugin_dirs=None):
        """
        Discovers and instantiates enabled plugins from specified directories.
        Defaults to scanning castervoice/plugins/ and caster_user_content/plugins/.
        """
        plugins_config = self._settings.get("plugins", {})

        # Determine which plugins are enabled in settings
        self._enabled_names = set()
        for key, val in plugins_config.items():
            if isinstance(val, bool) and val:
                self._enabled_names.add(key)
            elif isinstance(val, dict) and val.get("enabled", False):
                self._enabled_names.add(key)

        if not plugin_dirs:
            plugin_dirs = self._default_plugin_directories()

        for directory in plugin_dirs:
            if not os.path.isdir(directory):
                continue
            self._scan_directory(directory, plugins_config)

    @classmethod
    def prepare_environment(cls, settings_dict=None):
        """Ensures plugin directories are registered in sys.path before rule loading."""
        pm = cls(settings_dict=settings_dict)
        return pm._default_plugin_directories()

    def _default_plugin_directories(self):
        """Calculates default plugin search directories (built-in and user)."""
        dirs = []
        try:
            import castervoice
            base_dir = os.path.dirname(os.path.abspath(castervoice.__file__))
            builtin_plugins = os.path.join(base_dir, "plugins")
            if os.path.isdir(builtin_plugins):
                dirs.append(builtin_plugins)
                if builtin_plugins not in sys.path:
                    sys.path.append(builtin_plugins)
        except Exception:
            pass

        # User directory from settings or defaults
        user_dir = self._settings.get("paths", {}).get("USER_DIR")
        if not user_dir or not os.path.isdir(user_dir):
            try:
                from castervoice.lib import settings
                user_dir = settings.settings(["paths", "USER_DIR"])
            except Exception:
                pass
        if not user_dir or not os.path.isdir(user_dir):
            try:
                from appdirs import user_data_dir
                user_dir = user_data_dir(appname="caster", appauthor=False)
            except Exception:
                pass

        if user_dir and os.path.isdir(user_dir):
            user_plugins = os.path.join(user_dir, "caster_user_content", "plugins")
            if os.path.isdir(user_plugins):
                dirs.append(user_plugins)
                if user_plugins not in sys.path:
                    sys.path.insert(0, user_plugins)

        return dirs

    def _scan_directory(self, directory, plugins_config):
        """Scans a directory for plugin packages or modules."""
        for entry in os.listdir(directory):
            entry_path = os.path.join(directory, entry)
            if entry.startswith((".", "_")):
                continue

            plugin_name = entry
            plugin_file = None

            if os.path.isdir(entry_path):
                candidate_py = os.path.join(entry_path, "plugin.py")
                candidate_init = os.path.join(entry_path, "__init__.py")
                if os.path.isfile(candidate_py):
                    plugin_file = candidate_py
                elif os.path.isfile(candidate_init):
                    plugin_file = candidate_init
            elif entry.endswith(".py"):
                plugin_name = entry[:-3]
                plugin_file = entry_path

            if not plugin_file:
                continue

            # Only load if enabled in settings
            if plugin_name not in self._enabled_names:
                _logger.debug("Plugin '%s' is not enabled in settings.toml; skipping.", plugin_name)
                continue

            # Avoid re-loading if already registered
            if plugin_name in self._plugins:
                continue

            self._load_plugin_file(plugin_name, plugin_file, plugins_config.get(plugin_name, {}))

    def _load_plugin_file(self, plugin_name, plugin_file, plugin_config):
        """Loads a plugin module, instantiates its PluginBase class, and registers it."""
        try:
            module = None
            for cand_module_name in [
                plugin_name,
                "caster_user_content.plugins.{}".format(plugin_name),
                "castervoice.plugins.{}".format(plugin_name),
            ]:
                try:
                    module = importlib.import_module(cand_module_name)
                    break
                except (ImportError, ModuleNotFoundError):
                    continue

            if not module and os.path.isfile(plugin_file):
                parent_dir = os.path.dirname(plugin_file)
                is_pkg = os.path.basename(plugin_file) in ("__init__.py", "plugin.py") and os.path.isdir(parent_dir) and os.path.basename(parent_dir) == plugin_name

                if is_pkg:
                    init_file = os.path.join(parent_dir, "__init__.py") if os.path.isfile(os.path.join(parent_dir, "__init__.py")) else plugin_file
                    spec = importlib.util.spec_from_file_location(
                        plugin_name,
                        init_file,
                        submodule_search_locations=[parent_dir],
                    )
                else:
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_name] = module
                    spec.loader.exec_module(module)

            if not module:
                return

            if plugin_name not in sys.modules:
                sys.modules[plugin_name] = module

            plugin_instance = None

            # 1. Check for factory function get_plugin()
            if hasattr(module, "get_plugin") and callable(module.get_plugin):
                plugin_instance = module.get_plugin()

            # 2. Otherwise search for concrete PluginBase subclass
            if not plugin_instance:
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, PluginBase) and obj is not PluginBase:
                        plugin_instance = obj()
                        break

            if not plugin_instance:
                _logger.warning("No PluginBase subclass or get_plugin() found in '%s'.", plugin_file)
                return

            if isinstance(plugin_config, bool):
                cfg = {}
            else:
                cfg = dict(plugin_config)

            plugin_instance.initialize(self._nexus, cfg)
            self._plugins[plugin_name] = plugin_instance

            # Register companion rules with GrammarManager if supported
            if self._nexus and hasattr(self._nexus, "_grammar_manager") and self._nexus._grammar_manager:
                try:
                    rules = plugin_instance.get_rules() if hasattr(plugin_instance, "get_rules") else []
                    if rules:
                        for rule_item in rules:
                            if inspect.isclass(rule_item):
                                self._nexus._grammar_manager.add_rule(rule_item)
                            elif isinstance(rule_item, tuple) and len(rule_item) >= 2:
                                self._nexus._grammar_manager.add_rule(rule_item[0], rule_item[1])
                except Exception as r_err:
                    _logger.warning("Failed to register rules for plugin '%s': %s", plugin_name, r_err)

            _logger.info("Plugin '%s' loaded and initialized successfully.", plugin_name)

        except Exception as ex:
            printer.out("Caster PluginManager: Failed to load plugin '{}': {}".format(plugin_name, ex))
            _logger.exception("Error loading plugin '%s':", plugin_name)

    def start_plugins(self):
        """Starts all loaded plugins."""
        for name, plugin in list(self._plugins.items()):
            try:
                plugin.start()
                _logger.info("Plugin '%s' started.", name)
            except Exception as ex:
                printer.out("Caster PluginManager: Failed to start plugin '{}': {}".format(name, ex))
                _logger.exception("Error starting plugin '%s':", name)

    def stop_plugins(self):
        """Gracefully stops all running plugins in reverse order."""
        for name in reversed(list(self._plugins.keys())):
            plugin = self._plugins[name]
            try:
                if plugin.is_running:
                    plugin.stop()
                    _logger.info("Plugin '%s' stopped.", name)
            except Exception as ex:
                _logger.exception("Error stopping plugin '%s':", name)

    def load_plugin(self, name):
        """Loads and starts a single plugin dynamically."""
        if name in self._plugins and self._plugins[name].is_running:
            return True, "Plugin '{}' is already running.".format(name)

        plugin_file = None
        for directory in self._default_plugin_directories():
            cand_dir = os.path.join(directory, name)
            if os.path.isdir(cand_dir):
                cand_py = os.path.join(cand_dir, "plugin.py")
                cand_init = os.path.join(cand_dir, "__init__.py")
                if os.path.isfile(cand_py):
                    plugin_file = cand_py
                    break
                elif os.path.isfile(cand_init):
                    plugin_file = cand_init
                    break
            cand_file = os.path.join(directory, "{}.py".format(name))
            if os.path.isfile(cand_file):
                plugin_file = cand_file
                break

        if not plugin_file:
            return False, "Plugin '{}' not found in plugin directories.".format(name)

        self._enabled_names.add(name)
        plugins_config = self._settings.get("plugins", {})
        self._load_plugin_file(name, plugin_file, plugins_config.get(name, {}))

        plugin = self._plugins.get(name)
        if not plugin:
            return False, "Failed to instantiate plugin '{}'.".format(name)

        try:
            if getattr(plugin, "replaces_hud", False):
                from castervoice.asynch import hud_support
                hud_support.stop_hud()

            plugin.start()
            _logger.info("Plugin '%s' dynamically started.", name)
            return True, "Plugin '{}' loaded and started successfully.".format(name)
        except Exception as ex:
            _logger.exception("Error starting plugin '%s':", name)
            return False, "Error starting plugin '{}': {}".format(name, ex)

    def unload_plugin(self, name):
        """Stops and unloads a single plugin dynamically."""
        plugin = self._plugins.get(name)
        if not plugin:
            return False, "Plugin '{}' is not currently loaded.".format(name)

        try:
            if plugin.is_running:
                plugin.stop()
            self._plugins.pop(name, None)
            if name in self._enabled_names:
                self._enabled_names.remove(name)

            _logger.info("Plugin '%s' stopped and unloaded.", name)
            return True, "Plugin '{}' stopped and unloaded.".format(name)
        except Exception as ex:
            _logger.exception("Error unloading plugin '%s':", name)
            return False, "Error unloading plugin '{}': {}".format(name, ex)

    def reload_all(self):
        """Stops all running plugins, refreshes settings, and reloads all enabled plugins."""
        self.stop_plugins()
        self._plugins.clear()
        try:
            from castervoice.lib import settings
            self._settings = settings.SETTINGS
        except Exception:
            pass
        self.load_plugins()
        self.start_plugins()
        return True, "Reloaded all plugins: {}".format(", ".join(self._plugins.keys()) or "none")


_GLOBAL_PLUGIN_MANAGER = None


def get_plugin_manager(nexus=None, settings_dict=None):
    """Returns the global PluginManager singleton."""
    global _GLOBAL_PLUGIN_MANAGER
    if _GLOBAL_PLUGIN_MANAGER is None:
        _GLOBAL_PLUGIN_MANAGER = PluginManager(nexus=nexus, settings_dict=settings_dict)
    return _GLOBAL_PLUGIN_MANAGER
