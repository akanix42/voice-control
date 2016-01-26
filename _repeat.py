﻿#
# This file is a command-module for Dragonfly.
# (c) Copyright 2008 by Christo Butcher
# (c) Copyright 2015 by James Stout
# Licensed under the LGPL, see <http://www.gnu.org/licenses/>
#

"""
This contains all commands which may be spoken continuously or repeated.

This is heavily modified from _multiedit.py, found here:
https://code.google.com/p/dragonfly-modules/

"""

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
from _eye_tracker_utils import *
from _linux_utils import *
from _text_utils import *
from _webdriver_utils import *

# Load local hooks if defined.
try:
    import _dragonfly_local_hooks as local_hooks
    def RunLocalHook(name, *args, **kwargs):
        """Function to run local hook if defined."""
        try:
            hook = getattr(local_hooks, name)
            return hook(*args, **kwargs)
        except AttributeError:
            pass
except:
    print("Local hooks not loaded.")
    def RunLocalHook(name, *args, **kwargs):
        pass


# Make sure dragonfly errors show up in NatLink messages.
dragonfly.log.setup_log()

grammar = None
global_environment = None
print "repeat loaded"

# Load _repeat.txt.
config = Config("repeat")
namespace = config.load()

#-------------------------------------------------------------------------------
# Common maps and lists.
symbol_map = {
    "plus": " + ",
    "dub plus": "++",
    "minus": " - ",
    "nad": ", ",
    "coal": ":",
    "equals": " = ",
    "dub equals": " == ",
    "not equals": " != ",
    "increment by": " += ",
    "greater than": " > ",
    "less than": " < ",
    "greater equals": " >= ",
    "less equals": " <= ",
    "dot": ".",
    "leap": "(",
    "reap": ")",
    "lake": "{",
    "rake": "}",
    "lobe": "[",
    "robe": "]",
    "luke": "<",
    "dub luke": " << ",
    "ruke": ">",
    "quote": "\"",
    "dash": "-",
    "semi": ";",
    "bang": "!",
    "percent": "%",
    "star": "*",
    "backslash": "\\",
    "slash": "/",
    "tilde": "~",
    "underscore": "_",
    "sick quote": "'",
    "dollar": "$",
    "carrot": "^",
    "arrow": "->",
    "fat arrow": "=>",
    "dub coal": "::",
    "amper": "&",
    "dub amper": " && ",
    "pipe": "|",
    "dub pipe": " || ",
    "hash": "#",
    "at symbol": "@",
    "question": "?",
}

numbers_map = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "point": ".",
    "minus": "-",
    "slash": "/",
    "coal": ":",
    "nad": ",",
}

short_letters_map = {
    "A": "a",
    "B": "b",
    "C": "c",
    "D": "d",
    "E": "e",
    "F": "f",
    "G": "g",
    "H": "h",
    "I": "i",
    "J": "j",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "O": "o",
    "P": "p",
    "Q": "q",
    "R": "r",
    "S": "s",
    "T": "t",
    "U": "u",
    "V": "v",
    "W": "w",
    "X": "x",
    "Y": "y",
    "Z": "z",
}

quick_letters_map = {
    "arch": "a",
    "brov": "b",
    "chair": "c",
    "dell": "d",
    "etch": "e",
    "fomp": "f",
    "goof": "g",
    "hark": "h",
    "ice": "i",
    "jinks": "j",
    "koop": "k",
    "lug": "l",
    "mowsh": "m",
    "nerb": "n",
    "ork": "o",
    "pooch": "p",
    "quash": "q",
    "rosh": "r",
    "souk": "s",
    "teek": "t",
    "unks": "u",
    "verge": "v",
    "womp": "w",
    "trex": "x",
    "yang": "y",
    "zooch": "z",
}

long_letters_map = {
    "alpha": "a",
    "bravo": "b",
    "charlie": "c",
    "delta": "d",
    "echo": "e",
    "foxtrot": "f",
    "golf": "g",
    "hotel": "h",
    "india": "i",
    "juliet": "j",
    "kilo": "k",
    "lima": "l",
    "mike": "m",
    "november": "n",
    "oscar": "o",
    "poppa": "p",
    "quebec": "q",
    "romeo": "r",
    "sierra": "s",
    "tango": "t",
    "uniform": "u",
    "victor": "v",
    "whiskey": "w",
    "x-ray": "x",
    "yankee": "y",
    "zulu": "z",
    "dot": ".",
}

prefixes = [
    "num",
    "min",
]

suffixes = [
    "bytes",
]

letters_map = combine_maps(quick_letters_map, long_letters_map)

char_map = dict((k, v.strip()) for (k, v) in combine_maps(letters_map, numbers_map, symbol_map).iteritems())
# Here we prepare the action map of formatting functions from the config file.
# Retrieve text-formatting functions from this module's config file. Each of
# these functions must have a name that starts with "format_".
format_functions = {}
if namespace:
    for name, function in namespace.items():
        if name.startswith("format_") and callable(function):
            spoken_form = function.__doc__.strip()

            # We wrap generation of the Function action in a function so
            #  that its *function* variable will be local.  Otherwise it
            #  would change during the next iteration of the namespace loop.
            def wrap_function(function):
                def _function(dictation):
                    formatted_text = function(dictation)
                    Text(formatted_text).execute()
                return Function(_function)

            action = wrap_function(function)
            format_functions[spoken_form] = action


#-------------------------------------------------------------------------------
# Simple elements that may be referred to within a rule.

numbers_dict_list  = DictList("numbers_dict_list", numbers_map)
letters_dict_list = DictList("letters_dict_list", letters_map)
char_dict_list = DictList("char_dict_list", char_map)

# Load commonly misrecognized words saved to a file.
saved_words = []
try:
    with open(WORDS_PATH) as file:
        for line in file:
            word = line.strip()
            if len(word) > 2 and word not in letters_map:
                saved_words.append(line.strip())
except:
    print("Unable to open: " + WORDS_PATH)

saved_word_list = List("saved_word_list", saved_words)
# Lists which will be populated later via RPC.
context_phrase_list = List("context_phrase_list", [])
context_word_list = List("context_word_list", [])
prefix_list = List("prefix_list", prefixes)
suffix_list = List("suffix_list", suffixes)

# Dictation consisting of sources of contextually likely words.
custom_dictation = RuleWrap(None, Alternative([
    ListRef(None, saved_word_list),
    ListRef(None, context_phrase_list),
]))

# Either arbitrary dictation or letters.
mixed_dictation = RuleWrap(None, JoinedSequence(" ", [
    Optional(ListRef(None, prefix_list)),
    Alternative([
        Dictation(),
        DictListRef(None, letters_dict_list),
        ListRef(None, saved_word_list),
    ]),
    Optional(ListRef(None, suffix_list))]))

# A sequence of either short letters or long letters.
letters_element = RuleWrap(None, JoinedRepetition("", DictListRef(None, letters_dict_list), min = 1, max = 10))

# A sequence of numbers.
numbers_element = RuleWrap(None, JoinedRepetition("", DictListRef(None, numbers_dict_list), min = 0, max = 10))

# A sequence of characters.
chars_element = RuleWrap(None, JoinedRepetition("", DictListRef(None, char_dict_list), min = 0, max = 10))

# Simple element map corresponding to keystroke action maps from earlier.
keystroke_element_map = {
    "n": (IntegerRef(None, 1, 21), 1),
    "text": Dictation(),
    "char": DictListRef(None, char_dict_list),
}

#-------------------------------------------------------------------------------
# Rules which we will refer to within other rules.

# Rule for formatting mixed_dictation elements.
format_rule = create_rule(
    "FormatRule",
    format_functions,
    {"dictation": mixed_dictation}
)

# Rule for formatting pure dictation elements.
pure_format_rule = create_rule(
    "PureFormatRule",
    dict([("pure " + k, v)
          for (k, v) in format_functions.items()]),
    {"dictation": Dictation()}
)

# Rule for formatting custom_dictation elements.
custom_format_rule = create_rule(
    "CustomFormatRule",
    dict([("my " + k, v)
          for (k, v) in format_functions.items()]),
    {"dictation": custom_dictation}
)

release = Key("shift:up, ctrl:up, alt:up")

# Rule for handling raw dictation.
dictation_rule = create_rule(
    "DictationRule",
    {
        "mimic text <text>": release + Text("%(text)s"),
        "mimic <text>": release + Mimic(extra="text"),
    },
    {
        "text": Dictation()
    }
)


# Actions for speaking out sequences of characters.
character_action_map = {
    "plain <chars>": Text("%(chars)s"),
    "numbers <numerals>": Text("%(numerals)s"),
    "print <letters>": Text("%(letters)s"),
    "shout <letters>": Function(lambda letters: Text(letters.upper()).execute()),
}

# Rule for printing single characters.
single_character_rule = create_rule(
    "SingleCharacterRule",
    character_action_map,
    {
        "numerals": DictListRef(None, numbers_dict_list),
        "letters": DictListRef(None, letters_dict_list),
        "chars": DictListRef(None, char_dict_list),
    }
)

# Rule for spelling a word letter by letter and formatting it.
spell_format_rule = create_rule(
    "SpellFormatRule",
    dict([("spell " + k, v)
          for (k, v) in format_functions.items()]),
    {"dictation": letters_element}
)

# Rule for printing a sequence of characters.
character_rule = create_rule(
    "CharacterRule",
    character_action_map,
    {
        "numerals": numbers_element,
        "letters": letters_element,
        "chars": chars_element,
    }
)

#-------------------------------------------------------------------------------
# Action maps to be used in rules.

# Key actions which may be used anywhere in any command.
global_key_action_map = {
    "slap [<n>]": Key("enter/5:%(n)d"),
    "pat [<n>]": Key("space/5:%(n)d"),
    "tab [<n>]": Key("tab/5:%(n)d"),
}

# Actions of commonly used text navigation and mousing commands. These can be
# used anywhere except after commands which include arbitrary dictation.
key_action_map = {
    "up [<n>]":                         Key("up/5:%(n)d"),
    "down [<n>]":                       Key("down/5:%(n)d"),
    "left [<n>]":                       Key("left/5:%(n)d"),
    "right [<n>]":                      Key("right/5:%(n)d"),
    "fomble [<n>]": Key("c-right/5:%(n)d"),
    "bamble [<n>]": Key("c-left/5:%(n)d"),
    "dumbbell [<n>]": Key("c-backspace/5:%(n)d"),
    "kimble [<n>]": Key("c-del/5:%(n)d"),
    "dird [<n>]": Key("a-backspace/5:%(n)d"),
    "kill [<n>]": Key("c-k/5:%(n)d"),
    "pup [<n>]":                        Key("pgup/5:%(n)d"),
    "pown [<n>]":                       Key("pgdown/5:%(n)d"),
    "up <n> (page | pages)":            Key("pgup/5:%(n)d"),
    "down <n> (page | pages)":          Key("pgdown/5:%(n)d"),
    "left <n> (word | words)":          Key("c-left/5:%(n)d"),
    "right <n> (word | words)":         Key("c-right/5:%(n)d"),
    "west":                             Key("home"),
    "east":                              Key("end"),
    "north":                            Key("c-home"),
    "south":                           Key("c-end"),
    "yankee|yang":                           Key("y"),
    "november|nerb":                           Key("n"),

    "crack [<n>]":                     release + Key("del/5:%(n)d"),
    "delete [<n> | this] (line|lines)": release + Key("home, s-down/5:%(n)d, del"),
    "snap [<n>]":                  release + Key("backspace/5:%(n)d"),
    "pop up":                           release + Key("apps"),
    "cancel|escape":                             release + Key("escape"),
    "(volume|audio|turn it) up": Key("volumeup"),
    "(volume|audio|turn it) down": Key("volumedown"),
    "(volume|audio) mute": Key("volumemute"),
    "next track": Key("tracknext"),
    "prev track": Key("trackprev"),
    "play pause|pause play": Key("playpause"),

    "paste":                            release + Key("c-v"),
    "copy":                             release + Key("c-c"),
    "cut":                              release + Key("c-x"),
    "shuck":                              release + Key("c-z"),
    "select everything":                       release + Key("c-a"),
    "template": Key("c-j") + Text("if") + Key("enter"),
   # "edit text": RunApp("notepad"),
   # "edit emacs": RunEmacs(".txt"),
   # "edit everything": Key("c-a, c-x") + RunApp("notepad") + Key("c-v"),
   # "edit region": Key("c-x") + RunApp("notepad") + Key("c-v"),
    "[hold] shift":                     Key("shift:down"),
    "release shift":                    Key("shift:up"),
    "[hold] control":                   Key("ctrl:down"),
    "release control":                  Key("ctrl:up"),
    "[hold] (meta|alt)":                   Key("alt:down"),
    "release (meta|alt)":                  Key("alt:up"),
    "release [all]":                    release,
    "do double shift": Key("shift:2"),

    "(I|eye) connect": Function(connect),
    "(I|eye) disconnect": Function(disconnect),
    "(I|eye) print position": Function(print_position),
    "(I|eye) move": Function(move_to_position),
    "(I|eye) click": Function(move_to_position) + Mouse("left"),
    "(I|eye) act": Function(activate_position),
    "(I|eye) pan": Function(panning_step_position),
    "(I|eye) right click": Function(move_to_position) + Mouse("right"),
    "(I|eye) middle click": Function(move_to_position) + Mouse("middle"),
    "(I|eye) double click": Function(move_to_position) + Mouse("left:2"),
    "(I|eye) triple click": Function(move_to_position) + Mouse("left:3"),
    "(I|eye) start drag": Function(move_to_position) + Mouse("left:down"),
    "(I|eye) stop drag": Function(move_to_position) + Mouse("left:up"),
    "do click": Mouse("left"),
    "do right click": Mouse("right"),
    "do middle click": Mouse("middle"),
    "do double click": Mouse("left:2"),
    "do triple click": Mouse("left:3"),
    "do start drag": Mouse("left:down"),
    "do stop drag": Mouse("left:up"),

    "create driver": Function(create_driver),
    "quit driver": Function(quit_driver),

    "win <n>": Key("w-%(n)d")
}

# Actions that can be used anywhere in any command.
global_action_map = combine_maps(global_key_action_map,
                                 text_map_to_action_map(symbol_map))

# Actions that can be used anywhere except after a command with arbitrary
# dictation.
command_action_map = combine_maps(global_action_map, key_action_map)

#-------------------------------------------------------------------------------
# Elements that are composed of rules. Note that the value of these elements are
# actions which will have to be triggered manually.

# Element matching simple commands.
# For efficiency, this should not contain any repeating elements.
single_action = RuleRef(rule=create_rule("CommandKeystrokeRule",
                                         command_action_map,
                                         keystroke_element_map))

# Element matching dictation and commands allowed at the end of an utterance.
# For efficiency, this should not contain any repeating elements. For accuracy,
# few custom commands should be included to avoid clashes with dictation
# elements.
dictation_element = RuleWrap(None, Alternative([
    RuleRef(rule=dictation_rule),
    RuleRef(rule=format_rule),
    RuleRef(rule=pure_format_rule),
    RuleRef(rule=custom_format_rule),
    RuleRef(rule=create_rule("DictationKeystrokeRule",
                             global_action_map,
                             keystroke_element_map)),
    RuleRef(rule=single_character_rule),
]))

#---------------------------------------------------------------------------
# Here we define the top-level rule which the user can say.

# This is the rule that actually handles recognitions.
#  When a recognition occurs, its _process_recognition()
#  method will be called.  It receives information about the
#  recognition in the "extras" argument: the sequence of
#  actions and the number of times to repeat them.
class RepeatRule(CompoundRule):
    def __init__(self, name, command, terminal_command, context):
        # Here we define this rule's spoken-form and special elements. Note that
        # nested_repetitions is the only one that contains Repetitions, and it
        # is not itself repeated. This is for performance purposes. We also
        # include a special escape command "terminal <dictation>" in case
        # recognition problems occur with repeated dictation commands.
        spec     = "[<sequence>] [<nested_repetitions>] ([<dictation_sequence>] [terminal <dictation>] | <terminal_command>) [[[and] repeat [that]] <n> times]"
        extras   = [
            Repetition(command, min=1, max = 5, name="sequence"),
            Alternative([RuleRef(rule=character_rule), RuleRef(rule=spell_format_rule)],
                        name="nested_repetitions"),
            Repetition(dictation_element, min = 1, max = 5, name = "dictation_sequence"),
            ElementWrapper("dictation", dictation_element),
            ElementWrapper("terminal_command", terminal_command),
            IntegerRef("n", 1, 100),  # Times to repeat the sequence.
        ]
        defaults = {
            "n": 1,                   # Default repeat count.
            "sequence": [],
            "nested_repetitions": None,
            "dictation_sequence": [],
            "dictation": None,
            "terminal_command": None,
        }

        CompoundRule.__init__(self, name=name, spec=spec,
                              extras=extras, defaults=defaults, exported=True, context=context)

    # This method gets called when this rule is recognized.
    # Arguments:
    #  - node -- root node of the recognition parse tree.
    #  - extras -- dict of the "extras" special elements:
    #     . extras["sequence"] gives the sequence of actions.
    #     . extras["n"] gives the repeat count.
    def _process_recognition(self, node, extras):
        sequence = extras["sequence"]   # A sequence of actions.
        nested_repetitions = extras["nested_repetitions"]
        dictation_sequence = extras["dictation_sequence"]
        dictation = extras["dictation"]
        terminal_command = extras["terminal_command"]
        count = extras["n"]             # An integer repeat count.
        for i in range(count):
            for action in sequence:
                action.execute()
                Pause("5").execute()
            if nested_repetitions:
                nested_repetitions.execute()
            for action in dictation_sequence:
                action.execute()
                Pause("5").execute()
            if dictation:
                dictation.execute()
            if terminal_command:
                terminal_command.execute()
        release.execute()

class Environment(object):
    """Environment where voice commands can be spoken. Combines grammar and
    context and adds hierarchy. When installed, will produce a top-level rule
    for each environment."""

    def __init__(self,
                 name,
                 parent=None,
                 context=None,
                 action_map=None,
                 terminal_action_map=None,
                 element_map=None):
        self.name = name
        self.children = []
        if parent:
            parent.add_child(self)
            self.context = combine_contexts(parent.context, context)
            self.action_map = combine_maps(parent.action_map, action_map)
            self.terminal_action_map = combine_maps(parent.terminal_action_map, terminal_action_map)
            self.element_map = combine_maps(parent.element_map, element_map)
        else:
            self.context = context
            self.action_map = action_map if action_map else {}
            self.terminal_action_map = terminal_action_map if terminal_action_map else {}
            self.element_map = element_map if element_map else {}

    def add_child(self, child):
        self.children.append(child)

    def install(self, grammar):
        exclusive_context = self.context
        for child in self.children:
            child.install(grammar)
            exclusive_context = combine_contexts(exclusive_context, ~child.context)
        if self.action_map:
            element = RuleRef(rule=create_rule(self.name + "KeystrokeRule",
                                               self.action_map,
                                               self.element_map))
        else:
            element = Empty()
        if self.terminal_action_map:
            terminal_element = RuleRef(rule=create_rule(self.name + "TerminalRule",
                                                        self.terminal_action_map,
                                                        self.element_map))
        else:
            terminal_element = Empty()
        self.rule = RepeatRule(self.name + "RepeatRule",
                                    element,
                                    terminal_element,
                                    exclusive_context)
        grammar.add_rule(self.rule)


def load():



    
    #-------------------------------------------------------------------------------
    # Define top-level rules for different contexts. Note that Dragon only allows
    # top-level rules to be context-specific, but we want control over sub-rules. To
    # work around this limitation, we compile a mutually exclusive top-level rule
    # for each context.

    
    global_environment = Environment(name="Global",
                                     action_map=command_action_map,
                                     element_map=keystroke_element_map)

    shell_command_map = combine_maps({
        "git commit": Text("git commit -am "),
        "git commit done": Text("git commit -am done "),
        "git checkout new": Text("git checkout -b "),
        "git reset hard head": Text("git reset --hard HEAD "),
        "(soft|sym) link": Text("ln -s "),
        "list": Text("ls -l "),
        "make dir": Text("mkdir "),
        "ps all": Text("ps aux "),
        "kill command": Text("kill "),
        "echo command": Text("echo "),
        "CH mod": Text("chmod "),
        "TK diff": Text("tkdiff "),
        "MV": Text("mv "),
        "CP": Text("cp "),
        "RM": Text("rm "),
        "CD": Text("cd "),
        "LS": Text("ls "),
        "PS": Text("ps "),
        "reset terminal": Text("exec bash\n"),
        "pseudo": Text("sudo "),
        "apt get": Text("apt-get "),
    }, dict((command, Text(command + " ")) for command in [
        "grep",
        "ssh",
        "diff",
        "cat",
        "man",
        "less",
        "git status",
        "git branch",
        "git diff",
        "git checkout",
        "git stash",
        "git stash pop",
        "git push",
        "git pull",
    ]))
    RunLocalHook("AddShellCommands", shell_command_map)


    def Exec(command):
        return Key("c-c, a-x") + Text(command) + Key("enter")

    # Work in progress.
    def FastExec(command):
        return Function(lambda: urllib.urlopen("http://127.0.0.1:9091/" + command).close())

    def jump_to_line(line_string):
        return Key("c-u") + Text(line_string) + Key("c-c, c, g")

    class OpenClipboardUrlAction(ActionBase):
        def _execute(self, data=None):
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            print "Opening link: %s" % data
            webbrowser.open(data)

    class MarkLinesAction(ActionBase):
        def __init__(self, tight=False):
            super(MarkLinesAction, self).__init__()
            self.tight = tight

        def _execute(self, data=None):
            jump_to_line("%(n1)d" % data).execute()
            if self.tight:
                Key("a-m").execute()
            Key("c-space").execute()
            if "n2" in data:
                jump_to_line("%d" % (data["n2"])).execute()
            if self.tight:
                Key("c-e").execute()
            else:
                Key("down").execute()

    class UseLinesAction(ActionBase):
        def __init__(self, pre_action, post_action, tight=False):
            super(UseLinesAction, self).__init__()
            self.pre_action = pre_action
            self.post_action = post_action
            self.tight = tight

        def _execute(self, data=None):
            # Set mark without activating.
            Key("c-backtick").execute()
            MarkLinesAction(self.tight).execute(data)
            self.pre_action.execute(data)
            # Jump to mark twice then to the beginning of the line.
            (Key("c-langle") + Key("c-langle")).execute()
            if not self.tight:
                Key("c-a").execute()
            self.post_action.execute(data)

   
    templates = {
        "beginend": "beginend",
        "car": "car",
        "class": "class",
        "const ref": "const_ref",
        "const pointer": "const_pointer",
        "def": "function",
        "each": "each",
        "else": "else",
        "entry": "entry",
        "error": "error",
        "eval": "eval",
        "fatal": "fatal",
        "for": "for",
        "fun declaration": "fun_declaration",
        "function": "function",
        "if": "if",
        "info": "info",
        "inverse if": "inverse_if",
        "key": "key",
        "method": "method",
        "ref": "ref",
        "ternary": "ternary",
        "text": "text",
        "to do": "todo",
        "unique pointer": "unique_pointer",
        "var": "vardef",
        "warning": "warning",
        "while": "while",
    }
    template_dict_list = DictList("template_dict_list", templates)
    # emacs_element_map = {
    #     "n1": IntegerRef(None, 0, 100),
    #     "n2": IntegerRef(None, 0, 100),
    #     "line": IntegerRef(None, 1, 10000),
    #     "template": DictListRef(None, template_dict_list),
    #     "context_word": ListRef(None, context_word_list),
    # }

    # emacs_environment = Environment(name="Emacs",
    #                                 parent=global_environment,
    #                                 context=UniversalAppContext(title = "Emacs editor"),
    #                                 action_map=emacs_action_map,
    #                                 element_map=emacs_element_map)

    # emacs_python_action_map = {
    #     "[python] indent": Key("c-c, rangle"),
    #     "[python] dedent": Key("c-c, langle"),
    # }
    # emacs_python_environment = Environment(name="EmacsPython",
    #                                        parent=emacs_environment,
    #                                        context=UniversalAppContext(title="- Python -"),
    #                                        action_map=emacs_python_action_map)


    # emacs_org_action_map = {
    #     "[new] heading": Key("c-e, a-enter"),
    #     "subheading": Key("c-e, a-enter, a-right"),
    #     "toggle heading": Key("c-c, asterisk"),
    #     "to do": Key("c-1, c-c, c-t"),
    #     "done": Key("c-2, c-c, c-t"),
    #     "clear to do": Key("c-3, c-c, c-t"),
    #     "indent tree": Key("as-right"),
    #     "indent": Key("a-right"),
    #     "dedent tree": Key("as-left"),
    #     "dedent": Key("a-left"),
    #     "move tree down": Key("as-down"),
    #     "move tree up": Key("as-up"),
    #     "open org link": Key("c-c, c-o"),
    #     "show to do's": Key("c-c, slash, t"),
    #     "archive": Key("c-c, c-x, c-a"),
    #     "org (West|white)": Key("c-c, c, c-a"),
    # }
    # emacs_org_environment = Environment(name="EmacsOrg",
    #                                     parent=emacs_environment,
    #                                     context=UniversalAppContext(title="- Org -"),
    #                                     action_map=emacs_org_action_map)


    # emacs_shell_action_map = combine_maps(
    #     shell_command_map,
    #     {
    #         "shell (preev|back)": Key("a-r"),
    #         "show output": Key("c-c, c-r"),
    #     })
    # emacs_shell_environment = Environment(name="EmacsShell",
    #                                       parent=emacs_environment,
    #                                       context=UniversalAppContext(title="- Shell -"),
    #                                       action_map=emacs_shell_action_map)


    shell_action_map = combine_maps(
        shell_command_map,
        {
            "copy": Key("cs-c"),
            "paste": Key("cs-v"),
            "cut": Key("cs-x"),
            "top [<n>]": Key("s-pgup/5:%(n)d"),
            "pown [<n>]": Key("s-pgdown/5:%(n)d"),
            "crack [<n>]": Key("c-d/5:%(n)d"),
            "pret [<n>]": Key("cs-left/5:%(n)d"),
            "net [<n>]": Key("cs-right/5:%(n)d"),
            "move tab left [<n>]": Key("cs-pgup/5:%(n)d"),
            "move tab right [<n>]": Key("cs-pgdown/5:%(n)d"),
            "shot <tab_n>": Key("a-%(tab_n)d"),
            "shot last": Key("a-1, cs-left"),
            "(prev|preev|back)": Key("c-r"),
            "(next|frack)": Key("c-s"),
            "(nope|no way)": Key("c-g"),
            "new tab": Key("cs-t"),
            "clote": Key("cs-w"),
            "forward": Key("f"),
            "backward": Key("b"),
            "quit": Key("q"),
            "kill process": Key("c-c"),
        })

    shell_element_map = {
        "tab_n": IntegerRef(None, 1, 10),
    }

    shell_environment = Environment(name="Shell",
                                    parent=global_environment,
                                    context=UniversalAppContext(title = " - Terminal"),
                                    action_map=shell_action_map,
                                    element_map=shell_element_map)


    chrome_action_map = {
        "link": Key("c-comma"),
        "new link": Key("c-dot"),
        "background links": Key("a-f"),
        "new tab":            Key("c-t"),
        "new incognito":            Key("cs-n"),
        "new window": Key("c-n"),
        "clote":          Key("c-w"),
        "address bar":        Key("c-l"),
        "back [<n>]":               Key("a-left/15:%(n)d"),
        "Frak [<n>]":            Key("a-right/15:%(n)d"),
        "reload": Key("c-r"),
        "shot <tab_n>": Key("c-%(tab_n)d"),
        "shot last": Key("c-9"),
        "net [<n>]":           Key("c-tab:%(n)d"),
        "pret [<n>]":           Key("cs-tab:%(n)d"),
        "move tab left [<n>]": Key("cs-pgup/5:%(n)d"),
        "move tab right [<n>]": Key("cs-pgdown/5:%(n)d"),
        "move tab <tab_n>": Key("cs-%(tab_n)d"),
        "move tab last": Key("cs-9"),
        "reote":         Key("cs-t"),
        "duplicate tab": Key("c-l/15, a-enter"),
        "find":               Key("c-f"),
        "<link>":          Text("%(link)s"),
        "(caret|carrot) browsing": Key("f7"),
        "moma": Key("c-l/15") + Text("moma") + Key("tab"),
        "code search car": Key("c-l/15") + Text("csc") + Key("tab"),
        "code search simulator": Key("c-l/15") + Text("css") + Key("tab"),
        "code search": Key("c-l/15") + Text("cs") + Key("tab"),
        "go to calendar": Key("c-l/15") + Text("calendar.google.com") + Key("enter"),
        "go to critique": Key("c-l/15") + Text("cr/") + Key("enter"),
        "go to (buganizer|bugs)": Key("c-l/15") + Text("b/") + Key("enter"),
        "go to presubmits": Key("c-l/15, b, tab") + Text("One shot") + Key("enter:2"),
        "go to postsubmits": Key("c-l/15, b, tab") + Text("Continuous") + Key("enter:2"),
        "go to latest test results": Key("c-l/15, b, tab") + Text("latest test results") + Key("enter:2"),
        "go to docs": Key("c-l/15") + Text("docs.google.com") + Key("enter"),
        "go to slides": Key("c-l/15") + Text("slides.google.com") + Key("enter"),
        "go to sheets": Key("c-l/15") + Text("sheets.google.com") + Key("enter"),
        "go to new doc": Key("c-l/15") + Text("go/newdoc") + Key("enter"),
        "go to new slides": Key("c-l/15") + Text("go/newslides") + Key("enter"),
        "go to new sheet": Key("c-l/15") + Text("go/newsheet") + Key("enter"),
        "go to drive": Key("c-l/15") + Text("drive.google.com") + Key("enter"),
        "go to amazon": Key("c-l/15") + Text("smile.amazon.com") + Key("enter"),
        "(new|insert) row": Key("a-i/15, r"),
        "delete row": Key("a-e/15, d"),
        "strikethrough": Key("as-5"),
        "bullets": Key("cs-8"),
        "bold": Key("c-b"),
        "create link": Key("c-k"),
        "text box": Key("a-i/15, t"),
        "paste raw": Key("cs-v"),
        "next match": Key("c-g"),
        "preev match": Key("cs-g"),
        "(go to|open) bookmark": Key("c-semicolon"),
        "new bookmark": Key("c-apostrophe"),
        "save bookmark": Key("c-d"),
        "next frame": Key("c-lbracket"),
        "developer tools": Key("cs-j"),
        "test driver": Function(test_driver),
        "search bar": ClickElementAction(By.NAME, "q"),
        "amazon bar": ClickElementAction(By.NAME, "field-keywords"),
        "add bill": ClickElementAction(By.LINK_TEXT, "Add a bill"),
    }

    chrome_terminal_action_map = {
        "search <text>":        Key("c-l/15") + Text("%(text)s") + Key("enter"),
    }

    link_char_map = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
    }
    link_char_dict_list  = DictList("link_char_dict_list", link_char_map)
    chrome_element_map = {
        "tab_n": IntegerRef(None, 1, 9),
        "link": JoinedRepetition("", DictListRef(None, link_char_dict_list), min = 0, max = 5),
    }

    chrome_environment = Environment(name="Chrome",
                                     parent=global_environment,
                                     context=AppContext(title=" - Google Chrome"),
                                     action_map=chrome_action_map,
                                     terminal_action_map=chrome_terminal_action_map,
                                     element_map=chrome_element_map)

    critique_action_map = {
        "preev": Key("p"),
        "next": Key("n"),
        "preev file": Key("k"),
        "next file": Key("j"),
        "open": Key("o"),
        "list": Key("u"),
        "comment": Key("c"),
        "resolve": Key("c-j"),
        "done": Key("d"),
        "save": Key("c-s"),
        "expand|collapse": Key("e"),
        "reply": Key("r"),
        "comment <line_n>": DoubleClickElementAction(By.XPATH,
                                                     ("//span[contains(@class, 'stx-line') and "
                                                      "starts-with(@id, 'c') and "
                                                      "substring-after(@id, '_') = '%(line_n)s']")),
    }
    critique_element_map = {
        "line_n": IntegerRef(None, 1, 10000),
    }
    critique_environment = Environment(name="Critique",
                                       parent=chrome_environment,
                                       context=AppContext(title = "<critique.corp.google.com>"),
                                       action_map=critique_action_map,
                                       element_map=critique_element_map)

    calendar_action_map = {
        "click <name>": ClickElementAction(By.XPATH, "//*[@role='option' and contains(string(.), '%(name)s')]"),
        "today": Key("t"),
        "preev": Key("k"),
        "next": Key("j"),
        "day": Key("d"),
        "week": Key("w"),
        "month": Key("m"),
    }
    names_dict_list = DictList(
        "name_dict_list",
        {
            "Sonica": "Sonica"
        })
    calendar_element_map = {
        "name": DictListRef(None, names_dict_list),
    }
    calendar_environment = Environment(name="Calendar",
                                       parent=chrome_environment,
                                       context=(AppContext(title = "Google Calendar") |
                                                AppContext(title = "Google.com - Calendar")),
                                       action_map=calendar_action_map,
                                       element_map=calendar_element_map)

    code_search_action_map = {
        "header": Key("r/25, h"),
        "source": Key("r/25, c"),
    }
    code_search_environment = Environment(name="CodeSearch",
                                          parent=chrome_environment,
                                          context=AppContext(title = "<cs.corp.google.com>"),
                                          action_map=code_search_action_map)

    gmail_action_map = {
        "open": Key("o"),
        "(archive|done)": Text("{"),
        "mark unread": Text("_"),
        "list": Key("u"),
        "preev": Key("k"),
        "next": Key("j"),
        "preev message": Key("p"),
        "next message": Key("n"),
        "compose": Key("c"),
        "reply": Key("r"),
        "reply all": Key("a"),
        "forward": Key("f"),
        "important": Key("plus"),
        "mark starred": Key("s"),
        "next section": Key("backtick"),
        "preev section": Key("tilde"),
        "not important|don't care": Key("minus"),
        "label waiting": Key("l/50") + Text("waiting") + Key("enter"),
        "select": Key("x"),
        "select next <n>": Key("x, j") * Repeat(extra="n"),
        "new messages": Key("N"),
        "go to inbox": Key("g, i"),
        "go to starred": Key("g, s"),
        "go to sent": Key("g, t"),
        "go to drafts": Key("g, d"),
        "expand all": ClickElementAction(By.XPATH, "//*[@aria-label='Expand all']"),
        "click to": ClickElementAction(By.XPATH, "//*[@aria-label='To']"),
        "click cc": Key("cs-c"),
        "open chat": Key("q"),
    }
    gmail_terminal_action_map = {
        "chat with <text>": Key("q/50") + Text("%(text)s") + Pause("50") + Key("enter"),
    }

    gmail_environment = Environment(name="Gmail",
                                    parent=chrome_environment,
                                    context=(AppContext(title = "Gmail") |
                                             AppContext(title = "Google.com Mail") |
                                             AppContext(title = "<mail.google.com>") |
                                             AppContext(title = "<inbox.google.com>")),
                                    action_map=gmail_action_map,
                                    terminal_action_map=gmail_terminal_action_map)

    docs_action_map = {
        "select column": Key("c-space"),
        "select row": Key("s-space"),
        "row up": Key("a-e/15, k"),
        "row down": Key("a-e/15, j"),
        "column left": Key("a-e/15, m"),
        "column right": Key("a-e/15, m"),
        "add comment": Key("ca-m"),
    }
    docs_environment = Environment(name="Docs",
                                   parent=chrome_environment,
                                   context=AppContext(title = "<docs.google.com>"),
                                   action_map=docs_action_map)

    buganizer_action_map = {}
    RunLocalHook("AddBuganizerCommands", buganizer_action_map)
    buganizer_environment = Environment(name="Buganizer",
                                        parent=chrome_environment,
                                        context=(AppContext(title = "Buganizer V2") |
                                                 AppContext(title = "<b.corp.google.com>") |
                                                 AppContext(title = "<buganizer.corp.google.com>") |
                                                 AppContext(title = "<b2.corp.google.com>")),
                                        action_map=buganizer_action_map)

    analog_action_map = {
        "next": Key("n"),
        "preev": Key("p"),
    }
    analog_environment = Environment(name="Analog",
                                     parent=chrome_environment,
                                     context=AppContext(title = "<analog.corp.google.com>"),
                                     action_map=analog_action_map)

    notepad_action_map = {
        "dumbbell [<n>]": Key("shift:down, c-left/5:%(n)d, backspace, shift:up"),
        "transfer out": Key("c-a, c-x, a-f4") + UniversalPaste(),
    }

    notepad_environment = Environment(name="Notepad",
                                      parent=global_environment,
                                      context=AppContext(executable = "notepad"),
                                      action_map=notepad_action_map)

   
    #-------------------------------------------------------------------------------
    # Populate and load the grammar.
    return global_environment


   
    # Connect to Chrome WebDriver if possible.
    #create_driver()

    # Connect to eye tracker if possible.
    #connect()

#-------------------------------------------------------------------------------
# Unload function which will be called by NatLink.
def unload():
    global grammar, server, server_thread, timer
    if grammar:
        grammar.unload()
        grammar = None
    #disconnect()
    #quit_driver()
    print "unloaded"