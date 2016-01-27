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

import _phonetics

# Make sure dragonfly errors show up in NatLink messages.
dragonfly.log.setup_log()
print ""


def load(global_environment):
    config = Config("webstorm")
    namespace = config.load()

    def insert_live_template(template):
        return Key("c-j") + Text(template) + Key("enter")

    webstorm_words_map = {
        "h t m l": Text("html")
    }
    webstorm_action_map = {
        "run app": Key("c-f5"),
        "camel": Function(_format.camelCase),
        "search project": Key("shift, shift"),
        "search files": Key("cs-n"),
    }

    def new_file():
        return Key("a-insert")

    uiprefix = "ui "
    webstorm_ui_map = {
        "guy new spacebars file <text>": new_file() + Text("%(text)s.html") + Key("enter/5")
                                         + insert_live_template("temp:"),
        "guy new file <text>": new_file() + Text("%(text)s"),
        "guy new file": new_file(),
        "guy new project": Key("a-f, j"),
        "guy file menu": Key("a-f"),
        "guy edit menu": Key("a-e"),
        "guy view menu": Key("a-v"),
        "guy code menu": Key("a-c"),
        "guy refactor menu": Key("a-r"),
        "guy run menu": Key("a-u"),
        "guy tools menu": Key("a-t"),
        "guy vcs menu": Key("a-s"),
        "guy window menu": Key("a-w"),
        "guy help menu": Key("a-h"),
        "guy terminal": Key("a-f12"),
        "guy settings": Key("ca-s"),
        "guy save all": Key("c-s"),
        "guy save as": Key("cs-s"),
        "guy select in": Key("a-f1"),
        "guy recent files": Key("c-e"),
        "guy recent changed files": Key("cs-e"),

    }

    def new_line(position):
        return Key("home, enter, home")

    webstorm_editor_map = combine_maps(dict([
        ("format code", Key("a-f8")),
        ("format file", Key("cas-l")),

    ]), {
        "line up [<n>]": Key("as-up/5:%(n)d"),
        "line down [<n>]": Key("as-down/5:%(n)d"),
        "statement up [<n>]": Key("cs-up/5:%(n)d"),
        "statement down [<n>]": Key("cs-down/5:%(n)d"),
        "join lines": Key("cs-j"),
        "refactor this": Key("cas-t"),
        "paste simple": Key("cas-v"),
        "paste [from] history": Key("cs-v"),
        "extend selection": Key("c-w"),
        "shrink selection": Key("cs-w"),
        "go to declaration": Key("c-b"),
        "go to (usage | implementations)": Key("ca-b"),
        "go to previous problem": Key("ca-up"),
        "go to next problem": Key("ca-down"),
        "go to next method": Key("a-down"),
        "go to previous method": Key("a-up"),
        "go next error": Key("f2"),
        "go previous error": Key("s-f2"),
        "surround with": Key("ca-t"),
        "block end": Key("c-rbracket"),
        "block start": Key("c-lbracket"),
        "select block end": Key("cs-rbracket"),
        "select block start": Key("cs-lbracket"),
        "dupe | doop": Key("c-d"),
        "comment": Key("c-slash"),
        "comment block": Key("cs-slash"),
        "auto complete": Key("c-space"),
        "finish statement": Key("cs-enter"),
        "unshuck": Key("cs-z"),
    })

    webstorm_editor_elements = {
        "new_line_position": ListRef(None, List("new_line_positions", ["above", "below"]))
    }

    def assign_var(text, text2):
        return "%(left)s = %(right)s;"

    def declare_var(declaration, varName=""):
        Text("{declaration} {varName}".format(declaration=declaration, varName=varName)).execute()

    webstorm_js_map = {
        "<declaration> [<varName>]": Function(declare_var),
        # "var [<varName>]": Text("var %(varName)s"),
        # "const": Text("const "),
        # "let": Text("let "),
        "var <text> equals <text2>": Text("var ") + Function(assign_var),
        "const <text> equals <text2>": Text("const ") + Function(assign_var),
        "let <text> equals <text2>": Text("let ") + Function(assign_var),

        "if": insert_live_template("if"),
        "else if": insert_live_template("else if"),
        "for": insert_live_template("for"),
        "for each": insert_live_template("foreach"),
        "while": insert_live_template("while"),

    }

    webstorm_html_map = dict([
        ("div", Text("<div>")),
        (_phonetics.convert_to_phonetics("ul"), Text("<ul")),
        (_phonetics.convert_to_phonetics("ol"), Text("<ol")),
        (_phonetics.convert_to_phonetics("li"), Text("<li")),
        (_phonetics.convert_to_phonetics("br"), Text("<br")),
        (_phonetics.convert_to_phonetics("id"), Text("id")),
        ("equals", Text("=")),
        ("pound", Text("####")),
        ("if", insert_live_template("#if")),
        ("each", insert_live_template("#each")),
        ("else", Text("{else}")),
        ("unless", insert_live_template("#unless")),
    ])

    webstorm_element_map = {
        "dictation": Dictation(),
        "text": Dictation(),
        "text2": Dictation(),
        "varName": Dictation(),
        "declaration": ListRef(None, List("declaration", ["var", "let", "const"]))
    }

    webstorm = AppContext(executable="WebStorm")
    grammar = Grammar("Webstorm", context=(webstorm))

    webstorm_environment = _repeat.Environment(name="WebStorm",
                                               parent=global_environment,
                                               context=AppContext(executable="WebStorm"),
                                               action_map=combine_maps(webstorm_words_map, webstorm_action_map,
                                                                       webstorm_ui_map,
                                                                       webstorm_editor_map),
                                               element_map=webstorm_element_map)

    webstorm_html_environment = _repeat.Environment(name="WebStorm html",
                                                    parent=webstorm_environment,
                                                    context=AppContext(title=".html"),
                                                    action_map=webstorm_html_map,
                                                    element_map=webstorm_element_map)

    webstorm_js_environment = _repeat.Environment(name="WebStorm js",
                                                  parent=webstorm_environment,
                                                  context=AppContext(title=".js"),
                                                  action_map=webstorm_js_map)

    return global_environment
