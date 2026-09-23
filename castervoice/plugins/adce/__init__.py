# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Active Desktop Context Engine (ADCE) Plugin Package
"""

from castervoice.plugins.adce.client import (
    adce,
    AdceBridgeClient,
    add_context_listener,
    remove_context_listener,
    is_ide_terminal_focused,
    is_ide_editor_focused,
    is_ide_git_commit_focused,
    get_current_zone,
    is_connected,
    print_adce_status,
)
from castervoice.plugins.adce.plugin import AdcePlugin, get_plugin
