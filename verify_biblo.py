import os
import sys
import enum
from io import StringIO

class ReadState(enum.Enum):
    NONE = 0
    NAME = 1
    VALUE = 2

def read_entry(f):
    """ Reads a single bibliography entry from the file stream,
    and returns a corresponding BibloEntry

    >>> str(read_entry(StringIO("@misc{abc,title = {Hello world},year = {5}}")))
    "abc: {'title': 'Hello world', 'year': '5'}"
    >>> str(read_entry(StringIO("@misc{abc,   title = {\{H\}ello world},year = {5}}")))
    "abc: {'title': '\\\\\\\\{H\\\\\\\\}ello world', 'year': '5'}"
    >>> str(read_entry(StringIO("@misc{abc,title = {Hello world},year = {5},}")))
    "abc: {'title': 'Hello world', 'year': '5'}"
    >>> str(read_entry(StringIO("@misc{abc,title = {Hello world},year = {5}")))
    'None'
    """
    # Find a starting '@'
    cur = ' '
    token = ""
    depth = 0
    name = ""
    attr_name = ""
    attrs = {}
    typ = ""
    while cur != '@' and cur != '':
        cur = f.read(1)
    if cur != '@' and cur != '':
        return None
    # Extract the type
    while cur != '{' and cur != '':
        cur = f.read(1)
        token += cur
    if cur != '{' and cur != '':
        return None
    depth += 1
    typ = token[:-1]
    token = ""
    # Read over the name
    while cur != ',' and cur != '':
        cur = f.read(1)
        token += cur
    name = token[:-1]
    token = ""
    # Scan through attrs until we close
    state = ReadState.NAME
    while depth != 0:
        cur = f.read(1)
        if cur == '' or cur == 0:
            break
        if cur == '{':
            depth += 1
            if depth > 2:
                token += '{'
        elif cur == '}':
            depth -= 1
            if state == ReadState.VALUE and depth == 1:
                attrs[attr_name] = token.strip()
                token = ""
                state = ReadState.NONE
            else:
                token += '}'
        elif state == ReadState.NAME and cur == '=':
            attr_name = token.strip()
            token = ""
            state = ReadState.VALUE
        elif state == ReadState.NONE and cur == ',':
            state = ReadState.NAME
        elif state != ReadState.NONE:
            token += cur
    if depth != 0:
        return None
    if typ == "book":
        return BookEntry(name, attrs)
    elif typ == "article":
        return ArticleEntry(name, attrs)
    return BibloEntry(name, attrs)

location_has_two_or_three_elements = lambda a: a.count(',') == 1 or a.count(',') == 2
location_has_two_or_three_elements.__name__ = "Location has form 'City, Country' or 'City, State, Country'"
from titlecase import titlecase
is_titlecase = lambda a: titlecase(a) == a
is_titlecase.__name__ = "Is Title Case"
def is_ieee_abrev(s):
    words = ['transactions', 'journal', 'biomedical', 'engineering']
    for w in s.split():
        if w.lower() in words:
            return False
    return True
is_ieee_abrev.__name__ = "specials words are acronyms"

class BibloEntry:
    validators = {}
    def __init__(self, name, attributes):
        """ Contructs a BibloEntry from a dictionary looking like:
        { "title": "Clustering by compression", "author": ...}

        Name is largely ignored
        """
        self.name = name
        self.attrs = attributes
        self.errors = []

    def errors(self):
        return self.errors

    def validate(self):
        self.errors = []
        for attr in self.validators.keys():
            if attr not in self.attrs:
                self.errors += ["%s missing" % attr]
            else:
                for validator in self.validators[attr]:
                    if not validator(self.attrs[attr]):
                        self.errors += ["failed to validate %s on %s" % (validator.__name__, attr)]
        return self.errors == []
    def __str__(self):
        return "%s: %s" % (self.name, self.attrs)

class BookEntry(BibloEntry):
    validators = {
        "location": [location_has_two_or_three_elements],
        "title": [is_titlecase],
    }

class ArticleEntry(BibloEntry):
    validators = {
        "journal": [is_ieee_abrev],
        "title": [is_titlecase],
    }

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--test":
        import doctest
        doctest.testmod()
        exit(0)
    if len(sys.argv) != 2:
        print("Usage: %s <filename> or %s --test" % (sys.argv[0], sys.argv[0]))
    with open(sys.argv[1], 'r') as f:
        entry = read_entry(f)
        names = []
        while entry != None:
            if entry.name in names:
                print("WARNING: duplicate entry %s, taking first" % (entry.name))
            elif not entry.validate():
                print("Check %s for: %s" % (entry.name, entry.errors))
                names += [entry.name]
            entry = read_entry(f)
