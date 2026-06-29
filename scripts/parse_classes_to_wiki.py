#!/usr/bin/env python3
"""
Zuluhotel Class Documentation ETL Pipeline Script
===========================================================================
This script automatically pulls raw Markdown files from the Hugo website repository
via the GitHub API, parses them into MediaWiki format, sanitizes elements like shortcodes,
and structures clean output text files inside the staging directory ready for import.

PROJECT SETTINGS:
- Target Host Path: ~/git/zuluhotel_omega_wiki/scripts/parse_classes_to_wiki.py
- Local Token Path: ~/git/zuluhotel_omega_wiki/scripts/.env (Contains: GITHUB_TOKEN=ghp_...)
- Category Tagging: All created assets are assigned to [[Category:Classes]]

DEVOPS RUNBOOK / STANDALONE IMPORT SEQUENCE:
---------------------------------------------------------------------------
# 1. Clear any old text staging assets and execute this script
rm -rf ~/wiki_import/*.txt
python3 ~/git/zuluhotel_omega_wiki/scripts/parse_classes_to_wiki.py

# 2. Copy the newly formatted text assets into the Docker container
sudo docker cp ~/wiki_import/. zuluhotelomega-wiki:/var/www/html/maintenance/wiki_import/

# 3. Run the MediaWiki import script to create/overwrite live articles
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php importTextFiles.php --prefix "" --overwrite /var/www/html/maintenance/wiki_import/*.txt

# 4. Clean up local and container text file staging areas
sudo docker exec -it zuluhotelomega-wiki rm -rf /var/www/html/maintenance/wiki_import
rm -rf ~/wiki_import

# 5. DevOps Cleanup: Direct DB query extraction to avoid stdClass object wrapper clutter
sudo docker exec -i zuluhotelomega-wiki-db mysql -u Nagash -p<password> zhowikidb -N -e "SELECT page_title FROM page WHERE page_namespace = 0 AND page_title LIKE 'Classes_%';" | sed '/^[[:space:]]*$/d' > to_clean.list

cat << EOF >> to_clean.list
Bladesinger
Crafter
Paladin
Powerplayer
Mystic_Archer
EOF

if [ -s to_clean.list ]; then
    sudo docker cp to_clean.list zuluhotelomega-wiki:/var/www/html/maintenance/to_clean.list
    sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php deleteBatch.php --r "DevOps Cleanup: Eliminating legacy class titles" /var/www/html/maintenance/to_clean.list
    sudo docker exec -i zuluhotelomega-wiki rm -f /var/www/html/maintenance/to_clean.list
fi
rm -f to_clean.list

# 6. Flush systemic caches and synchronize CategoryTree link indices
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php updateCollation.php --force
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php refreshLinks.php
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php runJobs.php
sudo docker exec -u www-data -it zuluhotelomega-wiki php /var/www/html/maintenance/run.php purgeParserCache.php --age 0
---------------------------------------------------------------------------
"""

import os
import re
import requests

# Project Configuration
SHARD_NAME = "Zuluhotel"
API_URL = "https://api.github.com/repos/Andries1985/zuluhotelomega-website/contents/content/infovault/classes?ref=master"
OUTPUT_DIR = os.path.expanduser("~/wiki_import")

# Secure Token Loading Engine
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Fallback: Read from the local .env file excluded via .gitignore
if not GITHUB_TOKEN:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as env_file:
            for line in env_file:
                if line.strip().startswith("GITHUB_TOKEN="):
                    GITHUB_TOKEN = line.split("=", 1)[1].strip()
                    break

def get_headers():
    """Generates authentication headers if a token is present."""
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def md_to_mediawiki(text):
    """
    Converts Hugo Markdown syntax to optimized MediaWiki formatting.
    """
    # Remove Hugo front matter (yaml blocks between ---)
    text = re.sub(r'^---[\s\S]+?---', '', text)
    
    # Enforce correct shard spelling capitalization
    text = re.sub(r'Zoulouhotel', SHARD_NAME, text, flags=re.IGNORECASE)
    
    # Convert Hugo relref patterns [Skill Name]({{< relref "..." >}}) to [[Skill Name]]
    text = re.sub(r'\[(.*?)\]\(\{\{\s*<\s*relref\s*".*?"\s*>\s*\}\}\)', r'[[\1]]', text)
    
    # Convert standard Markdown links [Label](URL) to MediaWiki external links https://www.merriam-webster.com/dictionary/label
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'[\2 \1]', text)
    
    # Convert Markdown list hyphens to MediaWiki asterisks
    text = re.sub(r'^-\s+', r'* ', text, flags=re.MULTILINE)
    
    # Convert Headers (### to ==)
    text = re.sub(r'^### (.*?)$', r'=== \1 ===', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'== \1 ==', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'= \1 =', text, flags=re.MULTILINE)
    
    # Convert Bold (**text** to '''text''')
    text = re.sub(r'\*\*(.*?)\*\*', r"'''\1'''", text)
    
    # Convert Italics (*text* to ''text'')
    text = re.sub(r'\*(.*?)\*', r"''\1''", text)
    
    # Convert inline code (`code` to <code>code</code>)
    text = re.sub(r'`(.*?)`', r"<code>\1</code>", text)
    
    return text.strip()

def process_md_file(download_url, class_name):
    """Downloads and parses an individual markdown file using auth headers."""
    file_response = requests.get(download_url, headers=get_headers())
    if file_response.status_code != 200:
        print(f"  Failed to download content for {class_name}. Skipping.")
        return
        
    mediawiki_content = md_to_mediawiki(file_response.text)
    
    base_title = class_name.replace("-", " ").replace("_", " ").title()
    
    # Clean file titles giving you exact clean page names without prefix rejections
    if "General" in base_title or base_title == "":
        file_title = "Classes_General_Info"
    else:
        file_title = f"{base_title}_Class"
        
    # Append Category Tree linkage
    mediawiki_content += "\n\n[[Category:Classes]]"
    
    # Save the file using clean filenames
    output_file_path = os.path.join(OUTPUT_DIR, f"{file_title}.txt")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(mediawiki_content)
        
    print(f"  Successfully generated: {output_file_path}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not found in environment or local .env file. Running unauthenticated.")

    print("Fetching top-level directory manifest from GitHub API...")
    response = requests.get(API_URL, headers=get_headers())
    
    if response.status_code != 200:
        print(f"Failed to fetch directory listing. Status: {response.status_code}")
        if response.status_code == 403:
            print("Rate limit exceeded. Check your token credentials inside .env configuration.")
        return

    items = response.json()
    print("Starting Zuluhotel Class Nested ETL Pipeline processing...")
    
    for item in items:
        if item['type'] == 'dir':
            class_name = item['name']
            print(f"Checking subdirectory: {class_name}...")
            
            sub_res = requests.get(item['url'], headers=get_headers())
            if sub_res.status_code == 200:
                sub_items = sub_res.json()
                for sub_item in sub_items:
                    if sub_item['name'] in ['index.md', '_index.md']:
                        process_md_file(sub_item['download_url'], class_name)

        elif item['type'] == 'file' and item['name'] in ['index.md', '_index.md']:
            print("Found top-level general info file...")
            process_md_file(item['download_url'], "General Info")

    print("Class extraction and processing complete.")

if __name__ == "__main__":
    main()
