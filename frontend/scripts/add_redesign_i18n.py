# -*- coding: utf-8 -*-
"""Adds the strings of the product-wide page redesign (Roleplay, Tone Coach,
Mistakes, ...) into all four locale files, as new lines inside their existing
sections. Idempotent: keys already present are skipped.
Run from frontend/: python scripts/add_redesign_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    # ---- Roleplay (pages/Roleplay.jsx) ----
    "roleplay.statOpen": L("Scenes open", "Открыто сцен", "Саҳнаҳои кушода", "已开放场景"),
    "roleplay.statPlayed": L("Conversations finished", "Завершено разговоров", "Суҳбатҳои анҷомёфта", "已完成对话"),
    "roleplay.pickScene": L("Choose where to talk", "Выберите, где поговорить", "Интихоб кунед, ки дар куҷо гап мезанед", "选择对话场景"),
    "roleplay.youMeet": L("You'll talk to", "Ваш собеседник:", "Ҳамсуҳбати шумо:", "对话对象："),
    "roleplay.noRecent": L(
        "No conversations yet — pick a scene to start your first.",
        "Разговоров пока нет — выберите сцену, чтобы начать первый.",
        "Ҳоло суҳбате нест — барои оғози аввалин саҳнаеро интихоб кунед.",
        "还没有对话——选一个场景开始吧。"),
    "roleplay.goalsMet": L("{{met}}/{{total}} goals", "Целей: {{met}}/{{total}}", "Ҳадафҳо: {{met}}/{{total}}", "目标 {{met}}/{{total}}"),
    "roleplay.useSuggestion": L(
        "Put this reply in the box — you can change it before sending",
        "Вставить ответ в поле — его можно изменить перед отправкой",
        "Ин ҷавобро ба майдон гузоштан — пеш аз фиристодан тағйир додан мумкин аст",
        "把这句话放进输入框——发送前还可以修改"),
    "roleplay.hinting": L("Thinking…", "Подбираю…", "Фикр мекунам…", "正在想…"),
    # ---- Tone Coach (pages/ToneCoach.jsx) ----
    "toneCoach.stepsLabel": L("Steps", "Шаги", "Қадамҳо", "步骤"),
    "toneCoach.stepListen": L("Listen", "Послушайте", "Гӯш кунед", "听"),
    "toneCoach.stepSay": L("Say it", "Произнесите", "Талаффуз кунед", "说"),
    "toneCoach.stepCompare": L("Compare", "Сравните", "Муқоиса кунед", "对比"),
    "toneCoach.legendTarget": L("The tone's shape", "Форма тона", "Шакли оҳанг", "声调的形状"),
    "toneCoach.legendVoice": L("Your voice", "Ваш голос", "Овози шумо", "你的声音"),
    # ---- Practice / Review (pages/Practice.jsx) ----
    "practice.keysHint": L(
        "Tip: press 1–{{n}} to answer, Enter for the next question.",
        "Совет: нажмите 1–{{n}}, чтобы ответить, и Enter — к следующему вопросу.",
        "Маслиҳат: барои ҷавоб 1–{{n}}-ро пахш кунед, барои саволи навбатӣ Enter.",
        "小提示：按 1–{{n}} 作答，按 Enter 进入下一题。"),
    # ---- Vocabulary as a dictionary (pages/Vocabulary.jsx) ----
    "pages.vocabulary.kpiWords": L("Words in this level", "Слов на уровне", "Калимаҳои сатҳ", "本级词数"),
    "pages.vocabulary.kpiKnown": L("You know", "Вы знаете", "Шумо медонед", "已掌握"),
    "pages.vocabulary.searchPlaceholder": L(
        "Search: 你好, nihao or a meaning", "Поиск: 你好, nihao или значение",
        "Ҷустуҷӯ: 你好, nihao ё маъно", "搜索：汉字、拼音或释义"),
    "pages.vocabulary.searchLabel": L("Search the words of HSK {{level}}", "Поиск по словам HSK {{level}}",
                                      "Ҷустуҷӯ дар калимаҳои HSK {{level}}", "搜索 HSK {{level}} 的词语"),
    "pages.vocabulary.levelLabel": L("HSK level", "Уровень HSK", "Сатҳи HSK", "HSK 等级"),
    "pages.vocabulary.listLabel": L("Words", "Слова", "Калимаҳо", "词语"),
    "pages.vocabulary.found": L(
        {"one": "{{count}} word found", "other": "{{count}} words found"},
        {"one": "Найдено {{count}} слово", "few": "Найдено {{count}} слова", "many": "Найдено {{count}} слов", "other": "Найдено {{count}} слова"},
        {"one": "{{count}} калима ёфт шуд", "other": "{{count}} калима ёфт шуд"},
        {"other": "找到 {{count}} 个词"}),
    "pages.vocabulary.noMatch": L(
        "Nothing at this level matches. Try another spelling or another HSK level.",
        "На этом уровне ничего не найдено. Попробуйте другое написание или другой уровень HSK.",
        "Дар ин сатҳ чизе ёфт нашуд. Навишти дигар ё сатҳи дигари HSK-ро санҷед.",
        "本级没有匹配的词。换个写法或换个 HSK 等级试试。"),
    "pages.vocabulary.traditional": L("Traditional", "Традиционное", "Анъанавӣ", "繁体"),
    "pages.vocabulary.example": L("In a sentence", "В предложении", "Дар ҷумла", "例句"),
    "pages.vocabulary.characters": L("Written with", "Пишется иероглифами", "Бо иероглифҳо навишта мешавад", "组成的汉字"),
    "pages.vocabulary.openChar": L("Open the character {{char}}", "Открыть иероглиф {{char}}", "Кушодани иероглифи {{char}}", "查看汉字 {{char}}"),
    "pages.vocabulary.related": L("Words that share a character", "Слова с тем же иероглифом", "Калимаҳо бо ҳамон иероглиф", "含相同汉字的词"),
    "pages.vocabulary.yourMastery": L("Your mastery", "Ваше освоение", "Азхудкунии шумо", "你的掌握度"),
    "pages.vocabulary.st_new": L("new", "новое", "нав", "未学"),
    "pages.vocabulary.st_learning": L("learning", "изучается", "дар омӯзиш", "学习中"),
    "pages.vocabulary.st_reviewing": L("reviewing", "на повторении", "дар такрор", "复习中"),
    "pages.vocabulary.st_mastered": L("mastered", "освоено", "азхудшуда", "已掌握"),
    "pages.vocabulary.st_due": L("due", "пора повторить", "вақти такрор", "待复习"),
    "pages.vocabulary.st_slipping": L("slipping", "забывается", "фаромӯш мешавад", "快忘了"),
    # ---- One Sentence (pages/SentenceLesson.jsx) ----
    "sentenceLesson.readTitle": L(
        "Read it — tap a word", "Прочитайте — нажмите на слово", "Хонед — ба калима пахш кунед", "读一读——点击词语"),
    "sentenceLesson.legend": L(
        "What the underline under a word means", "Что значит подчёркивание под словом",
        "Хати зери калима чӣ маъно дорад", "词语下划线的含义"),
    # ---- Detective case file (pages/DetectiveFile.jsx) ----
    "detective.culpritStamp": L("Culprit", "Виновник", "Гунаҳкор", "真凶"),
    "detective.filePin": L("Pin to your notes", "Закрепить в заметках", "Ба қайдҳо часпондан", "钉到笔记"),
    "detective.fileUnpin": L("Remove from your notes", "Убрать из заметок", "Аз қайдҳо гирифтан", "从笔记移除"),
    "detective.exhibit": L("Exhibit {{n}}", "Улика {{n}}", "Далели {{n}}", "证物 {{n}}"),
    "detective.notesTitle": L("Your notes", "Ваши заметки", "Қайдҳои шумо", "你的笔记"),
    "detective.notesEmpty": L(
        "Pin the statements, evidence and times that don't add up — they gather here while you read.",
        "Закрепляйте показания, улики и время, которые не сходятся, — они соберутся здесь, пока вы читаете.",
        "Шаҳодатҳо, далелҳо ва вақтҳоеро, ки мувофиқ намеоянд, часпонед — ҳангоми хондан онҳо дар ин ҷо ҷамъ мешаванд.",
        "把说不通的证词、证物和时间钉起来——阅读时它们会汇集在这里。"),
    "detective.notesNote": L(
        "Kept in this browser for this case only. The case is solved in the round.",
        "Хранятся только в этом браузере и только для этого дела. Дело раскрывается в раунде.",
        "Танҳо дар ҳамин браузер ва барои ҳамин парванда нигоҳ дошта мешаванд. Парванда дар давр кушода мешавад.",
        "只保存在这个浏览器里，仅限本案。破案要在练习回合中完成。"),
    # ---- Sound World (pages/SoundWorld.jsx) ----
    "soundWorld.enter": L("Listen · {{stage}}", "Слушать · {{stage}}", "Гӯш кардан · {{stage}}", "进去听 · {{stage}}"),
    # ---- Foundation: sounds and tones (pages/Foundation.jsx) ----
    "foundation.earTitle": L("Test your ear", "Проверьте слух", "Гӯши худро санҷед", "听力小测"),
    "foundation.earBody": L(
        "Play one of the pair and pick the one you heard. A warm-up: nothing here is graded or saved.",
        "Включите одно слово из пары и выберите, какое услышали. Это разминка: здесь ничего не оценивается и не сохраняется.",
        "Яке аз ҷуфтро гӯш кунед ва он чиро, ки шунидед, интихоб кунед. Ин гармкунӣ аст: дар ин ҷо чизе баҳо дода ва сабт намешавад.",
        "播放一对中的一个，选出你听到的那个。这只是热身：这里不评分，也不保存。"),
    "foundation.earPlay": L("Play one", "Включить", "Пахш кардан", "播放一个"),
    "foundation.earAgain": L("Another one", "Ещё раз", "Боз як бор", "再来一个"),
    "foundation.earWhich": L("Which did you hear?", "Что вы услышали?", "Чиро шунидед?", "你听到的是哪个？"),
    "foundation.earRight": L("Right!", "Верно!", "Дуруст!", "对了！"),
    "foundation.earWrong": L("It was {{zh}}", "Это было {{zh}}", "Ин {{zh}} буд", "是 {{zh}}"),
    # ---- Chinese Internet (pages/ChineseInternet.jsx) ----
    "internet.kindsLabel": L("Show one kind of page", "Показать один вид страниц", "Нишон додани як навъи саҳифа", "按页面类型查看"),
    # ---- Characters (pages/Hanzi.jsx, HanziTrace.jsx) ----
    "pages.hanzi.kpiChars": L("Characters in this level", "Иероглифов на уровне", "Иероглифҳои сатҳ", "本级汉字"),
    "pages.hanzi.searchPlaceholder": L("Search: 好, hao or a meaning", "Поиск: 好, hao или значение",
                                       "Ҷустуҷӯ: 好, hao ё маъно", "搜索：汉字、拼音或释义"),
    "pages.hanzi.searchLabel": L("Search the characters of HSK {{level}}", "Поиск по иероглифам HSK {{level}}",
                                 "Ҷустуҷӯ дар иероглифҳои HSK {{level}}", "搜索 HSK {{level}} 的汉字"),
    "pages.hanzi.filterLabel": L("Show", "Показать", "Нишон додан", "显示"),
    "pages.hanzi.filter_all": L("All", "Все", "Ҳама", "全部"),
    "pages.hanzi.filter_due": L("Due", "К повтору", "Барои такрор", "待复习"),
    "pages.hanzi.filter_writing": L("To write by hand", "Писать от руки", "Бо даст навиштан", "需手写"),
    "pages.hanzi.filter_new": L("Not started", "Не начаты", "Оғознашуда", "未开始"),
    "pages.hanzi.shownCount": L("{{count}} of {{total}}", "{{count}} из {{total}}", "{{count}} аз {{total}}", "{{count}} / {{total}}"),
    "pages.hanzi.pickOne": L(
        "Pick a character to hear it, check yourself, see its words and practise writing it.",
        "Выберите иероглиф, чтобы услышать его, проверить себя, увидеть слова с ним и потренироваться писать.",
        "Иероглиферо интихоб кунед, то онро шунавед, худро санҷед, калимаҳоро бинед ва навиштанро машқ кунед.",
        "选一个汉字：听读音、自我检测、看词语、练习书写。"),
    "pages.hanzi.step_watch": L("Watch", "Смотрите", "Тамошо кунед", "看"),
    "pages.hanzi.step_write": L("Write", "Пишите", "Нависед", "写"),
    "pages.hanzi.step_save": L("Save", "Сохраните", "Сабт кунед", "保存"),
    "pages.hanzi.strokesDone": L("{{done}} of {{total}} strokes", "Черт: {{done}} из {{total}}", "Хат: {{done}} аз {{total}}", "笔画 {{done}} / {{total}}"),
    # ---- Lesson (pages/LessonDetail.jsx) ----
    "pages.lessonDetail.level": L("Level", "Уровень", "Сатҳ", "等级"),
    "pages.lessonDetail.stepLearn": L("Learn", "Изучите", "Омӯзед", "学习"),
    "pages.lessonDetail.stepPractise": L("Practise to complete the lesson", "Практика, чтобы пройти урок",
                                         "Машқ барои анҷоми дарс", "练习以完成本课"),
    "pages.lessonDetail.yourLesson": L("This lesson", "Этот урок", "Ин дарс", "本课"),
    # ---- Daily quests (pages/Quests.jsx) ----
    "pages.quests.kpiDone": L("Done today", "Выполнено сегодня", "Имрӯз иҷрошуда", "今日完成"),
    "pages.quests.kpiXp": L("XP claimed", "Получено XP", "XP гирифта шуд", "已领取 XP"),
    "pages.quests.goDo": L("Go", "Перейти", "Гузаштан", "去完成"),
    "pages.quests.howNote": L(
        "Quests move forward by themselves as you study — there is nothing to tick off here. Claim the reward once one is complete.",
        "Задания продвигаются сами, пока вы учитесь, — отмечать здесь ничего не нужно. Заберите награду, когда задание выполнено.",
        "Вазифаҳо ҳангоми омӯзиш худ ба худ пеш мераванд — дар ин ҷо чизе қайд кардан лозим нест. Вақте вазифа иҷро шуд, мукофотро гиред.",
        "任务会随着你的学习自动推进——这里不需要手动勾选。完成后领取奖励即可。"),
    # ---- Missions (pages/Missions.jsx) ----
    "pages.missions.inProgress": L("Under way", "В процессе", "Дар ҷараён", "进行中"),
    "pages.missions.available": L("Ready to take on", "Можно взять", "Метавон гирифт", "可接受"),
    "pages.missions.lockedTitle": L("At a higher level", "На следующих уровнях", "Дар сатҳҳои баландтар", "更高等级"),
    "pages.missions.noneDone": L("Nothing finished yet.", "Пока ничего не завершено.", "Ҳоло чизе анҷом наёфтааст.", "还没有完成的任务。"),
    "pages.missions.howTitle": L("How missions work", "Как работают миссии", "Миссияҳо чӣ тавр кор мекунанд", "任务怎么进行"),
    "pages.missions.howText": L(
        "Accept a mission, then do the real activity it names. Progress is counted automatically and the reward arrives the moment you finish.",
        "Возьмите миссию и выполните настоящее занятие, о котором она говорит. Прогресс засчитывается сам, награда приходит сразу по завершении.",
        "Миссияро қабул кунед ва машғулияти воқеии номбаршударо иҷро кунед. Пешрафт худкор ҳисоб мешавад ва мукофот фавран меояд.",
        "接受任务后，去完成它所说的真实练习。进度会自动计算，完成时立即获得奖励。"),
    # ---- Daily Voice Companion (pages/VoiceCompanion.jsx) ----
    # What the previewed animal says in its own voice -- spoken Chinese, the
    # same in every locale.
    "voice.sampleLine": L("你好！我们一起说中文吧。", "你好！我们一起说中文吧。", "你好！我们一起说中文吧。", "你好！我们一起说中文吧。"),
    "voice.hearVoice": L("Hear the voice", "Послушать голос", "Овозро шунавед", "听听声音"),
    "voice.sessionOnly": L(
        "Only for today's conversation — your own companion stays the same.",
        "Только для сегодняшнего разговора — ваш компаньон не меняется.",
        "Танҳо барои суҳбати имрӯза — ҳамроҳи шумо иваз намешавад.",
        "只用于今天的对话——你的伙伴不会改变。"),
    # ---- Teach your companion (pages/PetTeacher.jsx) ----
    "pages.petTeacher.boardLabel": L("{{name}} wrote on the board", "{{name}} написал(а) на доске",
                                     "{{name}} дар тахта навишт", "{{name}} 在黑板上写道"),
    "pages.petTeacher.yourLesson": L("Your lesson", "Ваш урок", "Дарси шумо", "你的讲解"),
    # ---- Achievements cabinet (pages/Achievements.jsx) ----
    "achievements.page.cabinet": L("Your achievements", "Ваши достижения", "Дастовардҳои шумо", "你的成就"),
    # ---- Companion (pages/Companion.jsx) ----
    "pages.companion.tryPhrase": L("Phrases to try", "Фразы, чтобы попробовать", "Ибораҳо барои озмоиш", "可以试试的句子"),
    # ---- Duels lobby (pages/Duels.jsx) ----
    "pages.duels.kpiWins": L("Wins", "Победы", "Ғалабаҳо", "胜"),
    "pages.duels.kpiLosses": L("Losses", "Поражения", "Шикастҳо", "负"),
    "pages.duels.kpiDraws": L("Draws", "Ничьи", "Мусовӣ", "平"),
    # ---- Real Chinese conversation (pages/Conversation.jsx) ----
    "pages.conversation.speakerNpc": L("Local", "Собеседник", "Ҳамсуҳбат", "对方"),
    "pages.conversation.speakerYou": L("You", "Вы", "Шумо", "你"),
    # ---- Community (pages/Community.jsx) ----
    "pages.community.youFollow": L("People you follow", "Вы подписаны", "Шумо обуна шудаед", "你关注的人"),
    "pages.community.followNone": L(
        "You don't follow anyone yet — search for a learner above.",
        "Вы пока ни на кого не подписаны — найдите ученика через поиск выше.",
        "Шумо ҳоло ба касе обуна нашудаед — хонандаро тавассути ҷустуҷӯи боло ёбед.",
        "你还没有关注任何人——在上方搜索学习者吧。"),
    "pages.community.followYou": L("Who follows you", "Ваши подписчики", "Обуначиёни шумо", "关注你的人"),
    "pages.community.followersNone": L("No followers yet.", "Подписчиков пока нет.", "Ҳоло обуначӣ нест.", "还没有人关注你。"),
    "pages.community.myPublicPage": L("My public page", "Моя публичная страница", "Саҳифаи ҷамъиятии ман", "我的公开主页"),
    # ---- Mistake notebook (pages/Mistakes.jsx) ----
    "pages.mistakes.listen": L("Listen", "Прослушать", "Гӯш кардан", "听"),
    "pages.mistakes.missedTimes": L(
        {"one": "Missed {{count}} time", "other": "Missed {{count}} times"},
        {"one": "Ошибка {{count}} раз", "few": "Ошибка {{count}} раза", "many": "Ошибка {{count}} раз", "other": "Ошибка {{count}} раза"},
        {"one": "{{count}} бор хато", "other": "{{count}} бор хато"},
        {"other": "错了 {{count}} 次"}),
    "pages.mistakes.tabAll": L("All", "Все", "Ҳама", "全部"),
    "pages.mistakes.filterLabel": L("Show mistakes of one kind", "Показать ошибки одного вида", "Нишон додани хатоҳои як навъ", "按类型查看"),
    "pages.mistakes.focusStart": L("Test yourself", "Проверить себя", "Худро санҷед", "自我检测"),
    "pages.mistakes.focusTitle": L("Test yourself", "Проверьте себя", "Худро санҷед", "自我检测"),
    "pages.mistakes.focusCount": L("{{n}} of {{total}}", "{{n}} из {{total}}", "{{n}} аз {{total}}", "第 {{n}} / {{total}} 个"),
    "pages.mistakes.focusPrompt": L(
        "Say or write the answer to yourself, then check.",
        "Ответьте про себя или запишите, затем проверьте.",
        "Ҷавобро дар дил гӯед ё нависед, баъд санҷед.",
        "先自己说出或写出答案，再看答案。"),
    "pages.mistakes.reveal": L("Show the answer", "Показать ответ", "Ҷавобро нишон диҳед", "显示答案"),
    "pages.mistakes.lastTime": L("Last time you answered", "В прошлый раз вы ответили", "Дафъаи гузашта шумо ҷавоб додед", "上次你的回答"),
    "pages.mistakes.focusNext": L("Next", "Дальше", "Минбаъда", "下一个"),
    "pages.mistakes.focusClose": L("Back to the notebook", "Вернуться к тетради", "Бозгашт ба дафтар", "返回错题本"),
    "pages.mistakes.focusDone": L(
        "That's all of them. Now earn them back where it counts — in Review.",
        "Это все. Теперь закрепите их там, где это засчитывается, — в повторении.",
        "Ҳамааш ҳамин. Акнун онҳоро дар ҷое баргардонед, ки ҳисоб мешавад — дар такрор.",
        "全部看完了。现在去复习里真正把它们赢回来吧。"),
    "pages.mistakes.focusNote": L(
        "A self-check: nothing here is saved. A mistake is cleared only by answering it correctly in practice.",
        "Это самопроверка: здесь ничего не сохраняется. Ошибка исчезает, только когда вы правильно ответите в практике.",
        "Ин худсанҷӣ аст: дар ин ҷо чизе сабт намешавад. Хато танҳо вақте пок мешавад, ки шумо дар машқ дуруст ҷавоб диҳед.",
        "这是自我检测：这里不保存任何结果。只有在练习中答对，错题才会被清除。"),
    "pages.mistakes.progressTitle": L("Earned back", "Исправлено", "Ислоҳшуда", "已攻克"),
    "pages.mistakes.progressLine": L(
        "Mistakes and mix-ups you have since answered right in practice.",
        "Ошибки и путаницы, на которые вы с тех пор правильно ответили в практике.",
        "Хатоҳо ва омехтагиҳое, ки шумо баъдан дар машқ дуруст ҷавоб додед.",
        "之后在练习中答对了的错题和易混词。"),
}
KEYS = list(S)

if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        text = "\r\n".join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
