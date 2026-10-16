"""Mesh sockets for the UE 5.4 build. A socket's name is read-only to 5.4 Python (5.8 uses the MCP add_socket), so the
sockets are PASTED in the skeletal mesh editor's skeleton tree (Persona's own socket clipboard format, FEditableSkeleton::
HandlePasteSockets) and their transforms are then set by the usual in-editor steps (ue_build.py sockets, eyes).

    python tools/ue/ue54_sockets.py OUT.txt       the paste text: RightHandSlot / LeftHandSlot on the hands, EyeL / EyeR on the head
"""
import sys

SOCKETS = [("RightHandSlot", "hand_r"), ("LeftHandSlot", "hand_l"), ("EyeL", "head"), ("EyeR", "head")]


def text():
    out = ["SocketCopyPasteBuffer", "NumSockets=%d" % len(SOCKETS)]
    for i, (name, bone) in enumerate(SOCKETS):
        out += ["IsOnSkeleton=0",
                'Begin Object Class=/Script/Engine.SkeletalMeshSocket Name="SkeletalMeshSocket_%d"' % i,
                '   SocketName="%s"' % name, '   BoneName="%s"' % bone, "End Object"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    open(sys.argv[1], "w", newline="").write(text())
