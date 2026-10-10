#!/usr/bin/env python3
"""Copies each gun's real numbers from Counter-Strike 2's own weapon data (scripts/weapons.vdata, decompiled from the
developer's installed copy) into sheets/weapons.json under "cs2". Usage: import_cs2_stats.py <weapons.vdata>"""
import json, os, re, sys
txt = open(sys.argv[1]).read()
P = os.path.join(os.path.dirname(__file__), '..', 'sheets', 'weapons.json')
d = json.load(open(P))
def block(name):
    m = re.search(r'^\t' + re.escape(name) + r' = \n\t\{\n(.*?)^\t\}', txt, re.S | re.M)
    return m.group(1) if m else None
def val(b, key):
    m = re.search(r'^\t\t' + key + r' = (.+)$', b, re.M)
    if not m: return None
    v = m.group(1).strip()
    if v.startswith('['): return float(v.strip('[] ').split(',')[0])
    if v in ('true', 'false'): return v == 'true'
    try: return float(v)
    except ValueError: return v.strip('"')
KEYS = {'damage': 'm_nDamage', 'clip': 'm_iMaxClip1', 'full_auto': 'm_bIsFullAuto', 'bullets': 'm_nNumBullets', 'cycle_time': 'm_flCycleTime',
        'spread': 'm_flSpread', 'inaccuracy_stand': 'm_flInaccuracyStand', 'inaccuracy_crouch': 'm_flInaccuracyCrouch', 'inaccuracy_move': 'm_flInaccuracyMove',
        'inaccuracy_fire': 'm_flInaccuracyFire', 'recoil_magnitude': 'm_flRecoilMagnitude', 'recoil_angle_variance': 'm_flRecoilAngleVariance',
        'recovery_time_stand': 'm_flRecoveryTimeStand', 'headshot_multiplier': 'm_flHeadshotMultiplier', 'armor_ratio': 'm_flArmorRatio',
        'range_modifier': 'm_flRangeModifier', 'reload_time': 'm_flDisallowAttackAfterReloadStartDuration', 'max_speed': 'm_flMaxSpeed', 'price': 'm_nPrice',
        'reserve_clips_or_rounds': 'm_nPrimaryReserveAmmoMax', 'zoom_levels': 'm_nZoomLevels'}
for w in d['rows']:
    if w['type'] == 'knife': continue
    b = block(w['cs2_class'] + '_prefab')
    assert b, w['cs2_class']
    out = {}
    for k, key in KEYS.items():
        v = val(b, key)
        assert v is not None, (w['id'], key)
        out[k] = v
    # CS2 keeps a second value for the alternate mode: scoped for the AWP, the same number for guns without a scope
    for k in ('inaccuracy_stand', 'inaccuracy_crouch', 'inaccuracy_move', 'inaccuracy_fire'):
        m = re.search(r'^\t\t' + KEYS[k] + r' = \[\s*[^,]+,\s*([^\]]+)\]', b, re.M)
        out[k + '_alt'] = float(m.group(1)) if m else out[k]
    out['zoom_fov'] = val(b, 'm_nZoomFOV1') if out['zoom_levels'] else 0.0
    w['cs2'] = out
    # native Warband fields follow the CS2 numbers so the inventory card and AI use the same gun
    w['clip'] = int(out['clip'])
    print(w['id'], out)
d['_doc'] = ("One row per CS2 weapon item. cs2 = numbers copied from Counter-Strike 2's own weapon data by tools/import_cs2_stats.py; they drive the "
             "scripted fire (rate, automatic fire, spread, recoil, pellets) and the damage model (damage, headshot, armour, range falloff). "
             "damage/accuracy/speed/shoot_speed are the native Warband fields the AI and the item card use. asset -> assets.json id. sound -> sounds.json id.")
open(P, 'w').write('{"_doc":%s,\n "rows":[\n' % json.dumps(d['_doc']) + ',\n'.join(' ' + json.dumps(r) for r in d['rows']) + '\n ]}\n')
