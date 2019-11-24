#!/usr/bin/env python

import os
from datetime import datetime, timezone
import fnmatch
import mimetypes
from operator import attrgetter
import re
from urllib.parse import quote

from feedgen.feed import FeedGenerator


def get_mimetype(url):
    return mimetypes.guess_type(url, strict=False)[0]


class Entry:
    def __init__(self, base_url, start_path, rel_path):
        self.title = os.path.basename(rel_path)
        self.url = "{}/{}".format(base_url, rel_path)
        self.path = os.path.join(start_path, rel_path)

        self.is_dir = os.path.isdir(self.path)
        stat = os.stat(self.path)
        self._files, self._dirs = [], []
        if self.is_dir:
            self.size = None
            for x in os.scandir(self.path):
                if x.is_file():
                    self._files.append(x)
                elif x.is_dir():
                    self._dirs.append(x)
        else:
            self.size = stat.st_size

        self.date = datetime.utcfromtimestamp(stat.st_mtime).replace(
            tzinfo=timezone.utc
        )

    def links(self):
        if self.is_dir:
            for f in self._files:
                yield dict(
                    rel="enclosure",
                    href="{}/{}".format(self.url, quote(f.name)),
                    length=str(f.stat().st_size),
                    type=get_mimetype(f.name),
                )
        else:
            yield dict(
                rel="enclosure",
                href=self.url,
                length=str(self.size),
                type=get_mimetype(self.url),
            )

    def content(self):
        def listobjs(s, objs, name):
            if objs:
                s.append("<p>{} {}(s):</p>".format(len(objs), name))
                s.append("<ul>")
                for o in objs:
                    title = quote(o.name)
                    url = "{}/{}".format(self.url, title)
                    s.append('<li><a href="{}">{}</a></li>'.format(url, title))
                s.append("</ul><br>")

        s = []
        if self.is_dir:
            s.append("<p>Is a directory containing:</p>")
            listobjs(s, self._dirs, "dir")
            listobjs(s, self._files, "file")
        else:
            s.append("<p>Is a file<p>")
        return "".join(s)

def gen_feed(title, base_url, feed_url, num_cutoff, entries):
    fg = FeedGenerator()
    fg.id(feed_url)
    fg.title(title)
    fg.link(href=feed_url, rel="self")
    fg.generator(generator="dir2feed", uri="https://github.com/pR0Ps/dir2feed")
    all_entries = sorted(entries, key=attrgetter("date", "title"))
    for e in all_entries[-max(0, num_cutoff or 0) :]:
        fe = fg.add_entry()
        fe.id(e.url)
        fe.title(e.title)
        fe.link(rel="alternate", href=e.url)
        fe.updated(e.date)
        for l in e.links():
            fe.link(**l)
        fe.content(content=e.content(), type="html")

    return fg


def gen_files(path, type_, depth, exclude, exclude_dir):
    for dirpath, dirs, files in os.walk(path, topdown=True, followlinks=True):

        # Stop recursing if we've met the max depth
        relpath = os.path.relpath(dirpath, path)
        curr_depth = relpath.count(os.path.sep)
        if relpath == ".":
            curr_depth -= 1
        if curr_depth >= depth - 1:
            del dirs[:]
            continue

        # Ignore hidden folders (don't recurse into them)
        if dirs:
            dirs[:] = [d for d in dirs if not any(e.match(d) for e in exclude_dir)]

        if type_ in ("dir", "both"):
            for d in dirs:
                yield os.path.relpath(os.path.join(dirpath, d), start=path)

        if type_ in ("file", "both"):
            for f in files:
                if any(e.match(f) for e in exclude):
                    continue
                yield os.path.relpath(os.path.join(dirpath, f), start=path)


def gen_entries(start_path, paths, base_url, age_cutoff):
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    for p in paths:
        e = Entry(base_url, start_path, p)
        if age_cutoff and (now - e.date).days > age_cutoff:
            continue
        yield e


def dir2feed(
    path,
    type_,
    base_url,
    output,
    feed_url=None,
    title=None,
    depth=1,
    age_cutoff=30,
    num_cutoff=50,
    exclude=[],
    exclude_dir=[],
):
    base_url = base_url.rstrip("/")
    path = path.rstrip("/")
    if not feed_url:
        if output == "-":
            raise ValueError("'feed_url' is required if outputting to stdout")
        feed_url = base_url + "/" + output
    feed_url = feed_url.rstrip("/")
    if not title:
        title = os.path.basename(path)

    # No hidden files
    exclude.insert(0, ".*")
    exclude_dir.insert(0, ".*")
    exclude = [re.compile(fnmatch.translate(x)) for x in exclude]
    exclude_dir = [re.compile(fnmatch.translate(x)) for x in exclude_dir]

    paths = gen_files(path, type_, depth, exclude, exclude_dir)
    entries = gen_entries(path, paths, base_url, age_cutoff)
    feed = gen_feed(title, base_url, feed_url, num_cutoff, entries)
    if output == "-":
        print(feed.atom_str(pretty=True).decode("utf-8"))
    else:
        feed.atom_file(output, pretty=True)
