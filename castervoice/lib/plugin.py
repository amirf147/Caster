# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Caster Plugin Base Interface

Defines the standard lifecycle contract for all built-in and user-authored
Caster plugins.
"""


class PluginBase(object):
    """
    Abstract base class establishing the lifecycle contract for Caster plugins.
    """

    name = "base_plugin"
    version = "1.0.0"
    description = "Base Caster Plugin"

    def __init__(self):
        self._nexus = None
        self._config = {}
        self._is_running = False

    @property
    def is_running(self):
        return self._is_running

    def initialize(self, nexus, config):
        """
        Called during Caster startup prior to speech engine initialization.
        Plugins should register printer handlers, engine observers, and listeners here.

        :param nexus: The Caster Nexus global coordinator instance.
        :param config: Dictionary of plugin-specific settings from settings.toml.
        """
        self._nexus = nexus
        self._config = config or {}

    def start(self):
        """
        Called after engine configuration has completed.
        Plugins should start background worker threads, Named Pipe listeners,
        SSE streams, or GUI processes here.
        """
        self._is_running = True

    def stop(self):
        """
        Called during Caster shutdown or reload.
        Plugins should terminate background threads, close sockets/pipes,
        and release resources cleanly here.
        """
        self._is_running = False
