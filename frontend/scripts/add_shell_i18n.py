"""Strings of the app shell (logo, layout). Idempotent; keeps 2-space indent
and CRLF. Run from frontend/: python scripts/add_shell_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "pages.conversation.turns": L("Turns", "Реплики", "Навбатҳо", "轮次"),
    "pages.conversation.progressTitle": L("How far you are", "Как далеко вы продвинулись", "Чӣ қадар пеш рафтед", "进度"),
    "pages.conversation.turnOf": L("Turn {{n}} of {{total}}", "Реплика {{n}} из {{total}}", "Навбати {{n}} аз {{total}}",
                                   "第{{n}}轮，共{{total}}轮"),
    "pages.conversation.keyWords": L("Words that help here", "Слова, которые здесь пригодятся",
                                     "Калимаҳое, ки дар ин ҷо ба кор меоянд", "这里用得上的词"),
    "pages.petTeacher.howTitle": L("How it works", "Как это работает", "Чӣ тавр кор мекунад", "怎么玩"),
    "pages.petTeacher.how1": L("Your companion says a sentence with one real mistake in it.",
                               "Компаньон говорит фразу с одной настоящей ошибкой.",
                               "Ҳамроҳ ҷумлаеро бо як хатои воқеӣ мегӯяд.", "你的伙伴说一句带有一个真实错误的句子。"),
    "pages.petTeacher.how2": L("Write the sentence correctly.", "Напишите фразу правильно.",
                               "Ҷумларо дуруст нависед.", "把句子改写正确。"),
    "pages.petTeacher.how3": L("Explain the rule in your own words — teaching it is how you keep it.",
                               "Объясните правило своими словами — объясняя, вы его запоминаете.",
                               "Қоидаро бо суханони худ шарҳ диҳед — омӯзонда, онро дар ёд нигоҳ медоред.",
                               "用自己的话解释规则——教会别人，自己才记得牢。"),
    "pages.publicProfile.pickList": L("Choose Followers or Following above to see the list.",
                                      "Выберите «Подписчики» или «Подписки» выше, чтобы увидеть список.",
                                      "Барои дидани рӯйхат дар боло «Обуначиён» ё «Обунаҳо»-ро интихоб кунед.",
                                      "点击上方的“粉丝”或“关注”查看列表。"),
    "voice.micUnsupportedSkip": L(
        "Saying it aloud needs speech recognition, which this browser doesn't have (Chrome, Edge and Safari do). Your round carries on without it.",
        "Чтобы сказать это вслух, нужно распознавание речи — в этом браузере его нет (есть в Chrome, Edge и Safari). Раунд продолжится без этого шага.",
        "Барои баланд гуфтан шинохти нутқ лозим аст, ки дар ин браузер нест (дар Chrome, Edge ва Safari ҳаст). Давр бе ин қадам идома меёбад.",
        "大声说出来需要语音识别，这个浏览器没有（Chrome、Edge和Safari有）。本轮会跳过这一步继续。"),
    "nav.toLanding": L("ChineseVerse — main page", "ChineseVerse — главная страница",
                       "ChineseVerse — саҳифаи асосӣ", "ChineseVerse——首页"),
}


def set_path(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


if __name__ == "__main__":
    for loc in ("en", "ru", "tg", "zh"):
        path = os.path.join(LOCALES, f"{loc}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, per in S.items():
            set_path(data, key, per[loc])
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated {loc}.json")
