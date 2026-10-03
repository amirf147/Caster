from dragonfly import Choice, Function, MappingRule

from castervoice.lib.ctrl.mgr.rule_details import RuleDetails
from castervoice.lib.merge.state.short import R
from castervoice.lib.ctrl.mgr import plugin_support


class PluginRule(MappingRule):
    mapping = {
        "caster (list | show) plugins":
            R(Function(plugin_support.list_plugins), rdescript="List installed and running plugins"),
        "caster reload plugins":
            R(Function(plugin_support.reload_plugins), rdescript="Reload all enabled plugins"),
        "caster (load | start) plugin <plugin_name>":
            R(Function(plugin_support.load_plugin), rdescript="Load and start a plugin dynamically"),
        "caster (unload | stop) plugin <plugin_name>":
            R(Function(plugin_support.unload_plugin), rdescript="Stop and unload a plugin dynamically"),
        "caster install plugin <plugin_name>":
            R(Function(plugin_support.install_plugin), rdescript="Install and start a plugin from registry"),
    }
    extras = [
        Choice("plugin_name", plugin_support.get_plugin_choices()),
    ]


def get_rule():
    return PluginRule, RuleDetails(name="plugin rule")
