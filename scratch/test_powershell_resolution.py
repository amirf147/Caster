"""
Test full rule resolution with simulated Caster engine grammars.
"""

from dragonfly import Grammar, MappingRule, AppContext
from castervoice.lib.context import AppContext as CasterAppContext


class DummyRule(MappingRule):
    mapping = {"hello": None}


# 1. Simulate non-CCR Powershell rule
g_non_ccr = Grammar(name="g1", context=AppContext(executable="powershell"))
rule_non_ccr = DummyRule(name="Powershell")
g_non_ccr.add_rule(rule_non_ccr)

# 2. Simulate CCR Powershell rule
g_ccr = Grammar(name="ccr-3", context=AppContext(executable="PowerShell"))
rule_ccr = DummyRule(name="Repeater1")
g_ccr.add_rule(rule_ccr)

class DummyEngine(object):
    def __init__(self):
        self.grammars = [g_non_ccr, g_ccr]

engine = DummyEngine()

def extract_rules(target_proc, target_title, target_hwnd=0):
    rules = []
    seen = set()
    
    # Candidate process names for fuzzy terminal matching
    proc_candidates = [target_proc]
    proc_low = (target_proc or "").lower().strip()
    title_low = (target_title or "").lower().strip()
    if proc_low in ("windowsterminal", "conhost", "cmd", "wt"):
        if "powershell" in title_low or "pwsh" in title_low:
            proc_candidates.append("powershell")
            proc_candidates.append("pwsh")
    if proc_low == "pwsh":
        proc_candidates.append("powershell")
    if proc_low == "powershell":
        proc_candidates.append("pwsh")

    for grammar in engine.grammars:
        ctx = getattr(grammar, "context", None)
        if ctx is None:
            continue

        # Evaluate match across candidates
        is_match = False
        for p in proc_candidates:
            try:
                if ctx.matches(p, target_title or "", target_hwnd or 0):
                    is_match = True
                    break
            except Exception:
                pass
        
        if not is_match:
            try:
                is_match = ctx.matches()
            except Exception:
                pass

        if is_match:
            for rule in grammar.rules:
                r_name = str(rule.name).strip()
                # If rule name is a generic repeater, resolve from context executable
                if r_name.lower().startswith("repeater") or r_name == "RepeatRule":
                    execs = getattr(ctx, "_executable", None)
                    if execs and isinstance(execs, (list, tuple, set)) and len(execs) > 0:
                        r_name = str(list(execs)[0]).capitalize()
                
                # Check exclusion
                if r_name and not r_name.startswith('_') and not r_name.lower().startswith("repeater"):
                    if r_name not in seen:
                        seen.add(r_name)
                        rules.append(r_name)
    return rules

print("Resolving for ('powershell', 'Windows PowerShell'):", extract_rules("powershell", "Windows PowerShell"))
print("Resolving for ('windowsterminal', 'Administrator: Windows PowerShell'):", extract_rules("windowsterminal", "Administrator: Windows PowerShell"))
print("Resolving for ('pwsh', 'pwsh'):", extract_rules("pwsh", "pwsh"))
print("Resolving for ('code', 'main_window.py'):", extract_rules("code", "main_window.py"))
