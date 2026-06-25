#!/usr/bin/env python3
"""
Zuluhotel Omega NPC Configuration Parser
========================================
Description: Parses 'npcdesc.cfg', groups specific keys to Loot Information and
             Slayer Types, and formats the payload for MediaWiki rendering.
"""

import sys
import os
import re

DEFAULT_INPUT_DIR = os.path.expanduser("~/git/zuluhotel_omega_wiki/scripts/input")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/git/zuluhotel_omega_wiki/scripts/output")
DEFAULT_CFG_PATH = os.path.join(DEFAULT_INPUT_DIR, "npcdesc.cfg")

def clean_name(name_str):
    name_str = name_str.strip('"\'').replace("<random>", "").replace(",", "")
    name_str = ' '.join(name_str.split()).strip()
    lower_name = name_str.lower()
    if lower_name.startswith("a "): name_str = name_str[2:]
    elif lower_name.startswith("an "): name_str = name_str[3:]
    elif lower_name.startswith("the "): name_str = name_str[4:]
    return name_str.strip().title()

def clean_cprop_value(val):
    val = val.strip('"\'')
    if val.startswith('s'):
        return val[1:].title()
    if val.startswith('i'):
        remaining = val[1:]
        if remaining.isdigit() or (remaining.startswith('-') and remaining[1:].isdigit()):
            return remaining
    return val.title()

def convert_to_decimal_str(val_str):
    val_str = val_str.strip()
    try:
        if val_str.lower().startswith('0x'):
            return str(int(val_str, 16))
        return str(int(val_str, 10))
    except ValueError:
        return val_str.title()

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
            if header_content and not header_content.startswith('==') and not re.match(r'^[\s*/#=-]+$', header_content):
                current_category = header_content
                continue

        if not in_block:
            match = re.match(r'NpcTemplate\s+(\w+)', stripped, re.IGNORECASE)
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
        'summary': {},
        'loot': {},
        'other': {},
        'resistances': {},
        'attributes': {},
        'skills': {},
        'spells': []
    }

    DROPPED_PROPERTIES = {'dstart', 'saywords', 'movemode', 'deathsnd', 'cast_pct', 'num_casts', 'equip', 'truecolor', '{'}
    CORE_STATS = {'str', 'dex', 'int', 'basestrmod', 'basedexmod', 'baseintmod'}
    
    # Valid skills derived strictly from image_842ddb.png
    VALID_SKILLS = {
        "alchemy", "anatomy", "animal lore", "item identification", "arms lore", 
        "parrying", "begging", "blacksmithing", "bowcraft/fletching", "peacemaking", 
        "camping", "carpentry", "cartography", "cooking", "detecting hidden", 
        "enticement", "evaluating intelligence", "healing", "fishing", "forensic evaluation", 
        "herding", "hiding", "provocation", "inscription", "lockpicking", 
        "magery", "resisting spells", "tactics", "snooping", "musicianship", 
        "poisoning", "archery", "spirit speak", "stealing", "tailoring", 
        "animal taming", "taste identification", "tinkering", "tracking", "veterinary", 
        "swordsmanship", "mace fighting", "fencing", "wrestling", "lumberjacking", 
        "mining", "meditation", "stealth", "remove trap", "necromancy", 
        "focus", "chivalry", "bushido", "ninjitsu", "spellweaving", 
        "mysticism", "imbuing", "throwing"
    }

    for line in lines:
        line = line.strip()
        if not line or line.startswith('//') or line == '}':
            continue

        tokens = line.split()
        if not tokens:
            continue
        raw_key = tokens[0]
        key_lower = raw_key.lower()

        if key_lower in DROPPED_PROPERTIES:
            continue

        if key_lower == 'spell':
            spell_val = re.search(r'spell\s+(.+)', line, re.IGNORECASE).group(1).strip()
            npc_data['spells'].append(spell_val.title())
            continue
        elif key_lower == 'name':
            name_val = re.search(r'Name\s+(.+)', line).group(1).strip()
            npc_data['Name'] = clean_name(name_val)
            continue

        val_str = ' '.join(tokens[1:])
        final_key = raw_key
        final_val = val_str

        if key_lower == 'cprop':
            if len(tokens) >= 3:
                final_key = tokens[1]
                final_val = clean_cprop_value(' '.join(tokens[2:]))
        else:
            final_val = val_str.title()

        if final_key.lower() == 'parry': final_key = 'Parrying'
        elif final_key.lower() == 'macefighting': final_key = 'Mace Fighting'
        elif final_key.lower() == 'tameskill': final_key = 'Taming Required'
        elif final_key.lower() == 'provoke': final_key = 'Provocation Required'
        elif final_key.lower() == 'snoopme': final_key = 'Snooping Required'
        elif final_key.lower() == 'stealme': final_key = 'Stealing Required'
        elif final_key.lower() == 'peacemaking': final_key = 'Peacemaking Required'

        if final_key.title() == 'Gender' and final_val.strip() == '0':
            continue
        if final_val.strip() == '0' and final_key.lower() not in ['alignment', 'objtype', 'type']:
            continue

        final_key_title = final_key.title()

        if final_key.lower() in ['alignment', 'objtype', 'type']:
            npc_data['summary'][final_key.lower()] = final_val
        elif final_key.lower() in ['lootgroup', 'magicitemchance', 'magicitemlevel']:
            npc_data['loot'][final_key_title] = final_val
        elif final_key.lower().endswith('protection'):
            npc_data['resistances'][final_key_title] = final_val
        elif final_key.lower() in CORE_STATS:
            npc_data['attributes'][final_key_title] = final_val
        elif final_key.lower() in VALID_SKILLS:
            npc_data['skills'][final_key_title] = final_val
        else:
            npc_data['other'][final_key_title] = final_val

    if 'Name' not in npc_data or not npc_data['Name']:
        npc_data['Name'] = template_id.title()

    return npc_data

def generate_mediawiki_pages(npcs, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    npc_titles = set()
    
    ATTR_ORDER = ['Str', 'Dex', 'Int', 'Basestrmod', 'Basedexmod', 'Baseintmod']

    for npc in npcs:
        npc_titles.add(npc['Name'])
        filename = f"{npc['Name'].replace(' ', '_')}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            f.write(f"[[Category:NPCs]]\n")
            f.write(f"[[Category:{npc['category']}]]\n\n")
            
            f.write('<div class="uo-profile-card">\n\n')
            f.write('  <div class="uo-card-canvas">\n')
            f.write(f"    [[File:{npc['Name'].replace(' ', '_')}.png|240px]]\n")
            f.write('  </div>\n\n')
            f.write(f'  <div class="uo-card-title">{npc["Name"]}</div>\n\n')
            
            # 1. Summary Section
            f.write('  <div class="uo-section-header">Summary</div>\n  <div class="uo-data-group">\n')
            f.write(f'    <div class="uo-data-row"><span class="uo-label">Category</span><span class="uo-value">[[:Category:{npc["category"]}|{npc["category"]}]]</span></div>\n')
            if 'alignment' in npc['summary']:
                f.write(f'    <div class="uo-data-row"><span class="uo-label">Alignment</span><span class="uo-value">{npc["summary"]["alignment"].title()}</span></div>\n')
            if 'type' in npc['summary']:
                f.write(f'    <div class="uo-data-row"><span class="uo-label">Slayer Type</span><span class="uo-value">{npc["summary"]["type"].title()}</span></div>\n')
            if 'objtype' in npc['summary']:
                dec_graphic_id = convert_to_decimal_str(npc['summary']['objtype'])
                f.write(f'    <div class="uo-data-row"><span class="uo-label">Graphic ID</span><span class="uo-value">{dec_graphic_id}</span></div>\n')
            f.write('  </div>\n\n')
            
            # 2. Attributes Section
            if npc['attributes']:
                f.write('  <div class="uo-section-header">Attributes</div>\n  <div class="uo-data-group">\n')
                for attr in ATTR_ORDER:
                    if attr in npc['attributes']:
                        f.write(f'    <div class="uo-data-row"><span class="uo-label">{attr}</span><span class="uo-value">{npc["attributes"][attr]}</span></div>\n')
                f.write('  </div>\n\n')
            
            # 3. Skills Section
            if npc['skills']:
                f.write('  <div class="uo-section-header">Skills</div>\n  <div class="uo-data-group">\n')
                for sk_k, sk_v in sorted(npc['skills'].items()):
                    f.write(f'    <div class="uo-data-row"><span class="uo-label">{sk_k}</span><span class="uo-value">{sk_v}</span></div>\n')
                f.write('  </div>\n\n')

            # 4. Resistances Section
            if npc['resistances']:
                f.write('  <div class="uo-section-header">Resistances</div>\n  <div class="uo-data-group">\n')
                for res_k, res_v in sorted(npc['resistances'].items()):
                    f.write(f'    <div class="uo-data-row"><span class="uo-label">{res_k}</span><span class="uo-value">{res_v}</span></div>\n')
                f.write('  </div>\n\n')
                
            # 5. Known Spells Section
            if npc['spells']:
                f.write('  <div class="uo-section-header">Known Spells</div>\n  <div class="uo-data-group">\n')
                for index, spell in enumerate(sorted(npc['spells']), 1):
                    f.write(f'    <div class="uo-data-row"><span class="uo-label">Spell {index}</span><span class="uo-value">[[{spell}]]</span></div>\n')
                f.write('  </div>\n\n')

            # 6. Loot Information Section (New Block)
            if npc['loot']:
                f.write('  <div class="uo-section-header">Loot Information</div>\n  <div class="uo-data-group">\n')
                for key, val in sorted(npc['loot'].items()):
                    if key.lower() == 'lootgroup':
                        f.write(f'    <div class="uo-data-row"><span class="uo-label">[[:Category:Lootgroups|Lootgroup]]</span><span class="uo-value">[[Lootgroup {val}|{val}]]</span></div>\n')
                    else:
                        f.write(f'    <div class="uo-data-row"><span class="uo-label">{key}</span><span class="uo-value">{val}</span></div>\n')
                f.write('  </div>\n\n')

            # 7. Other Section
            if npc['other']:
                f.write('  <div class="uo-section-header">Other</div>\n  <div class="uo-data-group">\n')
                for key, val in sorted(npc['other'].items()):
                    if key.lower() == 'hostile': val = 'Yes' if val == '1' else 'No'
                    elif key.lower() in ['script', 'objtype']: val = f"<code>{val.lower()}</code>"
                    f.write(f'    <div class="uo-data-row"><span class="uo-label">{key}</span><span class="uo-value">{val}</span></div>\n')
                f.write('  </div>\n\n')
                
            f.write('</div>\n')

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
