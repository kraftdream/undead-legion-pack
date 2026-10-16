"""The demo widgets' trees (tools/ue/build_demo_ui.py builds them through the MCP UMG toolset) as UMG designer paste text
for UE 5.4: select the Widget Blueprint's root row in the Hierarchy panel, Ctrl+V.

    python tools/ue/ue54_widgets.py OUTDIR       -> WBP_DemoButton__tree.txt, WBP_DemoHeader__tree.txt, WBP_AnimBrowser__tree.txt

Format (calibrated 2026-10-16 by copying a designer-built tree): every panel exports its slot objects as inner objects
(Parent / Content references by name) and a Slots(i) list; leaf widgets are plain objects; the slot of a child is not
exported and is restored by the paste.
"""
import os, sys

NORMAL = (0.22, 0.23, 0.26, 1.0)
PANEL = (0.02, 0.02, 0.025, 0.72)
U = "/Script/UMG."


def col(c):
    return "(R=%f,G=%f,B=%f,A=%f)" % c


def margin(m):
    return "(Left=%f,Top=%f,Right=%f,Bottom=%f)" % m


class W:
    def __init__(self, cls, name, var=False, props=(), slot=(), children=()):
        self.cls, self.name, self.var, self.props, self.slot, self.children = cls, name, var, list(props), list(slot), list(children)


SLOT_CLASS = {"CanvasPanel": "CanvasPanelSlot", "Border": "BorderSlot", "VerticalBox": "VerticalBoxSlot", "HorizontalBox": "HorizontalBoxSlot",
              "ScrollBox": "ScrollBoxSlot", "Button": "ButtonSlot"}


def text(name, caption, size, bold=True, color=None, var=False, slot=()):
    p = ['Text=NSLOCTEXT("UndeadLegion", "%s", "%s")' % (name, caption),
         'Font=(Size=%d,TypefaceFontName="%s")' % (size, "Bold" if bold else "Regular")]
    if color:
        p.append("ColorAndOpacity=(SpecifiedColor=%s,ColorUseRule=UseColor_Specified)" % col(color))
    return W("TextBlock", name, var, p, slot)


def emit(root):
    out = []
    counter = [0]

    def rec(w):
        lines = ['Begin Object Class=%s%s Name="%s"' % (U, w.cls, w.name)]
        slots = []
        if w.children:
            sc = SLOT_CLASS[w.cls]
            for i, ch in enumerate(w.children):
                sn = "%s_%d" % (sc, counter[0]); counter[0] += 1
                slots.append((sn, sc, ch))
                lines += ['   Begin Object Class=%s%s Name="%s"' % (U, sc, sn), "   End Object"]
            for sn, sc, ch in slots:
                lines += ['   Begin Object Name="%s"' % sn]
                lines += ["      " + s for s in ch.slot]
                lines += ['      Parent="%s%s\'%s\'"' % (U, w.cls, w.name), '      Content="%s%s\'%s\'"' % (U, ch.cls, ch.name), "   End Object"]
            for i, (sn, sc, ch) in enumerate(slots):
                lines.append('   Slots(%d)="%s%s\'%s\'"' % (i, U, sc, sn))
        lines += ["   " + p for p in w.props]
        lines.append("   bIsVariable=%s" % ("True" if w.var else "False"))
        if w.children:
            lines.append("   bExpandedInDesigner=True")
        lines.append("End Object")
        out.append("\n".join(lines))
        for ch in w.children:
            rec(ch)

    rec(root)
    return "\n".join(out) + "\n"


def button():
    label = text("Label", "Button", 10, bold=False, color=(0.92, 0.92, 0.9, 1.0), var=True,
                 slot=["Padding=%s" % margin((6, 1, 6, 1)), "HorizontalAlignment=HAlign_Left"])
    return W("Button", "Btn", True, ["BackgroundColor=%s" % col(NORMAL)], children=[label])


def header():
    return text("Label", "SECTION", 11, color=(0.72, 0.78, 0.6, 1.0), var=True)


def canvas_slot(amin, amax, offsets):
    return ["LayoutData=(Offsets=%s,Anchors=(Minimum=(X=%f,Y=%f),Maximum=(X=%f,Y=%f)),Alignment=(X=0.000000,Y=0.000000))"
            % (margin(offsets), amin[0], amin[1], amax[0], amax[1])]


def browser():
    green = (0.72, 0.78, 0.6, 1.0)
    left_items = [text("Title", "UNDEAD LEGION", 16, color=(0.86, 0.84, 0.74, 1.0))]
    for head, box in (("CHARACTERS", "CharacterList"), ("ARMOUR MODULES", "ModuleList"), ("WEAPONS", "WeaponList")):
        left_items.append(text(box.replace("List", "Header"), head, 11, color=green, var=True, slot=["Padding=%s" % margin((0, 10, 0, 3))]))
        left_items.append(W("VerticalBox", box, True))
    left = W("Border", "LeftPanel", False, ["BrushColor=%s" % col(PANEL), "Padding=%s" % margin((8, 8, 8, 8))],
             canvas_slot((0, 0), (0, 1), (12, 12, 250, 74)), [W("ScrollBox", "LeftScroll", children=left_items)])
    right = W("Border", "RightPanel", False, ["BrushColor=%s" % col(PANEL), "Padding=%s" % margin((8, 8, 8, 8))],
              canvas_slot((1, 0), (1, 1), (-262, 12, 250, 74)), [W("ScrollBox", "RightScroll", children=[W("VerticalBox", "ClipList", True)])])
    info = text("InfoLabel", "", 11, bold=False, color=(0.9, 0.9, 0.86, 1.0), var=True,
                slot=["Padding=%s" % margin((16, 6, 0, 0)), "VerticalAlignment=VAlign_Center"])
    foot = W("Border", "Footer", False, ["BrushColor=%s" % col(PANEL), "Padding=%s" % margin((8, 6, 8, 6))],
             canvas_slot((0, 1), (1, 1), (12, -62, 12, 50)), [W("HorizontalBox", "FooterBar", True, children=[info])])
    return W("CanvasPanel", "Root", False, children=[left, right, foot])


if __name__ == "__main__":
    d = sys.argv[1]
    for name, root in (("WBP_DemoButton", button()), ("WBP_DemoHeader", header()), ("WBP_AnimBrowser", browser())):
        open(os.path.join(d, name + "__tree.txt"), "w", newline="").write(emit(root))
    print("ok")
