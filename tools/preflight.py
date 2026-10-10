#!/usr/bin/env python3
"""Lays the sheets over each other: lists every empty cell and every reference that does not resolve. Exit 1 if any."""
import json, os, re, sys
R = os.path.join(os.path.dirname(__file__), '..'); SH = os.path.join(R, 'sheets')
S = {n[:-5]: json.load(open(os.path.join(SH, n))) for n in sorted(os.listdir(SH)) if n.endswith('.json')}
bad = []
def rows(n): return S[n]['rows']
OPTIONAL = {('lords', 'fief'), ('assets', 'skip_materials'), ('troops', 'upgrades'), ('weapons', 'difficulty'), ('ammo', 'damage_bonus'), ('lords', 'female')}
for n, d in S.items():
    for i, r in enumerate(d['rows']):
        for k, v in r.items():
            if (n, k) in OPTIONAL: continue
            if v is None and not (n == 'assets' and k == 'anchor'): bad.append(f'{n}[{r.get("id", i)}].{k} is empty')
            if isinstance(v, str) and v == '': bad.append(f'{n}[{r.get("id", i)}].{k} is empty')
            if isinstance(v, list) and len(v) == 0 and k not in ('upgrades',): bad.append(f'{n}[{r.get("id", i)}].{k} is empty')
    ids = [r['id'] for r in d['rows']]
    for x in set(ids):
        if ids.count(x) > 1: bad.append(f'{n}: duplicate id {x}')
native = lambda f: open(os.path.join(R, 'module_system', f), encoding='latin-1').read()
nat_items = set(re.findall(r'^\s*\["(\w+)"', native('module_items.py'), re.M))
nat_troops = set(re.findall(r'^\s*\["(\w+)"', native('module_troops.py'), re.M))
nat_meshes = set(re.findall(r'^\s*\("(\w+)"', native('module_meshes.py'), re.M))
nat_parties = set(re.findall(r'^\s*\("(\w+)"', native('module_parties.py'), re.M))
items = {r['id'] for n in ('weapons', 'ammo', 'armor') for r in rows(n)}
assets = {r['id']: r for r in rows('assets')}; sounds = {r['id'] for r in rows('sounds')}
troops = {r['id'] for r in rows('troops')}; lords = {r['id'] for r in rows('lords')}; sides = {f['side'] for f in rows('factions')}; kingdoms = {f['id'] for f in rows('factions')}
def need(cond, msg):
    if not cond: bad.append(msg)
for w in rows('weapons'):
    need(w['asset'] in assets, f'weapons[{w["id"]}].asset -> {w["asset"]} not in assets')
    need(w['asset'] not in assets or assets[w['asset']]['out'] == w['mesh'], f'weapons[{w["id"]}].mesh {w["mesh"]} is not what asset {w["asset"]} writes')
    need(w['sound'] in sounds, f'weapons[{w["id"]}].sound -> {w["sound"]} not in sounds')
    need(set(w['sides']) <= sides, f'weapons[{w["id"]}].sides unknown')
for a in rows('ammo'): need(set(a['sides']) <= sides, f'ammo[{a["id"]}].sides unknown')
suffix = {'suit': '_body', 'head': '_head', 'gloves': '_glove'}
for a in rows('armor'):
    need(a['asset'] in assets, f'armor[{a["id"]}].asset -> {a["asset"]} not in assets')
    need(a['asset'] not in assets or assets[a['asset']]['out'] + suffix[a['part']] == a['mesh'], f'armor[{a["id"]}].mesh {a["mesh"]} is not what asset {a["asset"]} writes')
used_assets = {w['asset'] for w in rows('weapons')} | {a['asset'] for a in rows('armor')}
for a in assets: need(a in used_assets, f'assets[{a}] is converted but no item uses it')
used_sounds = {w['sound'] for w in rows('weapons')}
for s in sounds: need(s in used_sounds, f'sounds[{s}] is converted but no weapon uses it')
for t in rows('troops'):
    for it in t['items']: need(it in items, f'troops[{t["id"]}].items -> {it} not an item')
    for u in t['upgrades']: need(u in troops, f'troops[{t["id"]}].upgrades -> {u} not a troop')
    need(t['faction'] in kingdoms or t['faction'] == 'deserters', f'troops[{t["id"]}].faction {t["faction"]}')
    kinds = {next((n for n in ('weapons', 'ammo', 'armor') for r in rows(n) if r['id'] == it), None) for it in t['items']}
    guns = [r for r in rows('weapons') if r['id'] in t['items'] and r['type'] != 'knife']
    need(not guns or any(it.startswith('cs2_ammo') for it in t['items']), f'troops[{t["id"]}] carries a gun but no ammo')
for l in rows('lords'):
    need(l['kingdom'] in kingdoms, f'lords[{l["id"]}].kingdom')
    for it in l['items']: need(it in items or it in nat_items, f'lords[{l["id"]}].items -> {it}')
    need(not l['fief'] or l['fief'] in nat_parties, f'lords[{l["id"]}].fief -> {l["fief"]}')
for l in rows('ladies'):
    need(l['kingdom'] in kingdoms, f'ladies[{l["id"]}].kingdom')
    for it in l['items']: need(it in nat_items, f'ladies[{l["id"]}].items -> {it} not a native item')
for f in rows('factions'):
    need(f['leader'] in lords and f['pretender'] in lords, f'factions[{f["id"]}] leader/pretender not in lords')
    for k in ('guard', 'prison_guard', 'castle_guard', 'messenger', 'deserter'): need(f[k] in troops, f'factions[{f["id"]}].{k} -> {f[k]}')
    for t in f['tiers'] + f['quick_battle'] + [x[0] for v in f['reinforcements'].values() for x in v]: need(t in troops, f'factions[{f["id"]}] -> troop {t}')
    for c in f['towns'] + f['castles'] + [f['capital']]: need(c in nat_parties, f'factions[{f["id"]}] centre {c}')
    need(f['banner_mesh'] in nat_meshes, f'factions[{f["id"]}].banner_mesh {f["banner_mesh"]}')
    for k in ('walker_m', 'walker_f'): need(f[k] in nat_troops, f'factions[{f["id"]}].{k}')
    need(f['starting_enemy'] in kingdoms, f'factions[{f["id"]}].starting_enemy')
    n_l = sum(1 for l in rows('lords') if l['kingdom'] == f['id'] and l['role'] == 'lord'); n_w = sum(1 for l in rows('ladies') if l['kingdom'] == f['id'])
    need(n_l == 12 and n_w == 20, f'factions[{f["id"]}] needs 12 lords and 20 ladies for the family script, has {n_l} and {n_w}')
cent = [c for f in rows('factions') for c in f['towns'] + f['castles']]
need(len(cent) == len(set(cent)), 'a centre is given to both factions')
for r in S['start']['rows']:
    for it in [r['body'], r['head'], r['gloves']] + r['weapons']: need(it in items, f'start[{r["id"]}] -> {it}')
    need(r['spawn'] in nat_parties, f'start[{r["id"]}].spawn -> {r["spawn"]}')
for h in rows('hooks'):
    for s_ in h['sheet'].split(','): need(s_ in S, f'hooks[{h["id"]}].sheet -> {s_}')
    need(h['verified'] in ('build', 'devrun', 'ingame'), f'hooks[{h["id"]}].verified')
unver = [h['id'] for h in rows('hooks') if h['verified'] != 'ingame']
print(f'{sum(len(d["rows"]) for d in S.values())} rows in {len(S)} sheets')
for b in bad: print('PREFLIGHT:', b)
print(f'{len(bad)} problems; {len(unver)} of {len(rows("hooks"))} hooks not yet verified in the running game')
sys.exit(1 if bad else 0)
