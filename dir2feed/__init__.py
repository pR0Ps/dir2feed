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


def custom_walk(top, max_depth=0, valid_entry=None, _depth=0):
    """
    Custom reimplementation of os.walk

     - Yields entries depth-first
     - Only yields directories that are accessible and non-empty
     - Allows only walking to a max depth
     - Uses a validator function to filter what is explored/returned
     - Ignores any errors encountered when accessing the files
     - Returns True if the dir is accessible and non-empty, False otherwise
    """

    dirs = []
    nondirs = []

    try:
        scandir_it = os.scandir(top)
    except OSError:
        return False

    if max_depth and _depth >= max_depth:
        # Past the max depth - check if it's empty without yielding the contents
        try:
            next(scandir_it)
        except (StopIteration, OSError):
            return False
        return True

    with scandir_it:
        while True:
            try:
                entry = next(scandir_it)
            except StopIteration:
                break
            except OSError:
                return False

            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False

            if valid_entry and not valid_entry(entry, is_dir):
                continue

            if is_dir:
                dirs.append(entry)
            else:
                nondirs.append(entry.name)

    # Recurse into sub-directories
    non_empty_dirs = []
    for entry in dirs:
        if (yield from custom_walk(entry.path, max_depth, valid_entry, _depth=_depth+1)):
            non_empty_dirs.append(entry.name)

    if non_empty_dirs or nondirs:
        yield top, non_empty_dirs, nondirs
        return True

    return False


def gen_paths(path, type_, max_depth, exclude, exclude_dir):

    def valid_entry(entry, is_dir):
        if is_dir and any(e.match(entry.name) for e in exclude_dir):
            return False
        elif not is_dir and any(e.match(entry.name) for e in exclude):
            return False

        return True

    # Store directories that have been explored
    processed = set()

    for dirpath, dirs, files in custom_walk(os.fspath(path), max_depth, valid_entry):
        relpath = os.path.relpath(dirpath, path)

        if type_ in ("dir", "both"):
            for d in dirs:
                # Only yield the directory if it hasn't alrady been explored.
                # Since custom_walk is depth-first, this means that only the bottom-level
                # directories will be yielded
                p = os.path.join(dirpath, d)
                if p in processed:
                    continue
                yield os.path.relpath(p, start=path)

        if type_ in ("file", "both"):
            for f in files:
                yield os.path.relpath(os.path.join(dirpath, f), start=path)

        processed.add(dirpath)


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

    paths = gen_paths(path, type_, depth, exclude, exclude_dir)
    entries = gen_entries(path, paths, base_url, age_cutoff)
    feed = gen_feed(title, base_url, feed_url, num_cutoff, entries)
    if output == "-":
        print(feed.atom_str(pretty=True).decode("utf-8"))
    else:
        feed.atom_file(output, pretty=True)
