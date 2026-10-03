"""The Unity showreel's three stages as Unreal shots: a port of ShowreelRecorder's BuildModular / BuildAttacks / BuildMovement
and its step loop (skeletons/Assets/UndeadLegion/Demo/Scripts/ShowreelRecorder.cs), with the same frame accounting.

    python tools/ue/showreel_plan.py            -> Showreel/unreal/plan.json

A stage = a title card + SHOTS; a shot is one character's run of steps (a change of character is a hard cut, as in Unity) and
is rendered on its own (ue_showreel.py shot). Per shot: the character, its loadout and idle at the start, a list of
director commands at output frames (BP_ShowreelDirector kinds), and the caption segments. Unity timing: each step holds its
idle `seconds`, then each attack plays for round((length / speed + crossFade 0.15) * fps) + 2 frames and settles
round(holdAfter 0.9 | a death's 1.6 * fps) frames; root motion recentres after each attack. The showcase's return-to-idle
rules (SkeletonShowcase.Sections) decide which loop runs under / after a one-shot.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(ROOT, "Showreel", "unreal")
FPS = 30
CARD_SECONDS = 1.6
HOLD_BEFORE, HOLD_AFTER, DEATH_HOLD, MOVEMENT_SECONDS, CROSSFADE = 0.8, 0.9, 1.6, 3.0, 0.15
LENGTH = json.load(open(os.path.join(OUTDIR, "clip_lengths.json")))
K = dict(loop=0, action=1, equip=2, wear=3, remove=4, block=5, overlay=6, rootmotion=7, recenter=8, hips=9, hold=10, pause=11,
         bow=12, fire=13, arrow=14)
BOW_EVENTS = {"Shoot_01": (15, 21)}      # manifest events BowAttach / BowRelease (clip frames, 1-based)
ARROW_HIDE = 1.2                         # SkeletonWeapon.arrowHideSeconds
LOADOUTS = ["Sword + shield", "Sword", "Axe + round shield", "Mace", "Dagger", "Two daggers", "Longsword (2H)",
            "Battle axe (2H)", "Recurve bow", "Staff", "Wand"]
MODULES = {"Knight": ["Boot_L", "Boot_R", "Chest", "Glove_L", "Glove_R", "Greave_L", "Greave_R", "Helm", "Skirt"],
           "Archer": ["Boot_L", "Boot_R", "Chest", "Glove_L", "Glove_R", "Helm", "Skirt"],
           "Assassin": ["Boot_L", "Boot_R", "Chest", "Glove_L", "Glove_R", "Helm", "Pants", "Skirt"],
           "Mage": ["Boot_L", "Boot_R", "Glove_L", "Glove_R", "Greave_L", "Greave_R", "Helm", "Robe"],
           "Necromancer": ["Boot_L", "Boot_R", "Glove_L", "Glove_R", "Greave_L", "Greave_R", "Helm", "Robe"],
           "Warrior": ["Boot_L", "Boot_R", "Chest", "Glove_L", "Glove_R", "Greave_L", "Greave_R", "Skirt"]}
GRIP_L = {"Idle_TwoHanded", "Attack_2H_01", "Attack_2H_02", "Cast_Staff_01"}          # manifest grip_hands L
RETURN = {"Attack_R_Stab": "Idle_1H_Combat", "Attack_R_Slice": "Idle_1H_Combat", "Attack_L_Stab": "Idle_1H_Combat",
          "Attack_L_Slice": "Idle_1H_Combat", "Attack_2H_01": "Idle_TwoHanded", "Attack_2H_02": "Idle_TwoHanded",
          "Shoot_01": "Idle_Bow", "Cast_Wand_01": "Idle_Staff", "Cast_Wand_02": "Idle_Staff", "Cast_Staff_01": "Idle_Staff"}
# everything else returns to the running idle (Specials / Reactions: returnToLastIdle); deaths hold; hits are overlays


def mesh(char, module):
    return "/Game/UndeadLegion/Characters/Skeleton%s/Armor/SK_Skeleton%s_%s" % (char, char, module)


def S(character, loadout, idle, seconds, title, text, **kw):
    st = dict(character=character, loadout=loadout, idle=idle, seconds=seconds, title=title, text=text, attacks=[],
              speed=1.0, after=-1.0, hips=False, hold_on=None, hold_off=None, wear=[], remove=[], root_motion=None)
    st.update(kw)
    return st


def A(character, loadout, idle, title, text, *attacks, **kw):
    return S(character, loadout, idle, HOLD_BEFORE, title, text, attacks=list(attacks), **kw)


def death(st):
    st.update(after=DEATH_HOLD, hips=True, seconds=0.3)
    return st


def modular():
    six = "Six class presets on one shared humanoid rig"
    st = [S(c, "", "Idle_03", 3, "Skeleton " + c, six) for c in ("Warrior", "Assassin", "Archer", "Mage", "Necromancer", "Knight")]
    st.append(S("Knight", "", "Idle_03", 3, "Warrior chest plate on the Knight",
                "Armour modules are separate assets: any piece binds to any skeleton by bone name", wear=["Warrior:Chest"]))
    st.append(S("Knight", "", "Idle_03", 3, "+ Archer helm", "Mix and match across the six sets", wear=["Archer:Helm"]))
    st.append(S("Knight", "", "Idle_03", 3, "+ Warrior greaves", "Each piece is its own renderer on the character's bones: on / off at zero cost",
                wear=["Warrior:Greave_L", "Warrior:Greave_R"]))
    st.append(S("Knight", "", "Idle_03", 3, "+ Assassin gloves", "The mixed skeleton animates like any other",
                wear=["Assassin:Glove_L", "Assassin:Glove_R"]))
    slots = "Weapons attach to hand slots; the fingers close on the grip"
    st += [S("Knight", "Sword + shield", "Idle_03", 3, "Sword + heater shield", slots),
           S("Knight", "Axe + round shield", "Idle_03", 3, "Axe + round shield", slots),
           S("Knight", "Sword", "Idle_02", 3, "Sword", "Three base idles to pick from per class"),
           S("Knight", "Dagger", "Idle_02", 3, "Dagger", slots),
           S("Knight", "Two daggers", "Idle_02", 3, "Two daggers", "One-handed items in either hand"),
           S("Knight", "Mace", "Idle_01", 3, "Mace", slots),
           S("Knight", "Longsword (2H)", "Idle_TwoHanded", 3, "Longsword", "Two-handed idle: the second hand rides the handle"),
           S("Knight", "Battle axe (2H)", "Idle_TwoHanded", 3, "Battle axe", "The same two-handed grip on every long weapon"),
           S("Archer", "Recurve bow", "Idle_Bow", 3.5, "Recurve bow", "Bow idle; the bow is a skinned model whose string follows the draw hand"),
           S("Necromancer", "Staff", "Idle_Staff", 3.5, "Staff", "Staff idle"),
           S("Mage", "Wand", "Idle_03", 3.5, "Wand", "Short staff, one-handed")]
    return dict(name="modular", title="MODULAR", text="six class presets  |  one shared rig  |  every armour piece and weapon on any skeleton",
                root_motion=False, steps=st)


def weapons():
    st = [A("Warrior", "Longsword (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Longsword", "Taunt", "Taunt_01"),
          A("Warrior", "Longsword (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Longsword", "Two-handed idle; the second hand rides the handle", "Attack_2H_01", "Attack_2H_02"),
          A("Warrior", "Battle axe (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Battle axe", "The same two-handed grip and attacks on every long weapon", "Attack_2H_01", "Attack_2H_02"),
          death(A("Warrior", "Battle axe (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Battle axe", "Death", "Death_01")),
          A("Knight", "Axe + round shield", "Idle_1H_Combat", "Skeleton Knight  |  Axe + round shield", "Taunt and rally", "Taunt_02", "Rally"),
          A("Knight", "Axe + round shield", "Idle_1H_Combat", "Skeleton Knight  |  Axe + round shield", "Left-arm block HELD on its own layer; the right arm attacks under it", "Attack_R_Slice", hold_on="Block_L_Idle"),
          A("Knight", "Sword + shield", "Idle_1H_Combat", "Skeleton Knight  |  Sword + heater shield", "Any one-handed weapon, any shield; the block still held", "Attack_R_Stab", "Attack_R_Slice"),
          A("Knight", "Sword", "Idle_1H_Combat", "Skeleton Knight  |  Sword", "Block released; the same attacks with the free hand", "Attack_R_Stab", "Attack_R_Slice", hold_off="Block_L_Idle"),
          death(A("Knight", "Sword", "Idle_1H_Combat", "Skeleton Knight  |  Sword", "Death", "Death_02")),
          A("Assassin", "Dagger", "Idle_1H_Combat", "Skeleton Assassin  |  Dagger", "Cutthroat", "Cutthroat"),
          A("Assassin", "Dagger", "Idle_1H_Combat", "Skeleton Assassin  |  Dagger", "Right-arm attacks at 1.6x speed", "Attack_R_Stab", "Attack_R_Slice", speed=1.6),
          A("Assassin", "Two daggers", "Idle_1H_Combat", "Skeleton Assassin  |  Two daggers", "Left-arm attacks at 1.6x speed", "Attack_L_Stab", "Attack_L_Slice", speed=1.6),
          death(A("Assassin", "Two daggers", "Idle_1H_Combat", "Skeleton Assassin  |  Two daggers", "Death", "Death_03")),
          A("Archer", "Recurve bow", "Idle_Bow", "Skeleton Archer  |  Recurve bow", "The string follows the draw hand; an arrow is fired on release", "Shoot_01"),
          A("Mage", "Wand", "Idle_03", "Skeleton Mage  |  Wand", "Two wand casts", "Cast_Wand_01", "Cast_Wand_02"),
          A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "Summon", "Summon"),
          A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "The wand casts on the staff, then the two-handed staff cast", "Cast_Wand_01", "Cast_Wand_02", "Cast_Staff_01"),
          A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "Area cast", "AOE_Cast"),
          death(A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "Death", "Death_04"))]
    return dict(name="weapons", title="WEAPONS & UTILS", text="every weapon with its idle and attacks  |  taunts, specials, deaths",
                root_motion=True, steps=st)


def movement():
    set01 = [("Walk_Fwd_01", "0.52"), ("Run_Fwd_01", "1.14"), ("Walk_Back_01", "0.34"), ("Strafe_Left_01", "0.20"), ("Strafe_Right_01", "0.20")]
    set02 = [("Walk_Fwd_02", "1.28"), ("Run_Fwd_02", "1.87"), ("Walk_Back_02", "0.77"), ("Strafe_Left_02", "0.93"), ("Strafe_Right_02", "0.93")]
    st = []
    for ch, lo, s in (("Warrior", "Axe + round shield", "01"), ("Mage", "Staff", "02")):
        line = "Shambling set (_01) for the lower ranks" if s == "01" else "Upright set (_02) for the higher ranks"
        for clip, speed in (set01 if s == "01" else set02):
            st.append(S(ch, lo, clip, MOVEMENT_SECONDS, "Skeleton %s  |  %s" % (ch, clip), line + "  |  root motion " + speed + " m/s, played in place here"))
    st.append(A("Warrior", "Axe + round shield", "Idle_1H_Combat", "Skeleton Warrior  |  Hit reactions", "Additive: blended over whatever the skeleton is playing", "Hit_01", "Hit_02"))
    st.append(A("Warrior", "Axe + round shield", "Idle_1H_Combat", "Skeleton Warrior  |  Staggers", "A hit with one step back, on root motion", "Stagger_01", "Stagger_02", root_motion=True))
    return dict(name="movement", title="MOVEMENT", text="two locomotion sets  |  hit reactions and staggers  |  measured speed table shipped",
                root_motion=False, steps=st)


def shots(stage):
    out, cur = [], None
    for step in stage["steps"]:
        ch = step["character"]
        if cur is None or cur["character"] != ch:
            cur = dict(character=ch, loadout=step["loadout"], idle=step["idle"], frames=0, cmds=[], captions=[],
                       state=dict(idle=step["idle"], loadout=step["loadout"], hold=None, rm=stage["root_motion"], block=False, worn=set()))
            out.append(cur)
            # settle before frame 0 (Unity: two uncaptured frames after SelectCharacter); BeginPlay already put on the loadout
            # and the idle (StartLoadout / StartClip)
            cmd(cur, -45, "rootmotion", n=int(stage["root_motion"]))
        f, s = cur["frames"], cur["state"]

        def caption(text, at):
            if cur["captions"] and cur["captions"][-1]["f1"] is None:
                cur["captions"][-1]["f1"] = at
            cur["captions"].append(dict(f0=at, f1=None, title=step["title"], text=text))

        t0 = f if f > 0 else -30                     # the first step of a shot is set up before frame 0
        for r in step["remove"]:
            cmd(cur, t0, "remove", mesh=mesh(ch, r))
        for w in step["wear"]:
            other, module = w.split(":")
            if module in MODULES[ch]:
                cmd(cur, t0, "remove", mesh=mesh(ch, module))   # the character's own piece of that module off
            cmd(cur, t0, "wear", mesh=mesh(other, module))
        if step["idle"] != s["idle"]:
            cmd(cur, t0, "loop", clip=step["idle"])
            s["idle"] = step["idle"]
        if step["loadout"] != s["loadout"]:
            cmd(cur, t0, "equip", n=LOADOUTS.index(step["loadout"]) if step["loadout"] else -1)
            s["loadout"] = step["loadout"]
        if step["hold_off"] and s["block"]:
            cmd(cur, t0, "block", n=0); s["block"] = False
        if step["hold_on"] and not s["block"]:
            cmd(cur, t0, "block", n=1); s["block"] = True
        hold(cur, t0, step["idle"] in GRIP_L)
        cmd(cur, t0, "hips", n=int(step["hips"]))
        if step["root_motion"] is not None and step["root_motion"] != s["rm"]:
            cmd(cur, t0, "rootmotion", n=int(step["root_motion"])); s["rm"] = step["root_motion"]
        caption(step["text"], f)
        f += round(step["seconds"] * FPS)
        for a in step["attacks"]:
            sp = step["speed"]
            caption(step["text"] + "  |  " + a + ("  (%.1fx)" % sp if sp != 1.0 else ""), f)
            if a.startswith("Hit_"):
                cmd(cur, f, "overlay", clip=a)
            else:
                cmd(cur, f, "action", clip=a, real=sp)
                ret = RETURN.get(a)
                if ret and ret != s["idle"]:
                    cmd(cur, f, "loop", clip=ret); s["idle"] = ret
                hold(cur, f, a in GRIP_L or (s["idle"] in GRIP_L and False))
            if a in BOW_EVENTS:
                fa, fr = BOW_EVENTS[a]
                cmd(cur, f + round((fa - 1) / sp), "bow", n=1)
                cmd(cur, f + round((fr - 1) / sp), "bow", n=0)
                cmd(cur, f + round((fr - 1) / sp), "fire")
                cmd(cur, f + round((fr - 1) / sp + ARROW_HIDE * FPS), "arrow")
            length = LENGTH[a] / sp
            if a.startswith("Death_"):
                cmd(cur, f + round((length - 0.3) * FPS), "pause")       # hold the corpse before the montage blends out
            f += round((length + CROSSFADE) * FPS) + 2
            if not a.startswith(("Hit_", "Death_")):
                hold(cur, f - 2, s["idle"] in GRIP_L)                      # the one-shot is over: the loop's grip again
            f += round((step["after"] if step["after"] >= 0 else HOLD_AFTER) * FPS)
            if s["rm"] and not a.startswith("Death_"):
                cmd(cur, f, "recenter")
        if step["attacks"]:
            caption(step["text"], f)
        cur["frames"] = f
    for sh in out:
        if sh["captions"]:
            sh["captions"][-1]["f1"] = sh["frames"]
        sh["captions"] = [c for c in sh["captions"] if c["f1"] > c["f0"]]
        del sh["state"]
    return out


def cmd(shot, frame, kind, clip=None, mesh=None, n=0, real=1.0):
    shot["cmds"].append(dict(f=frame, kind=K[kind], name=kind, clip=clip, mesh=mesh, n=n, real=real))


def hold(shot, frame, on):
    st = shot.get("state", {})
    if st.get("hold") != on:
        cmd(shot, frame, "hold", n=int(on))
        st["hold"] = on


if __name__ == "__main__":
    plan = []
    for stage in (modular(), movement(), weapons()):
        sh = shots(stage)
        plan.append(dict(name=stage["name"], title=stage["title"], text=stage["text"], card_frames=round(CARD_SECONDS * FPS), shots=sh))
        print("%-9s %2d shots, %5.1f s (+ card)  %s" % (stage["name"], len(sh), sum(s["frames"] for s in sh) / float(FPS),
                                                        ", ".join("%s %d" % (s["character"], s["frames"]) for s in sh)))
    json.dump(plan, open(os.path.join(OUTDIR, "plan.json"), "w"), indent=1)
