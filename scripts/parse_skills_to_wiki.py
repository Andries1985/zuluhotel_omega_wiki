#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zuluhotel Skills Documentation ETL Pipeline Script
===========================================================================
An automated ETL (Extract, Transform, Load) utility designed to parse raw
Markdown data from a GitHub Hugo repository and format it into clean,
well-structured MediaWiki syntax optimized for the Zuluhotel Omega Database.

Architecture & Workflow Pipeline:
---------------------------------
1. EXTRACT:   Queries the GitHub API to discover files located under the 
              remote content path (`/content/infovault/skills`). It crawls
              directories and downloads raw `index.md` / `_index.md` payloads.
2. TRANSFORM: Sanitizes metadata, converts complex nested HTML components 
              (<details> wrapper tables) into compliant sorting MediaWiki tables,
              flattens Hugo shortcode routing (`{{< relref >}}`), updates regional
              references, and formats typographic weights (**bold**, *italics*, `code`).
3. LOAD:      Writes standardized plain-text intermediate files (.txt) into 
              the target staging directory (`~/wiki_import`) mapped exactly to
              MediaWiki structural title names.

Configuration Environment Variables:
------------------------------------
* GITHUB_TOKEN : Optional/Recommended string authentication token. Used to 
                 prevent API rate limiting on high-frequency asset sweeps.
                 Can be placed in a local `.env` file alongside this script.

Dependencies:
-------------
* python3
* requests (Standard HTTP client binding layer)

Usage & Deployment Lifecycle:
-----------------------------
    $ python3 parse_skills_to_wiki.py
"""

import os
import re
import requests

# ===========================================================================
# GLOBAL CONFIGURATION MATRIX
# ===========================================================================

# Shard regional variable naming replacement string target
SHARD_NAME = "Zuluhotel"

# Remote GitHub Contents API endpoint for scanning skills content folders
API_URL = "https://api.github.com/repos/Andries1985/zuluhotelomega-website/contents/content/infovault/skills?ref=master"

# Local staging path where intermediate migration assets are compiled
OUTPUT_DIR = os.path.expanduser("~/wiki_import")

# Attempt authentication credentials fallback resolution
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as env_file:
            for line in env_file:
                if line.strip().startswith("GITHUB_TOKEN="):
                    GITHUB_TOKEN = line.split("=", 1)[1].strip()
                    break

# Static map aligning raw Hugo content folder labels with destination MediaWiki article titles
SKILL_NAME_OVERRIDES = {
    "armslore": "Arms Lore",
    "animallore": "Animal Lore",
    "animaltaming": "Animal Taming",
    "bowcraftfletching": "Bowcraft & Fletching",
    "resistingspells": "Magic Resistance",
    "detectinghidden": "Detecting Hidden",
    "evaluatingintelligence": "Evaluating Intelligence",
    "forensicevaluation": "Forensic Evaluation",
    "itemidentification": "Item Identification",
    "macefighting": "Mace Fighting",
    "removetrap": "Remove Trap",
    "spiritspeak": "Spirit Speak",
    "tasteidentification": "Taste Identification"
}

# ===========================================================================
# ETL PIPELINE SUBPROCESSES
# ===========================================================================

def get_headers():
    """
    Constructs default network headers for structural API communication layers.
    
    Returns:
        dict: Headers containing proper API versioning specifications and optional
              OAuth authorization tokens if available.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def clean_cell_text(text):
    """
    Applies custom typographical string normalization adjustments to individual 
    table cell values. Strips out extraneous leading articles to make sort rows clean.
    
    Args:
        text (str): Raw string slice parsed out of an individual markdown cell.
        
    Returns:
        str: Sanitized cell value.
    """
    return re.sub(r'^(a|an)\s+', '', text.strip(), flags=re.IGNORECASE).strip()


def convert_markdown_tables(text):
    """
    Scans entire raw source documents to locate, extract, and replace markdown
    pipe-table notation grids with native MediaWiki table objects.
    
    This parser breaks raw files into discrete text streams, scrubs out wrapping
    HTML details blocks (<details>, <summary>), monitors block transitions via pipe 
    delimiters ('|'), and hands structured ranges to the sub-parser layout builder.
    
    Args:
        text (str): Complete multi-line raw source content layout.
        
    Returns:
        str: Transformed document body text featuring natively integrated MediaWiki tables.
    """
    # Force clean structural HTML block constraints out of the data paths
    text = re.sub(r'<details[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</details>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<summary>([\s\S]*?)</summary>', '', text, flags=re.IGNORECASE)

    lines = text.split('\n')
    new_lines = []
    
    in_table = False
    table_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Evaluate if the line represents an active structural component of a markdown table grid
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(stripped)
        else:
            if in_table:
                # Compile table block arrays upon boundary collision events
                if len(table_lines) >= 2:
                    processed_table = parse_collected_table(table_lines)
                    new_lines.append(processed_table)
                else:
                    new_lines.extend(table_lines)
                in_table = False
            new_lines.append(line)
            
    # Trailing safety capture layer check
    if in_table and table_lines:
        if len(table_lines) >= 2:
            new_lines.append(parse_collected_table(table_lines))
        else:
            new_lines.extend(table_lines)

    return '\n'.join(new_lines)


def parse_collected_table(lines):
    """
    Parses an isolated matrix array of markdown string rows and morphs them into 
    an optimized, sortable MediaWiki structural table entity.
    
    Guards against variable column counts via inline alignment adjustments,
    filters away layout separator records (e.g. '|---|---|'), and processes 
    deduplication sweeps across identical entries.
    
    Args:
        lines (list): Raw text rows comprising the detected markdown table grid block.
        
    Returns:
        str: Completely formatted Wiki-syntax sortable data table text block.
    """
    raw_rows = []
    for line in lines:
        # Strip external wall structures and slice inner items cleanly via pipe separations
        cells = [c.strip() for c in line.split('|')[1:-1]]
        raw_rows.append(cells)
        
    if len(raw_rows) < 2:
        return '\n'.join(lines)
        
    headers = raw_rows[0]
    cols = len(headers)
    
    # Identify and skip markdown alignment separator records
    data_start_idx = 1
    if data_start_idx < len(raw_rows) and all(re.match(r'^[-:]+$', c) for c in raw_rows[data_start_idx] if c):
        data_start_idx += 1
        
    # Instantiate layout parameters using standard responsive CSS structures
    mw_table = ['{| class="wikitable sortable" style="width: 100%; border-collapse: collapse;"', '|-']
    mw_table.append('! ' + ' !! '.join(headers))
    
    seen_rows = set()
    for row in raw_rows[data_start_idx:]:
        if not row or all(c == '' for c in row):
            continue
            
        # Ensure column length integrity across the grid horizontal axis
        while len(row) < cols:
            row.append('')
        row = row[:cols]
        
        processed_row = [clean_cell_text(cell) for cell in row]
        row_fingerprint = "||".join(processed_row).lower()
        
        # Deduplicate row objects to strip redundant database records
        if row_fingerprint in seen_rows:
            continue
        seen_rows.add(row_fingerprint)
        
        mw_table.append('|-')
        mw_table.append('| ' + ' || '.join(processed_row))
        
    mw_table.append('|}')
    return '\n' + '\n'.join(mw_table) + '\n'


def md_to_mediawiki(text):
    """
    Executes structural translation mechanics mapping Markdown markers into MediaWiki tags.
    
    Applies comprehensive regex modifications filtering out Hugo Front Matter metadata blocks,
    stripping and flattening internal shortcode path directories, updating typography anchors,
    and handling custom casing rules across navigation components.
    
    Args:
        text (str): Raw Markdown content source text payload.
        
    Returns:
        str: Converted MediaWiki source markup formatting text layout.
    """
    # Remove Hugo parameters/front matter blocks bounded by triple-dashes
    text = re.sub(r'^---[\s\S]+?---', '', text)
    
    # Standardize server/shard regional names
    text = re.sub(r'Zoulouhotel', SHARD_NAME, text, flags=re.IGNORECASE)
    
    # Route structural table conversion matrix sweeps
    text = convert_markdown_tables(text)
    
    # Flatten internal cross-link reference maps (e.g. [Link]({{< relref "skills/musicianship" >}}) -> [[Musicianship|Link]])
    text = re.sub(r'\[(.*?)\]\(\{\{\s*<\s*relref\s*"[^"|]*?([^"/]+)"\s*>\s*\}\}\)', r'[[\2|\1]]', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'[\2 \1]', text)
    
    # Secondary tracking filter layer ensuring deep relative folder prefixes are completely discarded
    text = re.sub(r'\[\[(?:[^|\]]*/)*([^|\]]+)\|', r'[[\1|', text)
    
    # Standardize list indentation tracks
    text = re.sub(r'^-\s+', r'* ', text, flags=re.MULTILINE)
    
    # Translate Title Header layouts sequentially (h3, h2, h1)
    text = re.sub(r'^### (.*?)$', r'=== \1 ===', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'== \1 ==', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'= \1 =', text, flags=re.MULTILINE)
    
    # Map font decorations and markup codes natively
    text = re.sub(r'\*\*(.*?)\*\*', r"'''\1'''", text)
    text = re.sub(r'\*(.*?)\*', r"''\1''", text)
    text = re.sub(r'`(.*?)`', r"<code>\1</code>", text)
    
    # Enforce title capitalization alignments on core targeting parameters
    text = re.sub(r'\[\[musicianship\|', r'[[Musicianship|', text, flags=re.IGNORECASE)
    
    return text.strip()


def process_md_file(download_url, folder_name):
    """
    Retrieves a single target markdown file payload from GitHub, triggers the
    transformation engine, and writes out the file mapped to its permanent title.
    
    Args:
        download_url (str): Remote absolute URL pointing directly to the file raw text string data.
        folder_name (str): The origin folder label used to infer destination wiki filenames.
    """
    file_response = requests.get(download_url, headers=get_headers())
    if file_response.status_code != 200:
        return
        
    # Fire translation procedures
    mediawiki_content = md_to_mediawiki(file_response.text)
    
    # Determine the clean target database title
    lookup_key = folder_name.lower().replace("-", "").replace("_", "")
    if lookup_key in SKILL_NAME_OVERRIDES:
        base_title = SKILL_NAME_OVERRIDES[lookup_key]
    else:
        base_title = folder_name.replace("-", " ").replace("_", " ").title()
        
    # Sanitize titles to comply with file write tracking requirements
    file_title = base_title.replace('/', '_').replace('&', 'and')
    
    # Append global Category mapping tracking rules to the bottom edge of content files
    mediawiki_content += "\n\n[[Category:Skills]]"
    
    output_file_path = os.path.join(OUTPUT_DIR, f"{file_title}.txt")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(mediawiki_content)
    print(f"  Generated page for: {base_title}")


def main():
    """
    Core pipeline conductor routine.
    Initializes environment directories, interrogates the target GitHub repository folder
    tree structure, and sequentially maps child elements into processing tracks.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    response = requests.get(API_URL, headers=get_headers())
    if response.status_code != 200:
        print(f"ERROR: GitHub API tracking interrogation dropped with status code: {response.status_code}")
        return

    items = response.json()
    for item in items:
        # Crawl only directory type wrappers to extract documentation entries cleanly
        if item['type'] == 'dir':
            folder_name = item['name']
            sub_res = requests.get(item['url'], headers=get_headers())
            if sub_res.status_code == 200:
                for sub_item in sub_res.json():
                    # Interrogate index targets inside the folder structure
                    if sub_item['name'] in ['index.md', '_index.md']:
                        process_md_file(sub_item['download_url'], folder_name)


if __name__ == "__main__":
    main()
