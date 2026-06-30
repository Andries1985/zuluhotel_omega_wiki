#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zuluhotel Shard Mechanics Documentation ETL Pipeline Script
===========================================================================
An automated ETL utility designed to pull raw markdown records from the
Miscellaneous/Mechanics repository endpoint, translate them into optimized
MediaWiki syntax, flatten relative link paths, and stage them under the
centralized 'Mechanics' category structure.

Usage & Deployment Lifecycle:
-----------------------------
    $ python3 parse_mechanics_to_wiki.py
"""

import os
import re
import requests

# ===========================================================================
# GLOBAL CONFIGURATION MATRIX
# ===========================================================================

SHARD_NAME = "Zuluhotel"

API_URL = "https://api.github.com/repos/Andries1985/zuluhotelomega-website/contents/content/infovault/misc?ref=master"

OUTPUT_DIR = os.path.expanduser("~/wiki_import")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as env_file:
            for line in env_file:
                if line.strip().startswith("GITHUB_TOKEN="):
                    GITHUB_TOKEN = line.split("=", 1)[1].strip()
                    break

# Static map aligning folder tokens with beautiful target names if required
NAME_OVERRIDES = {
    "characterclasses": "Character Classes",
    "equipmentitems": "Equipment and Items",
    "classes": "Character Classes",
    "npcboatcommands": "Boat Commands",
    "repairandrefinement": "Repair and Refinement"
}

# ===========================================================================
# ETL PIPELINE SUBPROCESSES
# ===========================================================================

def get_headers():
    """Constructs default API headers including authorization if available."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def clean_cell_text(text):
    """Applies typographical string adjustments to individual table cell values."""
    return re.sub(r'^(a|an)\s+', '', text.strip(), flags=re.IGNORECASE).strip()


def convert_markdown_tables(text):
    """
    Processes the raw content using line-by-line stream blocks to ensure HTML wrappers
    do not break table capture layouts, converting them to native MediaWiki tables.
    """
    text = re.sub(r'<details[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</details>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<summary>([\s\S]*?)</summary>', '', text, flags=re.IGNORECASE)

    lines = text.split('\n')
    new_lines = []

    in_table = False
    table_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(stripped)
        else:
            if in_table:
                if len(table_lines) >= 2:
                    new_lines.append(parse_collected_table(table_lines))
                else:
                    new_lines.extend(table_lines)
                in_table = False
            new_lines.append(line)

    if in_table and table_lines:
        if len(table_lines) >= 2:
            new_lines.append(parse_collected_table(table_lines))
        else:
            new_lines.extend(table_lines)

    return '\n'.join(new_lines)


def parse_collected_table(lines):
    """Turns an isolated group of markdown text rows into a sortable MediaWiki table."""
    raw_rows = []
    for line in lines:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        raw_rows.append(cells)

    if len(raw_rows) < 2:
        return '\n'.join(lines)

    headers = raw_rows[0]
    cols = len(headers)

    data_start_idx = 1
    if data_start_idx < len(raw_rows) and all(re.match(r'^[-:]+$', c) for c in raw_rows[data_start_idx] if c):
        data_start_idx += 1

    mw_table = ['{| class="wikitable sortable" style="width: 100%; border-collapse: collapse;"', '|-']
    mw_table.append('! ' + ' !! '.join(headers))

    seen_rows = set()
    for row in raw_rows[data_start_idx:]:
        if not row or all(c == '' for c in row):
            continue

        while len(row) < cols:
            row.append('')
        row = row[:cols]

        processed_row = [clean_cell_text(cell) for cell in row]
        row_fingerprint = "||".join(processed_row).lower()

        if row_fingerprint in seen_rows:
            continue
        seen_rows.add(row_fingerprint)

        mw_table.append('|-')
        mw_table.append('| ' + ' || '.join(processed_row))

    mw_table.append('|}')
    return '\n' + '\n'.join(mw_table) + '\n'


def md_to_mediawiki(text):
    """Translates Markdown syntax rules into clean MediaWiki markup representations."""
    # Strip Hugo Front Matter
    text = re.sub(r'^---[\s\S]+?---', '', text)

    # Enforce precise Shard naming rules
    text = re.sub(r'Zoulouhotel', SHARD_NAME, text, flags=re.IGNORECASE)

    # CRITICAL SEQUENCE FIX: Convert markdown structural tables BEFORE parsing images.
    # This prevents the image formatting pipe '|' from getting caught by markdown column splits.
    text = convert_markdown_tables(text)

    # Global Image Normalizer
    def core_image_replacer(match):
        filename = match.group(1).strip()
        if filename:
            filename = filename[0].upper() + filename[1:]
        return f"[[File:{filename}|120px]]"

    # Match standard markdown format: ![alt](.../file.png)
    text = re.sub(r'!\[.*?\]\([^)]*/([^)/]+\.png)\)', core_image_replacer, text, flags=re.IGNORECASE)
    # Match anomalous bracket format: ![/path/.../file.png alt text]
    text = re.sub(r'!\[[^\]]*/([^/\]]+\.png)(?:\s+[^\]]*)?\]', core_image_replacer, text, flags=re.IGNORECASE)

    # Clean and flatten Hugo internal links entirely, discarding subdirectory strings
    text = re.sub(r'\[(.*?)\]\(\{\{\s*<\s*relref\s*"[^"|]*?([^"/]+)"\s*>\s*\}\}\)', r'[[\2|\1]]', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'[\2 \1]', text)
    text = re.sub(r'\[\[(?:[^|\]]*/)*([^|\]]+)\|', r'[[\1|', text)

    # Formatting transformations
    text = re.sub(r'^-\s+', r'* ', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*?)$', r'=== \1 ===', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'== \1 ==', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'= \1 =', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r"'''\1'''", text)
    text = re.sub(r'\*(.*?)\*', r"''\1''", text)
    text = re.sub(r'`(.*?)`', r"<code>\1</code>", text)

    # Structural Spacing Cleanup: Compress accidental vertical layout gaps
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'(==+.*?==+)\n+', r'\1\n', text)
    text = re.sub(r'(\|\})\n{2,}', r'\1\n', text)
    text = re.sub(r'\n{2,}(\{\|\s*class)', r'\n\1', text)

    # Link Fix: Enforce precise case-insensitive mapping fixes for the Animal Lore skill target link
    text = re.sub(r'\[\[animallore\|', r'[[Animal Lore|', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\[animallore\]\]', r'[[Animal Lore]]', text, flags=re.IGNORECASE)
    text = text.replace("Animal Lore|Animal Lore", "Animal Lore")

    return text.strip()


def process_md_file(download_url, folder_name):
    """Downloads content from target index files and exports processed media wiki files."""
    file_response = requests.get(download_url, headers=get_headers())
    if file_response.status_code != 200:
        return

    mediawiki_content = md_to_mediawiki(file_response.text)

    lookup_key = folder_name.lower().replace("-", "").replace("_", "")
    if lookup_key in NAME_OVERRIDES:
        base_title = NAME_OVERRIDES[lookup_key]
    else:
        base_title = folder_name.replace("-", " ").replace("_", " ").title()

    file_title = base_title.replace('/', '_').replace('&', 'and')

    # Track inside Category:Mechanics to pipe straight into your dashboard Card 2
    mediawiki_content += "\n\n[[Category:Mechanics]]"

    output_file_path = os.path.join(OUTPUT_DIR, f"{file_title}.txt")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(mediawiki_content)
    print(f"  Generated mechanics page for: {base_title}")


def main():
    """Iterates through target directories to find index.md files while ignoring _index.md files."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"Scanning Endpoint: MISC / SHARD MECHANICS")
    response = requests.get(API_URL, headers=get_headers())
    if response.status_code != 200:
        print(f"  Skipping endpoint. Status: {response.status_code}")
        return

    items = response.json()
    for item in items:
        # If it's a directory, drill inside to look for standard page content index files
        if item['type'] == 'dir':
            folder_name = item['name']
            sub_res = requests.get(item['url'], headers=get_headers())
            if sub_res.status_code == 200:
                for sub_item in sub_res.json():
                    # Process index files but explicitly skip structural _index configs
                    if sub_item['name'] == 'index.md' and sub_item['name'] != '_index.md':
                        process_md_file(sub_item['download_url'], folder_name)

if __name__ == "__main__":
    main()
