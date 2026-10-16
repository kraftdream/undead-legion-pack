# Shell helpers for driving the UE 5.4 editor (source it): every input goes to a named window or nowhere.
#   source tools/ue/ue54_gui.sh
#   on BP_UndeadSkeleton click 100 200        click only if that window can be put in front (else return 1)
#   on BP_UndeadSkeleton keys "^a"            the same for keys / paste / drag / clip-paste
G="powershell -STA -NoProfile -File $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/gui.ps1"

on() {
  local win="$1"; shift
  $G focus "$win" > /dev/null
  sleep 0.3
  if ! $G fgis "$win" > /dev/null; then
    echo "ABORT: '$win' is not in front ($($G fgis "$win"))" >&2
    return 1
  fi
  $G "$@"
}
