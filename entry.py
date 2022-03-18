# library file, not executable
from __future__ import annotations
import re

typeWeights = {
    "balance": 1,
    "open": 2,
    "price": 3,
    "*": 4,
    "!": 5,
    "document": 6,
    "close": 7
}

# regex compatible keys for typeWeights
typeWeightKeys = "|".join(k.replace("*", r"\*").replace("!", r"\!")
                          for k in typeWeights.keys())


##
# regex matches
#
# These must be tested _in_this_order_ otherwise one may mask another.
# NOTE that we match a commented-out entry _as_itself_ to sort it correctly.
##
# break point: do not reorder above/below this point in the file
breakStart = re.compile(
        r'^(;+\s*)?(plugin|option|pushtag|poptag)\s+(.*)'
        )
# beginning of an entry (may be commented), which may span multiple lines
entryStart = re.compile(
        rf'^(;+\s*)?([12][0-9]{{3}}-[0-1][0-9]-[0-3][0-9])\s+({typeWeightKeys})\s+(.*)'  # noqa: E501
        )
# indented line: is part of current entry
continuation = re.compile(
        r'^(;+)?\s{2,}(.*)'
        )
# toplevel comment line: precedes a Start but is part of it
comment = re.compile(
        r'^(;+)(.*)'
        )
# empty line: append the first to the preceding transaction (if any),
# otherwise discard.
trailer = re.compile(
        r'^\s*\n'
        )


class Entry():
    """
    Represent one "entry" or "atomic multiline block"
    """
    # params used for parsing:
    _is_breakpoint = False  # should _not_ allow reordering before/after
    _has_trailer = False  # have already added a trailing newline

    # params used for sort/weighting:
    parse_group = 0  # incremented on each breakpoint
    date = ''
    weight = 20

    # actual data is unchanged
    header = ''  # Have header already? Also used publicly for matching.
    lines = None

    def __init__(self, parse_group=0) -> Entry:
        self.lines = []
        self.parse_group = parse_group

    def __repr__(self) -> str:
        return "".join(ln for ln in self.lines)

    def __bool__(self) -> bool:
        return bool(self.lines)

    def _sortfields(self) -> tuple:
        return (self.parse_group, self.date, self.weight, self.__repr__())

    def __hash__(self) -> int:
        return hash(self._sortfields())

    def __eq__(self, other: Entry) -> bool:
        return self._sortfields() == other._sortfields()

    def __lt__(self, other: Entry) -> bool:
        return self._sortfields() < other._sortfields()

    def __gt__(self, other: Entry) -> bool:
        return self._sortfields() > other._sortfields()

    def _new(self) -> Entry:
        return Entry(self.parse_group + self._is_breakpoint)

    def _add_breakStart(self, match: re.Match, ln: str) -> Entry:
        self.lines.append(ln)
        self.header = ln
        self.weight = 0
        self._is_breakpoint = True
        self.parse_group += 1
        return self

    def _add_entryStart(self, match: re.Match, ln: str) -> Entry:
        self.lines.append(ln)
        self.header = ln
        self.date = match.group(2)
        self.weight = typeWeights[match.group(3)]
        return self

    def _add_line(self, ln: str) -> Entry:
        self.lines.append(ln)
        return self

    def _add_trailer(self, ln: str) -> Entry:
        self.lines.append(ln)
        self._has_trailer = True
        return self

    def append(self, ln: str) -> Entry:
        """Appends 'line' and returns either self _or_ a _new_ Entry"""
        # sanitize line on input
        ln = ln.replace("\t", "  ").rstrip() + "\n"

        if m := entryStart.match(ln):
            if self.header:
                self = self._new()
            return self._add_entryStart(m, ln)

        if m := breakStart.match(ln):
            if self.header:
                self = self._new()
            return self._add_breakStart(m, ln)

        if m := continuation.match(ln):
            assert self.header, f"unexpected continuation: {ln}!"
            return self._add_line(ln)

        if m := comment.match(ln):
            if self.header:
                self = self._new()
            return self._add_line(ln)

        if m := trailer.match(ln):
            if not self._has_trailer:
                return self._add_trailer(ln)
            if len(self.lines) == 0:
                return self
            return self._new()

        raise AssertionError(f"unmatched line: {ln}")
