# -*- coding: utf-8 -*-
"""Adds the companion-reaction strings (moods, causes, DNA skill names,
figure labels) to all four locale files (en/ru/tg/zh). The causes mirror
backend app/services/companion_reaction.py. Idempotent: re-running
overwrites the same keys with the same text.
Run from frontend/: python scripts/add_companion_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")

T = {
    "en": {
        "figureLabel": "{{animal}} companion — {{mood}}",
        "hear": "Listen",
        "example": "Example:",
        "lessonWords": "Peek at this lesson's words (tap one to hear it)",
        "skillUp": "{{skill}} reached {{value}}",
        "skillTrained": "Trained: {{skill}} · now {{value}}/100",
        "mood": {
            "neutral": "calm", "happy": "happy", "excited": "excited", "proud": "proud",
            "encouraging": "encouraging", "worried": "concerned", "sad": "sad",
            "frustrated": "playfully grumpy", "serious": "focused", "celebrating": "celebrating",
        },
        "noun": {"vocab": "word", "hanzi": "character", "grammar": "grammar point"},
        "skill": {
            "speaking": "Speaking", "listening": "Listening", "reading": "Reading", "writing": "Writing",
            "vocabulary": "Vocabulary", "grammar": "Grammar", "tones": "Tones", "memory": "Memory",
            "reaction_speed": "Reaction speed",
        },
        "cause": {
            "correct": "{{name}} is happy — that's right!",
            "new_item": "{{name}} is delighted — a new {{noun}} learned!",
            "recovering": "{{name}} perks up — you found your footing again. Keep going!",
            "streak": "{{name}} is proud — {{count}} in a row!",
            "hot_streak": "{{name}} is thrilled — {{count}} in a row, you're on fire!",
            "comeback": "{{name}} is proud — this one tripped you up before, and now you've got it.",
            "mastered": "{{name}} is proud — you've mastered this {{noun}}!",
            "skill_up": "{{name}} noticed: your {{skill}} just grew in your Learning DNA!",
            "miss": "{{name}} says: not quite — look at the answer, it will stick next time.",
            "streak_break": "{{name}} shrugs it off — one miss after a great run. Keep your rhythm.",
            "two_misses": "{{name}} is a little concerned — slow down and read the answer carefully.",
            "mistake_run": "{{name}} can see this is tricky right now. Slow down — every miss goes to Review, nothing is lost.",
            "long_slump": "{{name}} is sitting right beside you. Tough stretch — take a breath; these will come back in Review.",
            "repeat_item": "{{name}} gets focused — this {{noun}} has come up before. Let's look at it closely together.",
            "tricky_item": "{{name}} huffs at this sneaky {{noun}} (not at you!). Say it aloud once and it will stick.",
            "self_known": "{{name}} is happy you know this one.",
            "still_learning": "{{name}} nods — an honest check. It will come back in Review.",
            "lesson_complete": "{{name}} is celebrating — lesson complete!",
            "outstanding": "{{name}} is celebrating — {{score}}%, outstanding work!",
            "solid": "{{name}} is happy — {{score}}%, a solid round.",
            "review_done": "{{name}} is proud — review done at {{score}}%.",
            "keep_practicing": "{{name}} says: {{score}}% — good effort. Revisit the item below and try another round.",
            "needs_review": "{{name}} is with you — {{score}}% this time. Your misses are waiting in Review; let's go over them.",
            "review_clear": "{{name}} is relaxed — your review queue is empty.",
            "lesson_start": "{{name}} is ready to learn with you. Meet this lesson's words first.",
            "review_start": "{{name}} is focused — {{due}} items to bring back from memory.",
            "session_start": "{{name}} is ready when you are.",
            "clean_trace": "{{name}} is proud — every stroke clean!",
            "good_trace": "{{name}} is happy — well written, just a slip or two.",
            "shaky_trace": "{{name}} cheers you on — the character is done; one more trace will make it steadier.",
            "writing_mastered": "{{name}} is celebrating — you can write this character now!",
        },
    },
    "ru": {
        "figureLabel": "Компаньон {{animal}} — {{mood}}",
        "hear": "Послушать",
        "example": "Пример:",
        "lessonWords": "Подсмотреть слова урока (нажмите, чтобы услышать)",
        "skillUp": "{{skill}}: уже {{value}}",
        "skillTrained": "Тренировали: {{skill}} · сейчас {{value}}/100",
        "mood": {
            "neutral": "спокоен", "happy": "рад", "excited": "в восторге", "proud": "гордится",
            "encouraging": "подбадривает", "worried": "переживает", "sad": "грустит",
            "frustrated": "шутливо ворчит", "serious": "сосредоточен", "celebrating": "празднует",
        },
        "noun": {"vocab": "слово", "hanzi": "иероглиф", "grammar": "грамматика"},
        "skill": {
            "speaking": "Говорение", "listening": "Аудирование", "reading": "Чтение", "writing": "Письмо",
            "vocabulary": "Словарный запас", "grammar": "Грамматика", "tones": "Тоны", "memory": "Память",
            "reaction_speed": "Скорость реакции",
        },
        "cause": {
            "correct": "{{name}} радуется — верно!",
            "new_item": "{{name}} в восторге — новое выучено: {{noun}}!",
            "recovering": "{{name}} оживился — вы снова поймали ритм. Продолжайте!",
            "streak": "{{name}} гордится — {{count}} подряд!",
            "hot_streak": "{{name}} в восторге — {{count}} подряд, вы в ударе!",
            "comeback": "{{name}} гордится — раньше здесь была ошибка, а теперь всё верно.",
            "mastered": "{{name}} гордится — освоено: {{noun}}!",
            "skill_up": "{{name}} заметил: навык «{{skill}}» в вашей ДНК обучения вырос!",
            "miss": "{{name}} говорит: не совсем — посмотрите на ответ, в следующий раз запомнится.",
            "streak_break": "{{name}} не расстраивается — одна ошибка после отличной серии. Держите ритм.",
            "two_misses": "{{name}} немного переживает — не спешите и внимательно прочитайте ответ.",
            "mistake_run": "{{name}} видит, что сейчас непросто. Не спешите — каждая ошибка попадает в повторение, ничего не теряется.",
            "long_slump": "{{name}} рядом с вами. Трудный момент — сделайте вдох; всё это вернётся в повторении.",
            "repeat_item": "{{name}} сосредоточился — это уже встречалось ({{noun}}). Давайте разберём внимательно вместе.",
            "tricky_item": "{{name}} ворчит на хитрое задание ({{noun}}), а не на вас! Произнесите вслух — и запомнится.",
            "self_known": "{{name}} рад, что вы это знаете.",
            "still_learning": "{{name}} кивает — честная проверка. Это вернётся в повторении.",
            "lesson_complete": "{{name}} празднует — урок пройден!",
            "outstanding": "{{name}} празднует — {{score}}%, превосходно!",
            "solid": "{{name}} радуется — {{score}}%, уверенный раунд.",
            "review_done": "{{name}} гордится — повторение завершено на {{score}}%.",
            "keep_practicing": "{{name}}: {{score}}% — хорошая попытка. Посмотрите ещё раз на пример ниже и пройдите ещё раунд.",
            "needs_review": "{{name}} с вами — в этот раз {{score}}%. Ошибки ждут в повторении — давайте разберём их.",
            "review_clear": "{{name}} спокоен — очередь повторения пуста.",
            "lesson_start": "{{name}} готов учиться вместе с вами. Сначала познакомьтесь со словами урока.",
            "review_start": "{{name}} сосредоточен — нужно вспомнить {{due}} элементов.",
            "session_start": "{{name}} готов, когда будете готовы вы.",
            "clean_trace": "{{name}} гордится — все черты чистые!",
            "good_trace": "{{name}} радуется — хорошо написано, лишь пара неточностей.",
            "shaky_trace": "{{name}} подбадривает — иероглиф написан; ещё одна попытка сделает его увереннее.",
            "writing_mastered": "{{name}} празднует — теперь вы умеете писать этот иероглиф!",
        },
    },
    "tg": {
        "figureLabel": "Ҳамроҳ {{animal}} — {{mood}}",
        "hear": "Гӯш кардан",
        "example": "Мисол:",
        "lessonWords": "Калимаҳои дарсро дидан (барои шунидан пахш кунед)",
        "skillUp": "{{skill}}: акнун {{value}}",
        "skillTrained": "Машқ шуд: {{skill}} · ҳоло {{value}}/100",
        "mood": {
            "neutral": "ором", "happy": "шод", "excited": "ба ваҷд омада", "proud": "фахр мекунад",
            "encouraging": "рӯҳбаланд мекунад", "worried": "нигарон", "sad": "ғамгин",
            "frustrated": "шӯхиомез ғур-ғур мекунад", "serious": "диққатманд", "celebrating": "ҷашн мегирад",
        },
        "noun": {"vocab": "калима", "hanzi": "иероглиф", "grammar": "грамматика"},
        "skill": {
            "speaking": "Гуфтор", "listening": "Шунидан", "reading": "Хондан", "writing": "Навиштан",
            "vocabulary": "Луғат", "grammar": "Грамматика", "tones": "Оҳангҳо", "memory": "Хотира",
            "reaction_speed": "Суръати вокуниш",
        },
        "cause": {
            "correct": "{{name}} шод аст — дуруст!",
            "new_item": "{{name}} хеле шод аст — чизи нав омӯхтед: {{noun}}!",
            "recovering": "{{name}} рӯҳ гирифт — шумо боз ба маром омадед. Идома диҳед!",
            "streak": "{{name}} фахр мекунад — {{count}} пай дар пай!",
            "hot_streak": "{{name}} ба ваҷд омад — {{count}} пай дар пай, офарин!",
            "comeback": "{{name}} фахр мекунад — пештар дар ин ҷо хато буд, акнун дуруст шуд.",
            "mastered": "{{name}} фахр мекунад — аз худ кардед: {{noun}}!",
            "skill_up": "{{name}} пай бурд: маҳорати «{{skill}}» дар ДНК-и омӯзиши шумо афзуд!",
            "miss": "{{name}} мегӯяд: на он қадар — ба ҷавоб нигаред, дафъаи оянда дар ёд мемонад.",
            "streak_break": "{{name}} парво накард — як хато баъди силсилаи олӣ. Маромро нигоҳ доред.",
            "two_misses": "{{name}} каме нигарон аст — шитоб накунед ва ҷавобро бодиққат хонед.",
            "mistake_run": "{{name}} мебинад, ки ҳоло душвор аст. Шитоб накунед — ҳар хато ба такрор меравад, ҳеҷ чиз гум намешавад.",
            "long_slump": "{{name}} дар паҳлӯи шумост. Лаҳзаи душвор — нафас кашед; инҳо дар такрор бармегарданд.",
            "repeat_item": "{{name}} диққат дод — ин пештар ҳам буд ({{noun}}). Биёед якҷоя бодиққат бубинем.",
            "tricky_item": "{{name}} ба ин супориши маккор ({{noun}}) ғур-ғур мекунад, на ба шумо! Бо овози баланд гӯед — дар ёд мемонад.",
            "self_known": "{{name}} шод аст, ки шумо инро медонед.",
            "still_learning": "{{name}} сар ҷунбонд — санҷиши ростқавлона. Ин дар такрор бармегардад.",
            "lesson_complete": "{{name}} ҷашн мегирад — дарс тамом шуд!",
            "outstanding": "{{name}} ҷашн мегирад — {{score}}%, аъло!",
            "solid": "{{name}} шод аст — {{score}}%, даври боэътимод.",
            "review_done": "{{name}} фахр мекунад — такрор бо {{score}}% анҷом ёфт.",
            "keep_practicing": "{{name}}: {{score}}% — кӯшиши хуб. Ба мисоли поён боз нигаред ва як даври дигар гузаронед.",
            "needs_review": "{{name}} бо шумост — ин дафъа {{score}}%. Хатоҳо дар такрор интизоранд — биёед онҳоро аз назар гузаронем.",
            "review_clear": "{{name}} ором аст — навбати такрор холӣ аст.",
            "lesson_start": "{{name}} омода аст бо шумо омӯзад. Аввал бо калимаҳои дарс шинос шавед.",
            "review_start": "{{name}} диққатманд аст — {{due}} чизро бояд ба ёд овард.",
            "session_start": "{{name}} омода аст, вақте ки шумо омода бошед.",
            "clean_trace": "{{name}} фахр мекунад — ҳамаи хатҳо тоза!",
            "good_trace": "{{name}} шод аст — хуб навиштед, танҳо як-ду хатои хурд.",
            "shaky_trace": "{{name}} рӯҳбаланд мекунад — иероглиф навишта шуд; боз як бор онро устувортар мекунад.",
            "writing_mastered": "{{name}} ҷашн мегирад — акнун шумо ин иероглифро навишта метавонед!",
        },
    },
    "zh": {
        "figureLabel": "{{animal}}伙伴——{{mood}}",
        "hear": "听一听",
        "example": "例句：",
        "lessonWords": "看看本课词语（点一下就能听）",
        "skillUp": "{{skill}}达到 {{value}}",
        "skillTrained": "本轮练习：{{skill}} · 现在 {{value}}/100",
        "mood": {
            "neutral": "平静", "happy": "开心", "excited": "兴奋", "proud": "骄傲",
            "encouraging": "鼓励", "worried": "担心", "sad": "难过",
            "frustrated": "假装生气", "serious": "专注", "celebrating": "庆祝",
        },
        "noun": {"vocab": "词", "hanzi": "汉字", "grammar": "语法点"},
        "skill": {
            "speaking": "口语", "listening": "听力", "reading": "阅读", "writing": "书写",
            "vocabulary": "词汇", "grammar": "语法", "tones": "声调", "memory": "记忆",
            "reaction_speed": "反应速度",
        },
        "cause": {
            "correct": "{{name}}很开心——答对了！",
            "new_item": "{{name}}高兴极了——又学会了一个新的{{noun}}！",
            "recovering": "{{name}}振作起来了——你找回了节奏，继续！",
            "streak": "{{name}}为你骄傲——连续答对 {{count}} 题！",
            "hot_streak": "{{name}}太兴奋了——连续答对 {{count}} 题，状态火热！",
            "comeback": "{{name}}为你骄傲——以前在这里出过错，现在答对了。",
            "mastered": "{{name}}为你骄傲——这个{{noun}}你已经掌握了！",
            "skill_up": "{{name}}发现：你的学习 DNA 里「{{skill}}」提高了！",
            "miss": "{{name}}说：差一点——看看答案，下次就记住了。",
            "streak_break": "{{name}}不在意——连对之后错了一题而已，保持节奏。",
            "two_misses": "{{name}}有点担心——慢一点，仔细看看答案。",
            "mistake_run": "{{name}}发现现在有点难。慢慢来——每个错误都会进入复习，什么都不会丢。",
            "long_slump": "{{name}}就在你身边。这段有点难——深呼吸，它们会在复习里再出现。",
            "repeat_item": "{{name}}认真起来了——这个{{noun}}之前出现过，我们一起仔细看看。",
            "tricky_item": "{{name}}对这个调皮的{{noun}}哼了一声（不是对你！）。大声读一遍，就记住了。",
            "self_known": "{{name}}很高兴你认识它。",
            "still_learning": "{{name}}点点头——诚实的自我检查。它会在复习里再出现。",
            "lesson_complete": "{{name}}在庆祝——课程完成！",
            "outstanding": "{{name}}在庆祝——{{score}}%，太出色了！",
            "solid": "{{name}}很开心——{{score}}%，很扎实的一轮。",
            "review_done": "{{name}}为你骄傲——复习完成，得分 {{score}}%。",
            "keep_practicing": "{{name}}说：{{score}}%——不错的尝试。再看看下面这一项，然后再练一轮。",
            "needs_review": "{{name}}陪着你——这次 {{score}}%。错题都在复习里等你，我们一起过一遍。",
            "review_clear": "{{name}}很放松——复习队列是空的。",
            "lesson_start": "{{name}}准备好和你一起学习了。先认识一下本课的词语。",
            "review_start": "{{name}}很专注——有 {{due}} 项需要回忆。",
            "session_start": "{{name}}准备好了，等你开始。",
            "clean_trace": "{{name}}为你骄傲——每一笔都很干净！",
            "good_trace": "{{name}}很开心——写得很好，只有一两处小失误。",
            "shaky_trace": "{{name}}为你加油——字已经写完了，再写一遍会更稳。",
            "writing_mastered": "{{name}}在庆祝——这个字你会写了！",
        },
    },
}


def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict):
            merge(dst.setdefault(k, {}), v)
        else:
            dst[k] = v


for lang, strings in T.items():
    path = os.path.join(LOCALES, f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    merge(data.setdefault("companionReact", {}), strings)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{lang}: companionReact now has {len(data['companionReact'])} keys")
