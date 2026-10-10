# Calradia Offensive

A Counter-Strike 2 x Mount & Blade: Warband mashup, published on [Melty](https://melty.gg).

You play Warband's campaign as a CS2 mercenary. Terrorists and Counter-Terrorists are a 7th and 8th faction alongside
the six kingdoms, each with their own towns, lords, troop tree and gun traders. You start neutral and can hire on with
either side.

- **Warband is the host.** The mod is a Warband module built from TaleWorlds' module system.
- **CS2 is read from your own copy.** On first launch a setup tool reads the agents, weapons and sounds from your
  installed Counter-Strike 2 and converts them to Warband's formats. No Valve or TaleWorlds game files are in this
  repository or its releases. CS2 itself is never launched or modified.

Status: early build, not yet verified in the running game. See `MODLOG.md`.

## Layout

| Path | What it is |
|---|---|
| `sheets/` | The design, as JSON sheets: factions, troops, lords, weapons, ammo, armor, CS2 assets, sounds, hooks. Source of truth. |
| `tools/preflight.py` | Checks every sheet cell and cross-reference. Run before every build. |
| `tools/apply_mod.py` | Generates the modded module-system source from the sheets. |
| `tools/build_module.sh` | Preflight-clean sheets -> compiled module text files in `build/module_txt`. |
| `module_system/` | Warband module system 1.171, ported to Python 3 (its vanilla output matches the game's Native files). |
| `converter/` | The setup tool (Go): CS2 models, textures and sounds -> Warband BRF, DDS and WAV. |
| `tools/build_converter.sh` | Builds the setup tool for Linux and Windows. |

## Build

```
python3 tools/preflight.py
tools/build_module.sh
tools/build_converter.sh
```

## Credits

- Mount & Blade: Warband and its module system: TaleWorlds Entertainment.
- Counter-Strike 2: Valve Corporation.
- [ValveResourceFormat / Source 2 Viewer](https://github.com/ValveResourceFormat/ValveResourceFormat) (MIT) reads CS2's files at setup.
- [OpenBRF](https://github.com/cfcohen/openbrf) was the reference for the BRF format.

Unofficial fan project, not affiliated with TaleWorlds or Valve.
