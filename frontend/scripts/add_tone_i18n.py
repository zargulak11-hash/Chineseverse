# -*- coding: utf-8 -*-
"""Adds the Tone Coach strings (pages/ToneCoach.jsx) to all four locale
files as new lines: a top-level "toneCoach" block and "nav.toneCoach".
Idempotent. Run from frontend/: python scripts/add_tone_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "title": L("Tone Coach", "Тренер тонов", "Мураббии оҳангҳо", "声调教练"),
    "subtitle": L(
        "Say a word and see the pitch of your voice next to the shape each tone should have. Practice moves to the tones you miss.",
        "Произнесите слово и посмотрите на высоту своего голоса рядом с формой каждого тона. Тренировка подстраивается под тоны, которые у вас не получаются.",
        "Калимаро гӯед ва баландии овози худро дар паҳлӯи шакли ҳар оҳанг бинед. Машқ ба оҳангҳое мегузарад, ки ба шумо душвор аст.",
        "说一个词，看看你的音高和每个声调应有的形状对比。练习会集中在你常说错的声调上。"),
    "modeLabel": L("What to practise", "Что тренировать", "Чиро машқ кунем", "练习内容"),
    "modeSingle": L("Characters", "Иероглифы", "Иероглифҳо", "单字"),
    "modePair": L("Two-syllable words", "Слова из двух слогов", "Калимаҳои дуҳиҷогӣ", "双音节词"),
    "expected": L("Tones to say", "Какие тоны сказать", "Кадом оҳангҳоро гӯед", "要说的声调"),
    "sandhi": L("tone change: here it is said {{tones}}", "изменение тона: здесь говорят {{tones}}",
                "тағйири оҳанг: дар ин ҷо {{tones}} гуфта мешавад", "变调：这里读作 {{tones}}"),
    "how": L("Listen first, then press Record and say the word once, clearly.",
             "Сначала послушайте, затем нажмите «Записать» и чётко скажите слово один раз.",
             "Аввал гӯш кунед, баъд «Сабт»-ро пахш кунед ва калимаро як бор равшан гӯед.",
             "先听一听，然后按“录音”，清楚地说一遍。"),
    "listen": L("Listen", "Прослушать", "Гӯш кардан", "听一听"),
    "record": L("Record", "Записать", "Сабт", "录音"),
    "recording": L("Recording — say it now", "Идёт запись — говорите", "Сабт меравад — ҳозир гӯед", "正在录音——请说"),
    "analysing": L("Analysing…", "Анализ…", "Таҳлил…", "正在分析…"),
    "playMine": L("Play my recording", "Моя запись", "Сабти ман", "播放我的录音"),
    "next": L("Next", "Дальше", "Навбатӣ", "下一个"),
    "verdict_correct": L("Right tones!", "Тоны верные!", "Оҳангҳо дурустанд!", "声调正确！"),
    "verdict_wrong": L("Not quite — compare the curves", "Пока не совсем — сравните кривые",
                       "Ҳанӯз на он қадар — хатҳоро муқоиса кунед", "还不太对——比较一下两条线"),
    "verdict_unclear": L("Couldn't hear the pitch clearly — try again a little louder, somewhere quieter",
                         "Не удалось чётко расслышать высоту — попробуйте громче и в более тихом месте",
                         "Баландиро равшан шунида натавонистем — каме баландтар ва дар ҷои ором такрор кунед",
                         "没听清音高——请大声一点，在安静的地方再试一次"),
    "verdict_silent": L("Nothing was heard — check your microphone", "Ничего не слышно — проверьте микрофон",
                        "Ҳеҷ чиз шунида нашуд — микрофонро санҷед", "什么也没听到——请检查麦克风"),
    "syllableLine": L("expected {{expected}} · heard {{heard}}", "нужен {{expected}} · услышан {{heard}}",
                      "лозим {{expected}} · шунида шуд {{heard}}", "应为{{expected}} · 听到{{heard}}"),
    "heardUnclear": L("unclear", "неясно", "норавшан", "不清楚"),
    "notJudged": L("neutral tone (not judged)", "нейтральный тон (не оценивается)", "оҳанги бетараф (баҳо дода намешавад)",
                   "轻声（不评判）"),
    "tone1": L("1st tone", "1-й тон", "оҳанги 1", "一声"),
    "tone2": L("2nd tone", "2-й тон", "оҳанги 2", "二声"),
    "tone3": L("3rd tone", "3-й тон", "оҳанги 3", "三声"),
    "tone4": L("4th tone", "4-й тон", "оҳанги 4", "四声"),
    "chartLabel": L("Your pitch (solid line) and the shape of each tone (dashed)",
                    "Высота вашего голоса (сплошная линия) и форма каждого тона (пунктир)",
                    "Баландии овози шумо (хати пурра) ва шакли ҳар оҳанг (хати нуқтадор)",
                    "你的音高（实线）和每个声调的形状（虚线）"),
    "statsTitle": L("Your tones (last {{days}} days)", "Ваши тоны (последние {{days}} дней)",
                    "Оҳангҳои шумо ({{days}} рӯзи охир)", "你的声调（最近{{days}}天）"),
    "statsNone": L("Not enough attempts yet — say a few words.", "Пока мало попыток — произнесите несколько слов.",
                   "Ҳанӯз кӯшиш кам аст — чанд калима гӯед.", "练习还不够——先说几个词吧。"),
    "statsTone": L("{{correct}} of {{judged}} right", "верно {{correct}} из {{judged}}", "{{correct}} аз {{judged}} дуруст",
                   "{{judged}}次中对{{correct}}次"),
    "confusion": L("Tone {{expected}} said as tone {{heard}}: {{count}}", "Тон {{expected}} звучал как тон {{heard}}: {{count}}",
                   "Оҳанги {{expected}} ҳамчун оҳанги {{heard}}: {{count}}", "{{expected}}声说成{{heard}}声：{{count}}次"),
    "focus": L("Practising tone {{tone}} — your weakest right now", "Тренируем тон {{tone}} — сейчас он у вас самый слабый",
               "Оҳанги {{tone}}-ро машқ мекунем — ҳоло заифтарин аст", "练习{{tone}}声——这是你现在最弱的声调"),
    "privacy": L("Analysed in your browser: only the pitch numbers are sent — never your voice.",
                 "Анализ идёт в вашем браузере: отправляются только числа высоты тона — не ваш голос.",
                 "Таҳлил дар браузери шумо мегузарад: танҳо рақамҳои баландӣ фиристода мешаванд — на овози шумо.",
                 "在你的浏览器里分析：只发送音高数据，不会上传你的声音。"),
    "honest": L(
        "This checks the pitch of your voice (the tones), not consonants or vowels. It is an estimate: background noise can make it unsure.",
        "Проверяется высота голоса (тоны), а не согласные и гласные. Это оценка: шум вокруг может сделать её неуверенной.",
        "Баландии овоз (оҳангҳо) санҷида мешавад, на ҳамсадо ва садонокҳо. Ин баҳои тахминӣ аст: садои атроф метавонад онро норавшан кунад.",
        "这里只检查你声音的音高（声调），不检查声母和韵母。这是估计：周围的噪音可能让结果不准确。"),
    "unsupported": L(
        "Recording isn't available in this browser. Use a current Chrome, Edge, Safari or Firefox on a device with a microphone.",
        "В этом браузере запись недоступна. Используйте свежий Chrome, Edge, Safari или Firefox на устройстве с микрофоном.",
        "Дар ин браузер сабт дастрас нест. Chrome, Edge, Safari ё Firefox-и навро дар дастгоҳе бо микрофон истифода баред.",
        "这个浏览器不能录音。请在有麦克风的设备上使用新版 Chrome、Edge、Safari 或 Firefox。"),
    "listenCourseWhy": L("Hearing the tones comes before saying them.", "Сначала нужно слышать тоны, потом — произносить.",
                         "Аввал оҳангҳоро шунидан лозим, баъд гуфтан.", "先听清声调，再说准声调。"),
    "listenCourse": L("Pronunciation course (listening)", "Курс произношения (на слух)", "Курси талаффуз (шунидан)",
                      "发音课程（听力）"),
}
EXTRA = {"nav.toneCoach": L("Tone Coach", "Тренер тонов", "Мураббии оҳангҳо", "声调教练")}
KEYS = [f"toneCoach.{k}" for k in S] + list(EXTRA)


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        if '  "toneCoach": {' not in lines:
            end = max(i for i, l in enumerate(lines) if l == "}")
            block = json.dumps({"toneCoach": {k: v[lang] for k, v in S.items()}}, ensure_ascii=False,
                               indent=2).split("\n")[1:-1]
            lines[end - 1] = lines[end - 1].rstrip(",") + ","
            lines[end:end] = block
        for dotted, value in EXTRA.items():
            put(lines, dotted, value[lang])
        text = "\r\n".join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
