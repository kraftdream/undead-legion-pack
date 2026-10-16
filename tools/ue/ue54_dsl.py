"""The graph DSL of the MCP-built Blueprints (build_abp.py, build_character.py, build_demo_logic.py, build_bow_notifies.py,
build_showreel_director.py), read back as data for the UE 5.4 build, which has no MCP: an s-expression parser and the
collection of every graph the 5.8 build writes, with its function signatures.

    python tools/ue/ue54_dsl.py heads        every distinct node head used, with a count
"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("UL_EPIC", "1")


class Sym(str):
    """A bare symbol (as opposed to a string literal)."""


class Kw(str):
    """A :keyword (named argument or branch label)."""


def tokenize(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
        elif c == ";":
            while i < n and src[i] != "\n":
                i += 1
        elif c in "()":
            out.append(c); i += 1
        elif c == '"':
            j = i + 1
            while src[j] != '"':
                j += 1
            out.append(("str", src[i + 1:j])); i = j + 1
        elif c == ":" and i + 1 < n and src[i + 1] == '"':
            j = i + 2
            while src[j] != '"':
                j += 1
            out.append(Kw(src[i + 2:j])); i = j + 1
        else:
            j = i
            # a head may carry a parenthesised variant suffix: Utilities|Array|Get(acopy), Widget|SetText(Text)
            while j < n and src[j] not in " \t\r\n()":
                j += 1
            if j < n and src[j] == "(" and "|" in src[i:j] and re.match(r"\(([A-Za-z]+)\)", src[j:]):
                k = src.index(")", j) + 1
                tok = src[i:k]; j = k
            else:
                tok = src[i:j]
            out.append(Kw(tok[1:]) if tok.startswith(":") else tok); i = j
    return out


def _atom(t):
    if isinstance(t, tuple):
        return t[1] if False else Str(t[1])
    if isinstance(t, Kw):
        return t
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d*(e-?\d+)?|-?\d*\.\d+", t):
        return float(t)
    if t in ("true", "false"):
        return t == "true"
    return Sym(t)


class Str(str):
    """A string literal."""


def parse(src):
    toks = tokenize(src)
    pos = 0

    def read():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == "(":
            lst = []
            while toks[pos] != ")":
                lst.append(read())
            pos += 1
            return lst
        return _atom(t)

    forms = []
    while pos < len(toks):
        forms.append(read())
    return forms


# ------------------------------------------------------------------------------------------ the graphs of the 5.8 build

def sources():
    """[(blueprint asset path, graph name, params [(name, type, is_input)] or None for an event graph, dsl text)]."""
    import build_abp, build_character, build_demo_logic, build_showreel_director
    out = []
    # ABP: event graph + functions (split as build_abp.event_graph does)
    parts = build_abp.EVENT_DSL.split(chr(10) + "(fn ")
    abp_params = {"PlayBase": [("Clip", "/Script/Engine.AnimSequenceBase", True)],
                  "GetBaseClip": [("Clip", "/Script/Engine.AnimSequenceBase", False)],
                  "SetHandTargets": [(n, "float", True) for n in ("GripL", "GripR", "FingerL", "FingerR")],
                  "SetBlockTarget": [("Target", "float", True)],
                  "SetTwitchWeight": [("Index", "int", True), ("Weight", "float", True)]}
    out.append((build_abp.ABP, "EventGraph", None, parts[0]))
    for body in parts[1:]:
        name = body.split()[0]
        out.append((build_abp.ABP, name, abp_params[name], "(fn " + body))
    # the character
    V = build_character.V
    for fn in build_character.ORDER:
        params, code = build_character.FUNCS[fn]
        out.append((build_character.BPP, fn, params, code % {"V": V}))
    out.append((build_character.BPP, "EventGraph", None, build_character.EVENTS % {"V": V}))
    # the demo widgets and actors
    f = build_demo_logic.fill
    UI = build_demo_logic.UI
    for bpname, funcs, order in (("WBP_DemoButton", build_demo_logic.BUTTON, ["Setup", "SetSelected"]),
                                 ("WBP_DemoHeader", build_demo_logic.HEADER, ["SetCaption"]),
                                 ("WBP_AnimBrowser", build_demo_logic.BROWSER, build_demo_logic.BROWSER_ORDER)):
        for fn in order:
            params, code = funcs[fn]
            out.append((UI + "/" + bpname, fn, params, f(code)))
    out.append((UI + "/WBP_AnimBrowser", "EventGraph", None, f(build_demo_logic.BROWSER_EVENTS)))
    D = build_demo_logic.D
    for fn, (params, code) in build_demo_logic.PAWN_FUNCS.items():
        out.append((D + "/BP_OrbitPawn", fn, params, f(code)))
    out.append((D + "/BP_OrbitPawn", "EventGraph", None, f(build_demo_logic.PAWN_EVENTS)))
    out.append((D + "/BP_DemoShowcase", "EventGraph", None, f(build_demo_logic.SHOWCASE_EVENTS)))
    return out


def notify_sources():
    """The four bow notifies' Received_Notify overrides (build_bow_notifies.py's text, the manifest's frames)."""
    import build_bow_notifies, inspect
    from pathlib import Path
    manifest = json.loads((Path(__file__).resolve().parents[2] / "Animations/clips.json").read_text())
    shot = next(c for c in manifest["clips"] if c["name"] == "Shoot_01" and not c.get("disabled"))
    src = inspect.getsource(build_bow_notifies.build)
    tmpl = src[src.index('code="""') + 8:src.index('""" % {')]
    out = []
    for event in ("BowReset", "BowDraw", "BowAttach", "BowRelease"):
        code = tmpl % {"event": event, "expected": (shot["events"][event] - 1) / 30}
        out.append(("/Game/UndeadLegion/Blueprints/Notifies/AN_" + event, "Received_Notify",
                    [("MeshComp", "/Script/Engine.SkeletalMeshComponent", True), ("Animation", "/Script/Engine.AnimSequenceBase", True),
                     ("EventReference", "AnimNotifyEventReference", True), ("ReturnValue", "bool", False)], code))
    return out


SPECIAL = {"event", "fn", "bind", "if", "else", "for", "switch", "select", "return", "range", "and", "or", "not",
           "==", "!=", "<", "<=", ">", ">=", "+", "-", "*", "/", "while", ".x", ".y", ".z", ".yaw"}


def heads():
    from collections import Counter
    cnt = Counter()

    def walk(x):
        if isinstance(x, list) and x:
            h = x[0]
            if isinstance(h, Sym) and "|" in h:
                cnt[str(h)] += 1
            for y in x:
                walk(y)
    for _, _, _, code in sources() + notify_sources():
        for form in parse(code):
            walk(form)
    return cnt


if __name__ == "__main__":
    if sys.argv[1:] == ["heads"]:
        for h, c in sorted(heads().items()):
            print("%3d %s" % (c, h))
