"""
Test compound context matching (AppContext & FuncContext).
"""

from dragonfly import AppContext, FuncContext

is_term = True


def check_term(**kwargs):
    return is_term


ctx_compound = AppContext(executable=["code", "antigravity"]) & FuncContext(function=check_term)

print("Compound with is_term=True on 'code':", ctx_compound.matches("code", "Visual Studio Code", 100))
print("Compound with is_term=True on 'powershell':", ctx_compound.matches("powershell", "PowerShell", 100))

is_term = False
print("Compound with is_term=False on 'code':", ctx_compound.matches("code", "Visual Studio Code", 100))
