dir2feed
========

Generate an Atom feed from the contents of a directory

Makes it super easy to allow others to keep track of your periodic content.

For example, if you want to roll your own podcast/website/other, simply serve the static files from a
directory, then run this script to generate a feed for them. Then, whenever new content is uploaded,
re-run the script to update the feed. All people need is the URL to your generated feed and they'll
automatically see your new content in their feed reader. No fancy frameworks required.

Installation
------------
```
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv)$ pip install git+https://github.com/pR0Ps/dir2feed.git
```

Usage
-----
```
$ dir2feed --help
usage: dir2feed [-h] [--type {file,dir,both}] [--title TITLE] [--depth DEPTH]
                [--exclude EXCLUDE] [--exclude-dir EXCLUDE_DIR]
                [--age-cutoff AGE_CUTOFF] [--num-cutoff NUM_CUTOFF]
                [--output OUTPUT]
                path base_url [feed_url]

Generate an Atom feed from the contents of a directory

positional arguments:
  path                  The directory to process
  base_url              URL prefix for the top-level path
  feed_url              The URL that this feed will be accessed from. Not
                        required, but is recommended. If provided, this will
                        be used as the feed's ID, otherwise the base_url will
                        be used.

optional arguments:
  -h, --help            show this help message and exit
  --type {file,dir,both}
                        What element types to add to the feed (default is
                        "file")
  --title TITLE         The title of the feed (default is to use the starting
                        directory name)
  --depth DEPTH         The depth to recurse (0 for unlimited, default is 1)
  --exclude EXCLUDE     Files to exclude (can be provided multiple times)
  --exclude-dir EXCLUDE_DIR
                        Directories to exclude (can be provided multiple
                        times)
  --age-cutoff AGE_CUTOFF
                        Entries over this many days old are dropped (default
                        is no cutoff)
  --num-cutoff NUM_CUTOFF
                        The maximum number of entries to generate (default 50,
                        0 for no limit)
  --output OUTPUT       The file to write the results to (defaults to stdout)
```

License
=======
Licensed under the [Mozilla Public License, version 2.0](https://www.mozilla.org/en-US/MPL/2.0)
