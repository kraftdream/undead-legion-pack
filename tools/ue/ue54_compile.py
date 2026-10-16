"""Compile the MCP graph DSL (tools/ue/ue54_dsl.py) into UE 5.4 paste text (tools/ue/ue54_t3d.py).

    python tools/ue/ue54_compile.py OUTDIR      every Blueprint's variables, functions and event graph, one file per paste

The DSL as the 5.8 build writes it (build_abp.py, build_character.py, build_demo_logic.py, build_bow_notifies.py):
  (event Name (params) stmt...)    (fn Name (params) stmt...)
  stmt: (bind name expr [branches])  (bind (a b) expr)  (if cond stmt... [(else stmt...)])  (for x coll stmt...)
        (for i (range n) stmt...)  (switch int expr (:0 stmt...)...)  (return [expr])  a call  a setter
  expr: literals, bound names, params, self, (op a b), (select c a b), (.x v), calls, getters
The pin names come from the 5.4 engine (calibrated by pasting pin-less nodes and copying them back, 2026-10-16).
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue54_dsl import parse, Sym, Kw, Str, sources, notify_sources
import ue54_sigs as SG
from ue54_t3d import T, parse_type, Node, link, guid, obj_text, pintype_struct, K2

E, U, C = SG.E, SG.U, SG.C
PKG = "/Game/UndeadLegion"
KML = E + "KismetMathLibrary"
MACROS = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros"


def gen_class(bp_path):
    return "%s.%s_C" % (bp_path, bp_path.split("/")[-1])


# ------------------------------------------------------------------------------------------ the Blueprints

CHAR = PKG + "/Blueprints/BP_UndeadSkeleton"
ABP = PKG + "/Blueprints/ABP_UndeadSkeleton"
UI = PKG + "/Demo/UI"
BTN, HDR, BROWSER = UI + "/WBP_DemoButton", UI + "/WBP_DemoHeader", UI + "/WBP_AnimBrowser"
PAWN, SHOW = PKG + "/Demo/Blueprints/BP_OrbitPawn", PKG + "/Demo/Blueprints/BP_DemoShowcase"
ARROW = PKG + "/Weapons/Blueprints/BP_Weapon_Arrow"

SEQ, SKM, SKC = "obj:" + E + "AnimSequenceBase", "obj:" + E + "SkeletalMesh", "obj:" + E + "SkeletalMeshComponent"
VEC, LC, XF = SG.VEC, SG.LC, SG.XF


def _abp_vars():
    from ue_common import ABP_FLOATS
    v = [("BaseA", SEQ, True, None), ("BaseB", SEQ, True, None), ("UseB", "bool", True, "false")]
    v += [(n, "real", True, "%f" % d) for n, d in ABP_FLOATS.items()]
    return v


# (name, type, instance editable, default text or None)
VARS = {
    ABP: _abp_vars(),
    CHAR: [("DefaultModules", SKM + "[]", True, None), ("ArmorComponents", SKC + "[]", False, None),
           ("LoadoutNames", "str[]", True, None), ("LoadoutRight", "cls:" + E + "Actor[]", True, None),
           ("LoadoutLeft", "cls:" + E + "Actor[]", True, None), ("WeaponActors", "obj:" + E + "Actor[]", False, None),
           ("CurrentLoadout", "int", False, "-1"), ("StartLoadout", "int", True, "-1"), ("StartClip", SEQ, True, None),
           ("DisplayName", "str", True, "Undead Skeleton"), ("FingerIdleLeft", "bool", True, "true"), ("FingerIdleRight", "bool", True, "true"),
           ("ClipHoldLeft", "bool", False, None), ("ClipHoldRight", "bool", False, None), ("FingersSuspended", "bool", False, None),
           ("StartActions", SEQ + "[]", True, None), ("StartActionDelay", "real", True, "0.800000"), ("StartActionGap", "real", True, "0.900000"),
           ("StartActionIndex", "int", False, None), ("StartHoldLeft", "bool", True, None),
           ("LoopMontage", "obj:" + E + "AnimMontage", False, None), ("ActionMontage", "obj:" + E + "AnimMontage", False, None),
           ("HasWeaponLeft", "bool", False, None), ("HasWeaponRight", "bool", False, None),
           ("BowMesh", "obj:" + E + "PoseableMeshComponent", False, None), ("HeldArrow", "obj:" + E + "Actor", False, None),
           ("HasBow", "bool", False, None), ("BowAttached", "bool", False, None), ("BowShotActive", "bool", False, None),
           ("BowClip", SEQ, False, None), ("Draw", "real", False, None), ("Apex", VEC, False, None),
           ("ArrowClass", "cls:" + E + "Actor", True, None),
           ("EyesVisible", "bool", True, "true"), ("EyeColor", LC, True, "(R=5.000000,G=0.200000,B=0.100000,A=1.000000)")],
    BTN: [("Browser", "obj:" + gen_class(BROWSER), False, None), ("Kind", "int", False, None), ("Index", "int", False, None)],
    HDR: [],
    BROWSER: [("CharacterClasses", "cls:" + gen_class(CHAR) + "[]", True, None), ("CharacterNames", "str[]", True, None),
              ("Clips", SEQ + "[]", True, None), ("ClipNames", "str[]", True, None), ("ClipModes", "int[]", True, None),
              ("ClipArgs", "int[]", True, None), ("ClipSections", "int[]", True, None), ("ClipLoco", "bool[]", True, None),
              ("ClipGrip", "bool[]", True, None), ("SectionNames", "str[]", True, None), ("AllModules", SKM + "[]", True, None),
              ("AllModuleOwner", "int[]", True, None), ("AllModuleNames", "str[]", True, None), ("LoadoutNames", "str[]", True, None),
              ("SpawnTransform", XF, True, None), ("Current", "obj:" + gen_class(CHAR), False, None), ("CurrentChar", "int", False, None),
              ("CharButtons", "obj:" + gen_class(BTN) + "[]", False, None), ("ClipButtons", "obj:" + gen_class(BTN) + "[]", False, None),
              ("ModuleButtons", "obj:" + gen_class(BTN) + "[]", False, None), ("ModuleButtonMesh", SKM + "[]", False, None),
              ("WeaponButtons", "obj:" + gen_class(BTN) + "[]", False, None), ("FooterButtons", "obj:" + gen_class(BTN) + "[]", False, None),
              ("CurrentClip", "int", False, None), ("LastIdle", "int", False, None), ("BaseLoco", "bool", False, None),
              ("RootMotionOn", "bool", True, "true"), ("TurntableOn", "bool", True, "false"), ("EyesOn", "bool", True, "true"),
              ("TwitchOn", "bool[]", False, None), ("BlockHeld", "bool", False, None), ("ActionClip", "int", False, "-1"),
              ("ActionEnd", "real", False, None), ("DeathPauseAt", "real", False, None), ("DeathResumeAt", "real", False, None)],
    PAWN: [("Yaw", "real", True, "-25.000000"), ("Pitch", "real", True, "-10.000000"), ("Distance", "real", True, "420.000000"),
           ("Target", "obj:" + E + "Actor", False, None), ("PivotHeight", "real", True, "5.000000")],
    SHOW: [],
}
# components and widget variables (made by the component / widget-tree steps, not pasted): name -> type
OWN_OBJECTS = {
    CHAR: {"EyeL": "obj:" + E + "StaticMeshComponent", "EyeR": "obj:" + E + "StaticMeshComponent"},
    PAWN: {"Arm": "obj:/Script/Engine.SpringArmComponent", "Pivot": "obj:" + E + "SceneComponent", "Camera": "obj:" + E + "CameraComponent"},
    BTN: {"Btn": "obj:" + U + "Button", "Label": "obj:" + U + "TextBlock"},
    HDR: {"Label": "obj:" + U + "TextBlock"},
    BROWSER: {"CharacterList": "obj:" + U + "VerticalBox", "ModuleList": "obj:" + U + "VerticalBox", "WeaponList": "obj:" + U + "VerticalBox",
              "ClipList": "obj:" + U + "VerticalBox", "FooterBar": "obj:" + U + "HorizontalBox", "InfoLabel": "obj:" + U + "TextBlock"},
}
PARENT = {ABP: E + "AnimInstance", CHAR: E + "Character", BTN: U + "UserWidget", HDR: U + "UserWidget", BROWSER: U + "UserWidget",
          PAWN: E + "Pawn", SHOW: E + "Actor"}
NATIVE_SELF_VARS = {E + "Character": {"Mesh": SKC}}
CLASS_ALIASES = {"BPUndeadSkeleton": CHAR, "ABPUndeadSkeleton": ABP, "WBPDemoButton": BTN, "WBPDemoHeader": HDR,
                 "WBPAnimBrowser": BROWSER, "BPOrbitPawn": PAWN}
NATIVE_CLASS_VARS = {"PlayerController": (E + "PlayerController", {"ShowMouseCursor": ("bShowMouseCursor", "bool")}),
                     "SpringArmComponent": (E + "SpringArmComponent", {"TargetArmLength": ("TargetArmLength", "real")})}
CASTS = {"ABP_UndeadSkeleton": gen_class(ABP), "BP_UndeadSkeleton": gen_class(CHAR), "BP_OrbitPawn": gen_class(PAWN),
         "BP_Weapon_Arrow": gen_class(ARROW), "PoseableMeshComponent": E + "PoseableMeshComponent",
         "StaticMeshComponent": E + "StaticMeshComponent"}


def _ptype(t):
    """A FUNCS parameter type (basic name or object class path) as a sig type string."""
    if t.startswith("/"):
        return "obj:" + t
    return {"float": "real", "string": "str", "LinearColor": LC, "name": "name", "int": "int", "bool": "bool",
            "AnimNotifyEventReference": "struct:" + E + "AnimNotifyEventReference"}.get(t, t)


def function_table():
    """bp -> {fn: (ins [(n, type)], outs [(n, type)])} from the DSL sources' signatures."""
    tab = {}
    for bp, name, params, _ in sources() + notify_sources():
        if params is None:
            continue
        tab.setdefault(bp, {})[name] = ([(n, _ptype(t)) for n, t, i in params if i], [(n, _ptype(t)) for n, t, i in params if not i])
    return tab


FUNCS = None


# ------------------------------------------------------------------------------------------ values

class Val:
    def __init__(self, pin=None, t=None, lit=None, is_lit=False):
        self.pin, self.t, self.lit, self.is_lit = pin, parse_type(t) if isinstance(t, str) else t, lit, is_lit

    @staticmethod
    def literal(v):
        if isinstance(v, bool):
            return Val(t="bool", lit=v, is_lit=True)
        if isinstance(v, int):
            return Val(t="int", lit=v, is_lit=True)
        if isinstance(v, float):
            return Val(t="real", lit=v, is_lit=True)
        return Val(t="str", lit=str(v), is_lit=True)


def lit_text(v, t):
    if isinstance(v, bool):
        return "true" if v else "false"
    if t is not None and t.cat == "real":
        return "%f" % float(v)
    if t is not None and t.cat == "int":
        return "%d" % int(v)
    return str(v)


class CompileError(Exception):
    pass


# ------------------------------------------------------------------------------------------ the graph builder

class Graph:
    def __init__(self, bp, fn_name=None):
        self.bp = bp
        self.cls = gen_class(bp)
        self.fn = fn_name
        self.nodes = []
        self.cur = None          # the exec output pin the next statement attaches to
        self.env = {}            # name -> Val
        self.col = 0
        self.lane = 0
        self.self_node = None

    # ---- layout: exec nodes left to right on their lane (else / case branches one lane lower), pure nodes placed by
    # layout() to the left of what they feed
    def add(self, node, pure=False):
        node.pure = pure
        if not pure:
            self.col += 1
            node.x, node.y = 660 * self.col, 560 * self.lane     # every exec node on the pure-node grid (330)
        self.nodes.append(node)
        return node

    def chain(self, node, in_name="execute", out_name="then"):
        if self.cur is None:
            raise CompileError("statement after the flow ended in %s.%s" % (self.bp, self.fn))
        link(self.cur, node.get(in_name, "in"))
        self.cur = node.get(out_name, "out") if out_name else None
        return node

    # ---- inputs
    def feed(self, pin, val):
        """Connect a value (or put a literal) on an input pin."""
        if val is None:
            return
        if val.is_lit:
            t = pin.t
            if t.cat == "class" or (t.cat == "object" and isinstance(val.lit, str) and val.lit.startswith("/")):
                pin.default_object = val.lit
            elif t.cat == "struct" and t.obj == "/Script/InputCore.Key":
                pin.default = val.lit
            else:
                pin.default = lit_text(val.lit, t)
            return
        flex = getattr(val, "flex", None)
        if flex and pin.t.cat in ("name", "text") and val.t.cat == "string":
            for p in flex:
                p.t = T(pin.t.cat)
            val.t = T(pin.t.cat)
        link(val.pin, pin)

    # ---- self
    def self_val(self):
        if self.self_node is None:
            n = self.add(Node(K2 + "K2Node_Self"), pure=True)
            n.pin("self", "out", "obj:" + self.cls)
            self.self_node = n
        return Val(self.self_node.get("self"), "obj:" + self.cls)

    # ---- variables
    def var_type(self, bp, name):
        for n, t, _, _ in VARS.get(bp, []):
            if n == name:
                return t
        if name in OWN_OBJECTS.get(bp, {}):
            return OWN_OBJECTS[bp][name]
        par = PARENT.get(bp)
        if par in NATIVE_SELF_VARS and name in NATIVE_SELF_VARS[par]:
            return NATIVE_SELF_VARS[par][name]
        return None

    def get_var(self, name, owner=None, target=None):
        bp = owner or self.bp
        t = self.var_type(bp, name)
        if t is None:
            raise CompileError("unknown variable %s on %s" % (name, bp))
        if owner and owner != self.bp:
            ref = '(MemberParent="%s",MemberName="%s")' % (obj_text(T("class", gen_class(owner))), name)
        else:
            ref = '(MemberName="%s",bSelfContext=True)' % name
        n = self.add(Node(K2 + "K2Node_VariableGet", ["VariableReference=" + ref]), pure=True)
        out = n.pin(name, "out", t)
        if owner and owner != self.bp:
            self.feed(n.pin("self", "in", "obj:" + gen_class(owner)), target)
        return Val(out, t)

    def set_var(self, name, val, owner=None, target=None, native=None):
        if native:
            parent, prop, t = native
            ref = '(MemberParent="%s",MemberName="%s")' % (obj_text(T("class", parent)), prop)
            n = self.add(Node(K2 + "K2Node_VariableSet", ["VariableReference=" + ref]))
            n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
            self.feed(n.pin(prop, "in", t), self.coerce(val, parse_type(t)))
            self.feed(n.pin("self", "in", "obj:" + parent), target)
            self.chain(n)
            return
        t = self.var_type(owner or self.bp, name)
        if t is None:
            raise CompileError("unknown variable %s on %s" % (name, owner or self.bp))
        n = self.add(Node(K2 + "K2Node_VariableSet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % name]))
        n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
        self.feed(n.pin(name, "in", t), self.coerce(val, parse_type(t)))
        n.pin("Output_Get", "out", t)
        self.chain(n)

    def coerce(self, val, t):
        """A literal written as 1 where the pin is a float, and so on."""
        if val is not None and val.is_lit and t is not None and t.cat == "real" and isinstance(val.lit, int) and not isinstance(val.lit, bool):
            return Val(t="real", lit=float(val.lit), is_lit=True)
        return val

    # ---- calls
    def call(self, head, sig, args, kwargs, owner_cls=None):
        """A K2Node_CallFunction / CallArrayFunction from a signature dict."""
        cls = sig["cls"]
        kind = "K2Node_CallArrayFunction" if sig.get("array") else "K2Node_CallFunction"
        props = ['FunctionReference=(MemberParent="%s",MemberName="%s")' % (obj_text(T("class", cls)), sig["fn"])]
        n = Node(K2 + kind, props)
        pure = sig["pure"]
        if not pure:
            n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
        ins = sig["ins"]
        target = kwargs.pop("self", None)
        if sig.get("target"):
            self.feed(n.pin("self", "in", "obj:" + sig["target"]), target)
        names = [i[0] for i in ins]
        bound = {}
        for k, v in kwargs.items():
            pn = _match_kw(k, names)
            if pn is None:
                raise CompileError("%s has no input %s (%s)" % (head, k, names))
            bound[pn] = v
        for i, v in enumerate(args):
            bound[names[i]] = v
        outs = {}
        for spec in ins:
            name, t = spec[0], parse_type(spec[1])
            default = spec[2] if len(spec) > 2 else None
            v = bound.get(name)
            if t.cat == "wildcard" and v is not None and not v.is_lit and v.t is not None:
                t = T(v.t.cat, v.t.obj, t.arr or v.t.arr, t.ref, v.t.sub) if not t.arr else T(v.t.cat, v.t.obj, True, t.ref, v.t.sub)
            p = n.pin(name, "in", t, default=default)
            if v is not None:
                self.feed(p, self.coerce(v, t))
        for name, t in sig["outs"]:
            outs[name] = n.pin(name, "out", t)
        self.add(n, pure=pure)
        if not pure:
            self.chain(n)
        return n, outs

    def call_user(self, owner, fn, args, kwargs):
        ins, outs = FUNCS[owner][fn]
        n = Node(K2 + "K2Node_CallFunction",
                 ['FunctionReference=(MemberParent="%s",MemberName="%s")' % (obj_text(T("class", gen_class(owner))), fn)])
        n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
        self.feed(n.pin("self", "in", "obj:" + gen_class(owner)), kwargs.pop("self", None))
        names = [i[0] for i in ins]
        bound = dict(zip(names, args))
        for k, v in kwargs.items():
            if k not in names:
                raise CompileError("%s.%s has no input %s" % (owner, fn, k))
            bound[k] = v
        for name, t in ins:
            p = n.pin(name, "in", t)
            if name in bound:
                self.feed(p, self.coerce(bound[name], parse_type(t)))
        o = {name: n.pin(name, "out", t) for name, t in outs}
        self.add(n)
        self.chain(n)
        return n, o


def _match_kw(k, names):
    for cand in (k, "In" + k, k[2:] if k.startswith("In") else None, "b" + k, "In" + k[0].upper() + k[1:]):
        if cand and cand in names:
            return cand
    low = {n.lower(): n for n in names}
    return low.get(k.lower())


# ------------------------------------------------------------------------------------------ expressions and statements

COMPARE = ("==", "!=", "<", "<=", ">", ">=")
ARITH = ("+", "-", "*", "/")


class Compiler:
    def __init__(self, graph):
        self.g = graph

    # ------------------------------------------------ expressions
    def expr(self, x):
        g = self.g
        if isinstance(x, bool) or isinstance(x, (int, float)):
            return Val.literal(x)
        if isinstance(x, Str):
            return Val.literal(str(x))
        if isinstance(x, Sym):
            if x == "self":
                return g.self_val()
            if x in g.env:
                return g.env[x]
            raise CompileError("unbound %s in %s.%s" % (x, g.bp, g.fn))
        if not isinstance(x, list) or not x:
            raise CompileError("bad expression %r" % (x,))
        h = x[0]
        if h in COMPARE or h in ARITH:
            return self.op(h, x[1:])
        if h in ("and", "or"):
            a, b = self.expr(x[1]), self.expr(x[2])
            n, o = g.call(h, {"cls": KML, "fn": "BooleanAND" if h == "and" else "BooleanOR", "pure": True,
                              "ins": [("A", "bool"), ("B", "bool")], "outs": [("ReturnValue", "bool")]}, [a, b], {})
            return Val(o["ReturnValue"], "bool")
        if h == "not":
            n, o = g.call(h, {"cls": KML, "fn": "Not_PreBool", "pure": True, "ins": [("A", "bool")], "outs": [("ReturnValue", "bool")]},
                          [self.expr(x[1])], {})
            return Val(o["ReturnValue"], "bool")
        if h == "select":
            return self.select(x[1], x[2], x[3])
        if isinstance(h, Sym) and h.startswith(".") and len(h) > 1:
            v = self.expr(x[1])
            comp = h[1:]
            if comp in ("x", "y", "z"):
                n, o = g.call(h, {"cls": KML, "fn": "BreakVector", "pure": True, "ins": [("InVec", VEC)],
                                  "outs": [("X", "real"), ("Y", "real"), ("Z", "real")]}, [v], {})
                return Val(o[comp.upper()], "real")
            n, o = g.call(h, {"cls": KML, "fn": "BreakRotator", "pure": True, "ins": [("InRot", SG.ROT)],
                              "outs": [("Roll", "real"), ("Pitch", "real"), ("Yaw", "real")]}, [v], {})
            return Val(o[comp.capitalize()], "real")
        return self.head_call(x, as_expr=True)

    def op(self, h, args):
        g = self.g
        vals = [self.expr(a) for a in args]
        if h == "-" and len(vals) == 1:
            vals = [Val.literal(0.0 if (vals[0].t and vals[0].t.cat == "real") else 0), vals[0]]
        kinds = [v.t.kind() if v.t else "int" for v in vals]
        nonlit = [k for k, v in zip(kinds, vals) if not v.is_lit]
        if "vec" in kinds:
            kind = "vec"
        elif "obj" in nonlit:
            kind = "obj"
        elif "real" in kinds:
            kind = "real"
        elif "bool" in nonlit:
            kind = "bool"
        elif "name" in nonlit:
            kind = "name"
        elif "byte" in nonlit:
            kind = "byte"
        else:
            kind = "int"
        fn = SG.OPS[h][kind]
        pt = {"int": "int", "real": "real", "vec": VEC, "obj": "obj:" + C + "Object", "bool": "bool", "name": "name", "byte": "enum:None"}[kind]
        if kind == "byte":
            pt = "int"
        ins = [("A", pt), ("B", pt)]
        if kind == "vec" and h in ("*", "/") and vals[1].t.kind() != "vec":
            fn = "Multiply_VectorFloat" if h == "*" else "Divide_VectorFloat"
            ins = [("A", VEC), ("B", "real")]
        rt = "bool" if h in COMPARE else pt
        n, o = g.call(h, {"cls": KML, "fn": fn, "pure": True, "ins": ins, "outs": [("ReturnValue", rt)]}, vals, {})
        return Val(o["ReturnValue"], rt)

    def select(self, c, a, b):
        g = self.g
        cv, av, bv = self.expr(c), self.expr(a), self.expr(b)
        t = next((v.t for v in (av, bv) if not v.is_lit), None) or av.t
        if t.cat == "int" and any(v.is_lit and isinstance(v.lit, float) for v in (av, bv)):
            t = parse_type("real")
        n = Node(K2 + "K2Node_Select", ["NumOptionPins=2", 'IndexPinType=(PinCategory="bool")'])
        o0 = n.pin("Option 0", "in", t); o1 = n.pin("Option 1", "in", t)
        g.feed(o1, g.coerce(av, t)); g.feed(o0, g.coerce(bv, t))
        g.feed(n.pin("Index", "in", "bool"), cv)
        r = n.pin("ReturnValue", "out", t)
        g.add(n, pure=True)
        v = Val(r, t)
        if av.is_lit and bv.is_lit and t.cat == "string":
            v.flex = (o0, o1, r)          # retyped by Graph.feed to the pin it ends on (a Name socket, for instance)
        return v

    def split_args(self, rest):
        args, kwargs, branches = [], {}, []
        i = 0
        while i < len(rest):
            a = rest[i]
            if isinstance(a, Kw):
                kwargs[str(a)] = rest[i + 1]; i += 2
            elif isinstance(a, list) and a and isinstance(a[0], Kw):
                branches.append(a); i += 1
            else:
                args.append(a); i += 1
        return args, kwargs, branches

    def head_call(self, x, as_expr, bind_names=None):
        """Any (Head ...) form: a call, a getter, a setter, a cast, a macro. Returns a Val (expression) or the node's outputs."""
        g = self.g
        h = str(x[0])
        args, kwargs, branches = self.split_args(x[1:])
        ev = lambda v: self.expr(v)
        parts = h.split("|")
        # ------------------------------------------------ variables
        if parts[0] == "Variables" or (parts[0] == "Class" and parts[1] in CLASS_ALIASES and parts[-1][:3] in ("Get", "Set")
                                       and parts[-1][3:] and not self._is_user_fn(CLASS_ALIASES.get(parts[1]), parts[-1])):
            owner = None
            target = None
            if parts[0] == "Class":
                owner = CLASS_ALIASES[parts[1]]
                target = ev(kwargs.pop("self")) if "self" in kwargs else None
            verb, name = parts[-1][:3], parts[-1][3:]
            if verb == "Get":
                return g.get_var(name, owner, target)
            val = ev(args[0]) if args else ev(list(kwargs.values())[0])
            g.set_var(name, val, owner, target)
            return None
        if parts[0] == "Class" and parts[1] in NATIVE_CLASS_VARS and parts[-1].startswith("Set"):
            parent, props = NATIVE_CLASS_VARS[parts[1]]
            prop, t = props[parts[-1][3:]]
            target = ev(kwargs.pop("self"))
            val = ev(list(kwargs.values())[0] if kwargs else args[0])
            g.set_var(None, val, native=(parent, prop, t), target=target)
            return None
        # ------------------------------------------------ user functions
        if parts[0] == "CallFunction":
            fn = parts[1]
            n, outs = g.call_user(g.bp, fn, [ev(a) for a in args], {k: ev(v) for k, v in kwargs.items()})
            return self._result(outs, bind_names)
        if parts[0] == "Class" and parts[1] in CLASS_ALIASES:
            owner = CLASS_ALIASES[parts[1]]
            n, outs = g.call_user(owner, parts[2], [ev(a) for a in args], {k: ev(v) for k, v in kwargs.items()})
            return self._result(outs, bind_names)
        # ------------------------------------------------ casts
        if h.startswith("Utilities|Casting|CastTo"):
            tgt = CASTS[h[len("Utilities|Casting|CastTo"):]]
            n = Node(K2 + "K2Node_DynamicCast", ['TargetType="%s"' % obj_text(T("class", tgt))])
            n.pin("execute", "in", "exec"); then = n.pin("then", "out", "exec"); fail = n.pin("CastFailed", "out", "exec")
            g.feed(n.pin("Object", "in", "obj:" + C + "Object"), ev(kwargs["Object"]))
            disp = tgt.split(".")[-1]
            disp = disp[:-2] if disp.endswith("_C") else _display(disp)
            out = n.pin("As" + disp, "out", "obj:" + tgt)
            g.add(n)
            g.chain(n, out_name=None)
            val = Val(out, "obj:" + tgt)
            return ("branches", val, {"then": then, "CastFailed": fail}, branches)
        # ------------------------------------------------ macros
        if h == "Utilities|IsValid":
            n = Node(K2 + "K2Node_MacroInstance", [_macro("IsValid")])
            n.pin("exec", "in", "exec")
            g.feed(n.pin("InputObject", "in", "obj:" + C + "Object"), ev(args[0]))
            pins = {"Is Valid": n.pin("Is Valid", "out", "exec"), "Is Not Valid": n.pin("Is Not Valid", "out", "exec")}
            g.add(n)
            g.chain(n, in_name="exec", out_name=None)
            return ("branches", None, pins, branches)
        # ------------------------------------------------ special nodes
        if h == "Utilities|Array|Get(acopy)":
            arr, idx = ev(args[0]), ev(args[1])
            n = Node(K2 + "K2Node_GetArrayItem")
            at = arr.t
            g.feed(n.pin("Array", "in", T(at.cat, at.obj, True, False, at.sub)), arr)
            g.feed(n.pin("Dimension 1", "in", "int"), idx)
            out = n.pin("Output", "out", T(at.cat, at.obj, False, False, at.sub))
            g.add(n, pure=True)
            return Val(out, at.elem())
        if h == "Game|SpawnActorfromClass":
            n = Node(K2 + "K2Node_SpawnActorFromClass")
            n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
            cv = ev(kwargs["Class"])
            g.feed(n.pin("Class", "in", "cls:" + E + "Actor"), cv)
            g.feed(n.pin("SpawnTransform", "in", XF), ev(kwargs["SpawnTransform"]))
            g.feed(n.pin("CollisionHandlingOverride", "in", "enum:" + E + "ESpawnActorCollisionHandlingMethod"),
                   ev(kwargs.get("CollisionHandlingOverride", Str("Undefined"))))
            rt = "obj:" + (cv.t.obj if cv.t and cv.t.cat == "class" and cv.t.obj else E + "Actor")
            out = n.pin("ReturnValue", "out", rt)
            g.add(n); g.chain(n)
            return Val(out, rt) if as_expr or bind_names else None
        if h == "UserInterface|CreateWidget":
            cls = str(kwargs["Class"])
            n = Node("/Script/UMGEditor.K2Node_CreateWidget")
            n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
            g.feed(n.pin("Class", "in", "cls:" + U + "UserWidget"), Val(t="cls:" + U + "UserWidget", lit=cls, is_lit=True))
            g.feed(n.pin("OwningPlayer", "in", "obj:" + E + "PlayerController"), ev(kwargs["OwningPlayer"]))
            out = n.pin("ReturnValue", "out", "obj:" + cls)
            g.add(n); g.chain(n)
            return Val(out, "obj:" + cls)
        if h == "Game|AddComponentbyClass":
            cls = str(kwargs["Class"])
            n = Node(K2 + "K2Node_AddComponentByClass")
            n.pin("execute", "in", "exec"); n.pin("then", "out", "exec")
            g.feed(n.pin("Class", "in", "cls:" + E + "ActorComponent"), Val(t="cls:x", lit=cls, is_lit=True))
            out = n.pin("ReturnValue", "out", "obj:" + cls)
            g.add(n); g.chain(n)
            return Val(out, "obj:" + cls)
        if h == "Rendering|Material|SetColorParameterValueonMaterials":     # 5.4: the vector version (ue54_sigs)
            col = ev(kwargs.pop("ParameterValue"))
            _, o = g.call("conv", SG.SIGS["Math|Conversions|LinearColorToVector"], [col], {})
            kw = {k: ev(v) for k, v in kwargs.items()}
            kw["ParameterValue"] = Val(o["ReturnValue"], VEC)
            g.call(h, SG.SIGS["Rendering|Material|SetVectorParameterValueonMaterials"], [], kw)
            return None
        if h in SG.ARRAY:
            fn, pure, ins, outs = SG.ARRAY[h]
            sig = {"cls": SG.KAL, "fn": fn, "pure": pure, "ins": ins, "outs": outs, "array": True}
            vals = {k: ev(v) for k, v in kwargs.items()}
            n, o = g.call(h, sig, [ev(a) for a in args], vals)
            if "TargetArray" in vals and "NewItem" in vals and vals["TargetArray"].t is not None:
                pass
            return self._result(o, bind_names)
        if h in SG.SIGS and SG.SIGS[h]["kind"] == "make":
            s = SG.SIGS[h]
            n = Node(K2 + "K2Node_MakeStruct", ['StructType="%s"' % obj_text(T("struct", s["struct"]))])
            for spec in s["ins"]:
                p = n.pin(spec[0], "in", spec[1], default=spec[2] if len(spec) > 2 else None)
                if spec[0] in kwargs:
                    g.feed(p, g.coerce(ev(kwargs[spec[0]]), p.t))
            out = n.pin(s["out"], "out", "struct:" + s["struct"])
            g.add(n, pure=True)
            return Val(out, "struct:" + s["struct"])
        if h in SG.SIGS:
            sig = SG.SIGS[h]
            n, o = g.call(h, sig, [ev(a) for a in args], {k: (ev(v) if k != "self" else ev(v)) for k, v in kwargs.items()})
            return self._result(o, bind_names)
        raise CompileError("unknown head %s" % h)

    def _is_user_fn(self, bp, name):
        return bp is not None and name in FUNCS.get(bp, {})

    def _result(self, outs, bind_names):
        if bind_names and len(bind_names) > 1:
            return [Val(outs[k], outs[k].t) for k in outs]
        if not outs:
            return None
        if "ReturnValue" in outs:
            p = outs["ReturnValue"]
        else:
            p = list(outs.values())[-1]
        return Val(p, p.t)

    # ------------------------------------------------ statements
    def block(self, stmts):
        g = self.g
        for i, s in enumerate(stmts):
            if g.cur is None:
                raise CompileError("flow ended before %r in %s.%s" % (s[:2], g.bp, g.fn))
            rest = stmts[i + 1:]
            if rest and isinstance(s, list) and s and s[0] in ("if",):
                # Blueprint has no join: run the branch, then the rest, from a Sequence
                n = Node(K2 + "K2Node_ExecutionSequence")
                n.pin("execute", "in", "exec"); t0 = n.pin("then_0", "out", "exec"); t1 = n.pin("then_1", "out", "exec")
                g.add(n); g.chain(n, out_name=None)
                g.cur = t0
                self.stmt(s)
                g.cur = t1
                continue
            self.stmt(s)

    def stmt(self, s):
        g = self.g
        h = s[0]
        if h == "bind":
            names = s[1] if isinstance(s[1], list) else [s[1]]
            ex = s[2]
            branches = s[3:]
            r = self.head_call(ex, as_expr=True, bind_names=names) if isinstance(ex, list) and isinstance(ex[0], Sym) and "|" in ex[0] \
                else self.expr(ex)
            if isinstance(r, tuple) and r and r[0] == "branches":
                _, val, pins, br = r
                g.env[str(names[0])] = val
                self.branches(pins, list(branches) + br)
                return
            if isinstance(r, list):
                for n, v in zip(names, r):
                    g.env[str(n)] = v
            else:
                g.env[str(names[0])] = r
            return
        if h == "if":
            cond = self.expr(s[1])
            body = [x for x in s[2:] if not (isinstance(x, list) and x and x[0] == "else")]
            els = [x for x in s[2:] if isinstance(x, list) and x and x[0] == "else"]
            n = Node(K2 + "K2Node_IfThenElse")
            n.pin("execute", "in", "exec"); then = n.pin("then", "out", "exec"); else_ = n.pin("else", "out", "exec")
            g.feed(n.pin("Condition", "in", "bool"), cond)
            g.add(n); g.chain(n, out_name=None)
            lane = g.lane
            g.cur = then
            self.block(body)
            if els:
                g.lane = lane + 1
                g.cur = else_
                self.block(els[0][1:])
            g.lane = lane
            g.cur = None
            return
        if h == "for":
            var, coll = str(s[1]), s[2]
            if isinstance(coll, list) and coll and coll[0] == "range":
                n = Node(K2 + "K2Node_MacroInstance", [_macro("ForLoop")])
                n.pin("execute", "in", "exec")
                g.feed(n.pin("FirstIndex", "in", "int"), Val.literal(0))
                last = self.op("-", [coll[1], 1])
                g.feed(n.pin("LastIndex", "in", "int"), last)
                body, elem, done = n.pin("LoopBody", "out", "exec"), n.pin("Index", "out", "int"), n.pin("Completed", "out", "exec")
                et = parse_type("int")
                g.add(n); g.chain(n, out_name=None)
            else:
                arr = self.expr(coll)
                et0 = arr.t.elem()
                n = Node(K2 + "K2Node_MacroInstance", [_macro("ForEachLoop"), "ResolvedWildcardType=" + pintype_struct(et0)])
                n.pin("Exec", "in", "exec")
                g.feed(n.pin("Array", "in", T(arr.t.cat, arr.t.obj, True, False, arr.t.sub)), arr)
                body = n.pin("LoopBody", "out", "exec")
                et = arr.t.elem()
                elem = n.pin("Array Element", "out", et)
                n.pin("Array Index", "out", "int")
                done = n.pin("Completed", "out", "exec")
                g.add(n); g.chain(n, in_name="Exec", out_name=None)
            saved = g.env.get(var)
            g.env[var] = Val(elem, et)
            g.cur = body
            self.block(s[3:])
            g.env.pop(var, None)
            if saved is not None:
                g.env[var] = saved
            g.cur = done
            return
        if h == "switch":
            sel = self.expr(s[2])
            n = Node(K2 + "K2Node_SwitchInteger")
            n.pin("execute", "in", "exec")
            g.feed(n.pin("Selection", "in", "int"), sel)
            cases = []
            for c in s[3:]:
                cases.append((int(str(c[0])), c[1:]))
            pins = {k: n.pin(str(k), "out", "exec") for k, _ in cases}
            n.pin("Default", "out", "exec")
            g.add(n); g.chain(n, out_name=None)
            lane = g.lane
            for i, (k, body) in enumerate(cases):
                g.lane = lane + i
                g.cur = pins[k]
                self.block(body)
            g.lane = lane
            g.cur = None
            return
        if h == "return":
            _, outs = FUNCS[g.bp][g.fn]
            n = Node(K2 + "K2Node_FunctionResult", ['FunctionReference=(MemberName="%s")' % g.fn, "bIsEditable=True"])
            for name, t in outs:
                n.extra.append('CustomProperties UserDefinedPin (PinName="%s",PinType=%s,DesiredPinDirection=EGPD_Input)'
                               % (name, pintype_struct(parse_type(t))))
            n.pin("execute", "in", "exec")
            if len(s) > 1:
                name, t = outs[0]
                g.feed(n.pin(name, "in", t), g.coerce(self.expr(s[1]), parse_type(t)))
            else:
                for name, t in outs:
                    n.pin(name, "in", t)
            g.add(n); g.chain(n, out_name=None)
            return
        if h == "while":
            raise CompileError("while is not used by the shipped graphs")
        # a call or a setter as a statement
        r = self.head_call(s, as_expr=False)
        if isinstance(r, tuple) and r and r[0] == "branches":
            _, val, pins, br = r
            self.branches(pins, br)

    def branches(self, pins, br):
        g = self.g
        lane = g.lane
        for i, b in enumerate(br):
            label = str(b[0])
            if label not in pins:
                raise CompileError("no branch %s (%s)" % (label, list(pins)))
            g.lane = lane + i
            g.cur = pins[label]
            self.block(b[1:])
        g.lane = lane
        g.cur = None


def _display(name):
    """FName::NameToDisplayString for a native class name (PoseableMeshComponent -> Poseable Mesh Component)."""
    out = ""
    for i, ch in enumerate(name):
        if i and ch.isupper() and not name[i - 1].isupper():
            out += " "
        out += ch
    return out


def _macro(name):
    return ("MacroGraphReference=(MacroGraph=\"/Script/Engine.EdGraph'%s:%s'\",GraphBlueprint=\"/Script/Engine.Blueprint'%s'\")"
            % (MACROS, name, MACROS))


# ------------------------------------------------------------------------------------------ graphs -> text

EVENT_BOUND = {}   # (bp, event) -> (component, delegate owner, delegate)   widget bound events


def compile_event_graph(bp, code):
    g = Graph(bp, "EventGraph")
    comp = Compiler(g)
    for ei, form in enumerate(parse(code)):
        g.col, g.lane = 0, 4 * ei            # each event on its own band of rows
        if form[0] != "event":
            raise CompileError("event graph form %r" % form[:2])
        name = str(form[1])
        # a parameter list is bare names; (CallFunction|X) is a first statement with no arguments, not a parameter
        params = form[2] if (len(form) > 2 and isinstance(form[2], list) and all(isinstance(p, Sym) and "|" not in p for p in form[2])) else []
        body = form[3:] if params or (len(form) > 2 and form[2] == []) else form[2:]
        owner, fn, outs = SG.EVENTS[name]
        n = Node(K2 + "K2Node_Event", ['EventReference=(MemberParent="%s",MemberName="%s")' % (obj_text(T("class", owner)), fn),
                                        "bOverrideFunction=True"])
        then = n.pin("then", "out", "exec")
        g.env = {}
        for (pn, pt), sym in zip(outs, params):
            g.env[str(sym)] = Val(n.pin(pn, "out", pt), pt)
        g.add(n)
        g.cur = then
        comp.block(body)
    return g


def compile_function(bp, name, code):
    g = Graph(bp, name)
    ins, outs = FUNCS[bp][name]
    form = parse(code)[0]
    assert form[0] == "fn" and str(form[1]) == name, form[:2]
    params = form[2]
    body = form[3:]
    e = Node(K2 + "K2Node_FunctionEntry", ['FunctionReference=(MemberName="%s")' % name, "bIsEditable=True"])
    for pn, pt in ins:
        e.extra.append('CustomProperties UserDefinedPin (PinName="%s",PinType=%s,DesiredPinDirection=EGPD_Output)'
                       % (pn, pintype_struct(parse_type(pt))))
    then = e.pin("then", "out", "exec")
    for (pn, pt) in ins:
        g.env[pn] = Val(e.pin(pn, "out", pt), pt)
    g.add(e)
    g.cur = then
    Compiler(g).block(body)
    if g.cur is not None and outs:
        # the flow fell off the end of a function that has outputs: close it with a result (defaults)
        r = Node(K2 + "K2Node_FunctionResult", ['FunctionReference=(MemberName="%s")' % name, "bIsEditable=True"])
        for pn, pt in outs:
            r.extra.append('CustomProperties UserDefinedPin (PinName="%s",PinType=%s,DesiredPinDirection=EGPD_Input)' % (pn, pintype_struct(parse_type(pt))))
        r.pin("execute", "in", "exec")
        for pn, pt in outs:
            r.pin(pn, "in", pt)
        g.add(r); g.chain(r, out_name=None)
    return g


GRID = 330


def layout(g):
    """Pure nodes to the left of (and below) the first node they feed, on a 330-unit column grid shared with the exec
    nodes (every 660); a column never stacks two nodes on top of each other."""
    occupied = {}
    placed = set()

    def height(n):
        return 70 + 26 * len([p for p in n.pins if not p.hidden and p.t.cat != "exec"]) + (24 if any(p.t.cat == "exec" for p in n.pins) else 0)

    def claim(n, col, y):
        y = max(y, occupied.get(col, -10 ** 9) + 40)
        n.x, n.y = col * GRID, int(y)
        occupied[col] = n.y + height(n)

    def feeders(n):
        for p in n.pins:
            if p.dir == "in":
                for src in p.links:
                    m = src.node
                    if getattr(m, "pure", False) and m.name not in placed:
                        yield m

    def place(n, col, y):
        placed.add(n.name)
        claim(n, col, y)
        cy = n.y
        for m in list(feeders(n)):
            place(m, col - 1, cy)
            cy = m.y + height(m) + 20

    execs = sorted([n for n in g.nodes if not getattr(n, "pure", False)], key=lambda n: (n.y, n.x))
    for n in execs:
        claim(n, round(n.x / GRID), n.y)
    for n in execs:
        cy = n.y + height(n) + 40
        for m in list(feeders(n)):
            place(m, round(n.x / GRID) - 1, cy)
            cy = m.y + height(m) + 20
    for n in g.nodes:
        if getattr(n, "pure", False) and n.name not in placed:
            place(n, 0, 0)


def nodes_text(g):
    layout(g)
    return "\n".join(n.text() for n in g.nodes) + "\n"


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def function_paste(bp, name, code):
    g = compile_function(bp, name, code)
    return 'BPGraph(GraphName="%s",GraphType=GT_Function,NodesString="%s")' % (name, esc(nodes_text(g)))


def variable_paste(name, t, editable, default):
    t = parse_type(t)
    flags = 5 if editable else 65541          # CPF_Edit | CPF_BlueprintVisible (| CPF_DisableEditOnInstance)
    friendly = "".join((" " + ch if i and ch.isupper() and not name[i - 1].isupper() else ch) for i, ch in enumerate(name))
    s = 'BPVar(VarName="%s",VarGuid=%s,VarType=%s,FriendlyName="%s",Category=NSLOCTEXT("", "", "Default"),PropertyFlags=%d' % (
        name, guid(), pintype_struct(t), friendly, flags)
    if default is not None:
        s += ',DefaultValue="%s"' % default.replace('"', '\\"')
    return s + ")"


def build_all(outdir):
    global FUNCS
    FUNCS = function_table()
    os.makedirs(outdir, exist_ok=True)
    plan = []
    srcs = sources() + notify_sources()
    by_bp = {}
    for bp, name, params, code in srcs:
        by_bp.setdefault(bp, []).append((name, params, code))
    for bp, items in by_bp.items():
        short = bp.split("/")[-1]
        for i, (n, t, ed, d) in enumerate(VARS.get(bp, [])):
            f = os.path.join(outdir, "%s__var_%02d_%s.txt" % (short, i, n))
            open(f, "w", newline="").write(variable_paste(n, t, ed, d))
            plan.append((bp, "var", n, f))
        fns = {name: code for name, params, code in items if params is not None}
        order = []
        def visit(n, stack=()):
            if n in order or n not in fns:
                return
            if n in stack:
                raise CompileError("recursive functions %s" % (stack + (n,),))
            for dep in fns:
                if dep != n and ("CallFunction|%s " % dep in fns[n] or "CallFunction|%s)" % dep in fns[n]):
                    visit(dep, stack + (n,))
            order.append(n)
        for n in fns:
            visit(n)
        for name in order:
            code = fns[name]
            f = os.path.join(outdir, "%s__fn_%s.txt" % (short, name))
            open(f, "w", newline="").write(function_paste(bp, name, code))
            plan.append((bp, "fn", name, f))
        for name, params, code in items:
            if params is None:
                g = compile_event_graph(bp, code)
                f = os.path.join(outdir, "%s__events.txt" % short)
                open(f, "w", newline="").write(nodes_text(g))
                plan.append((bp, "events", name, f))
    json.dump(plan, open(os.path.join(outdir, "plan.json"), "w"), indent=1)
    return plan


if __name__ == "__main__":
    plan = build_all(sys.argv[1])
    from collections import Counter
    print(Counter((p[0].split("/")[-1], p[1]) for p in plan))


# ------------------------------------------------------------------------------------------ ABP_UndeadSkeleton's AnimGraph

AG = "/Script/AnimGraph."
POSE = "struct:/Script/Engine.PoseLink"


def anim_graph():
    """build_abp.anim_graph() as paste text (the same nodes, slots, caches and layers; the 5.8 build places them through the
    MCP). Everything but the Output Pose: the last layered blend's Pose is wired to it by hand (ue54_build: a drag)."""
    from ue_common import EPIC_FINGERS
    nodes = []

    def mk(cls, props=(), x=0, y=0):
        n = Node(AG + cls, list(props), x, y)
        nodes.append(n)
        return n

    def get(var, x, y):
        t = dict((n, t) for n, t, _, _ in VARS[ABP])[var]
        n = Node(K2 + "K2Node_VariableGet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % var], x, y)
        nodes.append(n)
        return n.pin(var, "out", t)

    def seq(clip):
        return '"/Script/Engine.AnimSequence\'%s/Animations/A_%s.A_%s\'"' % (PKG, clip, clip)

    def player(clip, x, y, show_seq=False):
        props = ['Node=(Sequence=%s)' % seq(clip)]
        if show_seq:
            props.append('ShowPinForProperties(6)=(PropertyName="Sequence",bShowPin=True)')
        n = mk("AnimGraphNode_SequencePlayer", props, x, y)
        if show_seq:
            n.pin("Sequence", "in", SEQ)
        n.pin("Pose", "out", POSE)
        return n

    def slot(name, src, x, y):
        n = mk("AnimGraphNode_Slot", ['Node=(SlotName="%s")' % name], x, y)
        link(src.get("Pose", "out"), n.pin("Source", "in", POSE))
        n.pin("Pose", "out", POSE)
        return n

    def save(name, src, x, y):
        n = mk("AnimGraphNode_SaveCachedPose", ['CacheName="%s"' % name], x, y)
        link(src.get("Pose", "out"), n.pin("Pose", "in", POSE))
        return n

    def use(name, x, y):
        n = mk("AnimGraphNode_UseCachedPose", ['NameOfCache="%s"' % name], x, y)
        n.pin("Pose", "out", POSE)
        return n

    def layered(base, blends, filters, x, y, weights=None):
        setup = ",".join("(BranchFilters=(%s))" % ",".join('(BoneName="%s")' % b for b in f) for f in filters)
        n = mk("AnimGraphNode_LayeredBoneBlend", ["Node=(LayerSetup=(%s))" % setup], x, y)
        link(base.get("Pose", "out"), n.pin("BasePose", "in", POSE))
        for i, b in enumerate(blends):
            link(b.get("Pose", "out"), n.pin("BlendPoses_%d" % i, "in", POSE))
            w = n.pin("BlendWeights_%d" % i, "in", "real", default="1.000000")
            if weights and weights[i]:
                link(get(weights[i], x - 250, y + 180 + 60 * i), w)
        n.pin("Pose", "out", POSE)
        return n

    def two_way(a, b, alpha_var, x, y):
        n = mk("AnimGraphNode_TwoWayBlend", [], x, y)
        link(a.get("Pose", "out"), n.pin("A", "in", POSE))
        link(b.get("Pose", "out"), n.pin("B", "in", POSE))
        link(get(alpha_var, x - 250, y + 160), n.pin("Alpha", "in", "real"))
        n.pin("Pose", "out", POSE)
        return n

    def additive(base, add, alpha_var, x, y):
        n = mk("AnimGraphNode_ApplyAdditive", [], x, y)
        link(base.get("Pose", "out"), n.pin("Base", "in", POSE))
        link(add.get("Pose", "out"), n.pin("Additive", "in", POSE))
        a = n.pin("Alpha", "in", "real", default="1.000000")
        if alpha_var:
            link(get(alpha_var, x - 250, y + 250), a)
        n.pin("Pose", "out", POSE)
        return n

    X = -4200
    a = player("Idle_01", X, -300, show_seq=True)
    b = player("Idle_01", X, 0, show_seq=True)
    link(get("BaseA", X - 250, -250), a.get("Sequence", "in"))
    link(get("BaseB", X - 250, 50), b.get("Sequence", "in"))
    sel = mk("AnimGraphNode_BlendListByBool", ["Node=(bResetChildOnActivation=True)"], X + 400, -150)
    link(get("UseB", X + 150, -250), sel.pin("bActiveValue", "in", "bool"))
    link(b.get("Pose", "out"), sel.pin("BlendPose_0", "in", POSE))      # BlendListByBool: index 0 = the TRUE pose
    link(a.get("Pose", "out"), sel.pin("BlendPose_1", "in", POSE))
    sel.pin("BlendTime_0", "in", "real", default="0.200000")
    sel.pin("BlendTime_1", "in", "real", default="0.200000")
    sel.pin("Pose", "out", POSE)
    sb = slot("Base", sel, X + 600, -150)
    s0 = slot("DefaultSlot", sb, X + 850, -150)
    save("Base", s0, X + 1100, -150)

    X = -2900
    up = layered(use("Base", X, -150), [slot("UpperBody", use("Base", X, 50), X + 250, 50)], [["spine_04"]], X + 550, -150)
    save("Upper", up, X + 850, -150)

    X = -2200
    blk = two_way(use("Upper", X, 100), player("Block_L_Idle", X, 250), "BlockAlpha", X + 250, 150)
    la = layered(use("Upper", X, -150), [slot("LeftArm", blk, X + 500, 150)], [["clavicle_l"]], X + 800, -150)
    save("Arms", la, X + 1100, -150)

    X = -1300
    prev = layered(use("Arms", X, -150), [slot("RightArm", use("Arms", X, 50), X + 250, 50)], [["clavicle_r"]], X + 550, -150)
    X = -600
    for i in (1, 2, 3):
        prev = additive(prev, player("Twitch_%02d" % i, X + 300 * i - 250, 100), "Twitch%d" % i, X + 300 * i, -150)
    ident = mk("AnimGraphNode_IdentityPose", [], 0, 300)
    ident.pin("Pose", "out", POSE)
    hit = additive(prev, slot("Hit", ident, 200, 300), None, 400, -150)
    save("Body", hit, 700, -150)

    X = 800
    hands = []
    for k, lr in enumerate(("L", "R")):
        y = 150 + 400 * k
        ev = mk("AnimGraphNode_SequenceEvaluator", ['Node=(Sequence=%s)' % seq("Grip")], X, y + 150)
        ev.pin("ExplicitTime", "in", "real", default="0.000000")
        ev.pin("Pose", "out", POSE)
        hands.append(two_way(player("Hand_Idle_" + lr, X, y), ev, "Grip" + lr, X + 300, y))
    fin = layered(use("Body", X + 300, -150), [hands[0]], [EPIC_FINGERS["Left"]], X + 700, -150, weights=["FingerL"])
    fin = layered(fin, [hands[1]], [EPIC_FINGERS["Right"]], X + 1000, -150, weights=["FingerR"])
    return nodes, fin


def override_body(bp, name, code):
    """An override's body (no entry node): the parameters are read through local getter nodes (the function's own
    'Get <param>'), so only the entry's exec needs wiring by hand; the result nodes are part of the body. Returns (text,
    the first exec node's name)."""
    global FUNCS
    if FUNCS is None:
        FUNCS = function_table()
    g = Graph(bp, name)
    ins, outs = FUNCS[bp][name]
    form = parse(code)[0]
    start = Node(K2 + "K2Node_Knot")          # a reroute stands in for the entry's exec (wired to the real entry by hand)
    g.add(start)
    i = start.pin("InputPin", "in", "exec")
    o = start.pin("OutputPin", "out", "exec")
    g.cur = o
    for pn, pt in ins:
        n = Node(K2 + "K2Node_VariableGet", ['VariableReference=(MemberName="%s",MemberScope="%s")' % (pn, name)])
        out = n.pin(pn, "out", pt)
        g.add(n, pure=True)
        g.env[pn] = Val(out, pt)
    Compiler(g).block(form[3:])
    return nodes_text(g), start.name
