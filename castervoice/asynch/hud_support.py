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
    "globalccr",
    "globalccrextended",
    "globalccrextendedrule",
    "global_ccr_extended_rule",
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


def get_adce_context():
    """
    Safely queries ADCE tracker if connected.
    """
    try:
        tracker = get_focus_tracker()
        if tracker and tracker.is_connected():
            ctx = tracker.get_current_context()
            return {
                "is_connected": True,
                "semantic_zone": ctx.get("semantic_zone", ""),
                "process_name": str(ctx.get("process_name") or "").lower().strip(),
                "window_title": ctx.get("window_title", ""),
                "active_file": ctx.get("active_file", ""),
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
    """Deprecated callback retained for signature compatibility. Focus tracking is handled out-of-process by ADCE."""
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
        active = []
        if is_connected and process_name:
            active = get_active_contextual_rules(target_process=process_name, target_title=window_title)
            pub.publish(ActiveRulesEvent(rules=active))
    except Exception:
        pass


def get_focus_tracker():
    """Returns the global desktop context tracker instance (ADCE SSE listener)."""
    global _FOCUS_TRACKER
    if _FOCUS_TRACKER is None:
        with _FOCUS_TRACKER_LOCK:
            if _FOCUS_TRACKER is None:
                try:
                    import adce
                    if hasattr(adce, "add_context_listener") and hasattr(adce, "adce"):
                        adce.add_context_listener(_on_adce_context_changed)
                        _FOCUS_TRACKER = adce.adce
                except Exception:
                    pass

                if _FOCUS_TRACKER is None:
                    from castervoice.asynch.hud.core.adce_tracker import get_adce_tracker
                    try:
                        _FOCUS_TRACKER = get_adce_tracker(on_context_changed=_on_adce_context_changed)
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


def _extract_context_executables(ctx):
    """
    Recursively extracts declared executable strings from AppContext or LogicAndContext.
    """
    if ctx is None:
        return []
    if hasattr(ctx, "_executable") and ctx._executable:
        return list(ctx._executable)
    if hasattr(ctx, "_children"):
        execs = []
        for child in ctx._children:
            sub = _extract_context_executables(child)
            if sub:
                execs.extend(sub)
        return execs
    return []


def _match_executable_precision(proc_candidates, declared_executables):
    """
    Universal precision executable matcher.
    Returns True if any candidate matches any declared executable by stem, filename, or path.
    Prevents false-positive substring matches (e.g. 'antigravity ide' matching 'antigravity',
    or 'notepad++' matching 'notepad').
    """
    if not declared_executables:
        return True

    target_stems = set()
    target_names = set()
    target_fulls = set()
    for dec in declared_executables:
        if not dec:
            continue
        d_norm = str(dec).lower().strip().replace('/', '\\')
        target_fulls.add(d_norm)
        target_names.add(Path(d_norm).name)
        target_stems.add(Path(d_norm).stem)

    for p in proc_candidates:
        if not p:
            continue
        p_norm = str(p).lower().strip().replace('/', '\\')
        p_name = Path(p_norm).name
        p_stem = Path(p_norm).stem

        # 1. Stem equality (e.g. 'antigravity' == 'antigravity', 'code' == 'code')
        if p_stem in target_stems:
            return True
        # 2. Filename equality (e.g. 'antigravity.exe' == 'antigravity.exe')
        if p_name in target_names:
            return True
        # 3. Full path match or suffix
        if p_norm in target_fulls or any(p_norm.endswith('\\' + name) for name in target_names):
            return True

    return False


def _get_enabled_rule_classes():
    """
    Returns a tuple of (enabled_rcns_set, whitelisted_rcns_set) representing
    authoritative rule activation state from Caster's live GrammarManager or rules.toml.
    """
    try:
        from castervoice.lib import control
        nex = control.nexus()
        if nex and hasattr(nex, "_grammar_manager") and nex._grammar_manager:
            gm = nex._grammar_manager
            cfg = getattr(gm, "_config", None)
            if cfg:
                enabled = set(cfg.get_enabled_rcns_ordered())
                whitelisted = set(cfg._config.get("whitelisted", {}).keys())
                return enabled, whitelisted
    except Exception:
        pass
    try:
        from castervoice.lib import settings
        if getattr(settings, "SETTINGS", None) is None:
            settings.initialize()
        from castervoice.lib.ctrl.mgr.rules_config import RulesConfig
        cfg = RulesConfig()
        enabled = set(cfg.get_enabled_rcns_ordered())
        whitelisted = set(cfg._config.get("whitelisted", {}).keys())
        return enabled, whitelisted
    except Exception:
        pass
    return None, None


def _format_rcn_display_name(rcn):
    """Formats a rule class name into a clean display title (e.g. FirefoxCcrRule -> Firefox CCR)."""
    if not rcn:
        return ""
    name = str(rcn).strip()
    if name.endswith("Rule") and len(name) > 4:
        name = name[:-4]
    if name.endswith("Ccr"):
        name = name[:-3] + " CCR"
    elif name.endswith("CCR"):
        name = name[:-3] + " CCR"
    return name


def _resolve_ccr_rcn_from_context(ctx):
    """
    Resolves the authoritative Rule Class Name (RCN) for a CCR context by cross-referencing
    GrammarManager's registered managed rules.
    """
    try:
        from castervoice.lib import control
        nex = control.nexus()
        if nex and hasattr(nex, "_grammar_manager") and nex._grammar_manager:
            gm = nex._grammar_manager
            managed = getattr(gm, "_managed_rules", {})
            ctx_execs = getattr(ctx, "_executable", None)
            if ctx_execs:
                if isinstance(ctx_execs, (list, tuple, set)):
                    ctx_exec_set = set(str(x).lower().strip() for x in ctx_execs)
                else:
                    ctx_exec_set = {str(ctx_execs).lower().strip()}

                for rcn, mr in managed.items():
                    rd = mr.get_details()
                    if rd and rd.declared_ccrtype is not None and rd.executable:
                        rd_execs = rd.executable
                        if isinstance(rd_execs, (list, tuple, set)):
                            rd_exec_set = set(str(x).lower().strip() for x in rd_execs)
                        else:
                            rd_exec_set = {str(rd_execs).lower().strip()}
                        if ctx_exec_set == rd_exec_set:
                            return rcn
    except Exception:
        pass
    return None


def _is_rule_enabled_in_config(rule, enabled_rcns, whitelisted_rcns):
    """
    Validates whether a rule is enabled in rules.toml.
    - For non-repeater rules, if the rule is registered in Caster's whitelisted config
      but not present in _enabled_ordered, returns False.
    - Dynamic CCR RepeatRules check their underlying ccr_rule_class_name against _enabled_ordered.
    """
    rcn = getattr(rule, "ccr_rule_class_name", None)
    if not rcn:
        grammar = getattr(rule, "_grammar", None)
        if grammar:
            rcn = getattr(grammar, "ccr_rule_class_name", None)

    if not rcn:
        rcn = rule.__class__.__name__

    if enabled_rcns is not None:
        if rcn in enabled_rcns:
            return True
        if whitelisted_rcns is not None and rcn in whitelisted_rcns:
            return False
        if rcn.lower().startswith("repeater") or rcn == "RepeatRule":
            return True

    return True


def get_active_contextual_rules(target_process=None, target_title=None, target_hwnd=0):
    """
    Returns a list of active application-specific / contextual rule names.
    If target_process is not specified, retrieves the active desktop context from ADCE.
    If only global rules are active, returns an empty list [] (prompting [Global Context] on HUD).
    """
    contextual_rules = []
    seen = set()

    # Query ADCE if target_process is not explicitly supplied
    if not target_process:
        try:
            tracker = get_focus_tracker()
            if tracker and tracker.is_connected():
                ctx = tracker.get_current_context()
                adce_proc = ctx.get("process_name")
                if adce_proc:
                    target_process = adce_proc
                    if not target_title:
                        target_title = ctx.get("window_title")
        except Exception:
            pass

    proc_candidates = []
    if target_process:
        p_clean = str(target_process).lower().strip()
        proc_candidates.append(p_clean)
        if not p_clean.endswith(".exe"):
            proc_candidates.append(p_clean + ".exe")
        else:
            bare = p_clean[:-4]
            if bare and bare not in proc_candidates:
                proc_candidates.append(bare)

    proc_low = str(target_process or "").lower().strip()
    proc_bare = proc_low[:-4] if proc_low.endswith(".exe") else proc_low
    title_low = str(target_title or "").lower().strip()

    if proc_low in ("windowsterminal", "conhost", "cmd", "wt") or proc_bare in ("windowsterminal", "conhost", "cmd", "wt"):
        if "powershell" in title_low or "pwsh" in title_low:
            proc_candidates.extend(["powershell", "pwsh"])
    if (proc_low == "pwsh" or proc_bare == "pwsh") and "powershell" not in proc_candidates:
        proc_candidates.append("powershell")
    if (proc_low == "powershell" or proc_bare == "powershell") and "pwsh" not in proc_candidates:
        proc_candidates.append("pwsh")

    has_target = bool(target_process or (proc_candidates and proc_candidates != [""]))
    if not proc_candidates:
        proc_candidates.append("")

    enabled_rcns, whitelisted_rcns = _get_enabled_rule_classes()

    engine = get_current_engine()
    if engine and hasattr(engine, "grammars"):
        for grammar in engine.grammars:
            ctx = getattr(grammar, "context", None)
            if ctx is not None:
                # 1. Universal precision executable matching: prevents false substring prefix matches
                declared_execs = _extract_context_executables(ctx)
                if declared_execs and has_target:
                    if not _match_executable_precision(proc_candidates, declared_execs):
                        continue

                # 2. Dragonfly context evaluation (titles, dynamic FuncContext predicates)
                is_match = False
                for p in proc_candidates:
                    try:
                        if ctx.matches(p, target_title or "", target_hwnd or 0):
                            is_match = True
                            break
                    except Exception:
                        pass

                if not is_match and not has_target:
                    try:
                        from dragonfly import AppContext
                        if not isinstance(ctx, AppContext):
                            is_match = ctx.matches()
                    except Exception:
                        pass

                if is_match:
                    for rule in grammar.rules:
                        # 3. Authoritative rules.toml and active state validation
                        if not _is_rule_enabled_in_config(rule, enabled_rcns, whitelisted_rcns):
                            continue

                        r_name = str(rule.name).strip()
                        if r_name.lower().startswith("repeater") or r_name == "RepeatRule":
                            display = getattr(rule, "ccr_display_name", None)
                            if not display:
                                g = getattr(rule, "_grammar", None) or grammar
                                display = getattr(g, "ccr_display_name", None)

                            if not display:
                                rcn = getattr(rule, "ccr_rule_class_name", None)
                                if not rcn:
                                    g = getattr(rule, "_grammar", None) or grammar
                                    rcn = getattr(g, "ccr_rule_class_name", None)
                                if rcn:
                                    display = _format_rcn_display_name(rcn)

                            if not display:
                                resolved_rcn = _resolve_ccr_rcn_from_context(ctx)
                                if resolved_rcn:
                                    display = _format_rcn_display_name(resolved_rcn)

                            if display:
                                r_name = display
                            else:
                                continue

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


def show_hud_theme_dialog():
    """
    Open the interactive Theme Customizer and appearance settings dialog.
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.show_theme_dialog()
    except Exception as e:
        printer.out("Unable to show hud theme dialog. Hud not available. \n{}".format(e))


def set_hud_opacity(opacity=1.0):
    """
    Set HUD window transparency / opacity (0.1 to 1.0).
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.set_opacity(float(opacity))
    except Exception as e:
        printer.out("Unable to set hud opacity. Hud not available. \n{}".format(e))


def set_hud_background_opacity(opacity=1.0):
    """
    Set HUD background transparency / opacity (0.0 to 1.0).
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.set_background_opacity(float(opacity))
    except Exception as e:
        printer.out("Unable to set hud background opacity. Hud not available. \n{}".format(e))


def set_hud_letter_opacity(opacity=1.0):
    """
    Set HUD letter / text transparency / opacity (0.1 to 1.0).
    """
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.set_text_opacity(float(opacity))
    except Exception as e:
        printer.out("Unable to set hud letter opacity. Hud not available. \n{}".format(e))


def set_hud_text_alignment(alignment="left", hud_alignment=None):
    """
    Set HUD telemetry text alignment ('left' or 'right').
    """
    align = hud_alignment if hud_alignment is not None else alignment
    hud = control.nexus().comm.get_com("hud")
    try:
        hud.set_text_alignment(str(align))
    except Exception as e:
        printer.out("Unable to set hud text alignment. Hud not available. \n{}".format(e))


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