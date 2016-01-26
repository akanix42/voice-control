#
try:
    import pkg_resources
    pkg_resources.require("dragonfly >= 0.6.5beta1.dev-r99")
except ImportError:
    pass

import BaseHTTPServer
import Queue
import socket
import threading
import time
import urllib
import webbrowser
import win32clipboard

from dragonfly import *
import dragonfly.log
from selenium.webdriver.common.by import By

from _dragonfly_utils import *
from _text_utils import *
from _webdriver_utils import *

import _repeat

import _format

# Make sure dragonfly errors show up in NatLink messages.
dragonfly.log.setup_log()

def load(global_environment):
	config = Config("webstorm")
	namespace = config.load()

	def insert_live_template(template):
		return Key("c-j") + Text(template) +  Key("enter")

	webstorm_words_map = {
		"h t m l": Text("html")
	}
	webstorm_action_map = {
	    "run app": Key("c-f5"),
		"camel": Function(_format.camelCase)
	    # "dog": Key("c-f5"),


	}

	def new_file():
		return Key("a-insert")

	uiprefix = "ui "
	webstorm_ui_map = {
		"ui new spacebars file <text>": new_file() + Text("%(text)s.html") + Key("enter/5") + insert_live_template("temp:"),
		"ui new file <text>": new_file() + Text("%(text)s"),
		"ui new file": new_file()
	}

	def assign_var(text, text2):
		return "%(left)s = %(right)s;"

	webstorm_js_map = {
		"var": "var ",
		"const": "const ",
		"let": "let ",
		"var <text> equals <text2>": Text("var ") + Function(assign_var),
		"const <text> equals <text2>":  Text("const ") + Function(assign_var),
		"let <text> equals <text2>":  Text("let ") + Function(assign_var),

	    "if": insert_live_template("if"),
		"else if": insert_live_template("else if"),
		"for": insert_live_template("for"),
		"for each": insert_live_template("foreach"),
		"while": insert_live_template("while"),

	}

	webstorm_html_map = {
		"div": Text("<div>"),
		"u l": Text("<ul>"),
		"oh ell": Text("<ol>"),
		"l i": Text("<li>"),

	    "if": insert_live_template("#if"),
		"each": insert_live_template("#each"),
		"else": Text("{else}"),
		"unless": insert_live_template("#unless"),
	}

	webstorm_element_map = {
		"dictation": Dictation(),
		"text": Dictation(),
		"text2": Dictation(),
	}


	webstorm = AppContext(executable = "WebStorm")
	grammar = Grammar("Webstorm", context=(webstorm))

	webstorm_environment = _repeat.Environment(name="WebStorm",
								       parent=global_environment,
									   context=AppContext(executable = "WebStorm"),
									   action_map=combine_maps(webstorm_words_map, webstorm_action_map, webstorm_ui_map),
									   element_map=webstorm_element_map)

	webstorm_html_environment = _repeat.Environment(name="WebStorm html",
									   parent=webstorm_environment,
									   context=AppContext(title = ".html"),
									   action_map=webstorm_html_map)

	webstorm_js_environment = _repeat.Environment(name="WebStorm js",
									   parent=webstorm_environment,
									   context=AppContext(title = ".js"),
									   action_map=webstorm_js_map)


	return global_environment