import json
import subprocess
import sys
import time

from dragonfly import CompoundRule, MappingRule, get_current_engine, Function

from pathlib import Path

try:  # Style C -- may be imported into Caster, or externally
    BASE_PATH = str(Path(__file__).resolve().parent.parent)
    if BASE_PATH not in sys.path:
        sys.path.append(BASE_PATH)
finally:
    from castervoice.lib import settings
    
from castervoice.lib import printer, control, utilities
from castervoice.lib.rules_collection import get_instance

def start_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.ping()
    except Exception:
        subprocess.Popen([settings.SETTINGS["paths"]["PYTHONW"],
                          settings.SETTINGS["paths"]["HUD_PATH"]])


def show_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_hud()
    except Exception as e:
        printer.out("Unable to show hud. Hud not available. \n{}".format(e))


def hide_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.hide_hud()
    except Exception as e:
        printer.out("Unable to hide hud. Hud not available. \n{}".format(e))


def clear_hud():
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.clear_hud()
    except Exception as e:
        printer.out("Unable to clear hud. Hud not available. \n{}".format(e))
        # clear cmd output if hud unavailable
        Function(utilities.clear_log).execute()


def set_hud_theme(hud_theme=None):
    """
    Instruct HUD to apply a specific theme stylesheet, or cycle if omitted.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        if hud_theme:
            hud.set_theme(str(hud_theme))
        else:
            hud.cycle_theme()
    except Exception as e:
        printer.out("Unable to set hud theme. Hud not available. \n{}".format(e))


def cycle_hud_theme():
    """
    Cycle HUD through available themes.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.cycle_theme()
    except Exception as e:
        printer.out("Unable to cycle hud theme. Hud not available. \n{}".format(e))


def toggle_hud_border():
    """
    Toggle title bar / frameless overlay mode.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_border()
    except Exception as e:
        printer.out("Unable to toggle hud border. Hud not available. \n{}".format(e))


def toggle_hud_drag():
    """
    Toggle mouse drag mode (locked vs draggable).
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_drag()
    except Exception as e:
        printer.out("Unable to toggle hud drag mode. Hud not available. \n{}".format(e))


def toggle_hud_scrollbars():
    """
    Toggle scrollbar visibility.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_scrollbars()
    except Exception as e:
        printer.out("Unable to toggle hud scrollbars. Hud not available. \n{}".format(e))


def increase_hud_font():
    """
    Increase HUD font size by 1pt.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.font_increase()
    except Exception as e:
        printer.out("Unable to increase hud font. Hud not available. \n{}".format(e))


def decrease_hud_font():
    """
    Decrease HUD font size by 1pt.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.font_decrease()
    except Exception as e:
        printer.out("Unable to decrease hud font. Hud not available. \n{}".format(e))


def reset_hud_font():
    """
    Reset HUD font size to default.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.font_reset()
    except Exception as e:
        printer.out("Unable to reset hud font. Hud not available. \n{}".format(e))


def save_hud_profile(name=None):
    """
    Save current HUD geometry, theme, and styling to named profile,
    or open interactive Profile Dialog if name is omitted.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        if name:
            hud.save_profile(str(name))
        else:
            hud.show_profile_dialog("save")
    except Exception as e:
        printer.out("Unable to save hud profile. Hud not available. \n{}".format(e))


def load_hud_profile(name=None):
    """
    Load saved HUD geometry, theme, and styling from named profile,
    or open interactive Profile Dialog if name is omitted.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        if name:
            hud.load_profile(str(name))
        else:
            hud.show_profile_dialog("load")
    except Exception as e:
        printer.out("Unable to load hud profile. Hud not available. \n{}".format(e))


def show_hud_profile_dialog(mode="save"):
    """
    Open the interactive Profile Manager dialog.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_profile_dialog(str(mode))
    except Exception as e:
        printer.out("Unable to show hud profile dialog. Hud not available. \n{}".format(e))


def show_hud_help():
    """
    Show the standalone HUD commands and help dialog.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_help()
    except Exception as e:
        printer.out("Unable to show hud help. Hud not available. \n{}".format(e))


def hide_hud_help():
    """
    Hide the standalone HUD commands and help dialog.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.hide_help()
    except Exception as e:
        printer.out("Unable to hide hud help. Hud not available. \n{}".format(e))


def show_rules():
    """
    Get a list of active grammars loaded into the current engine,
    including active rules and their attributes.  Send the list
    to HUD GUI for display.
    """
    grammars = []
    engine = get_current_engine()
    for grammar in engine.grammars:
        if any([r.active for r in grammar.rules]):
            rules = []
            for rule in grammar.rules:
                if rule.active and not rule.name.startswith('_'):
                    if isinstance(rule, CompoundRule):
                        specs = [rule.spec]
                    elif isinstance(rule, MappingRule):
                        specs = sorted(["{}::{}".format(x, rule._mapping[x]) for x in rule._mapping])
                    else:
                        specs = [rule.element.gstring()]
                    rules.append({
                        "name": rule.name,
                        "exported": rule.exported,
                        "specs": specs
                    })
            grammars.append({"name": grammar.name, "rules": rules})
    grammars.extend(get_instance().serialize())
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_rules(json.dumps(grammars))
    except Exception as e:
        printer.out("Unable to show hud. Hud not available. \n{}".format(e)) 

def hide_rules():
    """
    Instruct HUD to hide the frame with the list of rules.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.hide_rules()
    except Exception as e:
        printer.out("Unable to show hud. Hud not available. \n{}".format(e)) 
    

class HudPrintMessageHandler(printer.BaseMessageHandler):
    """
    Hud message handler which prints formatted messages to the gui Hud. 
    Add symbols as the 1st character in strings utilizing printer.out
    
    @ Purple arrow - Bold Text - Important Info
    # Red arrow - Plain text - Caster Info
    $ Blue arrow - Plain text - Commands/Dictation
    """

    def __init__(self):
        super(HudPrintMessageHandler, self).__init__()
        self.hud = control.nexus().comm.get_com("hud")
        self.is_hud_active = False
        
        if get_current_engine().name != "text":
            # Retry loop to handle the cold-boot race condition
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    self.hud.ping() # HUD running?
                    self.is_hud_active = True
                    break # Connection successful, break out of loop
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5) # Wait 500ms before next attempt
                    else:
                        # Log failure if it still won't connect after 5 seconds
                        self.is_hud_active = False
                        printer.out("Hud not available after {} retries. \n{}".format(max_retries, e))

    def handle_message(self, items):
        if self.is_hud_active is True:
            # The timeout with the hud can interfere with the dragonfly speech recognition loop.
            # This appears as a stutter in recognition.
            # This stutter only happens to end user once, while self.hud.ping() is executing.
            # is_hud_active is False if the hud is not available/text engine
            # TODO: handle raising exception gracefully
            try:
                self.hud.send("\n".join([str(m) for m in items]))
            except Exception as e:
                # If an exception, print is managed by SimplePrintMessageHandler
                self.is_hud_active = False
                printer.out("Hud not available. \n{}".format(e))
                raise("") # pylint: disable=raising-bad-type
        else:
            raise("") # pylint: disable=raising-bad-type