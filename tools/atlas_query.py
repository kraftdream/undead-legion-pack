"""Read a `bone_atlas.py` dump without Blender. Fast to iterate against.

    python tools/atlas_query.py Rig/atlas/atlas.json <probe> [more probes]
    python tools/atlas_query.py Rig/atlas/atlas.json --bone hand_fk.R
    python tools/atlas_query.py Rig/atlas/atlas.json --shape swivel
    python tools/atlas_query.py Rig/atlas/atlas.json --inert
    python tools/atlas_query.py Rig/atlas/atlas.json --probes

The atlas answers "which control does X", which is the question every
wrong-control bug in this pack was really asking. Sorting a recorded response
is a measurement; picking a channel because of what its axis is called is not.
"""

import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def probes(a):
    seen = {}
    for r in a["records"]:
        for k in r["probes"]:
            seen[k] = seen.get(k, 0) + 1
    for k, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        print("  %-24s moved by %d channels" % (k, n))


def query(a, name, top=15, bone=None):
    hits = []
    for r in a["records"]:
        if bone and bone not in r["bone"]:
            continue
        p = r["probes"].get(name)
        if not p:
            continue
        hits.append((p.get("mag", abs(p.get("delta", 0.0))), r, p))
    hits.sort(key=lambda h: -h[0])
    print("\n=== channels that move %r  (delta %.3f rad / %.4f m) ==="
          % (name, a["rot_delta"], a["loc_delta"]))
    print("  %-26s %-6s %9s  %-7s %-7s %s"
          % ("bone", "chan", "effect", "lin", "asym", "direction / sign"))
    for mag, r, p in hits[:top]:
        print("  %-26s %-6s %9.4f  %-7s %-7s %s%s"
              % (r["bone"], r["channel"], mag,
                 r["linearity"], r["asymmetry"],
                 p.get("says", "%+.5f" % p.get("delta", 0.0)),
                 "" if r["shape"] == "move" else "   [%s]" % r["shape"]))
    return hits


def bone(a, name):
    print("\n=== %s ===" % name)
    for r in a["records"]:
        if r["bone"] != name:
            continue
        print("  %-6s peak %8.4f  lin %-6s asym %-6s  %s"
              % (r["channel"], r["peak"], r["linearity"], r["asymmetry"], r["shape"]))
        for k, p in list(r["probes"].items())[:6]:
            print("      %-24s %s"
                  % (k, p.get("says", "%+.5f" % p.get("delta", 0.0))))


def shape(a, kind):
    print("\n=== channels classified %r ===" % kind)
    for r in a["records"]:
        if r["shape"].startswith(kind):
            print("  %-26s %-6s peak %8.4f  %-18s root_moved=%s ext=%s"
                  % (r["bone"], r["channel"], r["peak"], r["shape"],
                     r.get("root_moved"), r.get("extension_change")))


def inert(a):
    """Channels that do nothing. Key one and it is authored-and-discarded."""
    by_bone = {}
    for r in a["records"]:
        if r["shape"] == "inert":
            by_bone.setdefault(r["bone"], []).append(r["channel"])
    print("\n=== INERT channels: %d bones ===" % len(by_bone))
    for b, ch in sorted(by_bone.items()):
        print("  %-28s %s" % (b, " ".join(ch)))


def main():
    a = load(sys.argv[1])
    args = sys.argv[2:]
    if not args:
        probes(a)
        return
    i = 0
    while i < len(args):
        x = args[i]
        if x == "--bone":
            i += 1
            bone(a, args[i])
        elif x == "--shape":
            i += 1
            shape(a, args[i])
        elif x == "--inert":
            inert(a)
        elif x == "--probes":
            probes(a)
        else:
            query(a, x)
        i += 1


if __name__ == "__main__":
    main()
