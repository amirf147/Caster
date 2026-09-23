# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Standard Upstream Caster HUD Plugin

Wraps the original, lightweight, monolithic Caster Heads-Up Display from
upstream master for minimal or low-resource setups.
"""

import logging
from castervoice.lib.plugin import PluginBase
from castervoice.asynch import hud_support

_logger = logging.getLogger("caster.plugins.standard_hud")


class StandardHudPlugin(PluginBase):
    name = "standard_hud"
    version = "1.0.0"
    description = "Original Lightweight Upstream Caster Heads-Up Display"

    def initialize(self, nexus, config):
        super(StandardHudPlugin, self).initialize(nexus, config)
        _logger.info("Standard HUD plugin initialized.")

    def start(self):
        super(StandardHudPlugin, self).start()
        hud_support.start_hud()
        _logger.info("Standard HUD started.")

    def stop(self):
        super(StandardHudPlugin, self).stop()


def get_plugin():
    return StandardHudPlugin()
