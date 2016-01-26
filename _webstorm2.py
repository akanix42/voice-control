from dragonfly import (Grammar, AppContext, MappingRule, Dictation, Key, Text, Integer, Mimic)

print("webstorm")
webstorm = AppContext(executable = "WebStorm")
grammar = Grammar("Webstorm", context=(webstorm))

def insert_live_template(template):
    return Key("c-j") + Text(template) +  Key("enter")

rules = MappingRule(
    name = "javascript",
    mapping = {
        "run app": Key("c-f5"),
	    "if": insert_live_template("if"),
	    "pound": insert_live_template("if"),
    },

    extras = [
        Dictation("text", format=False),
        Integer("n", 1, 20000),
      ],
    defaults = {
      "n" : 1
      }
    )


#grammar.add_rule(rules)
#grammar.load()
def unload():
  global grammar
  if grammar: grammar.unload()
  grammar = None