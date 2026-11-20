# sotawhat/lessons/estimate.py
"""What a planned lesson will take to produce, shown in the review step of the Aulas tab before the voice is paid.

The constants were measured on the HyperFrames lessons 6 to 8 (2026-11-10 and 11); each one says where it comes
from. They are estimates: a lesson with longer scenes or a slower provider takes longer."""
from sotawhat.lessons import eleven

CHARS_PER_S = 12.9         # narration: 2,694 characters of plan → 208.8 s of video (lesson 6); 3,253 → 251.9 s (lesson 7)
CREDITS_PER_CHAR = 1.013   # ElevenLabs charged 2,730 credits for 2,694 characters and 3,295 for 3,253 (the spoken text
                           # is a bit longer: decimals and the glossary of pronunciations)
PLAN_S, PLAN_USD = 200, 0.02     # plan + fact check: lesson 7 took 200.9 s and US$ 0.0067; lesson 9 (from the
                                 # interface) 117 s and US$ 0.019, 18k reasoning tokens. The tab shows the upper end
STORYBOARD_S, STORYBOARD_USD = 120, 0.006     # 74 to 261 s, US$ 0.004 to 0.012 (lessons 6 to 8)
VOICE_S_PER_SCENE = 5      # not measured: lessons 7 and 8 came from the cache
FREE3D_S, FREE3D_USD = 315, 0.032             # lesson 8: two mechanism3d scenes, 631 s and US$ 0.063 (code, critic, fix)
CHECK_S = 31               # 30.9 and 31.9 s
RENDER_PER_VIDEO_S = 1.9   # 428 and 528 s of render for 251.9 s of video
SEND_S = 20                # the upload of a 30 to 50 MB video to Telegram (not measured)


def narration_chars(plan) -> int:
    return sum(len(beat.get("narration") or "") for scene in plan.get("scenes") or [] for beat in scene.get("beats") or [])


def free3d_scenes(plan) -> int:
    """Scenes whose 3D an LLM writes (mechanism3d): the slow and paid ones. volume3d and vectors3d come from the kit."""
    return sum(1 for scene in plan.get("scenes") or [] if scene.get("template") == "mechanism3d")


def production(plan, plan_usd=eleven.PLAN_USD, plan_credits=eleven.PLAN_CREDITS, send=True) -> dict:
    """`plan`: the plan as stored on the lesson (a dict). -> the numbers of the review: video length, voice credits and
    their price at the plan's rate, LLM still to spend, and the seconds of each step still to run."""
    chars, scenes, free3d = narration_chars(plan), len(plan.get("scenes") or []), free3d_scenes(plan)
    video_s = chars / CHARS_PER_S
    credits = round(chars * CREDITS_PER_CHAR)
    stages = {"storyboard": STORYBOARD_S, "voz": VOICE_S_PER_SCENE * scenes}
    if free3d:
        stages["3d"] = FREE3D_S * free3d
    stages.update(checagem=CHECK_S, video=round(RENDER_PER_VIDEO_S * video_s))
    if send:
        stages["envio"] = SEND_S
    llm = round(STORYBOARD_USD + FREE3D_USD * free3d, 3)
    voice_usd = eleven.credits_usd(credits, plan_usd, plan_credits)
    return {"chars": chars, "scenes": scenes, "free3d": free3d, "video_s": round(video_s), "credits": credits,
            "voice_usd": voice_usd, "llm_usd": llm, "total_usd": round(llm + voice_usd, 3), "stages": stages,
            "seconds": sum(stages.values())}
