"""
Diagnose PowerShell context matching and CCR extraction.
"""

from dragonfly import AppContext
from castervoice.asynch.hud_support import is_internal_rule_name

# 1. Test AppContext matching with different process and title combinations
ctx_ps = AppContext(executable="powershell")
ctx_pwsh = AppContext(executable="pwsh")
ctx_ps_title = AppContext(title="PowerShell")

print("AppContext('powershell') vs ('powershell', 'Windows PowerShell', 0):", 
      ctx_ps.matches("powershell", "Windows PowerShell", 0))

print("AppContext('powershell') vs ('windowsterminal', 'Windows PowerShell', 0):", 
      ctx_ps.matches("windowsterminal", "Windows PowerShell", 0))

print("AppContext('powershell') vs ('pwsh', 'pwsh', 0):", 
      ctx_ps.matches("pwsh", "pwsh", 0))

# 2. Test aliases normalization
def normalize_shell_process(proc, title):
    proc_low = (proc or "").lower().strip()
    title_low = (title or "").lower().strip()
    if proc_low in ("windowsterminal", "conhost", "cmd"):
        if "powershell" in title_low or "pwsh" in title_low:
            return "powershell"
    if proc_low == "pwsh":
        return "powershell"
    return proc_low

print("Normalized 'windowsterminal' with title 'Windows PowerShell':", 
      normalize_shell_process("windowsterminal", "Windows PowerShell"))
print("AppContext matching normalized process:", 
      ctx_ps.matches(normalize_shell_process("windowsterminal", "Windows PowerShell"), "Windows PowerShell", 0))
