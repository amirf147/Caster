from dragonfly import Choice, Function, MappingRule, RunCommand

from castervoice.lib import control, utilities
from castervoice.lib.ctrl.dependencies import find_pip  # pylint: disable=no-name-in-module
from castervoice.lib.ctrl.updatecheck import update
from castervoice.lib.ctrl.mgr.rule_details import RuleDetails
from castervoice.lib.merge.state.short import R
from castervoice.asynch.hud_support import (
    show_hud,
    hide_hud,
    show_rules,
    hide_rules,
    clear_hud,
    set_hud_theme,
    toggle_hud_border,
    toggle_hud_drag,
    toggle_hud_scrollbars,
    toggle_hud_status_bar,
    toggle_hud_rules_bar,
    toggle_hud_adce,
    toggle_hud_verbose,
    increase_hud_font,
    decrease_hud_font,
    reset_hud_font,
    save_hud_profile,
    load_hud_profile,
    show_hud_help,
    hide_hud_help,
)

_PIP = find_pip()


class _DependencyUpdate(RunCommand):
    synchronous = True

    # pylint: disable=method-hidden
    def process_command(self, proc):
        # Process the output from the command.
        RunCommand.process_command(self, proc)
        # Only reboot dragon if the command was successful and online_mode is true
        # 'pip install ...' may exit successfully even if there were connection errors.
        if proc.wait() == 0 and update:
            Function(utilities.reboot).execute()


class CasterRule(MappingRule):
    mapping = {
        "reboot caster":
            R(Function(utilities.reboot)),
        "update dragonfly":
            R(_DependencyUpdate([_PIP, "install", "--upgrade", "dragonfly2"])),
        # update management ToDo: Fully implement castervoice PIP install
        #"update caster":
        #    R(_DependencyUpdate([_PIP, "install", "--upgrade", "castervoice"])),

        # ccr de/activation
        "enable (c c r|ccr)":
            R(Function(lambda: control.nexus().set_ccr_active(True))),
        "disable (c c r|ccr)":
            R(Function(lambda: control.nexus().set_ccr_active(False))),
        "show caster hud":
            R(Function(show_hud), rdescript="Show the HUD window"),
        "hide caster hud":
            R(Function(hide_hud), rdescript="Hide the HUD window"),
        "show caster rules":
            R(Function(show_rules), rdescript="Open HUD frame with the list of active rules"),
        "hide caster rules":
            R(Function(hide_rules), rdescript="Hide the list of active rules"),
        "clear caster hud":
            R(Function(clear_hud), rdescript="Clear output the HUD window"),
        "show caster [hud] help":
            R(Function(show_hud_help), rdescript="Show standalone HUD commands and help dialog"),
        "hide caster [hud] help":
            R(Function(hide_hud_help), rdescript="Hide standalone HUD commands and help dialog"),
        "caster hud help":
            R(Function(show_hud_help), rdescript="Show standalone HUD commands and help dialog"),
        "caster hud theme [<hud_theme>]":
            R(Function(set_hud_theme), rdescript="Set or cycle HUD theme"),
        "caster hud (border | title bar | frame) [toggle]":
            R(Function(toggle_hud_border), rdescript="Toggle HUD title bar / frameless overlay"),
        "caster hud (drag | move) [toggle]":
            R(Function(toggle_hud_drag), rdescript="Toggle HUD mouse drag mode"),
        "caster hud scroll [toggle]":
            R(Function(toggle_hud_scrollbars), rdescript="Toggle HUD scrollbars"),
        # Modular Diagnostic Panels & Strip Toggles
        "[caster hud] verbose [toggle]":
            R(Function(toggle_hud_verbose), rdescript="Toggle HUD verbose diagnostic panels (Status Header + Rules Strip)"),
        "toggle [caster hud] verbose":
            R(Function(toggle_hud_verbose), rdescript="Toggle HUD verbose diagnostic panels (Status Header + Rules Strip)"),
        "[caster hud] (status | header | status bar) [toggle]":
            R(Function(toggle_hud_status_bar), rdescript="Toggle HUD top status banner"),
        "toggle [caster hud] (status | header | status bar)":
            R(Function(toggle_hud_status_bar), rdescript="Toggle HUD top status banner"),
        "[caster hud] (rules strip | active rules [strip] | rules bar | active rules) [toggle]":
            R(Function(toggle_hud_rules_bar), rdescript="Toggle HUD active rules tag strip"),
        "toggle [caster hud] (active rules [strip] | rules strip | rules bar)":
            R(Function(toggle_hud_rules_bar), rdescript="Toggle HUD active rules tag strip"),
        "[caster hud] (adce | a d c e | context engine | dynamic context) [strip] [toggle]":
            R(Function(toggle_hud_adce), rdescript="Toggle HUD ADCE dynamic context strip"),
        "toggle [caster hud] (adce | a d c e | context engine | dynamic context) [strip]":
            R(Function(toggle_hud_adce), rdescript="Toggle HUD ADCE dynamic context strip"),
        "caster hud font (increase | bigger | up)":
            R(Function(increase_hud_font), rdescript="Increase HUD font size"),
        "caster hud font (decrease | smaller | down)":
            R(Function(decrease_hud_font), rdescript="Decrease HUD font size"),
        "caster hud font reset":
            R(Function(reset_hud_font), rdescript="Reset HUD font size to default"),
        "caster hud save profile":
            R(Function(save_hud_profile), rdescript="Open Profile Dialog to save current layout"),
        "caster hud (profile save | profile record)":
            R(Function(save_hud_profile), rdescript="Open Profile Dialog to save current layout"),
        "caster hud (load profile | show profile | profile)":
            R(Function(load_hud_profile), rdescript="Open Profile Dialog to load or manage profiles"),
        "show caster [hud] profiles":
            R(Function(load_hud_profile), rdescript="Open Profile Dialog to load or manage profiles"),
    }
    extras = [
        Choice("hud_theme", {
            "classic": "classic",
            "frosted": "frosted-dark",
            "dark": "frosted-dark",
            "minimal": "minimal-transparent",
            "transparent": "minimal-transparent",
            "high contrast": "high-contrast",
            "contrast": "high-contrast",
        }, default=None),
    ]


def get_rule():
    return CasterRule, RuleDetails(name="caster rule")