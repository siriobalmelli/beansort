#!/usr/bin/env python3
# sort format and sort beancount files
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from entry import Entry
from sys import argv, stdin, stderr
import re

assert __name__ == '__main__', "this is a script, not a library"


##
# arguments
##
parser = ArgumentParser(
    description="Filter and sort entries in beancount files.",
    epilog=(
        "\n".join(
            (
                "Examples:",
                "",
                "# Output sorted contents:",
                f"{argv[0]} file.beancount",
                f"{argv[0]} < file.beancount",
                f"cat file.beancount | {argv[0]}",
                "",
                "# Sort file in-place:",
                f"{argv[0]} -i file.beancount",
                "# _don't_ do this:",
                f"{argv[0]} file.beancount >file.beancount  # breaks file!",
                "",
                "# Output matching transactions:",
                f"{argv[0]} -f '^2019' file.beancount",
                f"{argv[0]} -f '^[Rr]estaurant' -v file.beancount  # inverse",
                "",
                "# Sort file in-place, keeping matching transactions _only_,",
                "# output non-matching (discarded) transactions to stdout:",
                f"{argv[0]} -f '201[67]' -i file.beancount",
                "# Move transactions from year 2016 to a new file:",
                f"{argv[0]} -f '^2016' -v -i file.beancount >2016.beancount",
            )
        )
    ),
    formatter_class=RawDescriptionHelpFormatter,
)
parser.add_argument(
    "-f",
    "--filter",
    dest="filter",
    metavar="FILTER",
    nargs="?",
    help="optional regex filter against the first line of the entry",
)
parser.add_argument(
    "-i",
    "--inplace",
    dest="inplace",
    action="store_true",
    help="edit file in-place",
)
parser.add_argument(
    "-v",
    "--inverse",
    dest="inverse",
    action="store_true",
    help="inverse matching (eg 'grep -v')",
)
parser.add_argument(
    "-d",
    "--debug",
    dest="debug",
    action="store_true",
    help="print verbose/debug into to stderr",
)
parser.add_argument(
    dest="files",
    metavar="FILE",
    nargs="*",
    help="files to process; if no files or '-' is given, stdin is used",
)
args = parser.parse_args()


def error(message):
    print(message, file=stderr)
    exit(1)


def debug(message):
    if args.debug:
        print(f'(Debug) {message}', file=stderr)


##
# I/O vector
##
# correctly handle stdin FILE case
if '-' in args.files:
    args.files.remove('-')
    if len(args.files):
        error("cannot combine stdin '-' with other FILE arguments")
# make sure we are not trying to edit stdin in-place :P
if args.inplace and not len(args.files):
    error("must have one or more FILE arguments to edit in-place")


##
# match/insert code
##
if args.filter:
    linefilter = re.compile(args.filter)
    if not args.inverse:
        def insert(entry: Entry) -> None:
            if linefilter.match(entry.header):
                matching.add(entry)
            else:
                varying.add(entry)
    else:
        def insert(entry: Entry) -> None:
            if linefilter.match(entry.header):
                varying.add(entry)
            else:
                matching.add(entry)
else:
    def insert(entry: Entry) -> None:
        matching.add(entry)


##
# I/O on a single file
##
def iterate_file(filename):
    """Do program I/O over 'filename'"""
    cur = Entry()
    debug(f"open {filename if filename else 'stdin'}")
    line_number = 0
    with (open(filename, 'r') if filename else stdin) as file:
        for ln in file.readlines():
            line_number += 1
            try:
                nxt = cur.append(ln)
            except Exception as e:
                e.args = (*e.args,
                          f"file: {filename if filename else 'stdin'}",
                          f"line: {line_number}",
                          )
                raise e
            if nxt is not cur:
                insert(cur)
            cur = nxt
        if (cur):
            insert(cur)

    if args.inplace and filename:
        with open(filename, 'w') as outfile:
            for entry in sorted(matching):
                outfile.write(str(entry))
            for entry in sorted(varying):
                print(entry, end='')
    else:
        for entry in sorted(matching):
            print(entry, end='')


##
# run
##
for f in args.files or ['']:
    matching = set()
    varying = set()
    iterate_file(f)
