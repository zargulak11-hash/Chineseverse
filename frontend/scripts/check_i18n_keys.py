# -*- coding: utf-8 -*-
"""Fails if any translation key used in src/ is missing from any locale.

Checks every literal t("a.b.c") call, plus the dynamic key families built
from template strings that this script knows how to expand (lesson status,
practice question types/titles, companion moods/voices).
Run from frontend/: python scripts/check_i18n_keys.py
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
LOCALES = ("en", "ru", "tg", "zh")

DYNAMIC = (
    [f"lessonStatus.{s}" for s in ("not_started", "in_progress", "completed")]
    + [f"practice.title.{s}" for s in ("vocab", "hanzi", "grammar", "lesson", "review")]
    + [f"practice.q.{q}" for q in ("meaning_to_word", "word_to_meaning", "listen_to_word",
                                   "char_to_meaning", "char_to_pinyin", "example_to_point")]
    + [f"companionReact.{m}" for m in ("happy", "excited", "proud", "celebrating", "encouraging",
                                       "worried", "lessonComplete", "reviewClear")]
    + [f"companionReact.context.{c}" for c in ("vocab", "hanzi", "grammar")]
    + [f"pages.duels.focusType.{f}" for f in ("mix", "vocab", "listening", "hanzi", "tones", "grammar")]
    + [f"pages.duels.status.{s}" for s in ("pending", "active", "completed", "declined", "cancelled", "expired")]
    + [f"pages.duels.outcome.{o}" for o in ("win", "loss", "draw")]
    + [f"pages.duels.{k}" for k in ("incoming", "inProgress", "outgoing", "history")]
    + [f"pages.duels.errors.{e}" for e in ("generic", "not_found", "not_allowed", "cannot_challenge_self",
                                           "opponent_not_found", "duel_already_open", "invalid_level",
                                           "not_enough_content", "not_started", "no_such_question",
                                           "already_answered", "out_of_order", "invalid_option", "time_up",
                                           "already_finished", "not_pending", "not_active")]
    + [f"pages.duelBattle.{s}" for s in ("declined", "cancelled", "expired")]
    + [f"pages.duelBattle.decidedBy.{d}" for d in ("correct", "score", "time", "draw")]
    + [f"pages.duelBattle.finish.{f}" for f in ("completed", "timeout", "forfeit", "no_show")]
    + [f"practice.title.{s}" for s in ("scene", "sentence")]
    + [f"practice.q.{q}" for q in ("scene_reply", "scene_listen", "sentence_listen", "sentence_order", "sentence_word")]
    + [f"realLife.tier.{x}" for x in ("beginner", "intermediate", "advanced")]
    + [f"realLife.tierHow.{x}" for x in ("beginner", "intermediate", "advanced")]
    + [f"sentenceLesson.status.{x}" for x in ("new", "learning", "reviewing", "mastered")]
    + [f"sentenceLesson.fit.{x}" for x in ("below", "at", "above")]
    + [f"companionMemory.kind.{k}" for k in (
        "welcome_back", "welcome_back_active", "new_learner", "word_milestone", "streak", "achievement",
        "lesson_completed", "lesson_completed_today", "mastered_hard", "mastered_recently", "difficult_chars",
        "confused_pair", "recent_mistakes", "improving_listening", "reviews_done", "stale_area",
        "stale_area_never", "weak_skill")]
    + [f"companionMemory.area.{a}" for a in ("vocab", "hanzi", "grammar")]
    + [f"companionReact.cause.{c}" for c in ("mastered_hard", "confused_pair", "welcome_back", "scene_start",
                                             "sentence_start", "words_milestone")]
    + [f"companionReact.noun.{n}" for n in ("line", "sentence")]
    + [f"pages.progress.section.{x}" for x in ("real_life", "sentence")]
    + [f"practice.title.{s}" for s in ("detective", "sound")]
    + [f"detective.ask.{k}" for k in ("where", "where_me", "when", "when_me", "where_say", "where_seen", "deduce")]
    + [f"detective.case.{c}.{f}" for c in ("who_took", "where_lost", "who_lies") for f in ("zh", "title", "desc")]
    + [f"detective.tag.{x}" for x in ("evidence", "grammar_clue")]
    + [f"detective.mode.{x}" for x in ("read", "listen")]
    + [f"soundWorld.env.{e}" for e in ("night_market", "restaurant", "train_station", "school", "street", "airport", "shopping")]
    + [f"soundWorld.speaker.{s}" for s in ("vendor", "customer", "friend", "waiter", "cook", "announcer", "passenger",
                                           "staff", "teacher", "student", "local", "clerk")]
    + [f"soundWorld.stage.{n}" for n in (1, 2, 3, 4)]
    + [f"soundWorld.ask.{a}" for a in ("sound_identify", "sound_find", "sound_respond", "sound_memory",
                                       "sound_info.price", "sound_info.total", "sound_info.platform", "sound_info.room",
                                       "sound_info.bus", "sound_info.takeoff", "sound_info.floor",
                                       "sound_conversation.count", "sound_conversation.price", "sound_conversation.bus")]
    + [f"charDna.status.{x}" for x in ("new", "learning", "reviewing", "mastered", "due")]
    + [f"charDna.writingStatus.{x}" for x in ("not_practiced", "new", "learning", "reviewing", "mastered")]
    + [f"companionReact.cause.{c}" for c in ("detective_start", "sound_start")]
    + [f"companionReact.noun.{n}" for n in ("case", "sound")]
    + [f"pages.progress.section.{x}" for x in ("detective", "sound_world")]
    + [f"companionReact.voice.{s}" for s in ("fox", "wolf", "snake", "cat", "dog", "tiger", "rabbit", "bird",
                                             "capybara", "panther", "sheep", "panda", "red-panda", "phoenix",
                                             "monkey", "koala", "elephant", "cow", "penguin", "owl")]
)

CALL = re.compile(r"""\bt\(\s*["']([A-Za-z0-9_.-]+)["']""")


def lookup(d, key):
    *parents, leaf = key.split(".")
    for part in parents:
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    if not isinstance(d, dict):
        return None
    if leaf in d:
        return d[leaf]
    # i18next plural forms: key_one / key_few / key_many / key_other
    return d.get(f"{leaf}_other")


def main() -> int:
    data = {l: json.load(open(os.path.join(ROOT, "locales", f"{l}.json"), encoding="utf-8")) for l in LOCALES}
    used = set(DYNAMIC)
    for dirpath, _dirs, files in os.walk(ROOT):
        for name in files:
            if name.endswith((".js", ".jsx")):
                src = open(os.path.join(dirpath, name), encoding="utf-8").read()
                used.update(k for k in CALL.findall(src) if "." in k)
    missing = [(l, k) for k in sorted(used) for l in LOCALES if not isinstance(lookup(data[l], k), str)]
    for l, k in missing:
        print(f"MISSING [{l}] {k}")
    print(f"{len(used)} keys checked across {len(LOCALES)} locales: {len(missing)} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
