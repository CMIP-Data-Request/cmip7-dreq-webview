#!/usr/bin/env python3
"""One-time repair script: create minimal placeholder pages for removed UIDs.

Crawls the published version directories (docs/<version>/u/) from old to new
- without accessing the data request API - and creates a minimal placeholder
page (basic header + removal note + link to the last version holding the full
record) for every UID that was published in at least one prior version but is
missing in a later version directory. Existing files (i.e. reinstated records
and the detailed placeholders written for variables) are never overwritten.

Idempotent: rerunning it does not modify or duplicate anything. Ongoing
maintenance for future versions is handled by gen_c7dreq_htmls.py, which
carries these placeholders forward.
"""

import os
import re

BASE = "docs"
VERSIONS = [
    "v1.0",
    "v1.1",
    "v1.2",
    "v1.2.1",
    "v1.2.2",
    "v1.2.2.1",
    "v1.2.2.2",
    "v1.2.2.3",
    "v1.2.2.4",
    "v1.2.2.5",
    "v1.2.2.6",
]
REMOVED_NOTE = "This record was removed with the current or with a previous release"
H1_RE = re.compile(r"<h1>(.+?) record: (.+?) \(v[^)]*\)</h1>")


def read_head(path, nbytes=8192):
    """Read the first bytes of a page - enough for <h1> and the removal note."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(nbytes)


def write_placeholder(path, version, category, label, last_version, fname):
    cat_link = os.path.exists(os.path.join(BASE, version, f"{category}.html"))
    nav = (
        f"<p><a href='../{category}.html'>Back to {category}</a> | <a href='../index.html'>Category Index</a></p>"
        if cat_link
        else "<p><a href='../index.html'>Category Index</a></p>"
    )
    title = f"{category} record: {label} ({version})"
    html = "<!DOCTYPE html><html><head>"
    html += '<meta charset="UTF-8">'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    html += f"<title>{title}</title>"
    html += '<link rel="stylesheet" href="../../style_c7dreq.css">'
    html += '<link rel="icon" type="image/x-icon" href="../../ress/favico.ico">'
    html += "</head><body>"
    html += f"<h1>{category} record: {label} ({version})</h1>"
    html += nav
    html += f"<script src='../../check_deprecated.js' data-dreq-version=\"{version}\" data-dreq-latest=\"../../dreq_latest_version.txt\"></script>"
    html += f"<p><strong>Note:</strong> {REMOVED_NOTE} of the CMIP7 Data Request. Link to record of version {last_version}: <a href='../../{last_version}/u/{fname}'>LINK</a></p>"
    html += nav
    html += "</body></html>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# fname -> (version, category, label) of the last full (non-placeholder) record page
last_real = dict()
total = 0
for version in VERSIONS:
    udir = os.path.join(BASE, version, "u")
    present = set(os.listdir(udir))
    # Create placeholders for UIDs published earlier but missing in this version
    n_created = 0
    for fname, (last_version, category, label) in sorted(last_real.items()):
        if fname in present:
            continue
        write_placeholder(
            os.path.join(udir, fname), version, category, label, last_version, fname
        )
        n_created += 1
    total += n_created
    # Record the full record pages of this version as possible link targets
    for fname in sorted(present):
        if not fname.endswith(".html"):
            continue
        # Ignore 'default_<number>' UIDs: they are temporary per-release IDs
        #  and may denote a different object in another release
        if fname.startswith("default"):
            continue
        head = read_head(os.path.join(udir, fname))
        if REMOVED_NOTE in head:
            continue
        h1_match = H1_RE.search(head)
        if not h1_match:
            print(f"WARNING: Could not parse '{udir}/{fname}' - skipped")
            continue
        last_real[fname] = (version, h1_match.group(1), h1_match.group(2))
    print(f"{version}: {n_created} placeholder(s) created")

# Sync the 'latest' alias (a plain copy of the newest version directory)
latest_u = os.path.join(BASE, "latest", "u")
newest_u = os.path.join(BASE, VERSIONS[-1], "u")
n_synced = 0
if os.path.isdir(latest_u):
    present = set(os.listdir(latest_u))
    for fname in sorted(os.listdir(newest_u)):
        if fname not in present:
            with open(os.path.join(newest_u, fname), encoding="utf-8") as f:
                content = f.read()
            with open(os.path.join(latest_u, fname), "w", encoding="utf-8") as f:
                f.write(content)
            n_synced += 1
print(f"latest: {n_synced} placeholder(s) synced from {VERSIONS[-1]}")
print(f"Total: {total} placeholder(s) created")
