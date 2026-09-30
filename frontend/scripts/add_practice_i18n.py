# -*- coding: utf-8 -*-
"""Adds the practice/review, lesson-status and companion-reaction strings to
all four locale files (en/ru/tg/zh). Idempotent: re-running overwrites the
same keys with the same text. Run from frontend/: python scripts/add_practice_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")

SLUGS = ["fox", "wolf", "snake", "cat", "dog", "tiger", "rabbit", "bird", "capybara", "panther",
         "sheep", "panda", "red-panda", "phoenix", "monkey", "koala", "elephant", "cow", "penguin", "owl"]

VOICES = {
    "en": ["Yip!", "Awoo!", "Hsss…", "Mrrr!", "Woof!", "Rrrawr!", "*thump thump*", "Tweet!", "*calm nod*", "Prrr…",
           "Baa!", "*munch munch*", "*tail swish*", "*flames flicker*", "Ooh-ooh!", "*sleepy smile*", "*trumpets*",
           "Moo!", "*happy waddle*", "Hoo-hoo!"],
    "ru": ["Тяв!", "Ау-у!", "Ш-ш-ш…", "Мур!", "Гав!", "Р-р-р!", "*тук-тук лапкой*", "Чирик!", "*спокойный кивок*", "Мрр…",
           "Бе-е!", "*хрум-хрум*", "*взмах хвостом*", "*пламя вспыхивает*", "У-у-а-а!", "*сонная улыбка*", "*трубит*",
           "Му-у!", "*радостно ковыляет*", "Угу-угу!"],
    "tg": ["Вақ!", "Уууу!", "Ш-ш-ш…", "Мияу!", "Ҳав!", "Р-р-р!", "*пой мезанад*", "Чир-чир!", "*оромона сар меҷунбонад*", "Мрр…",
           "Ба-а!", "*хрум-хрум*", "*дум меҷунбонад*", "*аланга медурахшад*", "У-у-а-а!", "*табассуми хоболуд*", "*бонг мезанад*",
           "Му-у!", "*шодона қадам мезанад*", "Ку-ку!"],
    "zh": ["嘤嘤！", "嗷呜——！", "嘶嘶……", "喵～", "汪汪！", "嗷！", "（跺跺脚）", "叽叽喳喳！", "（淡定点头）", "呼噜……",
           "咩～", "（咔嚓咔嚓吃竹子）", "（甩甩尾巴）", "（火焰闪耀）", "吱吱！", "（迷迷糊糊地笑）", "（长鼻高歌）",
           "哞～", "（开心地摇摇摆摆）", "咕咕！"],
}

T = {
    "en": {
        "nav.review": "Review",
        "lessonStatus": {"not_started": "Not started", "in_progress": "In progress", "completed": "Completed"},
        "practice": {
            "title": {"vocab": "Vocabulary practice · HSK {{level}}", "hanzi": "Hanzi practice · HSK {{level}}",
                      "grammar": "Grammar practice · HSK {{level}}", "lesson": "Lesson practice", "review": "Review"},
            "retry": "Try again", "back": "Back", "loading": "Preparing your round…",
            "nothingDue": "Nothing is due right now — you're all caught up. Practice a level to add items to your review queue.",
            "score": "score", "resultLine": "{{correct}} of {{total}} correct",
            "lessonPassHint": "Score 70% or more to complete the lesson.", "toReview": "To review",
            "missedGoToReview": "These are now in your Review queue.", "again": "Practice again",
            "counter": "{{n}} / {{total}}", "playAgain": "Play again", "correct": "Correct!", "notQuite": "Not quite",
            "masteryNow": "Mastery now {{value}}%", "next": "Next", "finish": "See results",
            "startLevel": "Practice HSK {{level}}", "dueCount": "{{count}} due for review",
            "lessonDone": "Lesson complete!", "greatRound": "Great round!", "nice": "Nice!",
            "q": {"meaning_to_word": "Which word means this?", "word_to_meaning": "What does this word mean?",
                  "listen_to_word": "Listen and pick the word you hear.", "char_to_meaning": "What does this character mean?",
                  "char_to_pinyin": "How is this character pronounced?", "example_to_point": "Which grammar point does this sentence use?"},
        },
        "companionReact": {
            "fallbackName": "Your companion",
            "happy": "{{name}} is happy — that's right!",
            "excited": "{{name}} is thrilled — {{count}} in a row!",
            "proud": "{{name}} is proud of you. Solid round!",
            "celebrating": "{{name}} is celebrating — outstanding work!",
            "encouraging": "{{name}} says: not quite — look at the answer, it will stick next time.",
            "worried": "{{name}} can see this is tricky right now. Slow down — every miss goes to Review, nothing is lost.",
            "lessonComplete": "{{name}} is celebrating — lesson complete!",
            "reviewClear": "{{name}} is relaxed — your review queue is empty.",
            "context": {"vocab": "New words are sticking.", "hanzi": "These characters are becoming yours.",
                        "grammar": "That structure is clicking."},
        },
        "pages.vocabulary.tapToHear": "Tap a card to hear it.",
        "pages.vocabulary.subtitle": "Real HSK 3.0 words. Practice a level to build mastery — results feed your DNA, quests and review queue.",
        "pages.lessonDetail": {"wordsInLesson": "Words in this lesson ({{count}})", "grammarInLesson": "Grammar in this lesson ({{count}})",
                               "practiceAgain": "Practice again", "practiceToComplete": "Practice to complete",
                               "noPractice": "This lesson has no linked words or grammar to practice yet.",
                               "passHint": "The lesson is completed when you score 70% or more in its practice."},
        "pages.mistakes.reviewNow": "Review now",
        "pages.mistakes.subtitle": "Every slip is data. Mastery is earned by getting it right again — in Review, practice, voice, a case or a duel — not by a click here.",
        "pages.progress.section": {"practice": "Practice & Review", "hanzi": "Hanzi", "grammar": "Grammar"},
    },
    "ru": {
        "nav.review": "Повторение",
        "lessonStatus": {"not_started": "Не начат", "in_progress": "В процессе", "completed": "Пройден"},
        "practice": {
            "title": {"vocab": "Практика слов · HSK {{level}}", "hanzi": "Практика иероглифов · HSK {{level}}",
                      "grammar": "Практика грамматики · HSK {{level}}", "lesson": "Практика урока", "review": "Повторение"},
            "retry": "Попробовать снова", "back": "Назад", "loading": "Готовим раунд…",
            "nothingDue": "Сейчас нечего повторять — всё на месте. Попрактикуйте уровень, чтобы пополнить очередь повторения.",
            "score": "результат", "resultLine": "{{correct}} из {{total}} верно",
            "lessonPassHint": "Наберите 70% или больше, чтобы пройти урок.", "toReview": "Повторить",
            "missedGoToReview": "Они добавлены в очередь повторения.", "again": "Ещё раунд",
            "counter": "{{n}} / {{total}}", "playAgain": "Прослушать ещё", "correct": "Верно!", "notQuite": "Не совсем",
            "masteryNow": "Освоение: {{value}}%", "next": "Далее", "finish": "Результаты",
            "startLevel": "Практика HSK {{level}}", "dueCount": "К повторению: {{count}}",
            "lessonDone": "Урок пройден!", "greatRound": "Отличный раунд!", "nice": "Здорово!",
            "q": {"meaning_to_word": "Какое слово это означает?", "word_to_meaning": "Что означает это слово?",
                  "listen_to_word": "Послушайте и выберите услышанное слово.", "char_to_meaning": "Что означает этот иероглиф?",
                  "char_to_pinyin": "Как читается этот иероглиф?", "example_to_point": "Какая грамматика используется в этом предложении?"},
        },
        "companionReact": {
            "fallbackName": "Ваш компаньон",
            "happy": "{{name}} радуется — верно!",
            "excited": "{{name}} в восторге — {{count}} подряд!",
            "proud": "{{name}} гордится вами. Хороший раунд!",
            "celebrating": "{{name}} празднует — великолепно!",
            "encouraging": "{{name}}: почти — посмотрите ответ, в следующий раз запомнится.",
            "worried": "{{name}} видит, что сейчас непросто. Не спешите — каждая ошибка попадает в повторение, ничего не потеряно.",
            "lessonComplete": "{{name}} празднует — урок пройден!",
            "reviewClear": "{{name}} спокоен — очередь повторения пуста.",
            "context": {"vocab": "Новые слова запоминаются.", "hanzi": "Эти иероглифы становятся вашими.",
                        "grammar": "Конструкция начинает получаться."},
        },
        "pages.vocabulary.tapToHear": "Нажмите на карточку, чтобы услышать слово.",
        "pages.vocabulary.subtitle": "Настоящие слова HSK 3.0. Практикуйте уровень, чтобы освоить их — результаты влияют на ДНК, задания и повторение.",
        "pages.lessonDetail": {"wordsInLesson": "Слова урока ({{count}})", "grammarInLesson": "Грамматика урока ({{count}})",
                               "practiceAgain": "Практиковать снова", "practiceToComplete": "Пройти практику урока",
                               "noPractice": "У этого урока пока нет связанных слов или грамматики для практики.",
                               "passHint": "Урок засчитывается, когда вы набираете 70% или больше в его практике."},
        "pages.mistakes.reviewNow": "Повторить сейчас",
        "pages.mistakes.subtitle": "Каждая ошибка — это данные. Освоение засчитывается, когда вы снова отвечаете верно — в повторении, практике, голосом, в деле или дуэли, — а не по клику здесь.",
        "pages.progress.section": {"practice": "Практика и повторение", "hanzi": "Иероглифы", "grammar": "Грамматика"},
    },
    "tg": {
        "nav.review": "Такрор",
        "lessonStatus": {"not_started": "Оғоз нашудааст", "in_progress": "Дар ҷараён", "completed": "Анҷом ёфт"},
        "practice": {
            "title": {"vocab": "Машқи калимаҳо · HSK {{level}}", "hanzi": "Машқи иероглифҳо · HSK {{level}}",
                      "grammar": "Машқи грамматика · HSK {{level}}", "lesson": "Машқи дарс", "review": "Такрор"},
            "retry": "Боз кӯшиш кунед", "back": "Бозгашт", "loading": "Давр омода мешавад…",
            "nothingDue": "Ҳоло чизе барои такрор нест — ҳама чиз дар ҷояш. Барои пур кардани навбати такрор як сатҳро машқ кунед.",
            "score": "натиҷа", "resultLine": "{{correct}} аз {{total}} дуруст",
            "lessonPassHint": "Барои анҷом додани дарс 70% ё зиёдтар гиред.", "toReview": "Барои такрор",
            "missedGoToReview": "Инҳо ба навбати такрор илова шуданд.", "again": "Боз машқ",
            "counter": "{{n}} / {{total}}", "playAgain": "Боз гӯш кардан", "correct": "Дуруст!", "notQuite": "На он қадар",
            "masteryNow": "Азхудкунӣ: {{value}}%", "next": "Минбаъда", "finish": "Натиҷаҳо",
            "startLevel": "Машқи HSK {{level}}", "dueCount": "Барои такрор: {{count}}",
            "lessonDone": "Дарс анҷом ёфт!", "greatRound": "Даври олӣ!", "nice": "Офарин!",
            "q": {"meaning_to_word": "Кадом калима ин маъноро дорад?", "word_to_meaning": "Ин калима чӣ маъно дорад?",
                  "listen_to_word": "Гӯш кунед ва калимаи шунидаро интихоб кунед.", "char_to_meaning": "Ин иероглиф чӣ маъно дорад?",
                  "char_to_pinyin": "Ин иероглиф чӣ тавр хонда мешавад?", "example_to_point": "Дар ин ҷумла кадом қоидаи грамматикӣ истифода шудааст?"},
        },
        "companionReact": {
            "fallbackName": "Ҳамроҳи шумо",
            "happy": "{{name}} шод аст — дуруст!",
            "excited": "{{name}} хеле хурсанд аст — {{count}} пай дар пай!",
            "proud": "{{name}} аз шумо фахр мекунад. Даври хуб!",
            "celebrating": "{{name}} ҷашн мегирад — кори олӣ!",
            "encouraging": "{{name}}: қариб — ҷавобро бинед, дафъаи дигар дар ёд мемонад.",
            "worried": "{{name}} мебинад, ки ҳоло душвор аст. Шитоб накунед — ҳар хато ба такрор меравад, ҳеҷ чиз гум намешавад.",
            "lessonComplete": "{{name}} ҷашн мегирад — дарс анҷом ёфт!",
            "reviewClear": "{{name}} ором аст — навбати такрор холӣ аст.",
            "context": {"vocab": "Калимаҳои нав дар ёд мемонанд.", "hanzi": "Ин иероглифҳо аз они шумо мешаванд.",
                        "grammar": "Ин сохтор фаҳмо шуда истодааст."},
        },
        "pages.vocabulary.tapToHear": "Барои шунидан ба корт пахш кунед.",
        "pages.vocabulary.subtitle": "Калимаҳои воқеии HSK 3.0. Барои азхудкунӣ сатҳро машқ кунед — натиҷаҳо ба ДНК, супоришҳо ва такрор таъсир мерасонанд.",
        "pages.lessonDetail": {"wordsInLesson": "Калимаҳои дарс ({{count}})", "grammarInLesson": "Грамматикаи дарс ({{count}})",
                               "practiceAgain": "Боз машқ кардан", "practiceToComplete": "Машқи дарсро гузаронед",
                               "noPractice": "Ин дарс ҳоло калима ё грамматикаи алоқаманд барои машқ надорад.",
                               "passHint": "Дарс вақте анҷом меёбад, ки дар машқи он 70% ё зиёдтар гиред."},
        "pages.mistakes.reviewNow": "Ҳозир такрор кунед",
        "pages.mistakes.subtitle": "Ҳар хато маълумот аст. Азхудкунӣ вақте ҳисоб мешавад, ки шумо боз дуруст ҷавоб диҳед — дар такрор, машқ, бо овоз, дар парванда ё дуэл — на бо пахш кардан дар ин ҷо.",
        "pages.progress.section": {"practice": "Машқ ва такрор", "hanzi": "Иероглифҳо", "grammar": "Грамматика"},
    },
    "zh": {
        "nav.review": "复习",
        "lessonStatus": {"not_started": "未开始", "in_progress": "进行中", "completed": "已完成"},
        "practice": {
            "title": {"vocab": "词汇练习 · HSK {{level}}", "hanzi": "汉字练习 · HSK {{level}}",
                      "grammar": "语法练习 · HSK {{level}}", "lesson": "课程练习", "review": "复习"},
            "retry": "再试一次", "back": "返回", "loading": "正在准备练习…",
            "nothingDue": "现在没有需要复习的内容——全部完成了。练习一个级别，就会把新内容加入复习队列。",
            "score": "得分", "resultLine": "答对 {{correct}} / {{total}}",
            "lessonPassHint": "得分达到 70% 及以上即可完成本课。", "toReview": "需要复习",
            "missedGoToReview": "这些已加入你的复习队列。", "again": "再练一轮",
            "counter": "{{n}} / {{total}}", "playAgain": "再听一遍", "correct": "答对了！", "notQuite": "不太对",
            "masteryNow": "当前掌握度 {{value}}%", "next": "下一题", "finish": "查看结果",
            "startLevel": "练习 HSK {{level}}", "dueCount": "待复习 {{count}} 项",
            "lessonDone": "课程完成！", "greatRound": "这一轮很棒！", "nice": "太好了！",
            "q": {"meaning_to_word": "哪个词是这个意思？", "word_to_meaning": "这个词是什么意思？",
                  "listen_to_word": "听一听，选出你听到的词。", "char_to_meaning": "这个汉字是什么意思？",
                  "char_to_pinyin": "这个汉字怎么读？", "example_to_point": "这个句子用了哪个语法点？"},
        },
        "companionReact": {
            "fallbackName": "你的伙伴",
            "happy": "{{name}}很开心——答对了！",
            "excited": "{{name}}太兴奋了——连续答对 {{count}} 题！",
            "proud": "{{name}}为你骄傲。这一轮很扎实！",
            "celebrating": "{{name}}在庆祝——太出色了！",
            "encouraging": "{{name}}说：差一点——看看答案，下次就记住了。",
            "worried": "{{name}}发现现在有点难。慢慢来——每个错误都会进入复习，什么都不会丢。",
            "lessonComplete": "{{name}}在庆祝——课程完成！",
            "reviewClear": "{{name}}很放松——复习队列是空的。",
            "context": {"vocab": "新词记住了。", "hanzi": "这些汉字正在变成你的。", "grammar": "这个结构越来越顺了。"},
        },
        "pages.vocabulary.tapToHear": "点一下卡片就能听发音。",
        "pages.vocabulary.subtitle": "真实的 HSK 3.0 词汇。练习一个级别来提高掌握度——结果会计入你的 DNA、任务和复习队列。",
        "pages.lessonDetail": {"wordsInLesson": "本课词语（{{count}}）", "grammarInLesson": "本课语法（{{count}}）",
                               "practiceAgain": "再练一次", "practiceToComplete": "通过练习完成本课",
                               "noPractice": "本课暂时没有可练习的词语或语法。",
                               "passHint": "在本课练习中得分达到 70% 及以上即完成本课。"},
        "pages.mistakes.reviewNow": "立即复习",
        "pages.mistakes.subtitle": "每个错误都是数据。只有再次答对——在复习、练习、口语、案件或对战中——才算掌握，而不是在这里点一下。",
        "pages.progress.section": {"practice": "练习与复习", "hanzi": "汉字", "grammar": "语法"},
    },
}


def set_path(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    if isinstance(value, dict) and isinstance(d.get(parts[-1]), dict):
        merge(d[parts[-1]], value)
    else:
        d[parts[-1]] = value


def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            merge(dst[k], v)
        else:
            dst[k] = v


for loc, entries in T.items():
    path = os.path.join(LOCALES, f"{loc}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for key, value in entries.items():
        set_path(data, key, value)
    set_path(data, "companionReact.voice", dict(zip(SLUGS, VOICES[loc])))
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"updated {loc}.json")
