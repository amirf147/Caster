# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Sikuli Plugin

Manages the Sikuli visual GUI automation server proxy as a Caster plugin.
"""

import logging
from castervoice.lib.plugin import PluginBase

_logger = logging.getLogger("caster.plugins.sikuli")


class SikuliPlugin(PluginBase):
    name = "sikuli"
    version = "1.0.0"
    description = "Sikuli Visual GUI Automation Server Proxy"

    def initialize(self, nexus, config):
        super(SikuliPlugin, self).initialize(nexus, config)
        _logger.info("Sikuli plugin initialized.")

    def start(self):
        super(SikuliPlugin, self).start()
        try:
            from castervoice.asynch.sikuli import sikuli_controller
            sikuli_controller.get_instance().bootstrap_start_server_proxy()
            _logger.info("Sikuli server proxy bootstrapped successfully.")
        except Exception as ex:
            _logger.warning("Failed to bootstrap Sikuli server proxy: %s", ex)

    def stop(self):
        super(SikuliPlugin, self).stop()


def get_plugin():
    return SikuliPlugin()
