from dragonfly import Grammar, MappingRule, Function

def toggle_grammar():
    print("\n>>> VOICE COMMAND FIRED: toggling grammar mid-phrase! <<<")
    print("Unloading trace_grammar...")
    grammar.unload()
    print("Loading trace_grammar...")
    grammar.load()
    print(">>> VOICE COMMAND ACTION FUNCTION FINISHED <<<\n")

class TraceRule(MappingRule):
    mapping = {
        "trigger test": Function(toggle_grammar),
    }

grammar = Grammar("trace_grammar")
grammar.add_rule(TraceRule())
grammar.load()
