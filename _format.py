# (c) Copyright 2015 by James Stout
# (c) Copyright 2016 by Nathan Reid
# Licensed under the LGPL, see <http://www.gnu.org/licenses/>

import re
from _text_utils import SplitDictation

def camelCase(dictation):
    words = SplitDictation(dictation)
    return words[0] + "".join(w.capitalize() for w in words[1:])

def pascalCase(dictation):
    words = [word.capitalize() for words in SplitDictation(dictation)
    for word in re.findall(r"(\W+|\w+)", words)]
    return "".join(words)