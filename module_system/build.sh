#!/bin/bash
cd "$(dirname "$0")"; export MS_EXPORT="$1/"; mkdir -p "$1"
for s in init global_variables strings skills music animations meshes sounds skins map_icons factions items scenes troops particle_sys scene_props tableau_materials presentations party_tmps parties quests info_pages scripts mission_tmps game_menus simple_triggers dialogs global_variables_unused postfx; do
  python3 -W ignore process_$s.py 2>&1 || { echo "FAILED process_$s"; exit 1; }
done
