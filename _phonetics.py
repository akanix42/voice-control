
phonetics = {
    "a": "eh",
    "b": "bee",
    "c": "(see | sea)",
    "d": "(dee | de)",
    "f": "(ef | eff)",
    "h": "aitch",
    "i": "(i | eye)",
    "l": "el",
    "m": "em",
    "o": "oh",
    "r": "(are | arr)",
    "t": "(tea | tee)",
    "u": "(you | ewe)",
}


def convert_to_phonetics(characters):
    return " ".join(map(lambda char: phonetics[char], list(characters)))
