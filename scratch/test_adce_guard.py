"""
Test ADCE process-guard logic to prevent stale cross-window zone leakage.
"""

IDE_PROCESS_NAMES = frozenset(["code", "antigravity", "antigravity ide", "cursor", "windsurf", "vscodium"])

def mock_get_adce_context(target_process, adce_connected, adce_proc, adce_zone, adce_file):
    if not adce_connected:
        return {"is_connected": False, "semantic_zone": "", "process_name": "", "active_file": ""}
    
    target_clean = (target_process or "").lower().strip()
    adce_clean = (adce_proc or "").lower().strip()

    # Guard: process match check
    if not target_clean or target_clean == adce_clean or (target_clean in IDE_PROCESS_NAMES and adce_clean in IDE_PROCESS_NAMES):
        return {
            "is_connected": True,
            "semantic_zone": adce_zone,
            "process_name": adce_clean,
            "active_file": adce_file,
        }
    
    # Process mismatch -> suppress stale zone
    return {
        "is_connected": True,
        "semantic_zone": "",
        "process_name": target_clean,
        "active_file": "",
    }

# Case 1: In VS Code, ADCE is synced with VS Code
res1 = mock_get_adce_context("code", True, "code", "IntegratedTerminal", "main.py")
assert res1["semantic_zone"] == "IntegratedTerminal"
assert res1["active_file"] == "main.py"
print("Case 1 (In VS Code synced): PASS -> Zone:", res1["semantic_zone"])

# Case 2: Switched to Waterfox, but ADCE still has VS Code cached (race condition)
res2 = mock_get_adce_context("waterfox", True, "code", "IntegratedTerminal", "main.py")
assert res2["semantic_zone"] == ""
assert res2["active_file"] == ""
print("Case 2 (Switched to Waterfox, old ADCE cache guarded): PASS -> Zone:", repr(res2["semantic_zone"]))

# Case 3: In Antigravity IDE (alias of code)
res3 = mock_get_adce_context("antigravity", True, "code", "EditorCodeBuffer", "hud.py")
assert res3["semantic_zone"] == "EditorCodeBuffer"
print("Case 3 (IDE alias): PASS -> Zone:", res3["semantic_zone"])

# Case 4: ADCE Disconnected
res4 = mock_get_adce_context("code", False, "", "", "")
assert res4["is_connected"] == False
print("Case 4 (Disconnected): PASS")

print("\nAll ADCE process-guard assertions passed successfully!")
