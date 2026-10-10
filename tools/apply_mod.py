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
    elif a['part'] == 'boots':
        L.append(f'["{a["id"]}", "{a["name"]}", [("{a["mesh"]}",0)], itp_merchandise|itp_type_foot_armor|itp_attach_armature|itp_civilian, 0, {a["price"]}, {st}, imodbits_none, [], {fl}],')
    else: raise SystemExit('armor part ' + a['part'])
before('module_items.py', '["items_end", "Items End", [("shield_round_a",0)], 0, 0, 1, 0, 0],', '\n'.join(L) + '\n')

# ---------------- sounds
before('module_sounds.py', ' ("sounds_end", sf_2d|sf_priority_10|sf_vol_10, ["enemy_scored_a_point.ogg"]),',
       ''.join(' ("%s", %s, [%s]),\n' % (s_['id'], s_['flags'], ','.join(f'"{s_["id"]}_{i+1}.wav"' for i in range(len(s_['files'])))) for s_ in SN))

# ---------------- troops
def itm(l): return '[' + ','.join('itm_' + x for x in l) + ']'
reg = []
for t in TR:
    reg.append(f'  ["{t["id"]}","{t["name"]}","{t["plural"]}",tf_cs2|{t["flags"]},0,0,fac_{t["faction"]},\n   {itm(t["items"])},\n'
               f'   def_attrib|level({t["level"]}),wp_melee({t["wp_melee"]})|wp_firearm({t["wp_firearm"]}),{t["skills"]},swadian_face_younger_1, swadian_face_old_2],\n')
before('module_troops.py', '  ["looter","Looter","Looters",0,0,0,fac_outlaws,', ''.join(reg) + '\n')
FACE_M = '0x0000000a4b103354189c71d6d386e8ac00000000001e24eb0000000000000000, rhodok_face_older_2'
FACE_F = '0x000000055910200107632d675a92b92d00000000001e45620000000000000000'
def hero(l):
    fl = 'tf_hero|tf_female|tf_unmoveable_in_party_window' if l['role'] == 'pretender' and l['female'] else ('tf_cs2|tf_hero|tf_unmoveable_in_party_window' if l['role'] == 'pretender' else 'tf_cs2|tf_hero')
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
# The engine opens the second menu (start_phase_2) by itself once its own character screen closes.
# With the CS2 start already chosen there is nothing to ask there, so it places the party and goes to the map.
a = s.index('  ("start_phase_2",mnf_disable_all_keys,'); blk_end = s.index('\n  ),\n', a) + 6
blk = s[a:blk_end]; old = '    "none",\n    [],\n    [\n'; assert blk.count(old) == 1
s = s[:a] + blk.replace(old, """    "none",
    [
      (try_begin),
        (eq, "$current_startup_quest_phase", 4),
        (party_relocate_near_party, "p_main_party", "$g_starting_town", 2),
        (change_screen_return),
      (try_end),
    ],
    [
      ("cs2_to_map",[(eq, "$current_startup_quest_phase", 4),],"Continue...",
       [
         (party_relocate_near_party, "p_main_party", "$g_starting_town", 2),
         (change_screen_return),
       ]),
""") + s[blk_end:]
B = ST['build']
build = ''.join(f'         (troop_raise_attribute, "trp_player", {k}, {v}),\n' for k, v in B['attributes'].items()) \
      + ''.join(f'         (troop_raise_skill, "trp_player", {k}, {v}),\n' for k, v in B['skills'].items()) \
      + ''.join(f'         (troop_raise_proficiency_linear, "trp_player", {k}, {v}),\n' for k, v in B['proficiencies'].items())
opts = ''
for r in ST['rows']:
    sets = [('ek_body', r['body']), ('ek_head', r['head']), ('ek_gloves', r['gloves']), ('ek_foot', r['boots'])] + [(f'ek_item_{i}', w) for i, w in enumerate(r['weapons'])]
    opts += f"""      ("{r["id"]}",[],"{r["label"]}",
       [
         (troop_set_type, "trp_player", 2),
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


# ---------------- CS2 agent skin: a third body type with no visible Warband body, so only the CS2 model shows
with open(os.path.join(OUT, 'header_troops.py'), 'a') as fh: fh.write('\ntf_cs2 = 2\n')
s_ = rd('module_skins.py'); i_ = s_.rindex(']')
m_ = re.search(r'\n  \(\n    "man", 0,\n.*?\n  \),\n', s_, re.S); assert m_
cs2skin = m_.group(0).replace('"man", 0,', '"cs2_agent", 0,').replace('"man_body", "man_calf_l", "m_handL",', '"cs2_none_body", "cs2_none_calf_l", "cs2_none_handL",') \
    .replace('"male_head", man_face_keys,', '"cs2_none_head", [],')
cs2skin = re.sub(r'\[\"man_hair_s\".*?\], #man_hair_meshes[^\n]*', '[],', cs2skin)
cs2skin = re.sub(r'\[\"beard_e\".*?\], #beard meshes[^\n]*', '[],', cs2skin)
assert 'cs2_none_head' in cs2skin and 'man_hair_s' not in cs2skin and 'beard_e' not in cs2skin
# the list must hold man, woman, then this one (troop type 2)
assert len(re.findall(r'^  \(\n    "', s_[s_.index('skins = ['):], re.M)) == 2
wr('module_skins.py', s_[:i_] + cs2skin.lstrip('\n') + s_[i_:])
# native scripts read the troop type as "is female"; keep type 2 male for them
for fn in sorted(os.listdir(OUT)):
    if fn.startswith('module_') and fn.endswith('.py'):
        t_ = rd(fn)
        t2 = re.sub(r'\(troop_get_type,\s*([^,()]+),\s*([^()]+?)\),', r'(troop_get_type, \1, \2),(val_mod, \1, 2),', t_)
        if t2 != t_: wr(fn, t2)
suits = {part: [a['id'] for a in AR if a['part'] == part] for part in ('suit', 'head', 'gloves', 'boots')}
def any_of(var, ids): return ''.join(f'(this_or_next|eq, "{var}", "itm_{i}"),' for i in ids[:-1]) + f'(eq, "{var}", "itm_{ids[-1]}"),'
skin_script = f"""
  # script_cs2_set_player_skin: full CS2 kit shows the CS2 agent alone; anything else shows the Warband body under it
  ("cs2_set_player_skin", [
    (assign, ":type", 0),
    (try_begin),
      (troop_get_inventory_slot, ":b", "trp_player", ek_body), {any_of(':b', suits['suit'])}
      (troop_get_inventory_slot, ":h", "trp_player", ek_head), {any_of(':h', suits['head'])}
      (troop_get_inventory_slot, ":g", "trp_player", ek_gloves), {any_of(':g', suits['gloves'])}
      (troop_get_inventory_slot, ":f", "trp_player", ek_foot), {any_of(':f', suits['boots'])}
      (assign, ":type", 2),
    (try_end),
    (troop_set_type, "trp_player", ":type"),
  ]),
"""
s_ = rd(S); i_ = s_.rindex(']'); wr(S, s_[:i_] + skin_script + s_[i_:])
s_ = rd('module_simple_triggers.py'); i_ = s_.rindex(']')
wr('module_simple_triggers.py', s_[:i_] + '  (0, [(map_free), (call_script, "script_cs2_set_player_skin")]),\n' + s_[i_:])

# ---------------- CS2 gunplay: scripted fire for the player, CS2 damage model for everyone
import math
SL = dict(cycle=100, auto=101, bullets=102, dmg=103, clip=104, stand=105, crouch=106, move=107, fire=108, spread=109,
          mag=110, var=111, recov=112, hs=113, armor=114, rm=115, reload=116, snd=117, pistol=118,
          stand_a=119, crouch_a=120, move_a=121, fire_a=122, zoom=123)
def mdeg(x): return int(round(math.degrees(x) * 1000))
init = ''
for w in W:
    c = w.get('cs2')
    if not c: continue
    v = dict(cycle=round(c['cycle_time']*1000), auto=int(c['full_auto']), bullets=int(c['bullets']), dmg=int(c['damage']), clip=int(c['clip']),
             stand=mdeg(c['inaccuracy_stand']), crouch=mdeg(c['inaccuracy_crouch']), move=mdeg(c['inaccuracy_move']), fire=mdeg(c['inaccuracy_fire']),
             spread=mdeg(c['spread']), mag=int(c['recoil_magnitude']), var=int(c['recoil_angle_variance']), recov=max(50, round(c['recovery_time_stand']*1000)),
             hs=round(c['headshot_multiplier']*100), armor=round(c['armor_ratio']*500), rm=round(c['range_modifier']*1000), reload=round(c['reload_time']*1000),
             pistol=int(w['type'] == 'pistol'),
             stand_a=mdeg(c['inaccuracy_stand_alt']), crouch_a=mdeg(c['inaccuracy_crouch_alt']), move_a=mdeg(c['inaccuracy_move_alt']), fire_a=mdeg(c['inaccuracy_fire_alt']),
             zoom=(100 if c['zoom_levels'] else 45))  # aim-down-sights zoom, percent of Warband's full zoom
    init += ''.join(f'  (item_set_slot, "itm_{w["id"]}", {SL[k]}, {x}),\n' for k, x in v.items())
    init += f'  (item_set_slot, "itm_{w["id"]}", {SL["snd"]}, "snd_{w["sound"]}"),\n'
DEFAULT_AMMO = AM[0]['id']
ARMOR_FULL, HORSE_BASE = 50, 60
CS2_DEBUG = int(os.environ.get('CS2_DEBUG', '0'))
gun = f"""
cs2_before_start = (ti_before_mission_start, 0, 0, [], [
  (call_script, "script_cs2_set_player_skin"),
{init}  (assign, "$cs2_next_fire", 0), (assign, "$cs2_reload_end", 0), (assign, "$cs2_last_t", 0), (assign, "$cs2_acc", 0),
  (assign, "$cs2_recoil", 0), (assign, "$cs2_held", 0), (assign, "$cs2_last_item", -1), (assign, "$cs2_last_shot", 0), (assign, "$cs2_hud_clip", -1), (assign, "$cs2_ads", 0),
  (assign, "$cs2_debug", {CS2_DEBUG}),
  ])

cs2_fire = (0, 0, 0, [], [
  (get_player_agent_no, ":p"), (ge, ":p", 0), (agent_is_alive, ":p"),
  (store_mission_timer_a_msec, ":t"),
  (store_sub, ":dt", ":t", "$cs2_last_t"), (assign, "$cs2_last_t", ":t"), (val_clamp, ":dt", 0, 200),
  (agent_get_wielded_item, ":w", ":p", 0),
  (assign, ":cycle", 0),
  (try_begin), (ge, ":w", 0), (item_get_slot, ":cycle", ":w", {SL['cycle']}), (try_end),
  (try_begin),
    (le, ":cycle", 0),
    (assign, "$cs2_hud_clip", -1), (assign, "$cs2_reload_end", 0), (assign, "$cs2_last_item", -1),
    (try_begin), (neq, "$cs2_ads", 0), (assign, "$cs2_ads", 0), (set_fixed_point_multiplier, 100), (set_zoom_amount, 0), (try_end),
  (else_try),
    (try_begin), (agent_slot_eq, ":p", 84, 0), (agent_set_slot, ":p", 84, 1),
      (try_for_range, ":i", 0, 4),
        (agent_get_item_slot, ":it", ":p", ":i"), (ge, ":it", 0),
        (item_get_slot, ":c", ":it", {SL['clip']}), (store_add, ":s", 80, ":i"), (agent_set_slot, ":p", ":s", ":c"),
      (try_end),
    (try_end),
    (assign, ":si", 0), (assign, ":reserve", 0), (assign, ":ammo", "itm_{DEFAULT_AMMO}"),
    (try_for_range, ":i", 0, 4),
      (agent_get_item_slot, ":it", ":p", ":i"), (ge, ":it", 0),
      (try_begin), (eq, ":it", ":w"), (assign, ":si", ":i"), (try_end),
      (item_get_type, ":ty", ":it"), (eq, ":ty", itp_type_bullets),
      (agent_get_item_cur_ammo, ":n", ":p", ":i"), (val_add, ":reserve", ":n"), (assign, ":ammo", ":it"),
    (try_end),
    (store_add, ":cslot", 80, ":si"),
    (agent_get_slot, ":clip", ":p", ":cslot"),
    (item_get_slot, ":clipsize", ":w", {SL['clip']}),
    (try_begin), (neq, "$cs2_last_item", ":w"),
      (assign, "$cs2_last_item", ":w"), (assign, "$cs2_reload_end", 0), (store_add, "$cs2_next_fire", ":t", 350),
      (assign, "$cs2_acc", 0), (assign, "$cs2_recoil", 0),
    (try_end),
    # recovery
    (item_get_slot, ":rec", ":w", {SL['recov']}),
    (store_mul, ":d", "$cs2_acc", ":dt"), (val_div, ":d", ":rec"), (val_add, ":d", 1), (val_sub, "$cs2_acc", ":d"), (val_max, "$cs2_acc", 0),
    (try_begin),
      (store_add, ":idle", "$cs2_last_shot", ":cycle"), (val_add, ":idle", 60), (gt, ":t", ":idle"),
      (store_mul, ":d", ":dt", 1000), (val_div, ":d", ":rec"), (val_sub, "$cs2_recoil", ":d"), (val_max, "$cs2_recoil", 0),
    (try_end),
    # reload
    (try_begin), (gt, "$cs2_reload_end", 0), (ge, ":t", "$cs2_reload_end"),
      (assign, "$cs2_reload_end", 0),
      (store_sub, ":take", ":clipsize", ":clip"), (val_min, ":take", ":reserve"), (val_max, ":take", 0),
      (val_add, ":clip", ":take"), (val_sub, ":reserve", ":take"), (agent_set_slot, ":p", ":cslot", ":clip"),
      (try_for_range, ":i", 0, 4),
        (gt, ":take", 0),
        (agent_get_item_slot, ":it", ":p", ":i"), (ge, ":it", 0),
        (item_get_type, ":ty", ":it"), (eq, ":ty", itp_type_bullets),
        (agent_get_item_cur_ammo, ":n", ":p", ":i"),
        (assign, ":use", ":n"), (val_min, ":use", ":take"), (val_sub, ":n", ":use"), (val_sub, ":take", ":use"),
        (agent_set_ammo, ":p", ":it", ":n"),
      (try_end),
    (try_end),
    (try_begin), (eq, "$cs2_reload_end", 0), (lt, ":clip", ":clipsize"), (gt, ":reserve", 0),
      (this_or_next|le, ":clip", 0), (game_key_clicked, gk_toggle_weapon_mode),
      (item_get_slot, ":rl", ":w", {SL['reload']}), (store_add, "$cs2_reload_end", ":t", ":rl"),
      (try_begin), (item_slot_eq, ":w", {SL['pistol']}, 1), (agent_set_animation, ":p", "anim_reload_pistol", 1),
      (else_try), (agent_set_animation, ":p", "anim_reload_musket", 1), (try_end),
    (try_end),
    (assign, "$cs2_hud_clip", ":clip"), (assign, "$cs2_hud_reserve", ":reserve"),
    # right mouse button: aim down sights (zoom in, hold the aim; the AWP gets its scoped accuracy)
    (assign, ":ads", 0),
    (try_begin), (game_key_is_down, gk_defend), (eq, "$cs2_reload_end", 0), (assign, ":ads", 1), (try_end),
    (try_begin), (neq, ":ads", "$cs2_ads"),
      (assign, "$cs2_ads", ":ads"),
      (set_fixed_point_multiplier, 100),
      (try_begin), (eq, ":ads", 1),
        (item_get_slot, ":zoom", ":w", {SL['zoom']}), (set_zoom_amount, ":zoom"),
        (try_begin), (item_slot_eq, ":w", {SL['pistol']}, 1), (agent_set_animation, ":p", "anim_ready_pistol", 1),
        (else_try), (agent_set_animation, ":p", "anim_ready_musket", 1), (try_end),
      (else_try),
        (set_zoom_amount, 0),
        (try_begin), (item_slot_eq, ":w", {SL['pistol']}, 1), (agent_set_animation, ":p", "anim_release_pistol", 1),
        (else_try), (agent_set_animation, ":p", "anim_release_musket", 1), (try_end),
      (try_end),
    (try_end),
    # trigger
    (assign, ":down", 0),
    (try_begin), (game_key_is_down, gk_attack), (assign, ":down", 1), (try_end),
    (try_begin), (this_or_next|eq, ":down", 1), (eq, "$cs2_held", 1), (agent_set_attack_action, ":p", -2, 0), (try_end),
    (try_begin),
      (eq, ":down", 1), (eq, "$cs2_reload_end", 0), (gt, ":clip", 0), (ge, ":t", "$cs2_next_fire"),
      (this_or_next|item_slot_eq, ":w", {SL['auto']}, 1), (eq, "$cs2_held", 0),
      (val_sub, ":clip", 1), (agent_set_slot, ":p", ":cslot", ":clip"), (assign, "$cs2_hud_clip", ":clip"),
      (try_begin), (store_sub, ":late", ":t", "$cs2_next_fire"), (lt, ":late", 50), (gt, "$cs2_next_fire", 0), (val_add, "$cs2_next_fire", ":cycle"),
      (else_try), (store_add, "$cs2_next_fire", ":t", ":cycle"), (try_end),
      (assign, "$cs2_last_shot", ":t"),
      # inaccuracy in millidegrees
      (assign, ":s_stand", {SL['stand']}), (assign, ":s_crouch", {SL['crouch']}), (assign, ":s_move", {SL['move']}), (assign, ":s_fire", {SL['fire']}),
      (try_begin), (eq, "$cs2_ads", 1),
        (assign, ":s_stand", {SL['stand_a']}), (assign, ":s_crouch", {SL['crouch_a']}), (assign, ":s_move", {SL['move_a']}), (assign, ":s_fire", {SL['fire_a']}),
      (try_end),
      (item_get_slot, ":inacc", ":w", ":s_stand"),
      (try_begin), (agent_get_crouch_mode, ":cr", ":p"), (eq, ":cr", 1), (item_get_slot, ":inacc", ":w", ":s_crouch"), (try_end),
      (set_fixed_point_multiplier, 100),
      (agent_get_speed, pos3, ":p"), (position_get_x, ":vx", pos3), (position_get_y, ":vy", pos3),
      (val_abs, ":vx"), (val_abs, ":vy"), (store_add, ":v", ":vx", ":vy"),
      (store_sub, ":frac", ":v", 150), (val_clamp, ":frac", 0, 301),
      (item_get_slot, ":mv", ":w", ":s_move"), (val_mul, ":mv", ":frac"), (val_div, ":mv", 300), (val_add, ":inacc", ":mv"),
      (val_add, ":inacc", "$cs2_acc"),
      # recoil climb and sway
      (item_get_slot, ":mag", ":w", {SL['mag']}), (item_get_slot, ":var", ":w", {SL['var']}),
      (store_div, ":idx", "$cs2_recoil", 100),
      (assign, ":rise", ":idx"), (val_min, ":rise", 8), (val_mul, ":rise", ":mag"), (val_mul, ":rise", 30),
      (assign, ":side", 0),
      (try_begin), (gt, ":idx", 7),
        (store_sub, ":ph", ":idx", 8), (val_mod, ":ph", 12),
        (try_begin), (lt, ":ph", 6), (store_sub, ":tri", ":ph", 3), (else_try), (store_sub, ":tri", 9, ":ph"), (try_end),
        (store_mul, ":side", ":tri", ":var"), (val_mul, ":side", 12),
      (try_end),
      # ray from the camera through the crosshair
      (agent_get_look_position, pos1, ":p"), (mission_cam_get_position, pos2), (position_copy_origin, pos1, pos2),
      (agent_get_position, pos3, ":p"), (position_move_z, pos3, 150),
      (get_distance_between_positions, ":fd", pos2, pos3), (val_add, ":fd", 70),
      (position_move_y, pos1, ":fd"),
      (item_get_slot, ":pellets", ":w", {SL['bullets']}), (item_get_slot, ":spr", ":w", {SL['spread']}),
      (store_add, ":hi", ":inacc", 1), (store_mul, ":lo", ":inacc", -1),
      (store_random_in_range, ":rx", ":lo", ":hi"), (store_random_in_range, ":rz", ":lo", ":hi"),
      (val_add, ":rx", ":rise"), (val_add, ":rz", ":side"),
      (store_add, ":shi", ":spr", 1), (store_mul, ":slo", ":spr", -1),
      (set_fixed_point_multiplier, 1000),
      (try_for_range, ":unused", 0, ":pellets"),
        (copy_position, pos4, pos1),
        (store_random_in_range, ":sx", ":slo", ":shi"), (store_random_in_range, ":sz", ":slo", ":shi"),
        (val_add, ":sx", ":rx"), (val_add, ":sz", ":rz"),
        (position_rotate_z_floating, pos4, ":sz"), (position_rotate_x_floating, pos4, ":sx"),
        (add_missile, ":p", pos4, 250000, ":w", 0, ":ammo", 0),
      (try_end),
      (set_fixed_point_multiplier, 100),
      (val_add, "$cs2_recoil", 100),
      (item_get_slot, ":fi", ":w", ":s_fire"), (val_add, "$cs2_acc", ":fi"), (val_min, "$cs2_acc", 12000),
      (item_get_slot, ":snd", ":w", {SL['snd']}), (agent_play_sound, ":p", ":snd"),
      (particle_system_burst, "psys_pistol_smoke", pos1, 2),
      (try_begin), (eq, "$cs2_ads", 1), (assign, "$cs2_ads", -1),  # the kick plays, then the aim pose is taken again
      (try_end),
      (try_begin), (item_slot_eq, ":w", {SL['pistol']}, 1), (agent_set_animation, ":p", "anim_release_pistol", 1),
      (else_try), (agent_set_animation, ":p", "anim_release_musket", 1), (try_end),
    (try_end),
    (assign, "$cs2_held", ":down"),
    (try_begin), (neg|is_presentation_active, "prsnt_cs2_hud"), (neg|is_presentation_active, "prsnt_battle"), (start_presentation, "prsnt_cs2_hud"), (try_end),
  (try_end),
  ])

cs2_hit = (ti_on_agent_hit, 0, 0, [], [
  (assign, ":w", reg0),
  (store_trigger_param_1, ":v"), (store_trigger_param_2, ":a"), (store_trigger_param, ":bone", 4),
  (ge, ":w", 0), (item_get_slot, ":dmg", ":w", {SL['dmg']}), (gt, ":dmg", 0),
  (val_mul, ":dmg", 100),
  (agent_get_position, pos5, ":a"), (agent_get_position, pos6, ":v"), (get_distance_between_positions, ":dist", pos5, pos6),
  (item_get_slot, ":rm", ":w", {SL['rm']}),
  (store_div, ":steps", ":dist", 1270), (val_min, ":steps", 20),
  (try_for_range, ":unused", 0, ":steps"), (val_mul, ":dmg", ":rm"), (val_div, ":dmg", 1000), (try_end),
  (store_mod, ":rem", ":dist", 1270), (store_sub, ":loss", 1000, ":rm"), (val_mul, ":loss", ":rem"), (val_div, ":loss", 1270),
  (store_sub, ":keep", 1000, ":loss"), (val_mul, ":dmg", ":keep"), (val_div, ":dmg", 1000),
  # hit location and how much armour really covers it: the summed Warband armour value of what the victim wears there
  (assign, ":armor", 0), (assign, ":human", 0),
  (try_begin), (agent_is_human, ":v"),
    (assign, ":human", 1), (assign, ":loc", 1),
    (try_begin), (eq, ":bone", 9),
      (assign, ":loc", 0), (item_get_slot, ":hs", ":w", {SL['hs']}), (val_mul, ":dmg", ":hs"), (val_div, ":dmg", 100),
    (else_try), (is_between, ":bone", 1, 7),
      (assign, ":loc", 2), (val_mul, ":dmg", 3), (val_div, ":dmg", 4),
    (else_try), (eq, ":bone", 0),
      (val_mul, ":dmg", 5), (val_div, ":dmg", 4),
    (try_end),
    (try_for_range, ":i", 4, 8),
      (agent_get_item_slot, ":it", ":v", ":i"), (ge, ":it", 0),
      (try_begin), (eq, ":loc", 0), (item_get_head_armor, ":x", ":it"),
      (else_try), (eq, ":loc", 1), (item_get_body_armor, ":x", ":it"),
      (else_try), (item_get_leg_armor, ":x", ":it"), (try_end),
      (val_add, ":armor", ":x"),
    (try_end),
  (try_end),
  # cloth stops nothing; armour worth {ARMOR_FULL} or more protects as much as CS2 kevlar does against this gun, less armour proportionally less
  (store_mul, ":cover", ":armor", 1000), (val_div, ":cover", {ARMOR_FULL}), (val_clamp, ":cover", 0, 1001),
  (item_get_slot, ":ar", ":w", {SL['armor']}), (store_sub, ":stop", 1000, ":ar"), (val_max, ":stop", 0),
  (val_mul, ":stop", ":cover"), (val_div, ":stop", 1000), (store_sub, ":pass", 1000, ":stop"),
  (val_mul, ":dmg", ":pass"), (val_div, ":dmg", 1000),
  # CS2 damage is out of 100 health: people take it as that share of their own health; horses as a share of {HORSE_BASE}, so a big horse takes more bullets
  (try_begin), (eq, ":human", 1),
    (store_agent_hit_points, ":pct", ":v", 0), (store_agent_hit_points, ":abs", ":v", 1), (val_max, ":pct", 1),
    (store_mul, ":maxhp", ":abs", 100), (val_div, ":maxhp", ":pct"), (val_max, ":maxhp", 20),
  (else_try),
    (assign, ":maxhp", {HORSE_BASE}),
  (try_end),
  (val_mul, ":dmg", ":maxhp"), (val_div, ":dmg", 10000), (val_max, ":dmg", 1),
  (try_begin), (eq, "$cs2_debug", 1), (assign, reg1, ":bone"), (assign, reg2, ":dmg"), (assign, reg3, ":dist"), (assign, reg4, ":armor"), (display_message, "@hit bone {{reg1}} dmg {{reg2}} dist {{reg3}} armour {{reg4}}"), (try_end),
  (set_trigger_result, ":dmg"),
  ])

for cs2_mt in mission_templates: cs2_mt[5].extend([cs2_before_start, cs2_fire, cs2_hit])
"""
s_ = rd('module_mission_templates.py'); wr('module_mission_templates.py', s_ + gun)
hud = """
  ("cs2_hud", prsntf_read_only|prsntf_manual_end_only, 0, [
    (ti_on_presentation_load, [
      (set_fixed_point_multiplier, 1000),
      (create_text_overlay, "$cs2_hud_overlay", "@ ", tf_right_align|tf_with_outline),
      (overlay_set_color, "$cs2_hud_overlay", 0xFFFFFF),
      (position_set_x, pos1, 965), (position_set_y, pos1, 135), (overlay_set_position, "$cs2_hud_overlay", pos1),
      (position_set_x, pos1, 1600), (position_set_y, pos1, 1600), (overlay_set_size, "$cs2_hud_overlay", pos1),
      (presentation_set_duration, 999999),
      ]),
    (ti_on_presentation_run, [
      (try_begin), (lt, "$cs2_hud_clip", 0), (presentation_set_duration, 0),
      (else_try),
        (assign, reg1, "$cs2_hud_clip"), (assign, reg2, "$cs2_hud_reserve"),
        (try_begin), (gt, "$cs2_reload_end", 0), (overlay_set_text, "$cs2_hud_overlay", "@Reloading  {reg1} / {reg2}"),
        (else_try), (overlay_set_text, "$cs2_hud_overlay", "@{reg1} / {reg2}"), (try_end),
      (try_end),
      ]),
    ]),
"""
s_ = rd('module_presentations.py'); i_ = s_.rindex(']'); wr('module_presentations.py', s_[:i_] + hud + s_[i_:])

# provisional ids so the first build pass can import; pass 1 regenerates the real ID_*.py, pass 2 compiles with them
def prov(fn, names):
    with open(os.path.join(OUT, fn), 'a') as fh:
        for i, nm in enumerate(names): fh.write(f"\n{nm} = {90000+i}")
prov('ID_factions.py', ['fac_'+f['id'] for f in F] + ['fac_'+f['culture'] for f in F])
prov('ID_items.py', ['itm_'+x['id'] for x in W+AM+AR])
prov('ID_troops.py', ['trp_'+x['id'] for x in TR+LO+LA])
prov('ID_presentations.py', ['prsnt_cs2_hud'])
prov('ID_scripts.py', ['script_cs2_set_player_skin'])
prov('ID_party_templates.py', [f'pt_{f["id"]}_reinforcements_{k}' for f in F for k in 'abc'])
for n, s in files.items(): open(os.path.join(OUT, n), 'w', encoding='latin-1', newline='\n').write(s)
print('applied', len(files), 'files')
