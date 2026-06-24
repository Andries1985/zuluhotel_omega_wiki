#!/usr/bin/env python3
"""
Zuluhotel Omega NPC Configuration Parser
========================================
Author: Wiki Administration
Description: Parses 'npcdesc.cfg', sanitizes titles, writes MediaWiki pages,
             and outputs a flat manifest list of all active NPC names to assist 
             the bash pipeline with automated orphan deletion.
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
    name_str = name_str.replace(",", "")  # Strip problematic old commas
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
    blocks = re.findall(r'NpcTemplate\s+(\w+)\s*\{(.*?)\}', config_text, re.DOTALL)
    npcs = []
    
    for template_id, block_content in blocks:
        npc_data = {'template': template_id, 'skills': {}, 'cprops': {}, 'spells': []}
        lines = block_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
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
        npcs.append(npc_data)
    return npcs

def generate_mediawiki_pages(npcs, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # Store plain page titles to pass over to the deletion system manifest
    npc_titles = set()
    
    for npc in npcs:
        npc_titles.add(npc['Name'])
        filename = f"{npc['Name'].replace(' ', '_')}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"[[Category:NPCs]]\n\n")
            f.write(f"= {npc['Name']} =\n\n")
            f.write(f"== Appearance ==\n")
            f.write(f"[[File:{npc['Name'].replace(' ', '_')}.png|thumb|{npc['Name']}]]\n\n")
            f.write(f"----\n\n")
            f.write(f"== General Information ==\n")
            f.write(f"{{| class=\"wikitable\"\n")
            f.write(f"! Property !! Details\n")
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

    # Save the modern dynamic manifest containing only currently parsed names
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
