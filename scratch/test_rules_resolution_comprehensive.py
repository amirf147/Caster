"""
Unit test for get_active_contextual_rules logic.
"""

from dragonfly import Grammar, MappingRule, AppContext
from castervoice.asynch.hud_support import is_internal_rule_name

class DummyRule(MappingRule):
    mapping = {"hello": None}

g_non_ccr = Grammar(name="g1", context=AppContext(executable="powershell"))
rule_non_ccr = DummyRule(name="Powershell")
g_non_ccr.add_rule(rule_non_ccr)

g_ccr = Grammar(name="ccr-3", context=AppContext(executable="PowerShell"))
rule_ccr = DummyRule(name="Repeater1")
g_ccr.add_rule(rule_ccr)

g_global_ccr = Grammar(name="ccr-0", context=None)
rule_global_ccr = DummyRule(name="Repeater0")
g_global_ccr.add_rule(rule_global_ccr)

class DummyEngine(object):
    def __init__(self):
        self.grammars = [g_non_ccr, g_ccr, g_global_ccr]

engine = DummyEngine()

def get_rules_test(target_process=None, target_title=None, target_hwnd=0):
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

    for grammar in engine.grammars:
        ctx = getattr(grammar, "context", None)
        if ctx is None:
            continue

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
                pass

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

assert get_rules_test("powershell", "Windows PowerShell") == ["Powershell"]
assert get_rules_test("windowsterminal", "Windows PowerShell") == ["Powershell"]
assert get_rules_test("pwsh", "pwsh") == ["Powershell"]
assert get_rules_test("element", "Element") == []
assert get_rules_test("explorer", "") == []
print("All test assertions passed successfully!")
