#!/usr/bin/env python

import os
from datetime import datetime, timezone
import fnmatch
from html import escape as html_escape
import mimetypes
from operator import attrgetter
import re
from urllib.parse import quote as url_escape

from feedgen.feed import FeedGenerator


def get_mimetype(url):
    return mimetypes.guess_type(url, strict=False)[0]


class Entry:
    def __init__(self, base_url, start_path, rel_path):
        self.title = os.path.basename(rel_path)
        self.url = "{}/{}".format(base_url, url_escape(rel_path))
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
                    href="{}/{}".format(self.url, url_escape(f.name)),
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

    def _listobjs(self, objs, name):
        if objs:
            yield "<p>{} {}(s):</p>".format(len(objs), name)
            yield "<ul>"
            for o in sorted(objs, key=attrgetter("name")):
                title = html_escape(o.name)
                url = html_escape("{}/{}".format(self.url, url_escape(o.name)))
                yield '<li><a href="{}">{}</a></li>'.format(url, title)
            yield "</ul><br/>"

    def summary(self):
        s = []
        if self.is_dir:
            s.append("<p>Directory name: {}</p>".format(html_escape(self.title)))
            s.append("<p>This directory contains:</p>")
            s.extend(self._listobjs(self._dirs, "dir"))
            s.extend(self._listobjs(self._files, "file"))
        else:
            s.append("<p>Filename: {}</p>".format(html_escape(self.title)))

        dt_iso = self.date.isoformat()
        dt_readable = self.date.strftime("%Y-%m-%d %H:%M UTC")
        s.append(
            '<p>Last modified: <time datetime="{}">{}</time></p>'.format(
                dt_iso, dt_readable
            )
        )
        return "".join(s)


def gen_feed(title, base_url, feed_url, num_cutoff, entries):
    fg = FeedGenerator()
    if feed_url:
        fg.id(feed_url)
        fg.link(href=feed_url, rel="self")
    else:
        fg.id(base_url)
    fg.title(title)
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
        fe.summary(summary=e.summary(), type="html")

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
    if feed_url:
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
