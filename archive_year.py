#!/usr/bin/env python3
"""Archive this year's conference site.

Copies the built site (_site/) into past/<year>/ and adds the year to
_data/past_conferences.yaml so it shows up on the Past Conferences page.

Run it through make so the site is rebuilt first:

    make archive              # year comes from _data/dates.yaml
    make archive YEAR=2026    # or name the year yourself
    make archive FORCE=1      # replace an existing past/<year>/

The copy is frozen: it keeps its own styles, images, and pages, so later
changes to the site don't change how an archived year looks. Links inside it
are rewritten to stay inside past/<year>/, except links to the home page ("/")
and to the Past Conferences pages ("/past..."), which still go to the live
site, the same as the archives made by hand before this script existed.
"""

import argparse
import re
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "_site"
PAST = ROOT / "past"
DATES = ROOT / "_data" / "dates.yaml"
PAST_LIST = ROOT / "_data" / "past_conferences.yaml"

# Top-level entries of _site that don't belong in an archive. "past" holds
# the earlier archives, which would otherwise be nested inside the new one.
SKIP = ["past", "sitemap.xml", "robots.txt", "feed.xml", "google*.html"]

# Files whose links get rewritten.
TEXT_SUFFIXES = {".html", ".htm", ".css"}

ATTR_URL = re.compile(r"""(\b(?:href|src|action|poster)\s*=\s*)(["'])(/[^"']*)\2""", re.IGNORECASE)
SRCSET = re.compile(r"""(\bsrcset\s*=\s*)(["'])([^"']*)\2""", re.IGNORECASE)
CSS_URL = re.compile(r"""(url\(\s*)(["']?)(/[^"')]*)\2(\s*\))""", re.IGNORECASE)
META_REFRESH = re.compile(r"""(content\s*=\s*["']\s*\d+\s*;\s*url\s*=\s*)(/[^"']*)""", re.IGNORECASE)
LIVE_PAST = re.compile(r"^/past(?:[/?#]|$)")


def stays_live(url):
    """Return True for root-relative URLs that should keep pointing at the live site."""
    return url == "/" or url.startswith(("//", "/#", "/?")) or bool(LIVE_PAST.match(url))


def rewrite_links(text, prefix):
    """Point root-relative URLs in HTML or CSS at the archived copy. Returns (text, count)."""
    count = 0

    def rebase(url):
        nonlocal count
        if stays_live(url):
            return url
        count += 1
        return prefix + url

    text = ATTR_URL.sub(lambda m: m[1] + m[2] + rebase(m[3]) + m[2], text)
    text = CSS_URL.sub(lambda m: m[1] + m[2] + rebase(m[3]) + m[2] + m[4], text)
    text = META_REFRESH.sub(lambda m: m[1] + rebase(m[2]), text)

    def fix_srcset(m):
        parts = []
        for candidate in m[3].split(","):
            pieces = candidate.strip().split(None, 1)
            if pieces and pieces[0].startswith("/"):
                pieces[0] = rebase(pieces[0])
            parts.append(" ".join(pieces))
        return m[1] + m[2] + ", ".join(parts) + m[2]

    text = SRCSET.sub(fix_srcset, text)
    return text, count


def conference_year():
    """Read the conference year from _data/dates.yaml."""
    match = re.search(r"""^year:\s*["']?(\d{4})""", DATES.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        sys.exit(f"Could not find 'year:' in {DATES.relative_to(ROOT)}. Pass --year instead.")
    return match[1]


def copy_site(dest):
    """Copy _site into dest, leaving out the SKIP entries at the top level."""

    def ignore(directory, names):
        if Path(directory) != SITE:
            return []
        return [name for name in names if any(fnmatch(name, pattern) for pattern in SKIP)]

    shutil.copytree(SITE, dest, ignore=ignore)


def rewrite_archive(dest, prefix):
    """Rewrite links in every HTML and CSS file under dest. Returns (files, links) changed."""
    files = links = 0
    for path in dest.rglob("*"):
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        # surrogateescape keeps any non-UTF-8 bytes intact on the way back out.
        original = path.read_text(encoding="utf-8", errors="surrogateescape")
        updated, count = rewrite_links(original, prefix)
        if count:
            path.write_text(updated, encoding="utf-8", errors="surrogateescape")
            files += 1
            links += count
    return files, links


def add_to_past_list(year):
    """Add the year to the top of _data/past_conferences.yaml. Returns False if it's already there."""
    url = f"/past/{year}/"
    text = PAST_LIST.read_text(encoding="utf-8") if PAST_LIST.exists() else ""
    if re.search(rf"^\s*url:\s*{re.escape(url)}\s*$", text, re.MULTILINE):
        return False

    entry = f'- name: "{year}"\n  url: {url}\n'
    first_entry = re.search(r"^- ", text, re.MULTILINE)
    if first_entry:
        text = text[:first_entry.start()] + entry + "\n" + text[first_entry.start():]
    else:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + entry
    PAST_LIST.write_text(text, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--year", help="year to archive (default: 'year' in _data/dates.yaml)")
    parser.add_argument("--force", action="store_true", help="replace past/<year>/ if it already exists")
    args = parser.parse_args()

    year = args.year or conference_year()
    if not re.fullmatch(r"\d{4}", year):
        sys.exit(f"Year should look like 2026, not {year!r}.")

    if not (SITE / "index.html").is_file():
        sys.exit("_site/ hasn't been built. Run `make archive` so the site is built first.")

    dest = PAST / year
    if dest.exists():
        if not args.force:
            sys.exit(f"past/{year}/ already exists. Use `make archive FORCE=1` to replace it.")
        shutil.rmtree(dest)

    copy_site(dest)
    file_count = sum(1 for p in dest.rglob("*") if p.is_file())
    changed_files, changed_links = rewrite_archive(dest, f"/past/{year}")
    added = add_to_past_list(year)

    print(f"Archived {year} into past/{year}/ ({file_count} files; "
          f"rewrote {changed_links} links in {changed_files} files).")
    if added:
        print(f"Added {year} to the top of _data/past_conferences.yaml.")
    else:
        print(f"{year} was already listed in _data/past_conferences.yaml.")
    print(f"""
Next steps:
  make develop     # check http://localhost:4000/past/{year}/ and /past/
  git add past/{year} _data/past_conferences.yaml
  git commit -m "Archive {year}"
""")


if __name__ == "__main__":
    main()
