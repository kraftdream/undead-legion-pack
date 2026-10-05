#!/usr/bin/env bash
# Rebuild the Epic-skeleton Unreal project (skeletons_ue_epic) from Export_UE_Epic/ + Export_UE/Weapons, the same
# sequence as tools/ue/README.md "Rebuild from scratch" with the Epic bone names (UL_EPIC=1 for the MCP-driven builders;
# the in-editor steps detect the project themselves). The editor must be open on skeletons_ue_epic (editor_up.sh).
#   bash tools/ue/epic_build_all.sh [from-step]      steps: assets sockets abp character demo map
set -e
cd "$(dirname "$0")/../.."
export UL_EPIC=1 MSYS_NO_PATHCONV=1
PY="python tools/ue/ue_py.py"
from="${1:-assets}"; go=0
step() { [ "$1" = "$from" ] && go=1; [ $go = 1 ]; }
if step assets; then
  $PY tools/ue/ue_build.py models textures weapons materials clips montages --timeout 60
fi
if step sockets; then
  python tools/ue/ue_weapons.py                       # hand-slot + eye sockets (MCP), on hand_l / hand_r / head
  $PY tools/ue/ue_build.py sockets weapon_blueprints materials --timeout 60
fi
if step abp; then
  $PY tools/ue/ue_build.py abp_asset --timeout 60        # the ABP asset itself; build_abp.py writes its graphs
  python tools/ue/build_abp.py
  $PY tools/ue/ue_build.py abp_defaults --timeout 60      # the float defaults (FadeSpeed...) the MCP variable add leaves at 0
fi
if step character; then
  $PY tools/ue/ue_build.py character eyes --timeout 60     # eyes: the EyesVisible / EyeColor variables + sphere components on BP_UndeadSkeleton, before its graphs and its children
  python tools/ue/build_character.py
  $PY tools/ue/ue_build.py character_children --timeout 60
fi
if step demo; then
  python tools/ue/build_demo_ui.py trees
  $PY tools/ue/ue_build.py demo_vars demo_data demo_actors --timeout 60
  python tools/ue/build_demo_logic.py button Setup SetSelected
  python tools/ue/build_demo_logic.py header pawn browser
  python tools/ue/build_demo_logic.py button EventGraph
  python tools/ue/build_demo_logic.py showcase
fi
if step map; then
  $PY tools/ue/ue_demo_map.py overview demo --timeout 120
fi
$PY tools/ue/ue_build.py save_all --timeout 60         # the MCP-built widgets and graphs are only in memory until saved
echo "epic build done"
