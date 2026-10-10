#!/usr/bin/env python3
"""Generates the module-system source for the mashup from sheets/*.json.
Usage: apply_mod.py <clean_ms_dir> <out_ms_dir>
Every edit is anchored on native text and asserts the anchor exists exactly as expected."""
import json, os, re, shutil, sys
SRC, OUT = sys.argv[1], sys.argv[2]
SH = os.path.join(os.path.dirname(__file__), '..', 'sheets')
def sheet(n): return json.load(open(os.path.join(SH, n + '.json')))
F = sheet('factions')['rows']; W = sheet('weapons')['rows']; AM = sheet('ammo')['rows']; AR = sheet('armor')['rows']
TR = sheet('troops')['rows']; LO = sheet('lords')['rows']; LA = sheet('ladies')['rows']; SN = sheet('sounds')['rows']; ST = sheet('start')
if os.path.exists(OUT): shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
files = {}
def rd(n):
    if n not in files: files[n] = open(os.path.join(OUT, n), encoding='latin-1').read()
    return files[n]
def wr(n, s): files[n] = s
def sub1(n, old, new, count=1):
    s = rd(n); c = s.count(old)
    assert c == count, f"{n}: anchor found {c}x (want {count}): {old[:80]!r}"
    wr(n, s.replace(old, new))
def after(n, anchor, text, count=1): sub1(n, anchor, anchor + text, count)
def before(n, anchor, text, count=1): sub1(n, anchor, text + anchor, count)
SIDE_FAC = {f['side']: f['id'] for f in F}
def facs(sides): return '[' + ','.join('fac_' + SIDE_FAC[s] for s in sides) + ']'
K = [f['id'] for f in F]

# ---------------- factions
rel = '[("outlaws",-0.05),("peasant_rebels", -0.1),("deserters", -0.02),("mountain_bandits", -0.05),("forest_bandits", -0.05)]'
txt = ''.join(f'  ("{f["id"]}",  "{f["name"]}",  0, 0.9, {rel}, [], {f["color"]}),\n' for f in F)
before('module_factions.py', '  ("kingdoms_end","{!}kingdoms_end", 0, 0,[], []),', txt)
s = rd('module_factions.py'); i = s.rindex(']')
wr('module_factions.py', s[:i] + ''.join(f'  ("{f["culture"]}",  "{{!}}{f["culture"]}", 0, 0.9, [], []),\n' for f in F) + s[i:])

# ---------------- strings
after('module_strings.py', '  ("kingdom_6_adjective",                     "Sarranid"),\n',
      ''.join(f'  ("{f["id"]}_adjective", "{f["adjective"]}"),\n' for f in F))
after('module_strings.py', '  ("faction_title_male_6", "Emir {s0}"),\n',
      ''.join(f'  ("faction_title_male_{f["id"][-1]}", "{f["title_male"]}"),\n' for f in F))
after('module_strings.py', '  ("faction_title_female_6", "Sayeda {s0}"),\n',
      ''.join(f'  ("faction_title_female_{f["id"][-1]}", "{f["title_female"]}"),\n' for f in F))
s = rd('module_strings.py'); i = s.rindex(']')
wr('module_strings.py', s[:i] + ''.join(f'  ("cs2_{f["side"]}_colloquial", "{f["name"]}"),\n' for f in F) + s[i:])

# ---------------- items
def trig(w):
    if w['type'] == 'knife': return ''
    return (f',\n [(ti_on_weapon_attack, [(play_sound,"snd_{w["sound"]}"),(position_move_x, pos1,27),(position_move_y, pos1,36),'
            f'(particle_system_burst, "psys_pistol_smoke", pos1, {w["smoke"]})])]')
L = []
for w in W:
    fl = facs(w['sides'])
    if w['type'] == 'pistol':
        L.append(f'["{w["id"]}", "{w["name"]}", [("{w["mesh"]}",0)], itp_type_pistol|itp_merchandise|itp_primary, itcf_shoot_pistol|itcf_reload_pistol|itcf_carry_pistol_front_left, '
                 f'{w["price"]}, weight({w["weight"]})|abundance({w["abundance"]})|difficulty({w["difficulty"]})|spd_rtng({w["speed"]})|shoot_speed({w["shoot_speed"]})|thrust_damage({w["damage"]},pierce)|max_ammo({w["clip"]})|accuracy({w["accuracy"]}), imodbits_none{trig(w)}, {fl}],')
    elif w['type'] == 'long':
        L.append(f'["{w["id"]}", "{w["name"]}", [("{w["mesh"]}",0)], itp_type_musket|itp_merchandise|itp_primary|itp_two_handed, itcf_shoot_musket|itcf_reload_musket|itcf_carry_crossbow_back, '
                 f'{w["price"]}, weight({w["weight"]})|abundance({w["abundance"]})|difficulty({w["difficulty"]})|spd_rtng({w["speed"]})|shoot_speed({w["shoot_speed"]})|thrust_damage({w["damage"]},pierce)|max_ammo({w["clip"]})|accuracy({w["accuracy"]}), imodbits_none{trig(w)}, {fl}],')
    elif w['type'] == 'knife':
        L.append(f'["{w["id"]}", "{w["name"]}", [("{w["mesh"]}",0)], itp_type_one_handed_wpn|itp_merchandise|itp_primary|itp_secondary|itp_no_parry, itc_dagger|itcf_carry_dagger_front_left, '
                 f'{w["price"]}, weight({w["weight"]})|abundance({w["abundance"]})|difficulty(0)|spd_rtng({w["speed"]})|weapon_length({w["length"]})|swing_damage({w["damage"]},cut)|thrust_damage({w["thrust"]},pierce), imodbits_none, [], {fl}],')
    else: raise SystemExit('weapon type ' + w['type'])
for a in AM:
    L.append(f'["{a["id"]}", "{a["name"]}", [("{a["mesh"]}",0)], itp_type_bullets|itp_merchandise|itp_can_penetrate_shield, 0, '
             f'{a["price"]}, weight({a["weight"]})|abundance({a["abundance"]})|weapon_length(3)|thrust_damage({a["damage_bonus"]},pierce)|max_ammo({a["count"]}), imodbits_none, [], {facs(a["sides"])}],')
for a in AR:
    st = f'weight({a["weight"]})|abundance({a["abundance"]})|head_armor({a["head"]})|body_armor({a["body"]})|leg_armor({a["leg"]})|difficulty(0)'
    fl = facs(a['sides'])
    if a['part'] == 'suit':
        L.append(f'["{a["id"]}", "{a["name"]}", [("{a["mesh"]}",0)], itp_merchandise|itp_type_body_armor|itp_covers_legs|itp_civilian, 0, {a["price"]}, {st}, imodbits_none, [], {fl}],')
    elif a['part'] == 'head':
        L.append(f'["{a["id"]}", "{a["name"]}", [("{a["mesh"]}",0)], itp_merchandise|itp_type_head_armor|itp_covers_head|itp_civilian, 0, {a["price"]}, {st}, imodbits_none, [], {fl}],')
    elif a['part'] == 'gloves':
        L.append(f'["{a["id"]}", "{a["name"]}", [("{a["mesh"]}_L",0)], itp_merchandise|itp_type_hand_armor|itp_civilian, 0, {a["price"]}, {st}, imodbits_none, [], {fl}],')
    else: raise SystemExit('armor part ' + a['part'])
before('module_items.py', '["items_end", "Items End", [("shield_round_a",0)], 0, 0, 1, 0, 0],', '\n'.join(L) + '\n')

# ---------------- sounds
before('module_sounds.py', ' ("sounds_end", sf_2d|sf_priority_10|sf_vol_10, ["enemy_scored_a_point.ogg"]),',
       ''.join(' ("%s", %s, [%s]),\n' % (s_['id'], s_['flags'], ','.join(f'"{s_["id"]}_{i+1}.wav"' for i in range(len(s_['files'])))) for s_ in SN))

# ---------------- troops
def itm(l): return '[' + ','.join('itm_' + x for x in l) + ']'
reg = []
for t in TR:
    reg.append(f'  ["{t["id"]}","{t["name"]}","{t["plural"]}",{t["flags"]},0,0,fac_{t["faction"]},\n   {itm(t["items"])},\n'
               f'   def_attrib|level({t["level"]}),wp_melee({t["wp_melee"]})|wp_firearm({t["wp_firearm"]}),{t["skills"]},swadian_face_younger_1, swadian_face_old_2],\n')
before('module_troops.py', '  ["looter","Looter","Looters",0,0,0,fac_outlaws,', ''.join(reg) + '\n')
FACE_M = '0x0000000a4b103354189c71d6d386e8ac00000000001e24eb0000000000000000, rhodok_face_older_2'
FACE_F = '0x000000055910200107632d675a92b92d00000000001e45620000000000000000'
def hero(l):
    fl = 'tf_hero|tf_female|tf_unmoveable_in_party_window' if l['role'] == 'pretender' and l['female'] else ('tf_hero|tf_unmoveable_in_party_window' if l['role'] == 'pretender' else 'tf_hero')
    face = FACE_F if l['female'] else FACE_M
    return f'  ["{l["id"]}", "{l["name"]}", "{l["short"]}", {fl}, 0, reserved, fac_{l["kingdom"]}, {itm(l["items"])}, {l["attrib"]}, wp({l["wp"]})|wp_firearm({l["wp"]}), {l["skills"]}, {face}],\n'
before('module_troops.py', '  ["knight_1_1", "Count Klargus"', ''.join(hero(l) for l in LO if l['role'] == 'king'))
before('module_troops.py', '  ["kingdom_1_pretender",', ''.join(hero(l) for l in LO if l['role'] == 'lord'))
s = rd('module_troops.py'); m = re.search(r'^.*\["knight_1_1_wife"', s, re.M); assert m
wr('module_troops.py', s[:m.start()] + ''.join(hero(l) for l in LO if l['role'] == 'pretender') + s[m.start():])
before('module_troops.py', '  ["heroes_end", "{!}heroes end"',
       ''.join(f'  ["{l["id"]}","{l["name"]}","{l["short"]}",tf_hero|tf_female|tf_unmoveable_in_party_window,0,reserved,fac_{l["kingdom"]}, {itm(l["items"])}, def_attrib|level(2),wp(50),knows_common|knows_riding_2, {FACE_F}],\n' for l in LA))
ups = []
for t in TR:
    if len(t['upgrades']) == 1: ups.append(f'upgrade(troops,"{t["id"]}","{t["upgrades"][0]}")\n')
    elif len(t['upgrades']) == 2: ups.append(f'upgrade2(troops,"{t["id"]}","{t["upgrades"][0]}","{t["upgrades"][1]}")\n')
after('module_troops.py', 'upgrade(troops,"sarranid_horseman","sarranid_mamluke")\n', ''.join(ups))

# ---------------- party templates
after('module_party_templates.py', '  ("kingdom_6_reinforcements_c", "{!}kingdom_6_reinforcements_c", 0, 0, fac_commoners, 0, [(trp_sarranid_horseman,3,5)]),\n',
      ''.join(f'  ("{f["id"]}_reinforcements_{k}", "{{!}}{f["id"]}_reinforcements_{k}", 0, 0, fac_commoners, 0, [{",".join(f"(trp_{t},{a},{b})" for t,a,b in f["reinforcements"][k])}]),\n' for f in F for k in 'abc'))

# ---------------- scripts
S = 'module_scripts.py'
after(S, '      (faction_set_slot, "fac_culture_6", slot_faction_tier_5_troop, "trp_sarranid_mamluke"),\n',
      ''.join(f'      (faction_set_slot, "fac_{f["culture"]}", slot_faction_tier_{i+1}_troop, "trp_{t}"),\n' for f in F for i, t in enumerate(f['tiers'])))
after(S, '      (faction_set_slot, "fac_culture_6", slot_faction_town_spy_female_troop, "trp_spy_walker_2"),\n',
      ''.join(f'''      (faction_set_slot, "fac_{f["culture"]}", slot_faction_town_walker_male_troop, "trp_{f["walker_m"]}"),
      (faction_set_slot, "fac_{f["culture"]}", slot_faction_town_walker_female_troop, "trp_{f["walker_f"]}"),
      (faction_set_slot, "fac_{f["culture"]}", slot_faction_village_walker_male_troop, "trp_{f["walker_m"]}"),
      (faction_set_slot, "fac_{f["culture"]}", slot_faction_village_walker_female_troop, "trp_{f["walker_f"]}"),
      (faction_set_slot, "fac_{f["culture"]}", slot_faction_town_spy_male_troop, "trp_spy_walker_1"),
      (faction_set_slot, "fac_{f["culture"]}", slot_faction_town_spy_female_troop, "trp_spy_walker_2"),
''' for f in F))
after(S, '          (troop_set_slot, "trp_kingdom_6_lord", slot_troop_renown, 1200),\n',
      ''.join(f'''      (faction_set_slot, "fac_{f["id"]}",  slot_faction_culture, "fac_{f["culture"]}"),
      (faction_set_slot, "fac_{f["id"]}",  slot_faction_leader, "trp_{f["leader"]}"),
      (troop_set_slot, "trp_{f["leader"]}", slot_troop_renown, 1200),
''' for f in F))
after(S, '      (faction_set_slot, "fac_kingdom_6", slot_faction_banner, "mesh_banner_kingdom_e"),\n',
      ''.join(f'      (faction_set_slot, "fac_{f["id"]}", slot_faction_banner, "mesh_{f["banner_mesh"]}"),\n' for f in F), count=2)
before(S, '''          (eq, ":kingdom_hero_faction", "fac_kingdom_3"), #Khergit Khanate\n''',
       f'''          (is_between, ":kingdom_hero_faction", "fac_{K[0]}", kingdoms_end), #CS2 factions share their leader's banner
          (faction_get_slot, ":cs2_king", ":kingdom_hero_faction", slot_faction_leader),
          (troop_get_slot, ":banner_id", ":cs2_king", slot_troop_banner_scene_prop),
          (troop_set_slot, ":kingdom_hero", slot_troop_banner_scene_prop, ":banner_id"),
        (else_try),
''')
s = rd(S)
for f in F:
    for c in f['towns'] + f['castles']:
        pat = re.compile(r'(give_center_to_faction_aux", "p_%s", )"fac_kingdom_\d"' % c)
        assert len(pat.findall(s)) == 1, c
        s = pat.sub(r'\1"fac_%s"' % f['id'], s)
for l in LO:
    if l['fief']:
        pat = re.compile(r'(^      \(call_script, "script_give_center_to_lord", "p_%s",\s*)"trp_\w+"' % l['fief'], re.M)
        assert len(pat.findall(s)) == 1, l['fief']
        s = pat.sub(r'\1"trp_%s"' % l['id'], s)
wr(S, s)
after(S, '          (faction_set_slot, "fac_kingdom_6", slot_faction_adjective, "str_kingdom_6_adjective"),\n',
      ''.join(f'          (faction_set_slot, "fac_{f["id"]}", slot_faction_adjective, "str_{f["id"]}_adjective"),\n' for f in F))
after(S, '          (faction_set_slot, ":faction_no",  slot_faction_reinforcements_c, "pt_kingdom_6_reinforcements_c"),\n',
      ''.join(f'''        (else_try),
          (faction_slot_eq, ":faction_no", slot_faction_culture, "fac_{f["culture"]}"),
          (faction_set_slot, ":faction_no", slot_faction_deserter_troop, "trp_{f["deserter"]}"),
          (faction_set_slot, ":faction_no", slot_faction_guard_troop, "trp_{f["guard"]}"),
          (faction_set_slot, ":faction_no", slot_faction_messenger_troop, "trp_{f["messenger"]}"),
          (faction_set_slot, ":faction_no", slot_faction_prison_guard_troop, "trp_{f["prison_guard"]}"),
          (faction_set_slot, ":faction_no", slot_faction_castle_guard_troop, "trp_{f["castle_guard"]}"),
          (faction_set_slot, ":faction_no",  slot_faction_reinforcements_a, "pt_{f["id"]}_reinforcements_a"),
          (faction_set_slot, ":faction_no",  slot_faction_reinforcements_b, "pt_{f["id"]}_reinforcements_b"),
          (faction_set_slot, ":faction_no",  slot_faction_reinforcements_c, "pt_{f["id"]}_reinforcements_c"),
''' for f in F))
after(S, '        (troop_set_slot, "trp_kingdom_6_pretender",  slot_troop_original_faction, "fac_kingdom_6"),\n',
      ''.join(f'        (troop_set_slot, "trp_{f["pretender"]}",  slot_troop_original_faction, "fac_{f["id"]}"),\n' for f in F))
after(S, '''        (eq, ":faction_no", "fac_kingdom_6"),
        (assign, ":result", mtf_culture_6),
''', ''.join(f'''      (else_try),
        (eq, ":faction_no", "fac_{f["id"]}"),
        (assign, ":result", {f["music"]}),
''' for f in F))
after(S, '''                                (eq, ":faction_object", "fac_kingdom_6"),
                                (str_store_string, s39, "str_sarranids"),
''', ''.join(f'''                        (else_try),
                                (eq, ":faction_object", "fac_{f["id"]}"),
                                (str_store_string, s39, "str_cs2_{f["side"]}_colloquial"),
''' for f in F))
# aristocracy: 12 lords per CS2 kingdom
sub1(S, '''                        (is_between, ":cur_troop", "trp_knight_6_1", "trp_kingdom_1_pretender"),
                        (store_sub, ":npc_seed", ":cur_troop", "trp_knight_6_1"),
                        (assign, ":ancestor_seed", 31),
''', '''                        (is_between, ":cur_troop", "trp_knight_6_1", "trp_knight_7_1"),
                        (store_sub, ":npc_seed", ":cur_troop", "trp_knight_6_1"),
                        (assign, ":ancestor_seed", 31),
                (else_try),
                        (is_between, ":cur_troop", "trp_knight_7_1", "trp_knight_8_1"),
                        (store_sub, ":npc_seed", ":cur_troop", "trp_knight_7_1"),
                        (assign, ":ancestor_seed", 37),
                (else_try),
                        (is_between, ":cur_troop", "trp_knight_8_1", "trp_kingdom_1_pretender"),
                        (store_sub, ":npc_seed", ":cur_troop", "trp_knight_8_1"),
                        (assign, ":ancestor_seed", 43),
''')
# T and CT begin at war with each other
after(S, '''        (call_script, "script_randomly_start_war_peace_new", 0),
      (try_end),
''', f'''      (try_begin),
        (store_relation, ":cs2_rel", "fac_{K[0]}", "fac_{K[1]}"),
        (ge, ":cs2_rel", 0),
        (call_script, "script_diplomacy_start_war_between_kingdoms", "fac_{K[0]}", "fac_{K[1]}", 0),
      (try_end),
''')
# traders: CS2 stock in T / CT towns
def stock(merchant_items):
    out = ''
    for f in F:
        out += f'''      (try_begin),
        (eq, ":cur_faction", "fac_{f["id"]}"),
''' + ''.join(f'        (troop_add_items, ":cur_merchant", "itm_{i}", {n}),\n' for i, n in merchant_items(f['side'])) + '      (try_end),\n'
    return out
after(S, '      (troop_add_merchandise_with_faction, ":cur_merchant", ":cur_faction", itp_type_bolts, 2),\n',
      stock(lambda side: [(w['id'], 2 if w['price'] < 6000 else 1) for w in W if side in w['sides']] + [(a['id'], 4) for a in AM if side in a['sides']]))
after(S, '          (troop_add_merchandise_with_faction, ":cur_merchant", ":cur_faction", itp_type_hand_armor, 4),\n',
      stock(lambda side: [(a['id'], 3) for a in AR if side in a['sides']]))

# ---------------- simple triggers
sub1('module_simple_triggers.py', '     (store_add, ":fac_kingdom_6_plus_one", "fac_kingdom_6", 1),', '     (assign, ":fac_kingdom_6_plus_one", kingdoms_end),')

# ---------------- game menus: mercenary start (no character creator)
M = 'module_game_menus.py'
s = rd(M); a = s.index('  ("start_game_0",'); blk_end = s.index('\n  ),\n', a) + 6
blk = s[a:blk_end]; assert blk.count('(jump_to_menu, "mnu_start_game_1")') == 1
s = s[:a] + blk.replace('(jump_to_menu, "mnu_start_game_1")', '(jump_to_menu, "mnu_cs2_choose_look")').replace(
    'Before beginning the game you must create your character.', 'You arrive as a gun for hire.') + s[blk_end:]
B = ST['build']
build = ''.join(f'         (troop_raise_attribute, "trp_player", {k}, {v}),\n' for k, v in B['attributes'].items()) \
      + ''.join(f'         (troop_raise_skill, "trp_player", {k}, {v}),\n' for k, v in B['skills'].items()) \
      + ''.join(f'         (troop_raise_proficiency_linear, "trp_player", {k}, {v}),\n' for k, v in B['proficiencies'].items())
opts = ''
for r in ST['rows']:
    sets = [('ek_body', r['body']), ('ek_head', r['head']), ('ek_gloves', r['gloves'])] + [(f'ek_item_{i}', w) for i, w in enumerate(r['weapons'])]
    opts += f"""      ("{r["id"]}",[],"{r["label"]}",
       [
         (troop_set_type, "trp_player", 0),
         (assign, "$character_gender", tf_male),
{build}""" + ''.join(f'         (troop_set_inventory_slot, "trp_player", {slot}, "itm_{it}"),\n' for slot, it in sets) + f"""         (troop_add_gold, "trp_player", {ST["gold"]}),
         (assign, "$current_town", "p_{r["spawn"]}"),
         (assign, "$g_starting_town", "$current_town"),
         (assign, "$current_startup_quest_phase", 4),
         (call_script, "script_player_arrived"),
         (party_set_morale, "p_main_party", 100),
         (party_relocate_near_party, "p_main_party", "$g_starting_town", 2),
         (change_screen_return),
       ]),
"""
menu = f"""  ("cs2_choose_look",mnf_disable_all_keys,
    "Two armed factions from another war have carved out territory in Calradia: the Terrorists in the southern desert and the Counter-Terrorists in the heartland. Neither knows you yet, and both are hiring. Where do you walk in?",
    "none",
    [],
    [
{opts}    ]
  ),
"""
i = s.rindex(']'); s = s[:i] + menu + s[i:]
wr(M, s)

# provisional ids so the first build pass can import; pass 1 regenerates the real ID_*.py, pass 2 compiles with them
def prov(fn, names):
    with open(os.path.join(OUT, fn), 'a') as fh:
        for i, nm in enumerate(names): fh.write(f"\n{nm} = {90000+i}")
prov('ID_factions.py', ['fac_'+f['id'] for f in F] + ['fac_'+f['culture'] for f in F])
prov('ID_items.py', ['itm_'+x['id'] for x in W+AM+AR])
prov('ID_troops.py', ['trp_'+x['id'] for x in TR+LO+LA])
prov('ID_party_templates.py', [f'pt_{f["id"]}_reinforcements_{k}' for f in F for k in 'abc'])
for n, s in files.items(): open(os.path.join(OUT, n), 'w', encoding='latin-1', newline='\n').write(s)
print('applied', len(files), 'files')
