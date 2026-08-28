"""
Test rule extraction for global and contextual rules in Caster.
"""

from castervoice.asynch.hud_support import is_internal_rule_name

# Test sample rule names
test_names = [
    "Repeater1",
    "Repeater2",
    "PreparedRule",
    "RepeatRule",
    "ccr",
    "_smr_mapping",
    "g1",
    "g12",
    "caster_rule",
    "navigation",
    "window_mgmt",
    "vs code",
    "ide_terminal",
    "gemini",
    "chrome",
]

print("Filtering results:")
for name in test_names:
    internal = is_internal_rule_name(name)
    print("  Rule: %-15s -> Filtered Out: %s" % (name, internal))
