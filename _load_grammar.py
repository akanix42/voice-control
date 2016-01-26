import dragonfly

import _repeat
import _webstorm

print "loading"
# print ""
global_environment = _repeat.load()
global_environment = _webstorm.load(global_environment)

grammar = dragonfly.Grammar("repeat")
global_environment.install(grammar)
grammar.load()

print "loaded grammar"

def unload():
	_repeat.unload()