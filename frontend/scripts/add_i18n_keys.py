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

# ---------------- Roadmap (HSK) ----------------
ENTRIES.update({
    "pages.roadmap.loading": {"en": "Loading roadmap…", "ru": "Загрузка плана…", "tg": "Боркунии нақша…", "zh": "正在加载计划…"},
    "pages.roadmap.title": {"en": "HSK roadmap", "ru": "План HSK", "tg": "Нақшаи HSK", "zh": "HSK 计划"},
    "pages.roadmap.overall": {"en": "Overall", "ru": "Всего", "tg": "Умумӣ", "zh": "总体"},
    "pages.roadmap.locked": {"en": "locked", "ru": "заблокировано", "tg": "қулф", "zh": "已锁定"},
    "pages.roadmap.current": {"en": "current", "ru": "текущий", "tg": "ҷорӣ", "zh": "当前"},
    "pages.roadmap.unlocked": {"en": "unlocked", "ru": "открыто", "tg": "кушода", "zh": "已解锁"},
    "pages.roadmap.words": {"en": "words", "ru": "слов", "tg": "калима", "zh": "词"},
    "pages.roadmap.mastery": {"en": "Mastery", "ru": "Освоение", "tg": "Азхудкунӣ", "zh": "掌握度"},
    "pages.roadmap.lessons": {"en": "Lessons", "ru": "Уроки", "tg": "Дарсҳо", "zh": "课程"},
    "pages.roadmap.readyForNext": {"en": "Ready for HSK {{level}}", "ru": "Готово к HSK {{level}}", "tg": "Омода барои HSK {{level}}", "zh": "已可进入 HSK {{level}}"},
    "pages.roadmap.maxLevel": {"en": "Max level reached", "ru": "Достигнут максимальный уровень", "tg": "Сатҳи максималӣ расид", "zh": "已达最高级别"},
    "pages.roadmap.practiceVocab": {"en": "Practice vocabulary", "ru": "Практиковать словарь", "tg": "Луғатро машқ кун", "zh": "练习词汇"},
})

# ---------------- DNA ----------------
ENTRIES.update({
    "pages.dna.loading": {"en": "Sequencing your DNA…", "ru": "Секвенирование вашей ДНК…", "tg": "Пайдарпайкунии ДНК-и шумо…", "zh": "正在解析你的DNA…"},
    "pages.dna.title": {"en": "Your Learning DNA", "ru": "Ваша учебная ДНК", "tg": "ДНК-и омӯзиши шумо", "zh": "你的学习DNA"},
    "pages.dna.subtitle": {"en": "Nine strands measured from every interaction. Build the weak ones — daily quests and companions will adapt.", "ru": "Девять показателей, измеряемых по каждому взаимодействию. Развивайте слабые — ежедневные квесты и компаньоны подстроятся под вас.", "tg": "Нӯҳ нишондиҳанда аз ҳар амалиёт ҳисоб мешаванд. Заифҳоро рушд диҳед — квестҳои рӯзона ва ҳамроҳон мутобиқ мешаванд.", "zh": "根据每次互动衡量的九项指标。加强薄弱项——每日任务和伙伴会随之调整。"},
    "pages.dna.overall": {"en": "overall", "ru": "в целом", "tg": "умумӣ", "zh": "总体"},
    "pages.dna.weak": {"en": "Weak", "ru": "Слабые", "tg": "Заиф", "zh": "薄弱"},
    "pages.dna.strong": {"en": "Strong", "ru": "Сильные", "tg": "Қавӣ", "zh": "强项"},
    "pages.dna.none": {"en": "none", "ru": "нет", "tg": "нест", "zh": "无"},
    "pages.dna.status.weak": {"en": "weak", "ru": "слабо", "tg": "заиф", "zh": "薄弱"},
    "pages.dna.status.developing": {"en": "developing", "ru": "развивается", "tg": "рушдёбанда", "zh": "发展中"},
    "pages.dna.status.strong": {"en": "strong", "ru": "сильно", "tg": "қавӣ", "zh": "强"},
})

# ---------------- PetTeacher ----------------
ENTRIES.update({
    "pages.petTeacher.thinking": {"en": "Your companion is thinking of a mistake…", "ru": "Ваш компаньон придумывает ошибку…", "tg": "Ҳамроҳи шумо дар бораи хато фикр карда истодааст…", "zh": "你的伙伴正在想一个错误…"},
    "pages.petTeacher.title": {"en": "Pet Teacher Mode", "ru": "Режим «Учим питомца»", "tg": "Реҷаи 'Омӯзонидани ҳайвон'", "zh": "教宠物模式"},
    "pages.petTeacher.subtitle": {"en": "{{name}} sometimes gets Chinese wrong on purpose. Catch the mistake, fix it, and explain the rule — that's how it actually learns.", "ru": "{{name}} иногда специально ошибается в китайском. Найдите ошибку, исправьте её и объясните правило — так он и учится.", "tg": "{{name}} баъзан дар забони чинӣ қасдан хато мекунад. Хаторо пайдо кунед, ислоҳ кунед ва қоидаро шарҳ диҳед — маҳз ҳамин тавр ӯ меомӯзад.", "zh": "{{name}}有时会故意说错中文。找出错误、纠正它并解释规则——这才是它真正学习的方式。"},
    "pages.petTeacher.yourCompanion": {"en": "Your companion", "ru": "Ваш компаньон", "tg": "Ҳамроҳи шумо", "zh": "你的伙伴"},
    "pages.petTeacher.yourCorrection": {"en": "Your correction", "ru": "Ваше исправление", "tg": "Ислоҳи шумо", "zh": "你的修正"},
    "pages.petTeacher.correctionPlaceholder": {"en": "Rewrite the sentence correctly…", "ru": "Перепишите предложение правильно…", "tg": "Ҷумларо дуруст аз нав нависед…", "zh": "重新写出正确的句子…"},
    "pages.petTeacher.explainRule": {"en": "Explain the rule", "ru": "Объясните правило", "tg": "Қоидаро шарҳ диҳед", "zh": "解释规则"},
    "pages.petTeacher.explanationPlaceholder": {"en": "Why was it wrong? Tap the mic to speak your answer…", "ru": "Почему это было неправильно? Нажмите на микрофон, чтобы ответить голосом…", "tg": "Чаро он хато буд? Барои ҷавоб додан бо овоз микрофонро зер кунед…", "zh": "为什么错了？点击麦克风说出你的答案…"},
    "pages.petTeacher.checking": {"en": "Checking…", "ru": "Проверка…", "tg": "Тафтиш шуда истодааст…", "zh": "检查中…"},
    "pages.petTeacher.teachCompanion": {"en": "Teach your companion", "ru": "Научить компаньона", "tg": "Ҳамроҳро таълим диҳед", "zh": "教导你的伙伴"},
    "pages.petTeacher.correctSentence": {"en": "Correct sentence", "ru": "Правильное предложение", "tg": "Ҷумлаи дуруст", "zh": "正确的句子"},
    "pages.petTeacher.teachAnother": {"en": "Teach another rule", "ru": "Научить ещё одному правилу", "tg": "Қоидаи дигар таълим диҳед", "zh": "教另一条规则"},
    "pages.petTeacher.tryAgain": {"en": "Try again", "ru": "Попробовать снова", "tg": "Аз нав кӯшиш кунед", "zh": "再试一次"},
    "pages.petTeacher.rulesTaught": {"en": "Rules taught so far", "ru": "Правил объяснено", "tg": "Қоидаҳои таълимдодашуда", "zh": "已教授的规则数"},
})

# ---------------- Achievements gaps ----------------
ENTRIES.update({
    "pages.achievements.unlocked": {"en": "Unlocked", "ru": "Открыто", "tg": "Кушода шуд", "zh": "已解锁"},
    "pages.achievements.hidden": {"en": "hidden", "ru": "скрыто", "tg": "пинҳон", "zh": "隐藏"},
    "pages.achievements.category.world": {"en": "world", "ru": "мир", "tg": "ҷаҳон", "zh": "世界"},
    "pages.achievements.category.habit": {"en": "habit", "ru": "привычка", "tg": "одат", "zh": "习惯"},
    "pages.achievements.category.hsk": {"en": "HSK", "ru": "HSK", "tg": "HSK", "zh": "HSK"},
    "pages.achievements.category.animal": {"en": "companion", "ru": "компаньон", "tg": "ҳамроҳ", "zh": "伙伴"},
    "pages.achievements.category.voice": {"en": "voice", "ru": "голос", "tg": "овоз", "zh": "语音"},
    "pages.achievements.category.general": {"en": "general", "ru": "общее", "tg": "умумӣ", "zh": "综合"},
    "pages.achievements.category.vocabulary": {"en": "vocabulary", "ru": "словарь", "tg": "луғат", "zh": "词汇"},
    "pages.achievements.category.social": {"en": "social", "ru": "социальное", "tg": "иҷтимоӣ", "zh": "社交"},
})

# ---------------- Profile ----------------
ENTRIES.update({
    "pages.profile.joined": {"en": "joined", "ru": "с нами с", "tg": "аз", "zh": "加入于"},
    "pages.profile.findPeople": {"en": "Find people", "ru": "Найти людей", "tg": "Одамонро ёбед", "zh": "寻找好友"},
    "pages.profile.changeCompanion": {"en": "Change companion", "ru": "Сменить компаньона", "tg": "Ҳамроҳро иваз кунед", "zh": "更换伙伴"},
    "pages.profile.title": {"en": "Profile", "ru": "Профиль", "tg": "Профил", "zh": "个人资料"},
    "pages.profile.nativeLanguage": {"en": "Native language", "ru": "Родной язык", "tg": "Забони модарӣ", "zh": "母语"},
    "pages.profile.goal": {"en": "Goal", "ru": "Цель", "tg": "Мақсад", "zh": "目标"},
    "pages.profile.dailyGoal": {"en": "Daily goal", "ru": "Ежедневная цель", "tg": "Мақсади рӯзона", "zh": "每日目标"},
    "pages.profile.minPerDay": {"en": "min/day", "ru": "мин/день", "tg": "дақ/рӯз", "zh": "分钟/天"},
    "pages.profile.levelTest": {"en": "Level test", "ru": "Тест уровня", "tg": "Санҷиши сатҳ", "zh": "水平测试"},
    "pages.profile.pts": {"en": "pts", "ru": "балл.", "tg": "хол", "zh": "分"},
    "pages.profile.notTaken": {"en": "not taken", "ru": "не пройден", "tg": "гузаронида нашуд", "zh": "未参加"},
    "pages.profile.bio": {"en": "Bio", "ru": "О себе", "tg": "Дар бораи худ", "zh": "个人简介"},
    "pages.profile.editProfile": {"en": "Edit profile", "ru": "Редактировать профиль", "tg": "Профилро таҳрир кунед", "zh": "编辑资料"},
    "pages.profile.streak": {"en": "Streak", "ru": "Серия", "tg": "Силсила", "zh": "连续打卡"},
    "pages.profile.current": {"en": "current", "ru": "текущая", "tg": "ҷорӣ", "zh": "当前"},
    "pages.profile.longest": {"en": "longest", "ru": "самая долгая", "tg": "дарозтарин", "zh": "最长"},
    "pages.profile.activeDays": {"en": "active days", "ru": "активных дней", "tg": "рӯзҳои фаъол", "zh": "活跃天数"},
    "pages.profile.lastActive": {"en": "Last active", "ru": "Последняя активность", "tg": "Фаъолияти охирин", "zh": "最近活跃"},
    "pages.profile.rewardsEarned": {"en": "Rewards earned", "ru": "Полученные награды", "tg": "Мукофотҳои гирифташуда", "zh": "已获奖励"},
    "pages.profile.totalXp": {"en": "total xp", "ru": "всего оп.", "tg": "ҳамагӣ XP", "zh": "总经验"},
    "pages.profile.community": {"en": "Community", "ru": "Сообщество", "tg": "Ҷомеа", "zh": "社区"},
    "pages.profile.followers": {"en": "followers", "ru": "подписчиков", "tg": "пайравон", "zh": "粉丝"},
    "pages.profile.following": {"en": "following", "ru": "подписок", "tg": "пайравишавандагон", "zh": "关注"},
    "pages.profile.findPeopleToFollow": {"en": "Find people to follow", "ru": "Найти людей для подписки", "tg": "Барои пайравӣ одамон ёбед", "zh": "寻找可关注的人"},
})

# ---------------- Mistakes ----------------
ENTRIES.update({
    "pages.mistakes.title": {"en": "Mistakes lab", "ru": "Лаборатория ошибок", "tg": "Лабораторияи хатоҳо", "zh": "错题实验室"},
    "pages.mistakes.subtitle": {"en": "Every slip is data. Mastery is earned by getting it right again through voice, vocab review, a case, or a duel — not by a click here.", "ru": "Каждая ошибка — это данные. Освоение достигается тем, что вы снова отвечаете правильно через голос, повтор слов, дело или дуэль — а не нажатием здесь.", "tg": "Ҳар хато маълумот аст. Азхудкунӣ бо дурустона ҷавоб додан тавассути овоз, такрори калима, парванда ё дуэл ба даст меояд — на бо зер кардани ин ҷо.", "zh": "每一次失误都是数据。掌握是通过语音、词汇复习、案件或对决再次答对而获得的——不是靠点这里。"},
    "pages.mistakes.stillWorking": {"en": "Still working on", "ru": "Ещё в работе", "tg": "Ҳанӯз дар кор", "zh": "仍在攻克"},
    "pages.mistakes.youSaid": {"en": "You said", "ru": "Вы сказали", "tg": "Шумо гуфтед", "zh": "你说的是"},
    "pages.mistakes.correct": {"en": "correct", "ru": "правильно", "tg": "дуруст", "zh": "正确答案"},
    "pages.mistakes.dueNow": {"en": "due now", "ru": "пора повторить", "tg": "ҳозир лозим аст", "zh": "现在待复习"},
    "pages.mistakes.practiceThis": {"en": "Practice this", "ru": "Практиковать это", "tg": "Инро машқ кунед", "zh": "练习这个"},
    "pages.mistakes.mastered": {"en": "Mastered", "ru": "Освоено", "tg": "Азхудшуда", "zh": "已掌握"},
    "pages.mistakes.masteredBadge": {"en": "mastered", "ru": "освоено", "tg": "азхудшуда", "zh": "已掌握"},
    "pages.mistakes.empty": {"en": "No mistakes recorded yet. Go make some.", "ru": "Ошибок пока не зафиксировано. Пора их совершить.", "tg": "То ҳол хатое сабт нашудааст. Равед, чанде созед.", "zh": "尚未记录任何错误。快去犯几个吧。"},
})

# ---------------- Duels ----------------
ENTRIES.update({
    "pages.duels.title": {"en": "DNA duels", "ru": "ДНК-дуэли", "tg": "Дуэлҳои ДНК", "zh": "DNA对决"},
    "pages.duels.subtitle": {"en": "Rapid-fire word battles. The questions are picked from your weakest strand.", "ru": "Быстрые словесные битвы. Вопросы подбираются из вашего самого слабого направления.", "tg": "Ҷангҳои тези калимавӣ. Саволҳо аз рӯи заифтарин самти шумо интихоб мешаванд.", "zh": "快节奏的词语对决。题目从你最薄弱的技能中挑选。"},
    "pages.duels.newDuel": {"en": "New duel", "ru": "Новая дуэль", "tg": "Дуэли нав", "zh": "新对决"},
    "pages.duels.challengeSomeone": {"en": "Challenge someone", "ru": "Бросить вызов", "tg": "Ба касе даъват фиристед", "zh": "挑战某人"},
    "pages.duels.opponent": {"en": "Opponent", "ru": "Соперник", "tg": "Рақиб", "zh": "对手"},
    "pages.duels.opponentPlaceholder": {"en": "Buddy or a friend's username", "ru": "Buddy или имя пользователя друга", "tg": "Buddy ё номи корбарии дӯст", "zh": "Buddy 或好友用户名"},
    "pages.duels.challengeFocus": {"en": "Challenge focus", "ru": "Фокус вызова", "tg": "Самти даъват", "zh": "挑战重点"},
    "pages.duels.challengeType.auto": {"en": "Auto — my weakest strand", "ru": "Авто — моё слабое место", "tg": "Худкор — самти заифи ман", "zh": "自动——我最薄弱的方向"},
    "pages.duels.challengeType.vocabulary": {"en": "Vocabulary", "ru": "Словарь", "tg": "Луғат", "zh": "词汇"},
    "pages.duels.challengeType.tones": {"en": "Tones", "ru": "Тоны", "tg": "Оҳангҳо", "zh": "声调"},
    "pages.duels.challengeType.characters": {"en": "Characters", "ru": "Иероглифы", "tg": "Иероглифҳо", "zh": "汉字"},
    "pages.duels.challengeType.memory": {"en": "Memory", "ru": "Память", "tg": "Хотира", "zh": "记忆"},
    "pages.duels.challengeType.listening": {"en": "Listening", "ru": "Аудирование", "tg": "Гӯш кардан", "zh": "听力"},
    "pages.duels.challengeType.reactionSpeed": {"en": "Reaction speed", "ru": "Скорость реакции", "tg": "Суръати аксуламал", "zh": "反应速度"},
    "pages.duels.challengeType.speaking": {"en": "Speaking", "ru": "Говорение", "tg": "Гуфторӣ", "zh": "口语"},
    "pages.duels.creating": {"en": "Creating…", "ru": "Создание…", "tg": "Эҷод шуда истодааст…", "zh": "创建中…"},
    "pages.duels.start": {"en": "Start", "ru": "Начать", "tg": "Оғоз", "zh": "开始"},
    "pages.duels.vs": {"en": "VS", "ru": "VS", "tg": "VS", "zh": "对"},
    "pages.duels.you": {"en": "You", "ru": "Вы", "tg": "Шумо", "zh": "你"},
    "pages.duels.opponentWon": {"en": "Opponent won", "ru": "Соперник победил", "tg": "Рақиб бурд", "zh": "对手获胜"},
    "pages.duels.youWon": {"en": "You won 🎉", "ru": "Вы победили 🎉", "tg": "Шумо бурдед 🎉", "zh": "你赢了🎉"},
    "pages.duels.draw": {"en": "Draw", "ru": "Ничья", "tg": "Баробар", "zh": "平局"},
    "pages.duels.waitingFor": {"en": "Waiting for {{opponent}}", "ru": "Ожидание {{opponent}}", "tg": "Интизори {{opponent}}", "zh": "等待{{opponent}}"},
    "pages.duels.practiceVsAi": {"en": "Practice vs AI · in progress", "ru": "Практика против ИИ · идёт", "tg": "Машқ бар зидди ИИ · дар ҷараён", "zh": "对战AI练习·进行中"},
    "pages.duels.inProgress": {"en": "In progress", "ru": "В процессе", "tg": "Дар ҷараён", "zh": "进行中"},
    "pages.duels.open": {"en": "Open", "ru": "Открыть", "tg": "Кушодан", "zh": "打开"},
    "pages.duels.empty": {"en": "No duels yet. Challenge the Buddy to a first battle.", "ru": "Дуэлей пока нет. Бросьте вызов Buddy в первой битве.", "tg": "То ҳол дуэл нест. Buddy-ро ба ҷанги аввал даъват кунед.", "zh": "还没有对决。向Buddy发起你的第一场对决吧。"},
})

# ---------------- Community / PublicProfile ----------------
ENTRIES.update({
    "pages.community.title": {"en": "Find people", "ru": "Найти людей", "tg": "Одамонро ёбед", "zh": "寻找好友"},
    "pages.community.subtitle": {"en": "Search for other learners by username and follow the ones you want to keep up with.", "ru": "Ищите других учащихся по имени пользователя и подписывайтесь на тех, за кем хотите следить.", "tg": "Дигар омӯзандагонро бо номи корбарӣ ҷустуҷӯ кунед ва касонеро, ки мехоҳед пайгирӣ кунед.", "zh": "按用户名搜索其他学习者，并关注你想保持联系的人。"},
    "pages.community.searchPlaceholder": {"en": "Search by username…", "ru": "Поиск по имени пользователя…", "tg": "Ҷустуҷӯ бо номи корбарӣ…", "zh": "按用户名搜索…"},
    "pages.community.noMatch": {"en": "No learners match \"{{query}}\".", "ru": "Учащихся по запросу «{{query}}» не найдено.", "tg": "Ҳеҷ омӯзанда бо \"{{query}}\" мувофиқат намекунад.", "zh": "没有与“{{query}}”匹配的学习者。"},
    "pages.community.follow": {"en": "Follow", "ru": "Подписаться", "tg": "Пайравӣ кунед", "zh": "关注"},
    "pages.community.unfollow": {"en": "Unfollow", "ru": "Отписаться", "tg": "Пайравиро бас кунед", "zh": "取消关注"},
    "pages.community.following": {"en": "Following", "ru": "Вы подписаны", "tg": "Пайравӣ мекунед", "zh": "已关注"},
    "pages.publicProfile.nobodyHere": {"en": "Nobody here yet.", "ru": "Здесь пока никого нет.", "tg": "Дар ин ҷо то ҳол касе нест.", "zh": "这里还没有人。"},
})

# ---------------- Progress ----------------
ENTRIES.update({
    "pages.progress.loading": {"en": "Crunching your activity…", "ru": "Анализ вашей активности…", "tg": "Таҳлили фаъолияти шумо…", "zh": "正在统计你的活动…"},
    "pages.progress.title": {"en": "Your progress", "ru": "Ваш прогресс", "tg": "Пешрафти шумо", "zh": "你的进度"},
    "pages.progress.subtitle": {"en": "Real activity, tracked as you use the app — not estimates.", "ru": "Реальная активность, отслеживаемая по мере использования приложения — не оценки.", "tg": "Фаъолияти воқеӣ, ки ҳангоми истифодаи барнома пайгирӣ мешавад — на тахминҳо.", "zh": "根据你使用应用的真实活动记录——而非估算。"},
    "pages.progress.total": {"en": "total", "ru": "всего", "tg": "ҳамагӣ", "zh": "总计"},
    "pages.progress.noActivity": {"en": "No tracked activity yet.", "ru": "Активность пока не отслеживается.", "tg": "То ҳол фаъолияти пайгирӣшуда нест.", "zh": "尚无记录的活动。"},
    "pages.progress.learningRhythm": {"en": "Learning Rhythm", "ru": "Ритм обучения", "tg": "Оҳанги омӯзиш", "zh": "学习节奏"},
    "pages.progress.yourRealActivity": {"en": "Your real activity", "ru": "Ваша реальная активность", "tg": "Фаъолияти воқеии шумо", "zh": "你的真实活动"},
    "pages.progress.totalActiveTime": {"en": "total active time", "ru": "общее активное время", "tg": "вақти умумии фаъол", "zh": "总活跃时长"},
    "pages.progress.actions": {"en": "{{count}} action(s)", "ru": "{{count}} действие(й)", "tg": "{{count}} амал", "zh": "{{count}}次操作"},
    "pages.progress.record": {"en": "record", "ru": "рекорд", "tg": "рекорд", "zh": "纪录"},
    "pages.progress.timeBySection": {"en": "Time by Section", "ru": "Время по разделам", "tg": "Вақт аз рӯи бахшҳо", "zh": "各版块用时"},
    "pages.progress.activityMap": {"en": "Activity Map", "ru": "Карта активности", "tg": "Харитаи фаъолият", "zh": "活动地图"},
    "pages.progress.actionsThisYear": {"en": "{{count}} actions this year", "ru": "{{count}} действий в этом году", "tg": "{{count}} амал дар ин сол", "zh": "今年{{count}}次操作"},
    "pages.progress.currentStreakDays": {"en": "{{count}}-day current streak", "ru": "текущая серия {{count}} дн.", "tg": "силсилаи ҷории {{count}} рӯза", "zh": "当前连续{{count}}天"},
    "pages.progress.bestStreakDays": {"en": "{{count}}-day best streak", "ru": "лучшая серия {{count}} дн.", "tg": "беҳтарин силсилаи {{count}} рӯза", "zh": "最佳连续{{count}}天"},
    "pages.progress.section.world": {"en": "World & Conversations", "ru": "Мир и разговоры", "tg": "Ҷаҳон ва сӯҳбатҳо", "zh": "世界与对话"},
    "pages.progress.section.vocabulary": {"en": "Vocabulary", "ru": "Словарь", "tg": "Луғат", "zh": "词汇"},
    "pages.progress.section.lessons": {"en": "Lessons", "ru": "Уроки", "tg": "Дарсҳо", "zh": "课程"},
    "pages.progress.section.duels": {"en": "Duels", "ru": "Дуэли", "tg": "Дуэлҳо", "zh": "对决"},
    "pages.progress.section.quests": {"en": "Quests", "ru": "Квесты", "tg": "Квестҳо", "zh": "任务"},
    "pages.progress.section.missions": {"en": "Missions", "ru": "Миссии", "tg": "Вазифаҳо", "zh": "使命"},
    "pages.progress.section.pet_teacher": {"en": "Pet Teacher", "ru": "Учим питомца", "tg": "Омӯзонидани ҳайвон", "zh": "教宠物"},
    "pages.progress.section.other": {"en": "Other", "ru": "Другое", "tg": "Дигар", "zh": "其他"},
})

# ---------------- WorldMap gaps ----------------
ENTRIES.update({
    "pages.world.drawingMap": {"en": "Drawing the map…", "ru": "Рисуем карту…", "tg": "Харита кашида истодааст…", "zh": "正在绘制地图…"},
    "pages.world.locked": {"en": "Locked", "ru": "Заблокировано", "tg": "Қулф", "zh": "已锁定"},
    "pages.world.almostThere": {"en": "Almost there", "ru": "Почти готово", "tg": "Қариб расидед", "zh": "就快到了"},
    "pages.world.open": {"en": "Open", "ru": "Открыто", "tg": "Кушода", "zh": "已开放"},
    "pages.world.unlocksHsk": {"en": "Unlocks HSK {{level}}", "ru": "Открывается на HSK {{level}}", "tg": "Бо HSK {{level}} кушода мешавад", "zh": "HSK {{level}} 解锁"},
    "pages.world.openClickToEnter": {"en": "Open — click to enter", "ru": "Открыто — нажмите, чтобы войти", "tg": "Кушода — барои даромадан зер кунед", "zh": "已开放——点击进入"},
})

# ---------------- Dashboard gap ----------------
ENTRIES.update({
    "dashboard.noQuestsToday": {"en": "No quests today — go explore.", "ru": "Сегодня квестов нет — идите исследовать.", "tg": "Имрӯз квест нест — равед сайр кунед.", "zh": "今天没有任务——去探索一下吧。"},
})

# ---------------- Companion ----------------
ENTRIES.update({
    "pages.companion.waking": {"en": "Waking your companion…", "ru": "Будим вашего компаньона…", "tg": "Бедор кардани ҳамроҳи шумо…", "zh": "正在唤醒你的伙伴…"},
    "pages.companion.needCompanion": {"en": "You need a companion first.", "ru": "Сначала вам нужен компаньон.", "tg": "Аввал ба шумо ҳамроҳ лозим аст.", "zh": "你需要先选择一个伙伴。"},
    "pages.companion.chooseOne": {"en": "Choose one", "ru": "Выбрать", "tg": "Интихоб кунед", "zh": "选择一个"},
    "pages.companion.title": {"en": "Your companion", "ru": "Ваш компаньон", "tg": "Ҳамроҳи шумо", "zh": "你的伙伴"},
    "pages.companion.subtitle": {"en": "Talk to {{name}}. They react to how you speak their language.", "ru": "Поговорите с {{name}}. Они реагируют на то, как вы говорите на их языке.", "tg": "Бо {{name}} гап занед. Онҳо ба тарзи гуфтугӯи шумо бо забонашон вокуниш нишон медиҳанд.", "zh": "和{{name}}聊聊吧。它们会对你说它们语言的方式作出反应。"},
    "pages.companion.yourRhythm": {"en": "Your rhythm", "ru": "Ваш ритм", "tg": "Оҳанги шумо", "zh": "你的节奏"},
    "pages.companion.streak": {"en": "Streak", "ru": "Серия", "tg": "Силсила", "zh": "连续打卡"},
    "pages.companion.catchMistake": {"en": "{{name}} wants you to catch its mistake", "ru": "{{name}} хочет, чтобы вы поймали его ошибку", "tg": "{{name}} мехоҳад, ки шумо хатои ӯро пайдо кунед", "zh": "{{name}}想让你找出它的错误"},
    "pages.companion.freeChat": {"en": "Free chat", "ru": "Свободный чат", "tg": "Гуфтугӯи озод", "zh": "自由聊天"},
    "pages.companion.sayInChinese": {"en": "Say something in Chinese — try one of these:", "ru": "Скажите что-нибудь по-китайски — попробуйте один из вариантов:", "tg": "Бо забони чинӣ чизе гӯед — яке аз инҳоро санҷед:", "zh": "用中文说点什么——可以试试这些："},
    "pages.companion.send": {"en": "Send", "ru": "Отправить", "tg": "Фиристодан", "zh": "发送"},
    "pages.companion.recentSessions": {"en": "Recent voice sessions", "ru": "Недавние голосовые сессии", "tg": "Ҷаласаҳои охирини овозӣ", "zh": "最近的语音记录"},
    "pages.companion.noSessions": {"en": "No sessions yet.", "ru": "Сессий пока нет.", "tg": "То ҳол ҷаласае нест.", "zh": "暂无记录。"},
})

# ---------------- Grammar & Hanzi (real HSK 3.0 curriculum) ----------------
ENTRIES.update({
    "nav.hanzi": {"en": "Hanzi", "ru": "Иероглифы", "tg": "Иероглифҳо", "zh": "汉字"},
    "nav.grammar": {"en": "Grammar", "ru": "Грамматика", "tg": "Грамматика", "zh": "语法"},
    "pages.grammar.title": {"en": "Grammar", "ru": "Грамматика", "tg": "Грамматика", "zh": "语法"},
    "pages.grammar.subtitle": {
        "en": "The real HSK grammar points behind every sentence.",
        "ru": "Реальные грамматические темы HSK, лежащие в основе каждого предложения.",
        "tg": "Мавзӯъҳои воқеии грамматикии HSK, ки дар асоси ҳар ҷумла қарор доранд.",
        "zh": "每个句子背后真正的HSK语法点。",
    },
    "pages.grammar.gotIt": {"en": "Got it", "ru": "Понятно", "tg": "Фаҳмидам", "zh": "掌握了"},
    "pages.grammar.stillLearning": {"en": "Still learning", "ru": "Ещё учу", "tg": "Ҳанӯз меомӯзам", "zh": "还在学"},
    "pages.grammar.showExamples": {"en": "Show examples", "ru": "Показать примеры", "tg": "Мисолҳоро нишон диҳед", "zh": "显示例句"},
    "pages.grammar.hideExamples": {"en": "Hide examples", "ru": "Скрыть примеры", "tg": "Мисолҳоро пинҳон кунед", "zh": "隐藏例句"},
    "pages.grammar.empty": {"en": "No grammar points at this level yet.", "ru": "На этом уровне пока нет грамматических тем.", "tg": "Дар ин сатҳ ҳанӯз мавзӯи грамматикӣ нест.", "zh": "此级别暂无语法点。"},
    "pages.hanzi.title": {"en": "Hanzi", "ru": "Иероглифы", "tg": "Иероглифҳо", "zh": "汉字"},
    "pages.hanzi.subtitle": {
        "en": "Tap a character to self-review its reading and meaning.",
        "ru": "Нажмите на иероглиф, чтобы проверить его чтение и значение.",
        "tg": "Барои санҷидани хониш ва маънои аломат зер кунед.",
        "zh": "点击汉字自测读音和释义。",
    },
    "pages.hanzi.handwriting": {"en": "writing", "ru": "письмо", "tg": "хат", "zh": "书写"},
    "pages.hanzi.strokes": {"en": "{{count}} strokes", "ru": "{{count}} черт", "tg": "{{count}} хат", "zh": "{{count}} 笔画"},
    "pages.hanzi.empty": {"en": "No characters at this level yet.", "ru": "На этом уровне пока нет иероглифов.", "tg": "Дар ин сатҳ ҳанӯз аломат нест.", "zh": "此级别暂无汉字。"},
    "pages.roadmap.hanzi": {"en": "Hanzi", "ru": "Иероглифы", "tg": "Иероглифҳо", "zh": "汉字"},
    "pages.roadmap.grammar": {"en": "Grammar", "ru": "Грамматика", "tg": "Грамматика", "zh": "语法"},
    "pages.roadmap.advancedStage": {"en": "shared advanced pool", "ru": "общий продвинутый пул", "tg": "ҳавзи умумии пешрафта", "zh": "共享高级词库"},
    "pages.hanzi.practiceWriting": {"en": "Practice writing", "ru": "Практика письма", "tg": "Машқи навиштан", "zh": "练习书写"},
    "pages.hanzi.writingMastery": {"en": "Writing mastery", "ru": "Освоение письма", "tg": "Азхудкунии хат", "zh": "书写掌握度"},
    "pages.hanzi.noStrokeData": {"en": "No stroke data available for this character.", "ru": "Для этого иероглифа нет данных о чертах.", "tg": "Барои ин аломат маълумоти хат мавҷуд нест.", "zh": "该汉字没有笔画数据。"},
    "pages.hanzi.mistakes": {"en": "{{count}} mistake(s) so far", "ru": "{{count}} ошиб(ок) пока", "tg": "то ҳол {{count}} хато", "zh": "目前 {{count}} 次错误"},
    "pages.hanzi.traceComplete": {"en": "Traced correctly! ({{count}} mistakes)", "ru": "Начертано верно! ({{count}} ошибок)", "tg": "Дуруст навишта шуд! ({{count}} хато)", "zh": "描摹正确！（{{count}} 次错误）"},
    "pages.hanzi.retry": {"en": "Retry", "ru": "Повторить", "tg": "Такрор", "zh": "重试"},
    "pages.hanzi.saveProgress": {"en": "Save progress", "ru": "Сохранить прогресс", "tg": "Пешравиро нигоҳ доред", "zh": "保存进度"},
    "pages.hanzi.cancel": {"en": "Cancel", "ru": "Отмена", "tg": "Бекор кардан", "zh": "取消"},
    "pages.hanzi.watchingStrokeOrder": {"en": "Watching stroke order…", "ru": "Смотрим порядок черт…", "tg": "Тартиби хатҳо тамошо мешавад…", "zh": "正在演示笔顺…"},
    "pages.hanzi.strokeOrderShown": {"en": "That's the stroke order. Ready to try writing it yourself?", "ru": "Вот порядок черт. Готовы попробовать написать сами?", "tg": "Ин тартиби хатҳо буд. Омодаед худатон нависед?", "zh": "这就是笔顺。准备好自己写了吗？"},
    "pages.hanzi.watchAgain": {"en": "Watch again", "ru": "Посмотреть ещё раз", "tg": "Боз тамошо кунед", "zh": "再看一遍"},
    "pages.hanzi.tryWriting": {"en": "Try writing", "ru": "Попробовать написать", "tg": "Навиштанро санҷед", "zh": "尝试书写"},
    "pages.hanzi.hear": {"en": "Listen", "ru": "Слушать", "tg": "Гӯш кунед", "zh": "听"},
    "pages.hanzi.examples": {"en": "Examples", "ru": "Примеры", "tg": "Мисолҳо", "zh": "例词"},
    "pages.hanzi.noExamples": {"en": "No example words in the vocabulary list yet.", "ru": "В списке слов пока нет примеров.", "tg": "Дар рӯйхати луғат ҳанӯз мисол нест.", "zh": "词汇表中暂无例词。"},
    "pages.hanzi.recognitionProgress": {"en": "Recognition", "ru": "Узнавание", "tg": "Шинохтан", "zh": "识别"},
    "pages.hanzi.writingProgress": {"en": "Writing", "ru": "Письмо", "tg": "Хат", "zh": "书写"},
    "pages.hanzi.gotIt": {"en": "I recognize this", "ru": "Я узнаю это", "tg": "Ман инро мешиносам", "zh": "我认识"},
    "pages.hanzi.stillLearning": {"en": "Still learning", "ru": "Ещё учу", "tg": "Ҳанӯз меомӯзам", "zh": "还在学"},
    "pages.hanzi.viewDetail": {"en": "Learn this character", "ru": "Изучить этот иероглиф", "tg": "Ин аломатро омӯзед", "zh": "学习这个汉字"},
    "pages.hanzi.close": {"en": "Close", "ru": "Закрыть", "tg": "Пӯшидан", "zh": "关闭"},
    "pages.roadmap.advancedStageHint": {
        "en": "HSK 7/8/9 share one real advanced vocabulary/Hanzi/grammar pool, shown here as three progress stages.",
        "ru": "HSK 7/8/9 используют единый реальный продвинутый набор слов/иероглифов/грамматики, показанный здесь как три этапа прогресса.",
        "tg": "HSK 7/8/9 як ҳавзи воқеии пешрафтаи луғат/иероглиф/грамматикаро мубодила мекунанд, ки дар ин ҷо ҳамчун се марҳилаи пешрафт нишон дода шудааст.",
        "zh": "HSK 7/8/9 共享同一个真实的高级词汇/汉字/语法库，此处显示为三个进度阶段。",
    },
})

if __name__ == "__main__":
    merge(ENTRIES)
