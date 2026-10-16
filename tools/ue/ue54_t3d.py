"""Blueprint graphs as copy-paste text (T3D) for UE 5.4, which has no MCP graph toolset (2026-10-16).

The 5.8 build writes its graphs through the MCP's DSL (tools/ue/build_*.py); this compiles the SAME DSL text
(tools/ue/ue54_dsl.py) into what the 5.4 Blueprint editor pastes:
  * a member variable  -> "BPVar(...)"   (FBPVariableDescription; pasted in the My Blueprint panel)
  * a function graph    -> "BPGraph(...)" (FBPGraphClipboardData: entry + body + results; pasted in My Blueprint)
  * an event graph      -> plain node text (pasted into the graph panel)
Pins carry names, directions, types, defaults and links; the editor rebuilds each node's pins from its function on load
(UBlueprint regenerate-on-load reconstructs every node, matching pins by name), so a reload after the paste settles
wildcards and hidden pins. Engine signatures: tools/ue/ue54_sigs.py.
"""
import os, sys, uuid, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue54_dsl import parse, Sym, Kw, Str
import ue54_sigs as SG

E, U, C = SG.E, SG.U, SG.C


# ------------------------------------------------------------------------------------------ types

class T:
    """A pin type: cat in {exec bool int real name str text object class struct byte wildcard}, obj = path, arr, ref."""
    def __init__(self, cat, obj=None, arr=False, ref=False, sub=""):
        self.cat, self.obj, self.arr, self.ref, self.sub = cat, obj, arr, ref, sub

    def elem(self):
        return T(self.cat, self.obj, False, False, self.sub)

    def kind(self):           # the operator family
        if self.cat in ("object", "class"):
            return "obj"
        if self.cat == "struct" and self.obj == C + "Vector":
            return "vec"
        return {"real": "real", "int": "int", "bool": "bool", "name": "name", "byte": "byte", "string": "str"}.get(self.cat, self.cat)

    def __repr__(self):
        return "T(%s %s%s)" % (self.cat, self.obj or "", "[]" if self.arr else "")


def parse_type(s):
    if isinstance(s, T):
        return s
    ref = s.endswith("&"); s = s.rstrip("&")
    arr = s.endswith("[]"); s = s[:-2] if arr else s
    if ":" in s:
        k, p = s.split(":", 1)
        cat = {"obj": "object", "cls": "class", "struct": "struct", "enum": "byte"}[k]
        return T(cat, p, arr, ref)
    cat = {"bool": "bool", "int": "int", "real": "real", "float": "real", "name": "name", "str": "string", "string": "string",
           "text": "text", "wild": "wildcard", "exec": "exec"}[s]
    return T(cat, None, arr, ref, "double" if cat == "real" else "")


def class_ref(path):
    """An object path as T3D text with its class: native classes, structs, enums, Blueprint classes."""
    if path.startswith("/Script/"):
        return path      # resolved by the caller with the right outer kind
    return path


def obj_text(t):
    p = t.obj
    if p is None:
        return "None"
    if t.cat == "struct":
        return "/Script/CoreUObject.ScriptStruct'%s'" % p
    if t.cat == "byte":
        return "/Script/CoreUObject.Enum'%s'" % p
    if p.startswith("/Script/"):
        return "/Script/CoreUObject.Class'%s'" % p
    return "%s'%s'" % (bp_class_kind(p), p)


def bp_class_kind(path):
    """The UClass of a Blueprint's generated class, by asset name convention."""
    name = path.split("/")[-1]
    if name.startswith("WBP_"):
        return "/Script/UMG.WidgetBlueprintGeneratedClass"
    if name.startswith("ABP_"):
        return "/Script/Engine.AnimBlueprintGeneratedClass"
    return "/Script/Engine.BlueprintGeneratedClass"


def pintype_fields(t, prefix="PinType."):
    f = [("PinCategory", '"%s"' % t.cat), ("PinSubCategory", '"%s"' % t.sub), ("PinSubCategoryObject", '"%s"' % obj_text(t) if t.obj else "None"),
         ("PinSubCategoryMemberReference", "()"), ("PinValueType", "()"), ("ContainerType", "Array" if t.arr else "None"),
         ("bIsReference", "True" if t.ref else "False"), ("bIsConst", "False"), ("bIsWeakPointer", "False"), ("bIsUObjectWrapper", "False"),
         ("bSerializeAsSinglePrecisionFloat", "False")]
    return ",".join("%s%s=%s" % (prefix, k, v) for k, v in f)


def pintype_struct(t):
    """The (Field=..) form used by FUserPinInfo / FBPVariableDescription."""
    parts = ['PinCategory="%s"' % t.cat]
    if t.sub:
        parts.append('PinSubCategory="%s"' % t.sub)
    if t.obj:
        parts.append('PinSubCategoryObject="%s"' % obj_text(t))
    if t.arr:
        parts.append("ContainerType=Array")
    return "(" + ",".join(parts) + ")"


def guid():
    return uuid.uuid4().hex.upper()


# ------------------------------------------------------------------------------------------ nodes

class Pin:
    def __init__(self, node, name, direction, t, default=None, hidden=False, default_object=None):
        self.node, self.name, self.dir, self.t = node, name, direction, parse_type(t)
        self.id = guid()
        self.default, self.default_object, self.hidden = default, default_object, hidden
        self.links = []

    def text(self):
        f = ["PinId=%s" % self.id, 'PinName="%s"' % self.name]
        if self.dir == "out":
            f.append('Direction="EGPD_Output"')
        f.append(pintype_fields(self.t))
        if self.default is not None:
            f.append('DefaultValue="%s"' % str(self.default).replace('"', '\\"'))
            # an explicit value must survive the paste's node reconstruction, which keeps an input's DefaultValue only when it
            # differs from AutogeneratedDefaultValue: with that field absent (empty), a bool "false" counted as autogenerated and
            # was reset to the function's own default (Montage_Play bStopAllMontages came back TRUE and every loop montage
            # stopped the one-shots, 2026-10-16)
            f.append('AutogeneratedDefaultValue="%s"' % ("__ue54__" if self.dir == "in" else ""))
        if self.default_object is not None:
            f.append('DefaultObject="%s"' % self.default_object)
        if self.links:
            f.append("LinkedTo=(%s)" % "".join("%s %s," % (p.node.name, p.id) for p in self.links))
        f.append("PersistentGuid=00000000000000000000000000000000")
        f.append("bHidden=%s" % ("True" if self.hidden else "False"))
        f += ["bNotConnectable=False", "bDefaultValueIsReadOnly=False", "bDefaultValueIsIgnored=False", "bAdvancedView=False", "bOrphanedPin=False"]
        return "CustomProperties Pin (" + ",".join(f) + ",)"


_count = itertools.count()


class Node:
    def __init__(self, cls, props=(), x=0, y=0):
        self.cls = cls
        self.name = "%s_%d" % (cls.split(".")[-1], next(_count))
        self.props = list(props)
        self.pins = []
        self.x, self.y = x, y
        self.extra = []             # extra CustomProperties lines (UserDefinedPin)

    def pin(self, name, direction, t, **kw):
        p = Pin(self, name, direction, t, **kw)
        self.pins.append(p)
        return p

    def get(self, name, direction=None):
        for p in self.pins:
            if p.name == name and (direction is None or p.dir == direction):
                return p
        raise KeyError("%s has no pin %s (%s)" % (self.name, name, [q.name for q in self.pins]))

    def text(self):
        lines = ['Begin Object Class=%s Name="%s"' % (self.cls, self.name)]
        lines += ["   " + p for p in self.props]
        lines += ["   NodePosX=%d" % self.x, "   NodePosY=%d" % self.y, "   NodeGuid=%s" % guid()]
        lines += ["   " + e for e in self.extra]
        lines += ["   " + p.text() for p in self.pins]
        lines.append("End Object")
        return "\n".join(lines)


def link(out_pin, in_pin):
    if out_pin.dir != "out" or in_pin.dir != "in":
        raise ValueError("link %s.%s -> %s.%s" % (out_pin.node.name, out_pin.name, in_pin.node.name, in_pin.name))
    out_pin.links.append(in_pin)
    in_pin.links.append(out_pin)


def member_ref(parent, name, self_ctx=False):
    if self_ctx:
        return '(MemberName="%s",bSelfContext=True)' % name
    return '(MemberParent=%s,MemberName="%s")' % (obj_text(T("class", parent)), name)


K2 = "/Script/BlueprintGraph."
MACROS = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros"
MACRO_GUIDS = {}   # filled from the engine's StandardMacros on demand (optional: the graph resolves by path)
