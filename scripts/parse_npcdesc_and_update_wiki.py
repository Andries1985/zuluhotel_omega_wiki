#!/usr/bin/env python3
"""
Zoulouhotel Omega NPC Configuration Parser
========================================
File: parse_npcdesc_and_update_wiki.py
Description: Parses 'npcdesc.cfg', groups variants under a base name page,
             and uses a single unified tabber block inside the profile card
             to dynamically swap images and stats in perfect synchronization.
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
    uncategorized_zone = False

    npcs = []
    in_block = False
    block_lines = []
    template_id = ""
    is_block_commented = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('#'):
            continue

        if "uncategorized per category" in stripped.lower():
            uncategorized_zone = True
            current_category = "Uncategorized"
            continue

        if stripped.startswith('//'):
            header_content = stripped.lstrip('/').strip()
            if header_content and not header_content.startswith('==') and not re.match(r'^[\s*/#=-]+$', header_content):
                if not any(x in header_content.lower() for x in ['settings', 'privs', 'guardignore', 'dress', 'uncategorized']):
                    clean_cat = header_content.replace('}', '').replace('{', '').strip()
                    if not clean_cat:  # FIX: Prevent commented curly braces like '// }' from clearing category
                        continue
                    clean_cat_lower = clean_cat.lower().rstrip('.')

                    if clean_cat_lower in ["summons", "book summons", "summon", "songbook summons", "earthbook summons"]:
                        current_category = "Summon"
                    elif "donator animals" in clean_cat_lower:
                        current_category = "Vanity"
                    elif "slayer type" in clean_cat_lower:
                        current_category = clean_cat.replace("Slayer Type", "").replace("sType", "").strip().title()
                    else:
                        current_category = clean_cat
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
                    found_id = template_id.lower()
                    if found_id.startswith("beckon"):
                        assigned_cat = "Summon"
                    elif found_id.startswith("banker") or found_id.startswith("virtuebanker"):
                        assigned_cat = "Townsfolk"
                    else:
                        assigned_cat = current_category if not uncategorized_zone else "Uncategorized"

                    npc_data = process_npc_block(template_id, block_lines, assigned_cat, uncategorized_zone)
                    if npc_data:
                        npcs.append(npc_data)

                in_block = False
                is_block_commented = False
                template_id = ""
                block_lines = []

    return npcs

def process_npc_block(template_id, lines, assigned_category, uncategorized_zone):
    npc_data = {
        'template': template_id,
        'category': assigned_category,
        'is_uncategorized': uncategorized_zone,
        'summary': {},
        'skill_requirements': {},
        'loot': {},
        'other': {},
        'resistances': {},
        'attributes': {},
        'skills': {},
        'spells': []
    }

    # Added requested keys to drop list
    DROPPED_PROPERTIES = {
        'dstart', 'saywords', 'movemode', 'deathsnd', 'cast_pct', 'num_casts',
        'equip', 'truecolor', '{', 'speech', 'guardignore', 'dress', 'script',
        'settings', 'privs', 'basehpregen', 'basemanaregen', 'virtue', 
        'merchanttype', 'equipt', 'missileweapon', 'ammoamount', 'ammotype'
    }
    CORE_STATS = {'str', 'dex', 'int', 'basestrmod', 'basedexmod', 'baseintmod'}

    VALID_SKILLS = {
        "alchemy", "anatomy", "animal lore", "item identification", "arms lore",
        "parrying", "begging", "blacksmithing", "bowcraft/fletching", "peacemaking",
        "camping", "carpentry", "cartography", "cooking", "detecting hidden", "detectinghidden",
        "enticement", "evaluating intelligence", "evaluatingintelligence", "healing", "fishing",
        "forensic evaluation", "herding", "hiding", "provocation", "inscription", "lockpicking",
        "magery", "resisting spells", "tactics", "snooping", "musicianship",
        "poisoning", "archery", "spirit speak", "stealing", "tailoring",
        "animal taming", "taste identification", "tinkering", "tracking", "veterinary",
        "swordsmanship", "mace fighting", "fencing", "wrestling", "lumberjacking",
        "mining", "meditation", "stealth", "remove trap", "necromancy",
        "focus", "chivalry", "bushido", "ninjitsu", "spellweaving",
        "mysticism", "imbuing", "throwing", "animal lore", "animal taming"
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

        # Handle Re-routing and Renaming rules
        final_key_lower = final_key.lower()
        if final_key_lower == 'parry': final_key = 'Parrying'
        elif final_key_lower == 'macefighting': final_key = 'Mace Fighting'
        elif final_key_lower == 'detectinghidden': final_key = 'Detecting Hidden'
        elif final_key_lower == 'evaluatingintelligence': final_key = 'Evaluating Intelligence'
        elif final_key_lower == 'tameskill': final_key = 'Taming Required'
        elif final_key_lower == 'provoke': final_key = 'Provocation Required'
        elif final_key_lower == 'snoopme': final_key = 'Snooping Required'
        elif final_key_lower == 'stealme': final_key = 'Stealing Required'
        elif final_key_lower == 'peacemaking': final_key = 'Peacemaking Required'
        elif final_key_lower == 'permmagicimmunity': final_key = 'Magic Immunity'
        elif final_key_lower == 'permpoisonimmunity': final_key = 'Poison Immunity'
        elif final_key_lower == 'permmr': final_key = 'Magic Reflect'
        elif final_key_lower == 'airprotection': final_key = 'Air Protection'
        elif final_key_lower == 'earthprotection': final_key = 'Earth Protection'
        elif final_key_lower == 'fireprotection': final_key = 'Fire Protection'
        elif final_key_lower == 'holyprotection': final_key = 'Holy Protection'
        elif final_key_lower == 'necroprotection': final_key = 'Necro Protection'
        elif final_key_lower == 'waterprotection': final_key = 'Water Protection'
        elif final_key_lower == 'customhitslevel': final_key = 'Health Points'
        elif final_key_lower == 'magicitemchance': final_key = 'Magic Item Chance'
        elif final_key_lower == 'magicitemlevel': final_key = 'Magic Item Level'
        elif final_key_lower == 'attackattribute': final_key = 'Attack Attribute'
        elif final_key_lower == 'attackdamage': final_key = 'Attack Damage'
        elif final_key_lower == 'attackspeed': final_key = 'Attack Speed'
        elif final_key_lower == 'nocorpse': final_key = 'No Corpse'
        elif final_key_lower == 'freeaction': final_key = 'Free Action'
        elif final_key_lower == 'animallore': final_key = 'Animal Lore'
        elif final_key_lower == 'animaltaming': final_key = 'Animal Taming'

        # Yes/No Boolean Normalization
        if final_key.lower() in ['nocorpse', 'looter', 'boss', 'superboss']:
            final_val = 'Yes' if final_val.strip() in ['1', 'Boss 1', 'Superboss 1'] else 'No'

        if final_key.title() == 'Gender' and final_val.strip() == '0':
            continue
        if final_val.strip() == '0' and final_key.lower() not in ['alignment', 'objtype', 'type', 'boss', 'superboss', 'no corpse', 'looter']:
            continue

        final_key_title = final_key.title()

        if final_key.lower() in ['alignment', 'objtype', 'type']:
            npc_data['summary'][final_key.lower()] = final_val
        elif 'required' in final_key.lower():
            npc_data['skill_requirements'][final_key_title] = final_val
        elif final_key.lower() in ['lootgroup', 'magic item chance', 'magic item level']:
            npc_data['loot'][final_key_title] = final_val
        elif final_key.lower().endswith('protection') or final_key.lower() in ['magic immunity', 'poison immunity', 'magic reflect', 'free action']:
            npc_data['resistances'][final_key_title] = final_val
        elif final_key.lower() in CORE_STATS:
            npc_data['attributes'][final_key_title] = final_val
        elif final_key.lower() in VALID_SKILLS or final_key in ['Animal Lore', 'Animal Taming']:
            npc_data['skills'][final_key] = final_val
        else:
            npc_data['other'][final_key_title] = final_val

    # Apply Stat Modifiers dynamically to base core stats
    for stat in ['Str', 'Dex', 'Int']:
        mod_key = f'Base{stat.lower()}mod'
        if mod_key in npc_data['attributes']:
            try:
                base_val = int(npc_data['attributes'].get(stat, 0))
                mod_val = int(npc_data['attributes'][mod_key])
                npc_data['attributes'][stat] = str(base_val + mod_val)
            except ValueError:
                pass
            del npc_data['attributes'][mod_key]

    if 'Name' not in npc_data or not npc_data['Name']:
        base_template = re.sub(r'\d+$', '', template_id)
        npc_data['Name'] = base_template.title()

    if npc_data['category'] == "Vanity" and not npc_data['Name'].startswith("Vanity"):
        npc_data['Name'] = f"Vanity {npc_data['Name']}"

    return npc_data

def generate_mediawiki_pages(npcs, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    grouped_npcs = {}
    for npc in npcs:
        title = npc['Name']
        if title not in grouped_npcs:
            grouped_npcs[title] = []
        grouped_npcs[title].append(npc)

    ATTR_ORDER = ['Str', 'Dex', 'Int']
    RESIST_ORDER = [
        'Air Protection', 'Earth Protection', 'Fire Protection', 'Water Protection',
        'Holy Protection', 'Necro Protection', 'Magic Immunity', 'Magic Reflect', 
        'Poison Immunity', 'Free Action'
    ]

    for title, variant_list in grouped_npcs.items():
        filename = f"{title.replace(' ', '_')}.txt"
        filepath = os.path.join(output_dir, filename)

        first_npc = variant_list[0]
        use_tabber = len(variant_list) > 1

        with open(filepath, 'w') as f:
            f.write(f"[[Category:NPCs]]\n")
            f.write(f"[[Category:{first_npc['category']}]]\n\n")

            f.write('<div class="uo-profile-card">\n\n')

            if use_tabber:
                f.write("{{#tag:tabber|\n")

            for idx, npc in enumerate(variant_list):
                if use_tabber:
                    if idx > 0:
                        f.write("{{!}}-{{!}}\n")
                    f.write(f" {npc['template'].upper()} =\n")

                if npc['is_uncategorized']:
                    f.write('  <div class="uo-card-canvas" style="position: relative; box-shadow: 0 0 12px 2px rgba(239, 68, 68, 0.7); border: 1px solid #ef4444; margin-top: 10px;">\n')
                else:
                    f.write('  <div class="uo-card-canvas" style="position: relative; margin-top: 10px;">\n')

                if use_tabber:
                    v_image = f"{title.replace(' ', '_')}_{npc['template'].upper()}.png"
                else:
                    v_image = f"{title.replace(' ', '_')}.png"

                f.write(f"    [[File:{v_image}|240px]]\n")

                if npc['is_uncategorized']:
                    f.write('    <div class="npc-tooltip-trigger" style="position: absolute; top: 8px; right: 8px; background: #ef4444; color: #ffffff; width: 20px; height: 20px; border-radius: 50%; text-align: center; font-size: 12px; font-weight: bold; line-height: 20px; cursor: help;" title="Warning: This variant contains uncategorized layout data.">!</div>\n')

                f.write('  </div>\n\n')

                f.write(f'  <div class="uo-card-title">{title}</div>\n\n')

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

                if npc['attributes']:
                    f.write('  <div class="uo-section-header">Attributes</div>\n  <div class="uo-data-group">\n')
                    for attr in ATTR_ORDER:
                        if attr in npc['attributes']:
                            f.write(f'    <div class="uo-data-row"><span class="uo-label">{attr}</span><span class="uo-value">{npc["attributes"][attr]}</span></div>\n')
                    f.write('  </div>\n\n')

                if npc['skills']:
                    f.write('  <div class="uo-section-header">Skills</div>\n  <div class="uo-data-group">\n')
                    for sk_k, sk_v in sorted(npc['skills'].items()):
                        f.write(f'    <div class="uo-data-row"><span class="uo-label">{sk_k}</span><span class="uo-value">{sk_v}</span></div>\n')
                    f.write('  </div>\n\n')

                if npc['resistances']:
                    f.write('  <div class="uo-section-header">Resistances</div>\n  <div class="uo-data-group">\n')
                    for res_k in RESIST_ORDER:
                        if res_k in npc['resistances']:
                            f.write(f'    <div class="uo-data-row"><span class="uo-label">{res_k}</span><span class="uo-value">{npc["resistances"][res_k]}</span></div>\n')
                    f.write('  </div>\n\n')

                if npc['spells']:
                    f.write('  <div class="uo-section-header">Known Spells</div>\n  <div class="uo-data-group">\n')
                    for idx_s, spell in enumerate(sorted(npc['spells']), 1):
                        f.write(f'    <div class="uo-data-row"><span class="uo-label">Spell {idx_s}</span><span class="uo-value">[[{spell}]]</span></div>\n')
                    f.write('  </div>\n\n')

                if npc['skill_requirements']:
                    f.write('  <div class="uo-section-header">Skill Requirements</div>\n  <div class="uo-data-group">\n')
                    for req_k, req_v in sorted(npc['skill_requirements'].items()):
                        f.write(f'    <div class="uo-data-row"><span class="uo-label">{req_k}</span><span class="uo-value">{req_v}</span></div>\n')
                    f.write('  </div>\n\n')

                if npc['loot']:
                    f.write('  <div class="uo-section-header">Loot Information</div>\n  <div class="uo-data-group">\n')
                    for key, val in sorted(npc['loot'].items()):
                        if key.lower() == 'lootgroup':
                            f.write(f'    <div class="uo-data-row"><span class="uo-label">[[:Category:Lootgroups|Lootgroup]]</span><span class="uo-value">[[Lootgroup {val}|{val}]]</span></div>\n')
                        else:
                            f.write(f'    <div class="uo-data-row"><span class="uo-label">{key}</span><span class="uo-value">{val}</span></div>\n')
                    f.write('  </div>\n\n')

                if npc['other']:
                    f.write('  <div class="uo-section-header">Other</div>\n  <div class="uo-data-group">\n')
                    for key, val in sorted(npc['other'].items()):
                        if key.lower() == 'hostile': val = 'Yes' if val == '1' else 'No'
                        elif key.lower() in ['objtype']: val = f"<code>{val.lower()}</code>"
                        
                        # Added internal routing for Karma and Fame Wiki Page redirects
                        if key.lower() in ['karma', 'fame']:
                            f.write(f'    <div class="uo-data-row"><span class="uo-label">[[{key.title()}]]</span><span class="uo-value">{val}</span></div>\n')
                        else:
                            f.write(f'    <div class="uo-data-row"><span class="uo-label">{key}</span><span class="uo-value">{val}</span></div>\n')
                    f.write('  </div>\n\n')

            if use_tabber:
                f.write("}}\n")

            f.write('</div>\n')

    manifest_path = os.path.join(output_dir, "current_npcs.list")
    with open(manifest_path, 'w') as f:
        for title in sorted(grouped_npcs.keys()):
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
    print(f"✨ Parse Complete. Synchronized nested variant layouts inside {len(npcs)} core profiles.")

if __name__ == "__main__":
    main()
