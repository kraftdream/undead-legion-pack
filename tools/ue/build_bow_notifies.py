"""Wire bow AnimNotify Blueprints to the character's bow functions via MCP.

Run after ue_build.py showreel_bow bow_runtime and build_character.py's bow pass.
The clip importer places the four markers at the manifest's authoring frames.
"""
from mcp import bp, ref
import json
from pathlib import Path


def build():
    manifest = json.loads((Path(__file__).resolve().parents[2] / "Animations/clips.json").read_text())
    shot = next(c for c in manifest["clips"] if c["name"] == "Shoot_01" and not c.get("disabled"))
    for event in ("BowReset", "BowDraw", "BowAttach", "BowRelease"):
        blueprint = ref("/Game/UndeadLegion/Blueprints/Notifies/AN_" + event)
        graph = bp("add_function_graph", blueprint=blueprint, graph_name="Received_Notify")
        for node in bp("find_nodes", graph=graph, title="") or []:
            if not any(kind in node["refPath"] for kind in ("FunctionEntry", "FunctionResult")):
                bp("delete_node", node=node)
        bp("write_graph_dsl", graph=graph, code="""
(fn Received_Notify (MeshComp Animation EventReference)
  (bind character (Utilities|Casting|CastToBP_UndeadSkeleton
    :Object (Components|GetOwner :self MeshComp))
    (:then
      ; Ignore cancelled clips and notifies from an outgoing instance during a restart.
      (bind pos (Animation|Montage|MontageGetPosition
        :self (Components|SkeletalMesh|GetAnimInstance :self MeshComp)
        :Montage (Class|BPUndeadSkeleton|GetActionMontage :self character)))
      (if (and (Class|BPUndeadSkeleton|GetBowShotActive :self character)
            (and (Utilities|String|EqualExactly(String) :A (Utilities|GetObjectName :Object Animation)
                     :B (Utilities|GetObjectName :Object (Class|BPUndeadSkeleton|GetBowClip :self character)))
                 (>= pos (- %(expected)f 0.016667))))
        (Class|BPUndeadSkeleton|%(event)s :self character)
        (return true)
        (else (return false))))
    (:CastFailed (return false))))
""" % {"event": event, "expected": (shot["events"][event]-1)/30})
        bp("compile_blueprint", blueprint=blueprint, warnings_as_errors=True)
        print("Wired AN_" + event, flush=True)


if __name__ == "__main__":
    build()
