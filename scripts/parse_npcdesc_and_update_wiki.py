#!/usr/bin/env python3
"""
Zuluhotel Omega NPC Configuration Parser
========================================
Description: Parses 'npcdesc.cfg', assigns contextual categories from header comments,
             drops blocks commented out with '#', and creates the sync manifest.

Recommended Pipeline Execution Sequence:
  1. rm -rf output/*.txt
  2. python3 parse_npcdesc_and_update_wiki.py
  3. ./update_wiki_pages.sh
"""

import sys
import os
import re

DEFAULT_INPUT_DIR = os.path.expanduser("~/git/zuluhotel_omega_wiki/scripts/input")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/git/zuluhotel_omega_wiki/scripts/output")
DEFAULT_CFG_PATH = os.path.join(DEFAULT_INPUT_DIR, "npcdesc.cfg")

def clean_name(name_str):
    name_str = name_str.strip('"\'')
    name_str = name_str.replace("<random>", "")
    name_str = name_str.replace(",", "")  
    name_str = ' '.join(name_str.split())
    
    lower_name = name_str.lower()
    if lower_name.startswith("a "):
        name_str = name_str[2:]
    elif lower_name.startswith("an "):
        name_str = name_str[3:]
    elif lower_name.startswith("the "):
        name_str = name_str[4:]
        
    return name_str.strip().title()

def clean_cprop_value(val):
    val = val.strip('"\'')
    if val.startswith('i') and val[1:].isdigit():
        return val[1:]
    if val.startswith('s'):
        return val[1:]
    return val

def parse_npcs(config_text):
    lines = config_text.split('\n')
    current_category = "General NPCs" 
    
    npcs = []
    in_block = False
    block_lines = []
    template_id = ""
    is_block_commented = False

    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('#'):
            continue
            
        if stripped.startswith('//'):
            header_content = stripped.lstrip('/').strip()
            if header_content and not header_content.startswith('=='):
                if not re.match(r'^[\s*/#=-]+$', header_content):
                    current_category = header_content
                    continue

        if not in_block:
            match = re.match(r'NpcTemplate\s+(\w+)', stripped)
            if match:
                template_id = match.group(1)
                in_block = True
                block_lines = []
                if '#' in line and line.find('#') < line.find('NpcTemplate'):
                    is_block_commented = True
        else:
            if '#' in line:
                line = line.split('#')[0].strip()
                
            block_lines.append(line)
            
            if '}' in stripped:
                if not is_block_commented:
                    npc_data = process_npc_block(template_id, block_lines, current_category)
                    if npc_data:
                        npcs.append(npc_data)
                
                in_block = False
                is_block_commented = False
                template_id = ""
                block_lines = []

    return npcs

def process_npc_block(template_id, lines, assigned_category):
    npc_data = {
        'template': template_id,
        'category': assigned_category,
        'skills': {},
        'cprops': {},
        'spells': []
    }
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('//') or line == '}':
            continue
            
        if line.startswith('spell'):
            spell_match = re.match(r'spell\s+(.+)', line)
            if spell_match:
                npc_data['spells'].append(spell_match.group(1).strip())
            continue
            
        tokens = line.split()
        if not tokens:
            continue
        key = tokens[0]
        
        if key == 'Name':
            name_val = re.search(r'Name\s+(.+)', line).group(1).strip()
            npc_data['Name'] = clean_name(name_val)
        elif key == 'CProp':
            if len(tokens) >= 3:
                cp_key = tokens[1]
                cp_val = clean_cprop_value(' '.join(tokens[2:]))
                if cp_key == 'snoopme':
                    npc_data['cprops']['Snooping Required'] = f"{cp_val} Skill"
                elif cp_key == 'stealme':
                    npc_data['cprops']['Stealing Required'] = f"{cp_val} Skill"
                elif cp_key == 'Type':
                    npc_data['cprops']['Slayer Type'] = cp_val
                else:
                    npc_data['cprops'][cp_key] = cp_val
        else:
            val = ' '.join(tokens[1:])
            if key in ['STR', 'INT', 'DEX', 'HITS', 'MANA', 'STAM']:
                npc_data['skills'][key] = val
            elif key in ['alignment', 'hostile', 'script', 'objtype', 'Color']:
                npc_data[key] = val
            else:
                npc_data['skills'][key] = val
                
    if 'Name' not in npc_data or not npc_data['Name']:
        npc_data['Name'] = template_id.title()
        
    return npc_data

def generate_mediawiki_pages(npcs, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    npc_titles = set()
    
    for npc in npcs:
        npc_titles.add(npc['Name'])
        filename = f"{npc['Name'].replace(' ', '_')}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"[[Category:NPCs]]\n")
            f.write(f"[[Category:{npc['category']}]]\n\n")
            f.write(f"= {npc['Name']} =\n\n")
            f.write(f"== Appearance ==\n")
            f.write(f"[[File:{npc['Name'].replace(' ', '_')}.png|thumb|{npc['Name']}]]\n\n")
            f.write(f"----\n\n")
            f.write(f"== General Information ==\n")
            f.write(f"{{| class=\"wikitable\"\n")
            f.write(f"! Property !! Details\n")
            f.write(f"|-\n| '''Config Category''' || [[Category:{npc['category']}|{npc['category']}]]\n")
            f.write(f"|-\n| '''Alignment''' || {npc.get('alignment', 'Neutral').title()}\n")
            f.write(f"|-\n| '''Hostile''' || {'Yes' if npc.get('hostile') == '1' else 'No'}\n")
            f.write(f"|-\n| '''AI Script''' || <code>{npc.get('script', 'None')}</code>\n")
            f.write(f"|-\n| '''Object Type''' || <code>{npc.get('objtype', 'Unknown')}</code>\n")
            f.write(f"|-\n| '''Color Code''' || {npc.get('Color', 'Default')}\n")
            for cp_k, cp_v in npc['cprops'].items():
                f.write(f"|-\n| '''{cp_k}''' || {cp_v}\n")
            f.write(f"|}}\n\n")
            f.write(f"== Attributes & Combat Skills ==\n")
            f.write(f"{{| class=\"wikitable\"\n")
            f.write(f"! Attribute/Skill !! Value\n")
            for sk_k, sk_v in npc['skills'].items():
                f.write(f"|-\n| {sk_k} || {sk_v}\n")
            f.write(f"|}}\n\n")
            if npc['spells']:
                f.write(f"== Known Spells ==\n")
                for spell in npc['spells']:
                    f.write(f"* {spell.title()}\n")
                f.write(f"\n")

    manifest_path = os.path.join(output_dir, "current_npcs.list")
    with open(manifest_path, 'w') as f:
        for title in sorted(npc_titles):
            f.write(f"{title}\n")

def main():
    if len(sys.argv) >= 2:
        cfg_path = sys.argv[1]
    else:
        cfg_path = DEFAULT_CFG_PATH
        
    if not os.path.exists(cfg_path):
        print(f"❌ Error: Target configuration file not found at '{cfg_path}'")
        sys.exit(1)
        
    print(f"📖 Reading configuration from: {cfg_path}")
    with open(cfg_path, 'r', errors='ignore') as f:
        content = f.read()
        
    npcs = parse_npcs(content)
    generate_mediawiki_pages(npcs, DEFAULT_OUTPUT_DIR)
    print(f"✨ Parse Complete. Tracking {len(npcs)} items in output/current_npcs.list.")

if __name__ == "__main__":
    main()
