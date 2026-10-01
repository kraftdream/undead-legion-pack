"""Build the demo browser widgets through the Unreal MCP UMG + Blueprint toolsets (system Python, editor running).

    python tools/ue/build_demo_ui.py [trees] [graphs]

The Unity demo (SkeletonShowcase + DemoUI + the scene builder's canvas), re-cut for UMG:
  WBP_DemoButton   a Button + Label; Setup(Browser, Kind, Index, Caption), SetSelected; a click calls
                   Browser.OnButton(Kind, Index)
  WBP_DemoHeader   a section title
  WBP_AnimBrowser  left: title, CHARACTERS, ARMOUR MODULES (own set as toggles, All / None, then every other
                   character's set to borrow), WEAPONS; right: the animation sections; bottom: Root motion /
                   Turntable / Recenter and the clip line. Its logic graphs are written by build_demo_logic.py.
Everything below is regenerated; tune by editing this script, not the assets.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import umg, obj, bp

F = "/Game/UndeadLegion/Demo/UI"
NORMAL = {"r": 0.22, "g": 0.23, "b": 0.26, "a": 1.0}
PANEL = {"r": 0.02, "g": 0.02, "b": 0.025, "a": 0.72}


def W(name):
    return {"refPath": "%s/%s.%s" % (F, name, name)}


def create(name):
    try:
        umg("CreateWidgetBlueprint", folderPath=F, assetName=name, parentClass={"refPath": "/Script/UMG.UserWidget"})
    except RuntimeError as e:
        if "exist" not in str(e).lower():
            raise
    for w in (umg("GetWidgets", widgetBlueprint=W(name)) or {}).get("widgets", [])[:1]:
        umg("RemoveWidget", widgetBlueprint=W(name), widget=w["widget"])   # rebuild the tree from scratch


def add(bpname, cls, name, parent=None, var=False):
    r = umg("AddWidget", widgetBlueprint=W(bpname), widgetClass={"refPath": "/Script/UMG." + cls}, widgetDisplayName=name,
            parentWidget=parent, childIndex=-1)
    if var:
        umg("ToggleWidgetAsVariable", widgetBlueprint=W(bpname), widget=r["widget"], bIsVariable=True)
    return r


def props(ref, **values):
    obj("set_properties", instance=ref if isinstance(ref, dict) else {"refPath": ref}, values=json.dumps(values))


def text(ref, caption, size, bold=True, color=None):
    font = json.loads(obj("get_properties", instance=ref, properties=["Font"]))["Font"]
    font["size"] = size
    font["typefaceFontName"] = "Bold" if bold else "Regular"
    v = {"Text": caption, "Font": font}
    if color:
        v["ColorAndOpacity"] = {"specifiedColor": color, "colorUseRule": "UseColor_Specified"}
    obj("set_properties", instance=ref, values=json.dumps(v))


def canvas_slot(slot, amin, amax, offsets, alignment=(0, 0)):
    props(slot, LayoutData={"offsets": dict(zip(("left", "top", "right", "bottom"), offsets)),
                            "anchors": {"minimum": {"x": amin[0], "y": amin[1]}, "maximum": {"x": amax[0], "y": amax[1]}},
                            "alignment": {"x": alignment[0], "y": alignment[1]}})


def button_tree():
    create("WBP_DemoButton")
    b = add("WBP_DemoButton", "Button", "Btn", var=True)
    props(b["widget"], BackgroundColor=NORMAL)
    t = add("WBP_DemoButton", "TextBlock", "Label", b["widget"], var=True)
    text(t["widget"], "Button", 10, bold=False, color={"r": 0.92, "g": 0.92, "b": 0.9, "a": 1})
    props(t["slot"], Padding={"left": 6, "top": 1, "right": 6, "bottom": 1}, HorizontalAlignment="HAlign_Left")


def header_tree():
    create("WBP_DemoHeader")
    t = add("WBP_DemoHeader", "TextBlock", "Label", var=True)
    text(t["widget"], "SECTION", 11, color={"r": 0.72, "g": 0.78, "b": 0.6, "a": 1})


def browser_tree():
    create("WBP_AnimBrowser")
    B = "WBP_AnimBrowser"
    root = add(B, "CanvasPanel", "Root")["widget"]
    left = add(B, "Border", "LeftPanel", root)
    props(left["widget"], BrushColor=PANEL, Padding={"left": 8, "top": 8, "right": 8, "bottom": 8})
    canvas_slot(left["slot"], (0, 0), (0, 1), (12, 12, 250, 74))
    ls = add(B, "ScrollBox", "LeftScroll", left["widget"])["widget"]
    title = add(B, "TextBlock", "Title", ls)
    text(title["widget"], "UNDEAD LEGION", 16, color={"r": 0.86, "g": 0.84, "b": 0.74, "a": 1})
    for header, box in (("CHARACTERS", "CharacterList"), ("ARMOUR MODULES", "ModuleList"), ("WEAPONS", "WeaponList")):
        h = add(B, "TextBlock", box.replace("List", "Header"), ls, var=True)
        text(h["widget"], header, 11, color={"r": 0.72, "g": 0.78, "b": 0.6, "a": 1})
        props(h["slot"], Padding={"left": 0, "top": 10, "right": 0, "bottom": 3})
        add(B, "VerticalBox", box, ls, var=True)
    right = add(B, "Border", "RightPanel", root)
    props(right["widget"], BrushColor=PANEL, Padding={"left": 8, "top": 8, "right": 8, "bottom": 8})
    canvas_slot(right["slot"], (1, 0), (1, 1), (-262, 12, 250, 74))
    rs = add(B, "ScrollBox", "RightScroll", right["widget"])["widget"]
    add(B, "VerticalBox", "ClipList", rs, var=True)
    foot = add(B, "Border", "Footer", root)
    props(foot["widget"], BrushColor=PANEL, Padding={"left": 8, "top": 6, "right": 8, "bottom": 6})
    canvas_slot(foot["slot"], (0, 1), (1, 1), (12, -62, 12, 50))
    fb = add(B, "HorizontalBox", "FooterBar", foot["widget"], var=True)["widget"]
    info = add(B, "TextBlock", "InfoLabel", fb, var=True)
    text(info["widget"], "", 11, bold=False, color={"r": 0.9, "g": 0.9, "b": 0.86, "a": 1})
    props(info["slot"], Padding={"left": 16, "top": 6, "right": 0, "bottom": 0}, VerticalAlignment="VAlign_Center")


if __name__ == "__main__":
    steps = sys.argv[1:] or ["trees"]
    if "trees" in steps:
        button_tree(); header_tree(); browser_tree()
        for n in ("WBP_DemoButton", "WBP_DemoHeader", "WBP_AnimBrowser"):
            print(n, umg("CompileWidgetBlueprint", widgetBlueprint=W(n)))
