#!/usr/bin/env bash
# Start the Unreal editor on skeletons_ue if it is not running, and wait until both bridges answer
# (Python remote execution and the MCP server). Usage: bash tools/ue/editor_up.sh
cd "$(dirname "$0")/../.."
if ! tasklist | grep -qi unrealeditor; then
  "/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" "$(cygpath -w "$PWD/skeletons_ue/skeletons_ue.uproject")" > /dev/null 2>&1 &
fi
for i in $(seq 1 60); do
  sleep 10
  python tools/ue/mcp_call.py list > /dev/null 2>&1 && python tools/ue/ue_py.py -c "print('up')" 2>/dev/null | grep -q up && { echo "editor up"; exit 0; }
done
echo "editor did not come up"; exit 1
