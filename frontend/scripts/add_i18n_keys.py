import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_locales import merge

ENTRIES = {}

# ---------------- LessonDetail ----------------
ENTRIES.update({
    "pages.lessonDetail.allLessons": {"en": "All lessons", "ru": "Все уроки", "tg": "Ҳамаи дарсҳо", "zh": "所有课程"},
    "pages.lessonDetail.saved": {"en": "Saved — DNA updated.", "ru": "Сохранено — ДНК обновлена.", "tg": "Захира шуд — ДНК навсозӣ шуд.", "zh": "已保存——DNA已更新。"},
    "pages.lessonDetail.markComplete": {"en": "Mark complete", "ru": "Отметить завершённым", "tg": "Ҳамчун анҷомёфта қайд кун", "zh": "标记为已完成"},
    "pages.lessonDetail.keepPracticing": {"en": "Keep practicing", "ru": "Продолжить практику", "tg": "Машқро идома деҳ", "zh": "继续练习"},
    "pages.lessonDetail.tryInWorld": {"en": "Try it in the world", "ru": "Попробовать в Мире", "tg": "Дар Ҷаҳон санҷед", "zh": "在世界中尝试"},
})

# ---------------- Vocabulary ----------------
ENTRIES.update({
    "pages.vocabulary.title": {"en": "Vocabulary", "ru": "Словарь", "tg": "Луғат", "zh": "词汇"},
    "pages.vocabulary.subtitle": {"en": "Tap a card to self-review. Reviews feed your DNA and daily quests.", "ru": "Нажмите на карточку для самопроверки. Повторения влияют на ДНК и ежедневные квесты.", "tg": "Барои худсанҷӣ ба корт зер кунед. Такрорҳо ба ДНК ва квестҳои рӯзона таъсир мерасонанд.", "zh": "点击卡片进行自我复习。复习会影响你的DNA和每日任务。"},
    "pages.vocabulary.dueForReview": {"en": "{{count}} word(s) due for review — surfaced first below.", "ru": "{{count}} слов(о) готовы к повторению — показаны первыми ниже.", "tg": "{{count}} калима(ҳо) барои такрор омодаанд — дар поён аввал нишон дода мешаванд.", "zh": "{{count}}个词语待复习——已置顶显示。"},
    "pages.vocabulary.due": {"en": "due", "ru": "к повтору", "tg": "барои такрор", "zh": "待复习"},
    "pages.vocabulary.empty": {"en": "No words at this level yet.", "ru": "На этом уровне пока нет слов.", "tg": "Дар ин сатҳ то ҳол калима нест.", "zh": "该级别暂无词语。"},
})

# ---------------- LocationDetail ----------------
ENTRIES.update({
    "pages.locationDetail.entering": {"en": "Entering…", "ru": "Вход…", "tg": "Дохилшавӣ…", "zh": "正在进入…"},
    "pages.locationDetail.worldMap": {"en": "World map", "ru": "Карта мира", "tg": "Харитаи ҷаҳон", "zh": "世界地图"},
    "pages.locationDetail.almostThere": {"en": "Almost there — keep training to unlock this place.", "ru": "Почти готово — продолжайте тренироваться, чтобы открыть это место.", "tg": "Қариб расидед — барои кушодани ин макон машқро идома диҳед.", "zh": "就快到了——继续练习即可解锁此地。"},
    "pages.locationDetail.stillLocked": {"en": "This place is still locked. Keep leveling up to reach it.", "ru": "Это место всё ещё заблокировано. Продолжайте повышать уровень, чтобы добраться сюда.", "tg": "Ин макон то ҳол қулф аст. Барои расидан ба он сатҳи худро баланд бардоред.", "zh": "此地尚未解锁。继续升级才能到达这里。"},
    "pages.locationDetail.peopleHere": {"en": "People here", "ru": "Люди здесь", "tg": "Одамони ин ҷо", "zh": "这里的人物"},
    "pages.locationDetail.conversations": {"en": "Conversations", "ru": "Разговоры", "tg": "Сӯҳбатҳо", "zh": "对话"},
    "pages.locationDetail.solveCase": {"en": "Solve case", "ru": "Раскрыть дело", "tg": "Парвандаро ҳал кун", "zh": "破解案件"},
    "pages.locationDetail.talk": {"en": "Talk", "ru": "Говорить", "tg": "Гуфтугӯ", "zh": "对话"},
    "pages.locationDetail.usesVoice": {"en": "This conversation uses voice.", "ru": "В этом разговоре используется голос.", "tg": "Ин сӯҳбат овозро истифода мебарад.", "zh": "此对话需要使用语音。"},
})

# ---------------- Conversation ----------------
ENTRIES.update({
    "pages.conversation.entering": {"en": "Entering conversation…", "ru": "Вход в разговор…", "tg": "Ворид шудан ба сӯҳбат…", "zh": "正在进入对话…"},
    "pages.conversation.leaveCase": {"en": "Leave the case", "ru": "Покинуть дело", "tg": "Парвандаро тарк кардан", "zh": "离开案件"},
    "pages.conversation.leaveConversation": {"en": "Leave the conversation", "ru": "Покинуть разговор", "tg": "Сӯҳбатро тарк кардан", "zh": "离开对话"},
    "pages.conversation.completed": {"en": "You made it through the whole conversation. That counts toward your DNA.", "ru": "Вы прошли весь разговор целиком. Это засчитывается в вашу ДНК.", "tg": "Шумо тамоми сӯҳбатро анҷом додед. Ин ба ДНК-и шумо ҳисоб мешавад.", "zh": "你完成了整段对话，这会计入你的DNA。"},
    "pages.conversation.backToWorld": {"en": "Back to the world", "ru": "Вернуться в Мир", "tg": "Бозгашт ба Ҷаҳон", "zh": "返回世界"},
    "pages.conversation.whatDoYouSay": {"en": "What do you say?", "ru": "Что вы скажете?", "tg": "Шумо чӣ мегӯед?", "zh": "你会怎么说？"},
    "pages.conversation.micPlaceholder": {"en": "Tap the mic and speak, or type what you would say in Chinese…", "ru": "Нажмите на микрофон и говорите, или введите текст на китайском…", "tg": "Микрофонро зер карда гап занед ё бо забони чинӣ навишта диҳед…", "zh": "点击麦克风说话，或输入你想说的中文…"},
    "pages.conversation.checking": {"en": "Checking…", "ru": "Проверка…", "tg": "Тафтиш шуда истодааст…", "zh": "检查中…"},
    "pages.conversation.speak": {"en": "Speak", "ru": "Говорить", "tg": "Гап задан", "zh": "开口说"},
    "pages.conversation.skipForNow": {"en": "Skip for now", "ru": "Пропустить пока", "tg": "Ҳоло гузаред", "zh": "暂时跳过"},
    "pages.conversation.hint": {"en": "hint", "ru": "подсказка", "tg": "ишора", "zh": "提示"},
})

# ---------------- CaseSolve ----------------
ENTRIES.update({
    "pages.caseSolve.opening": {"en": "Opening the file…", "ru": "Открытие дела…", "tg": "Кушодани парванда…", "zh": "正在打开卷宗…"},
    "pages.caseSolve.caseFile": {"en": "Case file", "ru": "Материалы дела", "tg": "Парванда", "zh": "案件档案"},
    "pages.caseSolve.clues": {"en": "Clues", "ru": "Улики", "tg": "Далелҳо", "zh": "线索"},
    "pages.caseSolve.contradiction": {"en": "Contradiction", "ru": "Противоречие", "tg": "Зиддият", "zh": "矛盾之处"},
    "pages.caseSolve.witnessStatements": {"en": "Witness statements", "ru": "Показания свидетелей", "tg": "Гувоҳиҳо", "zh": "证人陈述"},
    "pages.caseSolve.noStatements": {"en": "No statements recorded.", "ru": "Показания не записаны.", "tg": "Ягон гувоҳӣ сабт нашудааст.", "zh": "暂无记录的陈述。"},
    "pages.caseSolve.yourVerdict": {"en": "Your verdict", "ru": "Ваш вердикт", "tg": "Хулосаи шумо", "zh": "你的裁定"},
    "pages.caseSolve.verdictPrompt": {"en": "Who is responsible, and why? Write your answer in Chinese.", "ru": "Кто виноват и почему? Напишите ответ на китайском.", "tg": "Кӣ гунаҳкор аст ва чаро? Ҷавобатонро бо забони чинӣ нависед.", "zh": "谁该负责，为什么？请用中文写出你的答案。"},
    "pages.caseSolve.checking": {"en": "Checking…", "ru": "Проверка…", "tg": "Тафтиш шуда истодааст…", "zh": "检查中…"},
    "pages.caseSolve.submitVerdict": {"en": "Submit verdict", "ru": "Отправить вердикт", "tg": "Хулосаро пешниҳод кун", "zh": "提交裁定"},
    "pages.caseSolve.caseSolved": {"en": "CASE SOLVED", "ru": "ДЕЛО РАСКРЫТО", "tg": "ПАРВАНДА ҲАЛ ШУД", "zh": "案件已破解"},
    "pages.caseSolve.notQuiteRight": {"en": "Not quite right", "ru": "Не совсем верно", "tg": "На комилан дуруст", "zh": "还不太对"},
    "pages.caseSolve.hint": {"en": "Hint", "ru": "Подсказка", "tg": "Ишора", "zh": "提示"},
})

# ---------------- common xp/coins ----------------
ENTRIES.update({
    "common.xp": {"en": "xp", "ru": "оп.", "tg": "XP", "zh": "经验"},
    "common.coins": {"en": "coins", "ru": "монет", "tg": "танга", "zh": "金币"},
})

# ---------------- Missions ----------------
ENTRIES.update({
    "pages.missions.loading": {"en": "Gathering missions…", "ru": "Сбор миссий…", "tg": "Ҷамъоварии вазифаҳо…", "zh": "正在收集任务…"},
    "pages.missions.title": {"en": "Missions", "ru": "Миссии", "tg": "Вазифаҳо", "zh": "使命"},
    "pages.missions.subtitle": {"en": "Real objectives across the world — speaking, listening, cases, duels and more. Progress updates automatically as you play; rewards land the moment you finish.", "ru": "Настоящие задачи по всему миру — говорение, аудирование, дела, дуэли и многое другое. Прогресс обновляется автоматически по ходу игры; награды начисляются сразу по завершении.", "tg": "Ҳадафҳои воқеӣ дар саросари ҷаҳон — гуфтор, шунавоӣ, парвандаҳо, дуэлҳо ва дигар. Пешрафт худкор навсозӣ мешавад; мукофотҳо дарҳол баъд аз анҷом дода мешаванд.", "zh": "遍布世界的真实目标——口语、听力、案件、对决等等。进度会在你游戏过程中自动更新；完成的瞬间即可获得奖励。"},
    "pages.missions.accept": {"en": "Accept mission", "ru": "Принять миссию", "tg": "Вазифаро қабул кун", "zh": "接受任务"},
    "pages.missions.completed": {"en": "Completed", "ru": "Завершено", "tg": "Анҷомёфта", "zh": "已完成"},
    "pages.missions.empty": {"en": "No missions yet.", "ru": "Пока нет миссий.", "tg": "То ҳол вазифае нест.", "zh": "暂无任务。"},
})

# ---------------- Quests ----------------
ENTRIES.update({
    "pages.quests.title": {"en": "Daily quests", "ru": "Ежедневные квесты", "tg": "Квестҳои рӯзона", "zh": "每日任务"},
    "pages.quests.subtitle": {"en": "Generated from your DNA every day. Complete them to feed your companion.", "ru": "Создаются на основе вашей ДНК каждый день. Выполняйте их, чтобы порадовать компаньона.", "tg": "Ҳар рӯз аз рӯи ДНК-и шумо тавлид мешаванд. Барои хушнуд кардани ҳамроҳатон онҳоро иҷро кунед.", "zh": "每天根据你的DNA生成。完成它们来喂养你的伙伴。"},
    "pages.quests.claimReward": {"en": "Claim reward", "ru": "Забрать награду", "tg": "Мукофотро гир", "zh": "领取奖励"},
    "pages.quests.claimed": {"en": "Claimed", "ru": "Получено", "tg": "Гирифта шуд", "zh": "已领取"},
    "pages.quests.empty": {"en": "Nothing today. Take a walk around the world.", "ru": "Сегодня ничего нет. Прогуляйтесь по Миру.", "tg": "Имрӯз чизе нест. Дар Ҷаҳон сайре кунед.", "zh": "今天没有任务。去世界中逛逛吧。"},
})

if __name__ == "__main__":
    merge(ENTRIES)
