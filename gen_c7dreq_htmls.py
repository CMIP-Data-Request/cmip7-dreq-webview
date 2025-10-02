from data_request_api.content import dreq_content as dc
from data_request_api.content import dump_transformation as dt
from data_request_api.query import data_request as dr
from data_request_api.query import dreq_query as dq
from html import unescape, escape
import re
import json
import os
from pathlib import Path

version="v1.0"
version="v1.1"
version="v1.2"
version="v1.2.1"
version="v1.2.2"
version="v1.2.2.1"
version="v1.2.2.2"
#version="v1.2.3"

full_content = dc.load(version=version, export="release", consolidate=True)
content_dic = dt.get_transformed_content(version=version)
DR = dr.DataRequest.from_separated_inputs(**content_dic)

# === SETTINGS ===
INPUT_FILES = [dc._dreq_res + "/" + version + '/VS_release_consolidate_content.json',
               dc._dreq_res + "/" + version + '/DR_release_consolidate_content.json']

# === Extract version ===
with open(INPUT_FILES[0], 'r', encoding='utf-8') as f:
    version_json = json.load(f)
if version != version_json.get("version"):
    raise Exception(f"Version mismatch: {version} != {version_json.get('version')}")

# Output directory with versioning
BASE_OUTPUT = 'docs'
OUTPUT_DIR = os.path.join(BASE_OUTPUT, version)

def path_in_version(subpath):
    return f"/{BASE_OUTPUT}/{version}/{subpath}"

# === STEP 1: LOAD & MERGE DATA ===
main_data = {}
extra_data = {}
uid_map = {}

# Load main data
with open(INPUT_FILES[0], 'r', encoding='utf-8') as f:
    main = json.load(f)
    for category, records in main.items():
        if category == "version":
            continue
        main_data[category] = records
        for record_id, record in records.items():
            uid = record_id
            record["uid"] = uid
            if "image" in record:
                del record["image"]
            if uid:
                uid_map[uid] = {
                    "category": category,
                    "record_id": record_id,
                    "main": record,
                    "extra": {}
                }

# Load extra data
with open(INPUT_FILES[1], 'r', encoding='utf-8') as f:
    extra = json.load(f)
    for category, records in extra.items():
        if category == "version":
            continue
        for record_id, extra_attrs in records.items():
            uid = record_id
            extra_attrs["uid"] = uid
            if uid and uid in uid_map:
                uid_map[uid]["extra"] = extra_attrs

# Build flat UID to record map for link resolution
uid_record_lookup = {}
for uid, obj in uid_map.items():
    full_record = obj["main"].copy()
    full_record.update(obj["extra"])
    uid_record_lookup[uid] = full_record

# Build combined dict (for reverse lookup table)
version = main.get("version") or extra.get("version")
main.pop("version", None)
extra.pop("version", None)
data_all = {}

# Merge main data
for category, records in main.items():
    data_all[category] = {**records}

# Merge in extras (adds or extends attributes)
for category, extra_records in extra.items():
    if category not in data_all:
        continue  # Only enrich existing categories
    for uid, extra_attrs in extra_records.items():
        if uid in data_all[category]:
            data_all[category][uid].update(extra_attrs)

# Extract description strings - category and fields per category
#   Adapted dump_transformation functions for consistent
#    renaming of categories and fields
category_desc = {}
field_desc = {}
transform_settings = dt.get_transform_settings(version=version)["one_to_transform"]

def transform_category_name(category, settings):
    for (patt, repl) in settings["tables_to_rename"].items():
        if re.compile(patt).match(category) is not None:
            category = re.sub(patt, repl, category)
    return category

def transform_field_name(field, category, settings):
    patterns_to_rename = settings["keys_to_rename"]
    patterns_to_merge = settings["keys_to_merge"]
    for (patt, repl) in patterns_to_rename.get(category, {}).items():
        patt = re.compile(patt)
        if patt.match(field) is not None:
            field = repl
    for (patt, repl) in patterns_to_merge.get(category, {}).items():
        patt = re.compile(patt)
        if patt.match(field) is not None:
            field = repl
    return field

for category, category_content in full_content["Data Request"].items():
    if category == "version":
        continue
    formatted_category = transform_category_name(dt.correct_key_string(category), transform_settings)
    category_desc[formatted_category] = category_content.get("description", "").strip()
    if category_desc[formatted_category] == "None":
        category_desc[formatted_category] = ""
    field_desc[formatted_category] = {}
    for field, field_content in category_content["fields"].items():
        formatted_field = transform_field_name(dt.correct_key_string(field_content["name"]), formatted_category, transform_settings)
        if field_desc[formatted_category].get(formatted_field, "") != "":
            desc_tmp = str(field_content.get("description", "")).strip()
            if desc_tmp and desc_tmp != "None":
                field_desc[formatted_category][formatted_field] += " " + desc_tmp
        else:
            desc_tmp = str(field_content.get("description", "")).strip()
            if desc_tmp and desc_tmp != "None":
                field_desc[formatted_category][formatted_field] = desc_tmp
            else:
                field_desc[formatted_category][formatted_field] = ""

        field_desc[formatted_category][formatted_field] = field_desc[formatted_category][formatted_field].strip()

for i in category_desc:
    print(i, category_desc[i])

for i in field_desc:
    for j in field_desc[i]:
        if field_desc[i][j]: print(i, j, field_desc[i][j])

for cat in data_all:
    if not cat in category_desc:
        print(f"ERROR: Missing category description for {cat}")
for cat in data_all:
    for rec in data_all[cat]:
        for f in data_all[cat][rec]:
            if not cat in field_desc:
                print(f"ERROR: '{cat}' missing in field descriptions {f}")
            elif not f in field_desc[cat]:
                print(f"ERROR: Missing field description for {cat} {f}")

# === CREATE OUTPUT DIRECTORIES ===
Path(f"{OUTPUT_DIR}/u").mkdir(parents=True, exist_ok=True)

# === HELPERS ===
def write_file(path, content, title="", style_location="../"):
    with open(os.path.join(OUTPUT_DIR, path), 'w', encoding='utf-8') as f:
        f.write("<!DOCTYPE html>")
        f.write("<html>")
        f.write("<head>")
        f.write('<meta charset="UTF-8">')
        f.write('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        if title:
            f.write(f'<title>{title}</title>')
        #f.write('<link rel="icon" type="image/x-icon" href="/ress/favico.ico">')
        f.write(f'<link rel="stylesheet" href="{style_location}style_c7dreq.css">')
        f.write("</head>")
        f.write("<body>")
        f.write(content)
        f.write("</body>")
        #f.write('<footer id="footer">')
        #f.write('<div class="footer-content">')
        #f.write('<a href="https://www.dkrz.de/about-en/contact/impressum">About</a>')
        #f.write('<a href="https://www.dkrz.de/about-en/contact/en-datenschutzhinweise">DKRZ Privacy Policy</a>')
        #f.write('</div></footer>')
        f.write("</html>")

def link_label(uid, uid_lookup):
    record = uid_lookup.get(uid, {})
    compound = record.get("cmip7_compound_name")
    name = record.get("cmip6_compound_name", record.get("name"))
    title = record.get("title")

    if compound and name:
        label = f"{compound} | {name}"
    elif name:
        label = name
    elif compound:
        label = compound
    else:
        label = uid
    return label, title

def make_link(value, uid_lookup, current_dir=""):
    def format_link(uid, single=False):
        label, title = link_label(uid, uid_lookup)
        label = escape(label)

        if current_dir == "index":
            href = f"u/{uid}.html"
        elif current_dir == "category":
            href = f"u/{uid}.html"
        elif current_dir == "record":
            href = f"{uid}.html"
        else:
            href = f"{uid}.html"

        if single and title:
            return f'<span><a href="{href}">{label}</a> ({escape(str(title))})</span>'
        else:
            return f'<span><a href="{href}">{label}</a></span>'

    if isinstance(value, str) and value.startswith("link::"):
        uid = value.split("::")[1]
        return format_link(uid, single=True)

    elif isinstance(value,str) and (value.startswith("http://") or value.startswith("https://")):
        return f'<a href="{value}" target="_blank">{escape(value)}</a>'

    elif isinstance(value, str) and "https://" in value:
        value = linkify_text(value)
        return value

    elif isinstance(value, list):
        links = []
        for v in value:
            if isinstance(v, str) and v.startswith("link::"):
                uid = v.split("::")[1]
                links.append(format_link(uid))
            elif isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
                links.append(f'<a href="{v}" target="_blank">{escape(v)}</a>')
            else:
                links.append(escape(str(v)))

        if len(links) <= 10:
            return "<span>"+", ".join(links)+"</span>"
        else:
            visible = ", ".join(links[:5])
            hidden = ", ".join(links)
            return f"""<details><summary><span class="short-view">{visible} ... and {len(links) - 5} more</span><span class="full-view">{hidden}</span></summary></details>"""

    else:
        return escape(str(value))

def build_uid_to_category_map(data_all):
    uid_to_category = {}
    for category, records in data_all.items():
        if not isinstance(records, dict):
            continue  # skip version or other non-record categories
        for uid in records:
            uid_to_category[uid] = category
    return uid_to_category

def build_reverse_links_map(data_all):
    reverse_links = {}

    for category, records in data_all.items():
        if not isinstance(records, dict):  # skip 'version' category
            continue
        for source_uid, record in records.items():
            for attr_val in record.values():
                links = []

                if isinstance(attr_val, str) and attr_val.startswith("link::"):
                    links = [attr_val]
                elif isinstance(attr_val, list):
                    links = [v for v in attr_val if isinstance(v, str) and v.startswith("link::")]

                for link in links:
                    target_uid = link.replace("link::", "")
                    reverse_links.setdefault(target_uid, {}).setdefault(category, []).append(source_uid)

    return reverse_links

def strip_html_tags(html):
    """Extracts visible text from HTML (e.g., link label)."""
    return unescape(re.sub(r"<.*?>", "", html))

def linkify_text(text):
    # Matches URLs with or without surrounding <>
    url_pattern = re.compile(r'<(https?://[^\s<>]+)>|(https?://[^\s,)\]>]+)')

    def repl(match):
        url = match.group(1) or match.group(2)
        escaped_url = escape(url)
        return f'<a href="{escaped_url}" target="_blank">{escaped_url}</a>'

    return url_pattern.sub(repl, text)

def render_reverse_links_section(uid, reverse_links, data_all, uid_to_category):
    if uid not in reverse_links:
        return ""  # No backlinks to this uid

    html = ['<h2>Links from Other Categories</h2>']

    for category, sources in reverse_links[uid].items():
        html.append(f'<details><summary><strong>{category}:</strong></summary><ul>')
        link_html = list()
        for source_uid in sources:
            source_cat = uid_to_category.get(source_uid)
            if not source_cat:
                continue
            source_record = data_all.get(source_cat, {}).get(source_uid)
            if not source_record:
                continue

            # Build label like before
            label_parts = []
            if 'cmip7_compound_name' in source_record:
                label_parts.append(source_record['cmip7_compound_name'])
            if 'cmip6_compound_name' in source_record:
                label_parts.append(source_record['cmip6_compound_name'])
            elif 'name' in source_record:
                label_parts.append(source_record['name'])
            label = " / ".join(label_parts)
            if 'title' in source_record and label_parts:
                label += f" ({source_record['title']})"

            link_html.append(f'<li><a href="{source_uid}.html">{label or source_uid}</a></li>')

        link_html.sort(key=lambda x: strip_html_tags(x))
        html.extend(link_html)
        html.append('</ul></details><br>')

    return "".join(html)

# Reverse links HTML (after extra data section)
uid_to_category = build_uid_to_category_map(data_all)
reverse_links = build_reverse_links_map(data_all)

# === index.html ===
index_html = f"<h1>DReq {version} All Categories</h1><ul>"
for category in sorted(main_data.keys()):
    if category_desc.get(category):
        index_html += f'<li><a title="{escape(category_desc.get(category))}" href="{category}.html">{escape(category)}</a></li>'
    else:
        index_html += f'<li><a href="{category}.html">{escape(category)}</a></li>'
index_html += f"</ul><p><a href='../index.html'>Back to Version Index</a></p>"
write_file("index.html", index_html, title=f"DReq {version} Index", style_location="../")

# === Category Pages ===
for category, records in main_data.items():
    html = f"<h1>Category: {escape(category)} ({version})</h1>"
    html += f"<p><a href='index.html'>Back to Category Index</a></p><ul>"
    if category_desc.get(category) not in ["", None]:
        print(f"category {category}: '{category_desc.get(category)}'")
        html += f"<p><strong>Category Description:</strong> {escape(category_desc.get(category))}</p>"
    link_html = list()
    for record_id, record in records.items():
        uid = record.get("uid")
        if uid:
            label, title = link_label(uid, uid_record_lookup)
            if title:
                link_html.append(f'<li><a href="u/{uid}.html">{escape(label)}</a> ({escape(title)})</li>')
            else:
                link_html.append(f'<li><a href="u/{uid}.html">{escape(label)}</a></li>')
    link_html.sort(key=lambda x: strip_html_tags(x))
    html += "".join(link_html)
    html += f"</ul><p><a href='index.html'>Back to Category Index</a></p>"
    write_file(f"{category}.html", html, title=f"{version} {category} Index")

# === Record Pages ===
for uid, obj in uid_map.items():
    category = obj["category"]
    record_id = obj["record_id"]
    main_record = obj["main"]
    extra_record = obj["extra"]

    html = f"<h1>{category} record: {escape(record_id)} ({version})</h1>"
    html += f"<p><a href='../{category}.html'>Back to {escape(category)}</a> | <a href='../index.html'>Category Index</a></p>"
    if category_desc.get(category) not in ["", None]:
        html += f"<br><details><summary><strong>Category Description</strong></summary><p>{escape(category_desc.get(category))}</p></details><br><br>"
    else:
        print(f"ERROR: '{category}' has no description")
    html += "<table><tr><th>Attribute</th><th>Value</th></tr>"
    for attr, value in main_record.items():
        if extra_record:
            if attr in extra_record:
                continue
        formatted_value = make_link(value, uid_record_lookup, current_dir="record")
        if category not in field_desc:
            print(f"ERROR: category '{category}' not in field description")
        elif field_desc[category].get(attr) not in ["", None]:
            html += f"<tr><td class='field_name' title='{escape(field_desc[category].get(attr))}'><strong>{escape(attr)}</strong></td><td>{formatted_value}</td></tr>"
        else:
            print(f"WARNING: field description of category '{category}' lacks attribute '{attr}'")
            html += f"<tr><td class='field_name'><strong>{escape(attr)}</strong></td><td>{formatted_value}</td></tr>"
    html += "</table>"

    if extra_record:
        html += "<h2>Data Request Information</h2><table>"
        for attr, value in extra_record.items():
            if attr == "uid":
                continue
            formatted_value = make_link(value, uid_record_lookup, current_dir="record")
            if field_desc[category].get(attr) != "":
                html += f"<tr><td class='field_name' title='{escape(field_desc[category].get(attr))}'><strong>{escape(attr)}</strong></td><td>{formatted_value}</td></tr>"
            else:
                html += f"<tr><td class='field_name'><strong>{escape(attr)}</strong></td><td>{formatted_value}</td></tr>"
        html += "</table>"

    reverse_html = render_reverse_links_section(uid, reverse_links, data_all, uid_to_category)
    html += reverse_html

    html += f"<p><a href='../{category}.html'>Back to {escape(category)}</a> | <a href='../index.html'>Category Index</a></p>"
    write_file(f"u/{uid}.html", html, title=f"{category} record: {escape(record_id)} ({version})", style_location="../../")

print()
print(f"HTML files generated in '{OUTPUT_DIR}/'")
