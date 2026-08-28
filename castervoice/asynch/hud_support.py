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
    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import ClearHistoryEvent
        get_telemetry_publisher().publish(ClearHistoryEvent())
    except Exception:
        pass
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.clear_hud()
    except Exception:
        Function(utilities.clear_log).execute()


def set_hud_theme(hud_theme=None):
    """
    Instruct HUD to apply a specific theme stylesheet, or cycle if omitted.
    """
    if hud_theme:
        try:
            from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
            from castervoice.asynch.hud.core.events import ThemeChangeEvent
            get_telemetry_publisher().publish(ThemeChangeEvent(theme_name=str(hud_theme)))
        except Exception:
            pass
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


def toggle_hud_status_bar():
    """
    Toggle top status header banner visibility.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_status_bar()
    except Exception as e:
        printer.out("Unable to toggle hud status bar. Hud not available. \n{}".format(e))


import threading

_FOCUS_TRACKER = None
_FOCUS_TRACKER_LOCK = threading.Lock()

INTERNAL_RULE_EXCLUSIONS = frozenset([
    "preparedrule",
    "repeatrule",
    "ccr",
    "ccrmerger",
    "ccrmerger2",
    "caster_rule",
    "casterrule",
    "caster_mic_rule",
    "castermicrule",
    "caster mic modes",
    "dictationsinkrule",
    "dictation_sink_rule",
    "dictationsink",
])


def is_internal_rule_name(name):
    """Returns True if rule name is an internal merger artifact or private helper."""
    if not name or str(name).startswith('_'):
        return True
    low = str(name).lower().strip().replace(" ", "").replace("_", "")
    if low in INTERNAL_RULE_EXCLUSIONS:
        return True
    if low.startswith("repeater"):
        return True
    if low.startswith("g") and low[1:].isdigit():
        return True
    return False


def get_adce_context(target_process=None):
    """
    Safely queries ADCE bridge if connected.
    Ensures cached zone is only returned if it matches the current target process.
    """
    try:
        from caster_user_content.util.adce_bridge import adce, IDE_PROCESS_NAMES
        if adce.is_connected():
            adce_proc = str(adce.get_current_process() or "").lower().strip()
            target_proc = str(target_process or "").lower().strip()

            # Only return ADCE zone/file if the target process matches the ADCE snapshot process
            if not target_proc or target_proc == adce_proc or (target_proc in IDE_PROCESS_NAMES and adce_proc in IDE_PROCESS_NAMES):
                return {
                    "is_connected": True,
                    "semantic_zone": adce.get_current_zone(),
                    "process_name": adce_proc,
                    "window_title": adce.get_current_title(),
                    "active_file": adce.get_active_file(),
                }
            else:
                # Process mismatch: native OS focus switched ahead of ADCE poller
                return {
                    "is_connected": True,
                    "semantic_zone": "",
                    "process_name": target_proc,
                    "window_title": "",
                    "active_file": "",
                }
    except Exception:
        pass
    return {
        "is_connected": False,
        "semantic_zone": "",
        "process_name": "",
        "window_title": "",
        "active_file": "",
    }


def _on_window_focus_changed(process_name, window_title, hwnd=0):
    """Callback executed when native OS window focus switches."""
    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import DesktopContextEvent, ActiveRulesEvent
        active = get_active_contextual_rules(target_process=process_name, target_title=window_title, target_hwnd=hwnd)
        pub = get_telemetry_publisher()

        adce_ctx = get_adce_context(target_process=process_name)
        zone = adce_ctx["semantic_zone"] if adce_ctx["is_connected"] else ""
        active_file = adce_ctx["active_file"] if adce_ctx["is_connected"] else ""

        pub.publish(
            DesktopContextEvent(
                process_name=process_name,
                window_title=window_title,
                semantic_zone=zone,
                active_file=active_file,
                is_connected=adce_ctx["is_connected"],
            )
        )
        pub.publish(ActiveRulesEvent(rules=active))
    except Exception:
        pass


def _on_adce_context_changed(process_name, window_title, semantic_zone, active_file, is_connected=True):
    """Real-time callback executed when ADCE emits a sub-window zone transition or active file switch."""
    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import DesktopContextEvent, ActiveRulesEvent
        pub = get_telemetry_publisher()
        pub.publish(
            DesktopContextEvent(
                process_name=process_name,
                window_title=window_title,
                semantic_zone=semantic_zone,
                active_file=active_file,
                is_connected=is_connected,
            )
        )
        if is_connected and process_name:
            active = get_active_contextual_rules(target_process=process_name, target_title=window_title)
            pub.publish(ActiveRulesEvent(rules=active))
    except Exception:
        pass


def get_focus_tracker():
    """Returns the global IFocusTracker instance, starting it and ADCE tracker if not yet running."""
    global _FOCUS_TRACKER
    if _FOCUS_TRACKER is None:
        with _FOCUS_TRACKER_LOCK:
            if _FOCUS_TRACKER is None:
                from castervoice.asynch.hud.core.window_tracker import create_window_focus_tracker
                from castervoice.asynch.hud.core.adce_tracker import get_adce_tracker
                _FOCUS_TRACKER = create_window_focus_tracker(on_focus_changed=_on_window_focus_changed)
                _FOCUS_TRACKER.start()
                try:
                    get_adce_tracker(on_context_changed=_on_adce_context_changed)
                except Exception:
                    pass
    return _FOCUS_TRACKER


def get_active_rule_names():
    """Returns a list of non-private active rule names in the current engine."""
    rule_names = []
    engine = get_current_engine()
    if engine and hasattr(engine, "grammars"):
        for grammar in engine.grammars:
            if any([r.active for r in grammar.rules]):
                for rule in grammar.rules:
                    if rule.active and not rule.name.startswith('_'):
                        rule_names.append(rule.name)
    return rule_names


def get_active_contextual_rules(target_process=None, target_title=None, target_hwnd=0):
    """
    Returns a list of active application-specific / contextual rule names.
    If the target window matches application-scoped rules, returns those contextual rules.
    If only global rules are active, returns an empty list [] (prompting [Global Context] on HUD).
    """
    contextual_rules = []
    seen = set()

    proc_candidates = []
    if target_process:
        proc_candidates.append(str(target_process).lower().strip())
    proc_low = str(target_process or "").lower().strip()
    title_low = str(target_title or "").lower().strip()
    if proc_low in ("windowsterminal", "conhost", "cmd", "wt"):
        if "powershell" in title_low or "pwsh" in title_low:
            proc_candidates.extend(["powershell", "pwsh"])
    if proc_low == "pwsh" and "powershell" not in proc_candidates:
        proc_candidates.append("powershell")
    if proc_low == "powershell" and "pwsh" not in proc_candidates:
        proc_candidates.append("pwsh")
    if not proc_candidates:
        proc_candidates.append("")

    engine = get_current_engine()
    if engine and hasattr(engine, "grammars"):
        for grammar in engine.grammars:
            ctx = getattr(grammar, "context", None)
            if ctx is not None:
                is_match = False
                for p in proc_candidates:
                    try:
                        if ctx.matches(p, target_title or "", target_hwnd or 0):
                            is_match = True
                            break
                    except Exception:
                        pass

                if not is_match and not target_process:
                    try:
                        is_match = ctx.matches()
                    except Exception:
                        is_match = any(r.active for r in grammar.rules)

                if is_match:
                    for rule in grammar.rules:
                        r_name = str(rule.name).strip()
                        if r_name.lower().startswith("repeater") or r_name == "RepeatRule":
                            execs = getattr(ctx, "_executable", None)
                            if execs and isinstance(execs, (list, tuple, set)) and len(execs) > 0:
                                r_name = str(list(execs)[0]).capitalize()

                        if not is_internal_rule_name(r_name):
                            if r_name and r_name not in seen:
                                seen.add(r_name)
                                contextual_rules.append(r_name)

    return contextual_rules


def toggle_hud_rules_bar():
    """
    Toggle active contextual rules tag strip visibility.
    """
    get_focus_tracker()
    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import ActiveRulesEvent
        active = get_active_contextual_rules()
        get_telemetry_publisher().publish(ActiveRulesEvent(rules=active))
    except Exception:
        pass
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_rules_bar()
    except Exception as e:
        printer.out("Unable to toggle hud rules bar. Hud not available. \n{}".format(e))


def toggle_hud_adce():
    """
    Toggle ADCE dynamic context strip visibility.
    """
    get_focus_tracker()
    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import DesktopContextEvent
        adce_ctx = get_adce_context()
        get_telemetry_publisher().publish(
            DesktopContextEvent(
                process_name=adce_ctx["process_name"] if adce_ctx["is_connected"] else "",
                window_title=adce_ctx["window_title"] if adce_ctx["is_connected"] else "",
                semantic_zone=adce_ctx["semantic_zone"] if adce_ctx["is_connected"] else "",
                active_file=adce_ctx["active_file"] if adce_ctx["is_connected"] else "",
                is_connected=adce_ctx["is_connected"],
            )
        )
    except Exception:
        pass
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_adce()
    except Exception as e:
        printer.out("Unable to toggle hud adce strip. Hud not available. \n{}".format(e))


def toggle_hud_verbose():
    """
    Toggle verbose diagnostic panels (Status Header + Active Contextual Rules Strip).
    Note: ADCE strip is managed separately via toggle_hud_adce.
    """
    get_focus_tracker()
    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import ActiveRulesEvent
        active = get_active_contextual_rules()
        get_telemetry_publisher().publish(ActiveRulesEvent(rules=active))
    except Exception:
        pass
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.toggle_verbose()
    except Exception as e:
        printer.out("Unable to toggle hud verbose mode. Hud not available. \n{}".format(e))


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
    rule_names = []
    engine = get_current_engine()
    if engine and hasattr(engine, "grammars"):
        for grammar in engine.grammars:
            if any([r.active for r in grammar.rules]):
                rules = []
                for rule in grammar.rules:
                    if rule.active and not rule.name.startswith('_'):
                        rule_names.append(rule.name)
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

    try:
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        from castervoice.asynch.hud.core.events import ActiveRulesEvent
        get_telemetry_publisher().publish(ActiveRulesEvent(rules=rule_names))
    except Exception:
        pass

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
    Asynchronous, non-blocking HUD message handler.
    Dispatches formatted recognition telemetry via in-memory queue with zero speech loop delay.
    
    @ Purple arrow - Bold Text - Important Info
    # Red arrow - Plain text - Caster Info
    $ Blue arrow - Plain text - Commands/Dictation
    """

    def __init__(self):
        super(HudPrintMessageHandler, self).__init__()
        from castervoice.asynch.hud.ipc.client import get_telemetry_publisher
        self._publisher = get_telemetry_publisher()
        try:
            get_focus_tracker()
        except Exception:
            pass

    def handle_message(self, items):
        from castervoice.asynch.hud.core.events import RecognitionEvent
        for item in items:
            text = str(item)
            kind = "cmd"
            if text.startswith('$'):
                text = text[1:].strip()
                kind = "cmd"
            elif text.startswith('@'):
                text = text[1:].strip()
                kind = "sys"
            elif text.startswith('#'):
                text = text[1:].strip()
                kind = "err"
            self._publisher.publish(RecognitionEvent(phrase=text, kind=kind))