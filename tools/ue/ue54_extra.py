"""Paste texts the DSL does not cover (tools/ue/ue54_compile.py handles the DSL graphs):

    python tools/ue/ue54_extra.py OUTDIR

  BP_UndeadSkeleton__ucs.txt      the construction script: UserConstructionScript -> ApplyDefaultModules (build_character.py
                                  places that call by hand through the MCP; here the whole graph is pasted as a function)
  WBP_DemoButton__click.txt       the button's bound OnClicked(Btn) -> Browser.OnButton(Kind, Index)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue54_t3d import Node, link, T, obj_text, K2
import ue54_compile as C


def esc(s):
    return C.esc(s)


def ucs():
    e = Node(K2 + "K2Node_FunctionEntry", ['FunctionReference=(MemberName="UserConstructionScript")', "bIsEditable=True"], 0, 0)
    then = e.pin("then", "out", "exec")
    c = Node(K2 + "K2Node_CallFunction",
             ['FunctionReference=(MemberParent="%s",MemberName="ApplyDefaultModules")' % obj_text(T("class", C.gen_class(C.CHAR)))], 350, 0)
    link(then, c.pin("execute", "in", "exec"))
    c.pin("then", "out", "exec")
    text = "\n".join(n.text() for n in (e, c)) + "\n"
    return 'BPGraph(GraphName="UserConstructionScript",GraphType=GT_Function,NodesString="%s")' % esc(text)


def button_click():
    """K2Node_ComponentBoundEvent for the Btn widget's OnClicked, calling the browser's OnButton(Kind, Index)."""
    ev = Node(K2 + "K2Node_ComponentBoundEvent",
              ['DelegatePropertyName="OnClicked"', 'DelegateOwnerClass="%s"' % obj_text(T("class", "/Script/UMG.Button")),
               'ComponentPropertyName="Btn"',
               'EventReference=(MemberParent="/Script/CoreUObject.Package\'/Script/UMG\'",MemberName="OnButtonClickedEvent__DelegateSignature")',
               "bInternalEvent=True", 'CustomFunctionName="BndEvt__WBP_DemoButton_Btn_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature"'],
              0, 0)
    then = ev.pin("then", "out", "exec")
    call = Node(K2 + "K2Node_CallFunction",
                ['FunctionReference=(MemberParent="%s",MemberName="OnButton")' % obj_text(T("class", C.gen_class(C.BROWSER)))], 450, 0)
    link(then, call.pin("execute", "in", "exec"))
    call.pin("then", "out", "exec")
    nodes = [ev, call]
    for name, t, pin in (("Browser", "obj:" + C.gen_class(C.BROWSER), "self"), ("Kind", "int", "Kind"), ("Index", "int", "Index")):
        g = Node(K2 + "K2Node_VariableGet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % name], 150, 150 + 80 * len(nodes))
        out = g.pin(name, "out", t)
        link(out, call.pin(pin, "in", t if pin != "self" else "obj:" + C.gen_class(C.BROWSER)))
        nodes.append(g)
    return "\n".join(n.text() for n in nodes) + "\n"


if __name__ == "__main__":
    d = sys.argv[1]
    C.FUNCS = C.function_table()
    open(os.path.join(d, "BP_UndeadSkeleton__ucs.txt"), "w", newline="").write(ucs())
    open(os.path.join(d, "WBP_DemoButton__click.txt"), "w", newline="").write(button_click())
    print("ok")
