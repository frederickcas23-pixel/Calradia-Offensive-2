#!/bin/bash
# Regenerates the modded module-system source from the sheets and compiles it twice (ids settle on pass 1).
set -e; cd "$(dirname "$0")/.."
rm -rf build/ms_mod build/module_txt
python3 tools/apply_mod.py module_system build/ms_mod
build/ms_mod/build.sh ../module_txt > build/pass1.log 2>&1 || { tail -20 build/pass1.log; exit 1; }
build/ms_mod/build.sh ../module_txt > build/pass2.log 2>&1 || { tail -20 build/pass2.log; exit 1; }
grep -inE "error|warning|unable|not found|invalid|unrecognized" build/pass2.log | head -40 || true
ls build/module_txt | wc -l
