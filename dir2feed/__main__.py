#!/usr/bin/env python

import argparse

from dir2feed import dir2feed
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an Atom feed from the contents of a directory"
    )
    parser.add_argument("path", help="The directory to process")
    parser.add_argument("base_url", help="URL prefix for the top-level path")
    parser.add_argument(
        "feed_url",
        nargs="?",
        help=(
            "The URL that this feed will be accessed from. "
            "Not required, but is recommended. If provided, this will be used "
            "as the feed's ID, otherwise the base_url will be used."
        ),
    )
    parser.add_argument(
        "--type",
        dest="type_",
        choices=["file", "dir", "both"],
        default="file",
        help='What element types to add to the feed (default is "file")',
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="The title of the feed (default is to use the starting directory name)",
    )
    parser.add_argument(
        "--depth", type=int, default=1, help="The depth to recurse (default: 1)"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=[],
        action="append",
        help="Files to exclude (can be provided multiple times)",
    )
    parser.add_argument(
        "--exclude-dir",
        type=str,
        default=[],
        action="append",
        help="Directories to exclude (can be provided multiple times)",
    )
    parser.add_argument(
        "--age-cutoff",
        type=int,
        default=None,
        help="Entries over this many days old are dropped (default is no cutoff)",
    )
    parser.add_argument(
        "--num-cutoff",
        type=int,
        default=50,
        help="The maximum number of entries to generate (default 50, 0 for no limit)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="-",
        help="The file to write the results to (defaults to stdout)",
    )
    return vars(parser.parse_args())


def main():
    dir2feed(**parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(main())
