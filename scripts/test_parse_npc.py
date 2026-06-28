#!/usr/bin/env python3
"""
Zuluhotel Omega NPC Configuration Parser - Single Asset Test Variant
====================================================================
File: test_parse_npc.py
"""

import sys
import os
import re
import pprint

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

def clean_category(cat_str):
    cat_str = cat_str.strip('"\'')
    # Safe suffix removal BEFORE .title() to preserve the double 's' in Boss
    if cat_str.lower().endswith("boss's"):
        cat_str = cat_str[:-2]
    return ' '.join(cat_str.split()).strip().title()

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

def parse_single_npc(cfg_path, target_template):
    target_template = target_template.lower()

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

    npc = None
    inside_target = False
    last_seen_category = "General NPCs"

    with open(cfg_path, 'r', errors='ignore') as f:
        for line in f:
            stripped = line.strip()

            if stripped.startswith('//'):
                cat_match = re.search(r'CATEGORY:\s*(.+)', stripped, re.IGNORECASE)
                if cat_match:
                    last_seen_category = clean_category(cat_match.group(1))
                continue

            match = re.match(r'NpcTemplate\s+(\w+)', stripped, re.IGNORECASE)
            if match:
                template_id = match.group(1)
                if template_id.lower() == target_template:
                    inside_target = True
                    npc = {
                        'template': template_id,
                        'category': last_seen_category,
                        'is_uncategorized': (last_seen_category.lower() == "uncategorized"),
                        'summary': {},
                        'skill_requirements': {},
                        'loot': {},
                        'other': {},
                        'resistances': {},
                        'attributes': {},
                        'skills': {},
                        'spells': []
                    }
                else:
                    inside_target = False
                continue

            if inside_target and npc is not None:
                line_content = re.split(r'//|#', line)[0].strip()
                if not line_content:
                    continue
                if '}' in line_content:
                    inside_target = False
                    break

                tokens = line_content.split()
                if not tokens:
                    continue
                raw_key = tokens[0]
                key_lower = raw_key.lower()

                if key_lower in DROPPED_PROPERTIES:
                    continue

                if key_lower == 'spell':
                    spell_val = re.search(r'spell\s+(.+)', line_content, re.IGNORECASE).group(1).strip()
                    npc['spells'].append(spell_val.title())
                    continue
                if key_lower == 'name':
                    name_val = re.search(r'Name\s+(.+)', line_content, re.IGNORECASE).group(1).strip()
                    npc['Name'] = clean_name(name_val)
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

                final_key_lower = final_key.lower()

                if final_key_lower in DROPPED_PROPERTIES:
                    continue

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

                if final_key.lower() in ['nocorpse', 'looter', 'boss', 'superboss']:
                    final_val = 'Yes' if final_val.strip() in ['1', 'Boss 1', 'Superboss 1'] else 'No'

                if final_key.title() == 'Gender' and final_val.strip() == '0':
                    continue
                if final_val.strip() == '0' and final_key.lower() not in ['alignment', 'objtype', 'type', 'boss', 'superboss', 'no corpse', 'looter']:
                    continue

                final_key_title = final_key.title()

                if final_key.lower() in ['alignment', 'objtype', 'type']:
                    npc['summary'][final_key.lower()] = final_val
                elif 'required' in final_key.lower():
                    npc['skill_requirements'][final_key_title] = final_val
                elif final_key.lower() in ['lootgroup', 'magic item chance', 'magic item level']:
                    npc['loot'][final_key_title] = final_val
                elif final_key.lower().endswith('protection') or final_key.lower() in ['magic immunity', 'poison immunity', 'magic reflect', 'free action']:
                    npc['resistances'][final_key_title] = final_val
                elif final_key.lower() in CORE_STATS:
                    npc['attributes'][final_key_title] = final_val
                elif final_key.lower() in VALID_SKILLS or final_key in ['Animal Lore', 'Animal Taming']:
                    npc['skills'][final_key] = final_val
                else:
                    npc['other'][final_key_title] = final_val

    if npc:
        if 'Name' not in npc or not npc['Name']:
            base_template = re.sub(r'\d+$', '', npc['template'])
            npc['Name'] = base_template.title()

        for stat in ['Str', 'Dex', 'Int']:
            mod_key = f'Base{stat.lower()}mod'
            if mod_key in npc['attributes']:
                try:
                    base_val = int(npc['attributes'].get(stat, 0))
                    mod_val = int(npc['attributes'][mod_key])
                    npc['attributes'][stat] = str(base_val + mod_val)
                except ValueError:
                    pass
                del npc['attributes'][mod_key]

        if npc['category'] == "Vanity" and not npc['Name'].startswith("Vanity"):
            npc['Name'] = f"Vanity {npc['Name']}"

    return npc

def generate_test_page(npc, output_dir):
    if not npc:
        return
    os.makedirs(output_dir, exist_ok=True)
    filename = f"test_{npc['template'].lower()}.txt"
    filepath = os.path.join(output_dir, filename)

    ATTR_ORDER = ['Str', 'Dex', 'Int']
    RESIST_ORDER = [
        'Air Protection', 'Earth Protection', 'Fire Protection', 'Water Protection',
        'Holy Protection', 'Necro Protection', 'Magic Immunity', 'Magic Reflect',
        'Poison Immunity', 'Free Action'
    ]

    with open(filepath, 'w') as f:
        f.write(f"[[Category:NPCs]]\n[[Category:{npc['category']}]]\n\n")
        f.write('<div class="uo-profile-card">\n')
        f.write(f'  <div class="uo-card-title">{npc["Name"]} (Test Variant: {npc["template"]})</div>\n\n')

        if npc['is_uncategorized']:
            f.write('  <div class="uo-card-canvas" style="position: relative; box-shadow: 0 0 12px 2px rgba(239, 68, 68, 0.7); border: 1px solid #ef4444;">\n')
        else:
            f.write('  <div class="uo-card-canvas" style="position: relative;">\n')

        img_filename = f"{npc['template'].strip().replace(' ', '_').title()}.png"
        f.write(f"    [[File:{img_filename}|240px]]\n")

        if npc['is_uncategorized']:
            f.write('    <div class="npc-tooltip-trigger" style="position: absolute; top: 8px; right: 8px; background: #ef4444; color: #ffffff; width: 20px; height: 20px; border-radius: 50%; text-align: center; font-size: 12px; font-weight: bold; line-height: 20px; cursor: help;" title="Warning: This NPC has not been categorized yet and contains dummy values.">!</div>\n')
        f.write('  </div>\n\n')

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
            for index, spell in enumerate(sorted(npc['spells']), 1):
                f.write(f'    <div class="uo-data-row"><span class="uo-label">Spell {index}</span><span class="uo-value">[[{spell}]]</span></div>\n')
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

                if key.lower() in ['karma', 'fame']:
                    f.write(f'    <div class="uo-data-row"><span class="uo-label">[[{key.title()}]]</span><span class="uo-value">{val}</span></div>\n')
                else:
                    f.write(f'    <div class="uo-data-row"><span class="uo-label">{key}</span><span class="uo-value">{val}</span></div>\n')
            f.write('  </div>\n\n')

        f.write('</div>\n')
    print(f"✨ Test file generated at: {filepath}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "balron"
    npc_data = parse_single_npc(DEFAULT_CFG_PATH, target)
    if npc_data:
        print(f"🔬 Verified Target Found. Internal Node Mapping Summary:")
        pprint.pprint(npc_data)
        generate_test_page(npc_data, DEFAULT_OUTPUT_DIR)
    else:
        print(f"❌ Error: Specified testing asset '{target}' could not be located inside your source file data pools.")
