# -*- coding: utf-8 -*-
"""Achievement strings in all four locales (en/ru/tg/zh): every achievement's
title, how to unlock it (plain words, no technical condition) and what it
says once earned, keyed by the code in backend/app/services/achievements.py;
"N more ... to unlock this" per unit (i18next plurals); the unlock note and
the page's labels. Idempotent. Run from frontend/: python scripts/add_achievements_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")
LANGS = ("en", "ru", "tg", "zh")

# code -> per locale: (title, how to unlock, done)
ITEMS = {
    "first_lesson": {
        "en": ("First Lesson", "Complete your first lesson.", "Completed your first lesson."),
        "ru": ("Первый урок", "Пройдите свой первый урок.", "Вы прошли свой первый урок."),
        "tg": ("Дарси аввал", "Дарси аввалини худро гузаред.", "Шумо дарси аввалини худро гузаштед."),
        "zh": ("第一课", "完成你的第一节课。", "你完成了第一节课。"),
    },
    "first_word": {
        "en": ("First Word", "Learn your first Chinese word: answer it correctly in practice.", "Learned your first Chinese word."),
        "ru": ("Первое слово", "Выучите первое китайское слово: ответьте на него правильно в практике.", "Вы выучили первое китайское слово."),
        "tg": ("Калимаи аввал", "Калимаи аввалини чиниро омӯзед: дар машқ ба он дуруст ҷавоб диҳед.", "Шумо калимаи аввалини чиниро омӯхтед."),
        "zh": ("第一个词", "学会你的第一个中文词：在练习中答对它。", "你学会了第一个中文词。"),
    },
    "first_hanzi": {
        "en": ("First Character", "Learn your first Chinese character in Hanzi practice.", "Learned your first Chinese character."),
        "ru": ("Первый иероглиф", "Выучите первый иероглиф в практике иероглифов.", "Вы выучили первый иероглиф."),
        "tg": ("Иероглифи аввал", "Иероглифи аввалро дар машқи иероглифҳо омӯзед.", "Шумо иероглифи аввалро омӯхтед."),
        "zh": ("第一个汉字", "在汉字练习中学会你的第一个汉字。", "你学会了第一个汉字。"),
    },
    "first_trace": {
        "en": ("First Strokes", "Trace a character stroke by stroke.", "Traced your first character stroke by stroke."),
        "ru": ("Первые черты", "Пропишите иероглиф черта за чертой.", "Вы впервые прописали иероглиф черта за чертой."),
        "tg": ("Хатҳои аввал", "Иероглифро хат ба хат нависед.", "Шумо бори аввал иероглифро хат ба хат навиштед."),
        "zh": ("第一笔", "按笔顺描写一个汉字。", "你第一次按笔顺描写了汉字。"),
    },
    "first_tones": {
        "en": ("Four Tones", "Finish a round in Sounds & tones.", "Finished your first tones round."),
        "ru": ("Четыре тона", "Пройдите раунд в разделе «Звуки и тоны».", "Вы прошли первый раунд по тонам."),
        "tg": ("Чор оҳанг", "Як даврро дар бахши «Садоҳо ва оҳангҳо» гузаред.", "Шумо даври аввали оҳангҳоро гузаштед."),
        "zh": ("四声", "在“声音和声调”里完成一轮练习。", "你完成了第一轮声调练习。"),
    },
    "first_sentence": {
        "en": ("First Sentence", "Finish a lesson in One Sentence.", "Finished your first sentence lesson."),
        "ru": ("Первое предложение", "Пройдите урок в разделе «Одно предложение».", "Вы прошли первый урок по предложениям."),
        "tg": ("Ҷумлаи аввал", "Як дарсро дар бахши «Як ҷумла» гузаред.", "Шумо дарси аввали ҷумлаҳоро гузаштед."),
        "zh": ("第一个句子", "在“一句话”里完成一节课。", "你完成了第一节句子课。"),
    },
    "first_listening": {
        "en": ("First Listen", "Understand a Chinese word or phrase by ear.", "Understood Chinese by ear for the first time."),
        "ru": ("Первое аудирование", "Поймите китайское слово или фразу на слух.", "Вы впервые поняли китайский на слух."),
        "tg": ("Шунидани аввал", "Калима ё ибораи чиниро аз рӯи шунавоӣ фаҳмед.", "Шумо бори аввал чиниро аз рӯи шунавоӣ фаҳмидед."),
        "zh": ("第一次听懂", "听懂一个中文词或短语。", "你第一次听懂了中文。"),
    },
    "first_voice": {
        "en": ("First Spoken Conversation", "Say your first sentence out loud.", "Spoke Chinese out loud for the first time."),
        "ru": ("Первый разговор", "Произнесите вслух своё первое предложение.", "Вы впервые заговорили по-китайски вслух."),
        "tg": ("Сӯҳбати аввал", "Ҷумлаи аввалини худро бо овози баланд гӯед.", "Шумо бори аввал бо овози баланд ба забони чинӣ гап задед."),
        "zh": ("第一次开口", "大声说出你的第一句中文。", "你第一次大声说了中文。"),
    },
    "first_story": {
        "en": ("First Story", "Read your first Chinese story.", "Completed your first Chinese story."),
        "ru": ("Первая история", "Прочитайте свою первую китайскую историю.", "Вы прочитали первую китайскую историю."),
        "tg": ("Ҳикояи аввал", "Ҳикояи аввалини чиниро хонед.", "Шумо ҳикояи аввалини чиниро хондед."),
        "zh": ("第一个故事", "读完你的第一个中文故事。", "你读完了第一个中文故事。"),
    },
    "first_review": {
        "en": ("First Review", "Finish a review round.", "Finished your first review round."),
        "ru": ("Первое повторение", "Пройдите раунд повторения.", "Вы прошли первый раунд повторения."),
        "tg": ("Такрори аввал", "Даври такрорро гузаред.", "Шумо даври аввали такрорро гузаштед."),
        "zh": ("第一次复习", "完成一轮复习。", "你完成了第一轮复习。"),
    },
    "first_real_chinese": {
        "en": ("Into Real Chinese", "Finish a scene in Real Chinese.", "Finished your first Real Chinese scene."),
        "ru": ("В живом китайском", "Пройдите сцену в разделе «Живой китайский».", "Вы прошли первую сцену в «Живом китайском»."),
        "tg": ("Дар чинии зинда", "Як саҳнаро дар бахши «Чинии зинда» гузаред.", "Шумо саҳнаи аввалро дар «Чинии зинда» гузаштед."),
        "zh": ("走进真实中文", "在“真实中文”里完成一个场景。", "你完成了第一个“真实中文”场景。"),
    },
    "case_solver": {
        "en": ("Case Solver", "Finish a case in Detective Mode.", "Finished your first Detective case."),
        "ru": ("Сыщик", "Пройдите дело в режиме детектива.", "Вы прошли первое дело в режиме детектива."),
        "tg": ("Ҷосус", "Як парвандаро дар ҳолати детектив гузаред.", "Шумо парвандаи аввалро дар ҳолати детектив гузаштед."),
        "zh": ("破案新手", "在侦探模式里完成一个案件。", "你完成了第一个侦探案件。"),
    },
    "first_sound_world": {
        "en": ("Sound Explorer", "Finish a round in Sound World.", "Finished your first Sound World round."),
        "ru": ("Исследователь звуков", "Пройдите раунд в «Мире звуков».", "Вы прошли первый раунд в «Мире звуков»."),
        "tg": ("Кашшофи садоҳо", "Як даврро дар «Олами садоҳо» гузаред.", "Шумо даври аввалро дар «Олами садоҳо» гузаштед."),
        "zh": ("声音探险家", "在声音世界里完成一轮练习。", "你完成了第一轮声音世界练习。"),
    },
    "first_internet": {
        "en": ("Online in Chinese", "Read something in Chinese Internet and answer its questions.", "Finished your first Chinese Internet round."),
        "ru": ("Онлайн по-китайски", "Прочитайте что-нибудь в «Китайском интернете» и ответьте на вопросы.", "Вы прошли первый раунд в «Китайском интернете»."),
        "tg": ("Онлайн бо чинӣ", "Дар «Интернети чинӣ» чизеро хонед ва ба саволҳо ҷавоб диҳед.", "Шумо даври аввалро дар «Интернети чинӣ» гузаштед."),
        "zh": ("中文上网", "在中文网络里读一篇内容并回答问题。", "你完成了第一轮中文网络阅读。"),
    },
    "words_10": {
        "en": ("10 Words", "Learn 10 Chinese words.", "Learned 10 Chinese words."),
        "ru": ("10 слов", "Выучите 10 китайских слов.", "Вы выучили 10 китайских слов."),
        "tg": ("10 калима", "10 калимаи чиниро омӯзед.", "Шумо 10 калимаи чиниро омӯхтед."),
        "zh": ("10 个词", "学会 10 个中文词。", "你学会了 10 个中文词。"),
    },
    "words_50": {
        "en": ("50 Words", "Learn 50 Chinese words.", "Learned 50 Chinese words."),
        "ru": ("50 слов", "Выучите 50 китайских слов.", "Вы выучили 50 китайских слов."),
        "tg": ("50 калима", "50 калимаи чиниро омӯзед.", "Шумо 50 калимаи чиниро омӯхтед."),
        "zh": ("50 个词", "学会 50 个中文词。", "你学会了 50 个中文词。"),
    },
    "words_150": {
        "en": ("150 Words", "Learn 150 Chinese words.", "Learned 150 Chinese words."),
        "ru": ("150 слов", "Выучите 150 китайских слов.", "Вы выучили 150 китайских слов."),
        "tg": ("150 калима", "150 калимаи чиниро омӯзед.", "Шумо 150 калимаи чиниро омӯхтед."),
        "zh": ("150 个词", "学会 150 个中文词。", "你学会了 150 个中文词。"),
    },
    "words_100": {
        "en": ("100 Words Mastered", "Master 100 words: keep answering them right in practice and review.", "Mastered 100 Chinese words."),
        "ru": ("100 слов в совершенстве", "Освойте 100 слов: продолжайте правильно отвечать на них в практике и повторении.", "Вы освоили 100 китайских слов."),
        "tg": ("100 калима комил", "100 калимаро азхуд кунед: дар машқ ва такрор ба онҳо дуруст ҷавоб диҳед.", "Шумо 100 калимаи чиниро азхуд кардед."),
        "zh": ("掌握 100 个词", "掌握 100 个词：在练习和复习中持续答对它们。", "你掌握了 100 个中文词。"),
    },
    "hanzi_25": {
        "en": ("25 Characters", "Learn 25 Chinese characters.", "Learned 25 Chinese characters."),
        "ru": ("25 иероглифов", "Выучите 25 иероглифов.", "Вы выучили 25 иероглифов."),
        "tg": ("25 иероглиф", "25 иероглифро омӯзед.", "Шумо 25 иероглифро омӯхтед."),
        "zh": ("25 个汉字", "学会 25 个汉字。", "你学会了 25 个汉字。"),
    },
    "hanzi_100": {
        "en": ("100 Characters", "Learn 100 Chinese characters.", "Learned 100 Chinese characters."),
        "ru": ("100 иероглифов", "Выучите 100 иероглифов.", "Вы выучили 100 иероглифов."),
        "tg": ("100 иероглиф", "100 иероглифро омӯзед.", "Шумо 100 иероглифро омӯхтед."),
        "zh": ("100 个汉字", "学会 100 个汉字。", "你学会了 100 个汉字。"),
    },
    "traces_10": {
        "en": ("Steady Hand", "Trace 10 characters stroke by stroke.", "Traced 10 characters stroke by stroke."),
        "ru": ("Твёрдая рука", "Пропишите 10 иероглифов черта за чертой.", "Вы прописали 10 иероглифов черта за чертой."),
        "tg": ("Дасти устувор", "10 иероглифро хат ба хат нависед.", "Шумо 10 иероглифро хат ба хат навиштед."),
        "zh": ("稳稳的手", "按笔顺描写 10 个汉字。", "你按笔顺描写了 10 个汉字。"),
    },
    "listening_50": {
        "en": ("Good Ears", "Answer 50 listening questions correctly.", "Answered 50 listening questions correctly."),
        "ru": ("Хороший слух", "Правильно ответьте на 50 вопросов на слух.", "Вы правильно ответили на 50 вопросов на слух."),
        "tg": ("Гӯши хуб", "Ба 50 саволи шунавоӣ дуруст ҷавоб диҳед.", "Шумо ба 50 саволи шунавоӣ дуруст ҷавоб додед."),
        "zh": ("好耳朵", "答对 50 道听力题。", "你答对了 50 道听力题。"),
    },
    "listening_200": {
        "en": ("Sharp Ears", "Answer 200 listening questions correctly.", "Answered 200 listening questions correctly."),
        "ru": ("Чуткий слух", "Правильно ответьте на 200 вопросов на слух.", "Вы правильно ответили на 200 вопросов на слух."),
        "tg": ("Гӯши тез", "Ба 200 саволи шунавоӣ дуруст ҷавоб диҳед.", "Шумо ба 200 саволи шунавоӣ дуруст ҷавоб додед."),
        "zh": ("顺风耳", "答对 200 道听力题。", "你答对了 200 道听力题。"),
    },
    "speaking_10": {
        "en": ("Finding Your Voice", "Speak Chinese out loud 10 times.", "Spoke Chinese out loud 10 times."),
        "ru": ("Свой голос", "Скажите что-нибудь по-китайски вслух 10 раз.", "Вы говорили по-китайски вслух 10 раз."),
        "tg": ("Овози худ", "10 бор бо овози баланд ба забони чинӣ гап занед.", "Шумо 10 бор бо овози баланд ба забони чинӣ гап задед."),
        "zh": ("找到声音", "大声说中文 10 次。", "你已经大声说了 10 次中文。"),
    },
    "speaking_50": {
        "en": ("Confident Speaker", "Speak Chinese out loud 50 times.", "Spoke Chinese out loud 50 times."),
        "ru": ("Уверенная речь", "Скажите что-нибудь по-китайски вслух 50 раз.", "Вы говорили по-китайски вслух 50 раз."),
        "tg": ("Сухани боварӣ", "50 бор бо овози баланд ба забони чинӣ гап занед.", "Шумо 50 бор бо овози баланд ба забони чинӣ гап задед."),
        "zh": ("自信开口", "大声说中文 50 次。", "你已经大声说了 50 次中文。"),
    },
    "tone_master": {
        "en": ("Tone Master", "Speak at least 5 times and get your average tone score to 80%.", "Your spoken tones average 80% or more."),
        "ru": ("Мастер тонов", "Говорите вслух хотя бы 5 раз и доведите средний балл за тоны до 80%.", "Ваш средний балл за тоны — 80% или выше."),
        "tg": ("Устоди оҳангҳо", "Ақаллан 5 бор гап занед ва холи миёнаи оҳангро то 80% расонед.", "Холи миёнаи оҳангҳои шумо 80% ё бештар аст."),
        "zh": ("声调大师", "至少开口说 5 次，让声调平均分达到 80%。", "你的声调平均分达到了 80% 以上。"),
    },
    "restaurant_survivor": {
        "en": ("Restaurant Survivor", "Order noodles out loud in the noodle-shop conversation.", "Ordered noodles in Chinese."),
        "ru": ("Выжил в ресторане", "Закажите лапшу вслух в разговоре в лапшичной.", "Вы заказали лапшу по-китайски."),
        "tg": ("Дар тарабхона наҷот ёфт", "Дар сӯҳбати угроҳона угро фармоиш диҳед.", "Шумо бо забони чинӣ угро фармоиш додед."),
        "zh": ("餐厅生存者", "在面馆对话里大声点一碗面。", "你用中文点了面。"),
    },
    "reading_50": {
        "en": ("Reader", "Answer 50 reading questions correctly.", "Answered 50 reading questions correctly."),
        "ru": ("Читатель", "Правильно ответьте на 50 вопросов на чтение.", "Вы правильно ответили на 50 вопросов на чтение."),
        "tg": ("Хонанда", "Ба 50 саволи хониш дуруст ҷавоб диҳед.", "Шумо ба 50 саволи хониш дуруст ҷавоб додед."),
        "zh": ("小读者", "答对 50 道阅读题。", "你答对了 50 道阅读题。"),
    },
    "reading_200": {
        "en": ("Bookworm", "Answer 200 reading questions correctly.", "Answered 200 reading questions correctly."),
        "ru": ("Книжный червь", "Правильно ответьте на 200 вопросов на чтение.", "Вы правильно ответили на 200 вопросов на чтение."),
        "tg": ("Китобдӯст", "Ба 200 саволи хониш дуруст ҷавоб диҳед.", "Шумо ба 200 саволи хониш дуруст ҷавоб додед."),
        "zh": ("书虫", "答对 200 道阅读题。", "你答对了 200 道阅读题。"),
    },
    "stories_3": {
        "en": ("Story Lover", "Read 3 different Chinese stories.", "Read 3 different Chinese stories."),
        "ru": ("Любитель историй", "Прочитайте 3 разные китайские истории.", "Вы прочитали 3 разные китайские истории."),
        "tg": ("Дӯстдори ҳикояҳо", "3 ҳикояи гуногуни чиниро хонед.", "Шумо 3 ҳикояи гуногуни чиниро хондед."),
        "zh": ("故事迷", "读完 3 个不同的中文故事。", "你读完了 3 个不同的中文故事。"),
    },
    "stories_10": {
        "en": ("Library Card", "Read 10 different Chinese stories.", "Read 10 different Chinese stories."),
        "ru": ("Читательский билет", "Прочитайте 10 разных китайских историй.", "Вы прочитали 10 разных китайских историй."),
        "tg": ("Билети китобхона", "10 ҳикояи гуногуни чиниро хонед.", "Шумо 10 ҳикояи гуногуни чиниро хондед."),
        "zh": ("借书证", "读完 10 个不同的中文故事。", "你读完了 10 个不同的中文故事。"),
    },
    "detective_5": {
        "en": ("Master Detective", "Solve 5 Detective cases with the right answer.", "Solved 5 Detective cases."),
        "ru": ("Опытный детектив", "Раскройте 5 дел в режиме детектива с правильным ответом.", "Вы раскрыли 5 дел."),
        "tg": ("Детективи ботаҷриба", "5 парвандаро бо ҷавоби дуруст ҳал кунед.", "Шумо 5 парвандаро ҳал кардед."),
        "zh": ("神探", "正确破解 5 个侦探案件。", "你破解了 5 个侦探案件。"),
    },
    "lessons_5": {
        "en": ("Five Lessons", "Complete 5 lessons.", "Completed 5 lessons."),
        "ru": ("Пять уроков", "Пройдите 5 уроков.", "Вы прошли 5 уроков."),
        "tg": ("Панҷ дарс", "5 дарсро гузаред.", "Шумо 5 дарсро гузаштед."),
        "zh": ("五节课", "完成 5 节课。", "你完成了 5 节课。"),
    },
    "lessons_20": {
        "en": ("Twenty Lessons", "Complete 20 lessons.", "Completed 20 lessons."),
        "ru": ("Двадцать уроков", "Пройдите 20 уроков.", "Вы прошли 20 уроков."),
        "tg": ("Бист дарс", "20 дарсро гузаред.", "Шумо 20 дарсро гузаштед."),
        "zh": ("二十节课", "完成 20 节课。", "你完成了 20 节课。"),
    },
    "hsk1_exam": {
        "en": ("HSK 1 Passed", "Finish the HSK 1 lessons and pass the HSK 1 exam.", "Passed the HSK 1 exam."),
        "ru": ("HSK 1 сдан", "Пройдите уроки HSK 1 и сдайте экзамен HSK 1.", "Вы сдали экзамен HSK 1."),
        "tg": ("HSK 1 супорида шуд", "Дарсҳои HSK 1-ро гузаред ва имтиҳони HSK 1-ро супоред.", "Шумо имтиҳони HSK 1-ро супоридед."),
        "zh": ("通过 HSK 1", "学完 HSK 1 的课程并通过 HSK 1 考试。", "你通过了 HSK 1 考试。"),
    },
    "hsk2_mastery": {
        "en": ("HSK 2 Mastery", "Reach HSK 2 and 80% overall mastery.", "Reached HSK 2 with 80% overall mastery."),
        "ru": ("Уровень HSK 2", "Достигните HSK 2 и 80% общего освоения.", "Вы достигли HSK 2 с освоением 80%."),
        "tg": ("Сатҳи HSK 2", "Ба HSK 2 ва 80% азхудкунии умумӣ расед.", "Шумо бо 80% азхудкунӣ ба HSK 2 расидед."),
        "zh": ("掌握 HSK 2", "达到 HSK 2，整体掌握度达到 80%。", "你达到了 HSK 2，整体掌握度 80%。"),
    },
    "hsk3_exam": {
        "en": ("HSK 3 Passed", "Finish the HSK 3 lessons and pass the HSK 3 exam.", "Passed the HSK 3 exam."),
        "ru": ("HSK 3 сдан", "Пройдите уроки HSK 3 и сдайте экзамен HSK 3.", "Вы сдали экзамен HSK 3."),
        "tg": ("HSK 3 супорида шуд", "Дарсҳои HSK 3-ро гузаред ва имтиҳони HSK 3-ро супоред.", "Шумо имтиҳони HSK 3-ро супоридед."),
        "zh": ("通过 HSK 3", "学完 HSK 3 的课程并通过 HSK 3 考试。", "你通过了 HSK 3 考试。"),
    },
    "hsk6_exam": {
        "en": ("HSK 6 Passed", "Finish the HSK 6 lessons and pass the HSK 6 exam.", "Passed the HSK 6 exam."),
        "ru": ("HSK 6 сдан", "Пройдите уроки HSK 6 и сдайте экзамен HSK 6.", "Вы сдали экзамен HSK 6."),
        "tg": ("HSK 6 супорида шуд", "Дарсҳои HSK 6-ро гузаред ва имтиҳони HSK 6-ро супоред.", "Шумо имтиҳони HSK 6-ро супоридед."),
        "zh": ("通过 HSK 6", "学完 HSK 6 的课程并通过 HSK 6 考试。", "你通过了 HSK 6 考试。"),
    },
    "reviews_10": {
        "en": ("Review Habit", "Finish 10 review rounds.", "Finished 10 review rounds."),
        "ru": ("Привычка повторять", "Пройдите 10 раундов повторения.", "Вы прошли 10 раундов повторения."),
        "tg": ("Одати такрор", "10 даври такрорро гузаред.", "Шумо 10 даври такрорро гузаштед."),
        "zh": ("复习习惯", "完成 10 轮复习。", "你完成了 10 轮复习。"),
    },
    "review_days_7": {
        "en": ("Never Forget", "Review on 7 different days.", "Reviewed on 7 different days."),
        "ru": ("Ничего не забыть", "Повторяйте в 7 разных дней.", "Вы повторяли в 7 разных дней."),
        "tg": ("Ҳеҷ чиз фаромӯш нашавад", "Дар 7 рӯзи гуногун такрор кунед.", "Шумо дар 7 рӯзи гуногун такрор кардед."),
        "zh": ("温故知新", "在 7 个不同的日子里复习。", "你在 7 个不同的日子里复习了。"),
    },
    "mistakes_10": {
        "en": ("Mistake Hunter", "Turn 10 of your mistakes into answers you get right.", "Fixed 10 of your mistakes for good."),
        "ru": ("Охотник за ошибками", "Превратите 10 своих ошибок в правильные ответы.", "Вы исправили 10 своих ошибок насовсем."),
        "tg": ("Шикорчии хатоҳо", "10 хатои худро ба ҷавобҳои дуруст табдил диҳед.", "Шумо 10 хатои худро барои ҳамеша ислоҳ кардед."),
        "zh": ("纠错猎人", "把 10 个错误变成能答对的题。", "你彻底改正了 10 个错误。"),
    },
    "streak_3": {
        "en": ("3-Day Streak", "Learn 3 days in a row.", "Learned 3 days in a row."),
        "ru": ("3 дня подряд", "Занимайтесь 3 дня подряд.", "Вы занимались 3 дня подряд."),
        "tg": ("3 рӯз пай дар пай", "3 рӯз пай дар пай омӯзед.", "Шумо 3 рӯз пай дар пай омӯхтед."),
        "zh": ("连续 3 天", "连续学习 3 天。", "你连续学习了 3 天。"),
    },
    "streak_7": {
        "en": ("7-Day Streak", "Learn 7 days in a row.", "Learned 7 days in a row."),
        "ru": ("7 дней подряд", "Занимайтесь 7 дней подряд.", "Вы занимались 7 дней подряд."),
        "tg": ("7 рӯз пай дар пай", "7 рӯз пай дар пай омӯзед.", "Шумо 7 рӯз пай дар пай омӯхтед."),
        "zh": ("连续 7 天", "连续学习 7 天。", "你连续学习了 7 天。"),
    },
    "streak_30": {
        "en": ("30-Day Streak", "Learn 30 days in a row.", "Learned 30 days in a row."),
        "ru": ("30 дней подряд", "Занимайтесь 30 дней подряд.", "Вы занимались 30 дней подряд."),
        "tg": ("30 рӯз пай дар пай", "30 рӯз пай дар пай омӯзед.", "Шумо 30 рӯз пай дар пай омӯхтед."),
        "zh": ("连续 30 天", "连续学习 30 天。", "你连续学习了 30 天。"),
    },
    "active_30": {
        "en": ("Thirty Days of Chinese", "Learn on 30 different days.", "Learned on 30 different days."),
        "ru": ("Тридцать дней китайского", "Занимайтесь в 30 разных дней.", "Вы занимались в 30 разных дней."),
        "tg": ("Сӣ рӯзи забони чинӣ", "Дар 30 рӯзи гуногун омӯзед.", "Шумо дар 30 рӯзи гуногун омӯхтед."),
        "zh": ("中文三十天", "在 30 个不同的日子里学习。", "你在 30 个不同的日子里学习了。"),
    },
    "xp_500": {
        "en": ("Rising Star", "Earn 500 XP by learning.", "Earned 500 XP."),
        "ru": ("Восходящая звезда", "Заработайте 500 XP, занимаясь.", "Вы заработали 500 XP."),
        "tg": ("Ситораи тулӯъкунанда", "Бо омӯзиш 500 XP ба даст оред.", "Шумо 500 XP ба даст овардед."),
        "zh": ("新星", "通过学习获得 500 XP。", "你获得了 500 XP。"),
    },
    "bond_3": {
        "en": ("Bonded Companion", "Reach bond level 3 with your companion.", "Reached bond level 3 with your companion."),
        "ru": ("Верный компаньон", "Достигните 3-го уровня дружбы с компаньоном.", "Вы достигли 3-го уровня дружбы с компаньоном."),
        "tg": ("Ҳамроҳи содиқ", "Бо ҳамроҳатон ба сатҳи 3-юми дӯстӣ расед.", "Шумо бо ҳамроҳатон ба сатҳи 3-юми дӯстӣ расидед."),
        "zh": ("亲密伙伴", "和你的伙伴达到 3 级亲密度。", "你和伙伴的亲密度达到了 3 级。"),
    },
    "pet_teacher_5": {
        "en": ("Patient Teacher", "Teach your companion 5 grammar rules.", "Taught your companion 5 grammar rules."),
        "ru": ("Терпеливый учитель", "Научите компаньона 5 грамматическим правилам.", "Вы научили компаньона 5 правилам грамматики."),
        "tg": ("Муаллими босабр", "Ба ҳамроҳатон 5 қоидаи грамматикаро омӯзонед.", "Шумо ба ҳамроҳатон 5 қоидаи грамматикаро омӯзондед."),
        "zh": ("耐心的老师", "教会你的伙伴 5 条语法规则。", "你教会了伙伴 5 条语法规则。"),
    },
    "world_4": {
        "en": ("City Explorer", "Open 4 places on the World map by growing your HSK level.", "Opened 4 places on the World map."),
        "ru": ("Исследователь города", "Откройте 4 места на карте мира, повышая уровень HSK.", "Вы открыли 4 места на карте мира."),
        "tg": ("Кашшофи шаҳр", "Бо баланд бардоштани сатҳи HSK 4 ҷойро дар харитаи ҷаҳон кушоед.", "Шумо 4 ҷойро дар харитаи ҷаҳон кушодед."),
        "zh": ("城市探险家", "提高 HSK 等级，在世界地图上开启 4 个地点。", "你在世界地图上开启了 4 个地点。"),
    },
    "first_mission": {
        "en": ("First Mission", "Complete your first mission.", "Completed your first mission."),
        "ru": ("Первая миссия", "Выполните свою первую миссию.", "Вы выполнили первую миссию."),
        "tg": ("Супориши аввал", "Супориши аввалини худро иҷро кунед.", "Шумо супориши аввалро иҷро кардед."),
        "zh": ("第一个任务", "完成你的第一个任务。", "你完成了第一个任务。"),
    },
    "duel_win": {
        "en": ("First Duel Victory", "Win a duel.", "Won your first duel."),
        "ru": ("Первая победа в дуэли", "Победите в дуэли.", "Вы выиграли первую дуэль."),
        "tg": ("Ғалабаи аввал дар дуэл", "Дар дуэл ғолиб шавед.", "Шумо дар дуэли аввал ғолиб шудед."),
        "zh": ("首次对决胜利", "赢得一场对决。", "你赢得了第一场对决。"),
    },
}

# "N more <unit> to unlock this." -- i18next plural forms per locale.
LEFT = {
    "words": {"en": ("{{count}} more word to unlock this.", "{{count}} more words to unlock this."),
              "ru": ("Ещё {{count}} слово — и оно ваше.", "Ещё {{count}} слова — и оно ваше.", "Ещё {{count}} слов — и оно ваше."),
              "tg": ("Боз {{count}} калима то кушода шудан.",),
              "zh": ("再学 {{count}} 个词就能解锁。",)},
    "chars": {"en": ("{{count}} more character to unlock this.", "{{count}} more characters to unlock this."),
              "ru": ("Ещё {{count}} иероглиф — и оно ваше.", "Ещё {{count}} иероглифа — и оно ваше.", "Ещё {{count}} иероглифов — и оно ваше."),
              "tg": ("Боз {{count}} иероглиф то кушода шудан.",),
              "zh": ("再学 {{count}} 个汉字就能解锁。",)},
    "traces": {"en": ("{{count}} more character to trace.", "{{count}} more characters to trace."),
               "ru": ("Осталось прописать {{count}} иероглиф.", "Осталось прописать {{count}} иероглифа.", "Осталось прописать {{count}} иероглифов."),
               "tg": ("Боз {{count}} иероглиф барои навиштан.",),
               "zh": ("再描写 {{count}} 个汉字。",)},
    "lessons": {"en": ("{{count}} more lesson to unlock this.", "{{count}} more lessons to unlock this."),
                "ru": ("Ещё {{count}} урок — и оно ваше.", "Ещё {{count}} урока — и оно ваше.", "Ещё {{count}} уроков — и оно ваше."),
                "tg": ("Боз {{count}} дарс то кушода шудан.",),
                "zh": ("再完成 {{count}} 节课就能解锁。",)},
    "rounds": {"en": ("{{count}} more round to unlock this.", "{{count}} more rounds to unlock this."),
               "ru": ("Ещё {{count}} раунд — и оно ваше.", "Ещё {{count}} раунда — и оно ваше.", "Ещё {{count}} раундов — и оно ваше."),
               "tg": ("Боз {{count}} давр то кушода шудан.",),
               "zh": ("再完成 {{count}} 轮就能解锁。",)},
    "answers": {"en": ("{{count}} more correct answer to unlock this.", "{{count}} more correct answers to unlock this."),
                "ru": ("Ещё {{count}} правильный ответ — и оно ваше.", "Ещё {{count}} правильных ответа — и оно ваше.",
                       "Ещё {{count}} правильных ответов — и оно ваше."),
                "tg": ("Боз {{count}} ҷавоби дуруст то кушода шудан.",),
                "zh": ("再答对 {{count}} 题就能解锁。",)},
    "turns": {"en": ("{{count}} more time speaking out loud.", "{{count}} more times speaking out loud."),
              "ru": ("Ещё {{count}} раз скажите вслух.", "Ещё {{count}} раза скажите вслух.", "Ещё {{count}} раз скажите вслух."),
              "tg": ("Боз {{count}} бор бо овози баланд гӯед.",),
              "zh": ("再大声说 {{count}} 次。",)},
    "stories": {"en": ("{{count}} more story to unlock this.", "{{count}} more stories to unlock this."),
                "ru": ("Ещё {{count}} история — и оно ваше.", "Ещё {{count}} истории — и оно ваше.", "Ещё {{count}} историй — и оно ваше."),
                "tg": ("Боз {{count}} ҳикоя то кушода шудан.",),
                "zh": ("再读 {{count}} 个故事就能解锁。",)},
    "cases": {"en": ("{{count}} more case to unlock this.", "{{count}} more cases to unlock this."),
              "ru": ("Ещё {{count}} дело — и оно ваше.", "Ещё {{count}} дела — и оно ваше.", "Ещё {{count}} дел — и оно ваше."),
              "tg": ("Боз {{count}} парванда то кушода шудан.",),
              "zh": ("再破 {{count}} 个案件就能解锁。",)},
    "days": {"en": ("{{count}} more day to unlock this.", "{{count}} more days to unlock this."),
             "ru": ("Ещё {{count}} день — и оно ваше.", "Ещё {{count}} дня — и оно ваше.", "Ещё {{count}} дней — и оно ваше."),
             "tg": ("Боз {{count}} рӯз то кушода шудан.",),
             "zh": ("再坚持 {{count}} 天就能解锁。",)},
    "mistakes": {"en": ("{{count}} more mistake to fix.", "{{count}} more mistakes to fix."),
                 "ru": ("Осталось исправить {{count}} ошибку.", "Осталось исправить {{count}} ошибки.", "Осталось исправить {{count}} ошибок."),
                 "tg": ("Боз {{count}} хато барои ислоҳ.",),
                 "zh": ("再改正 {{count}} 个错误。",)},
    "xp": {"en": ("{{count}} more XP to unlock this.", "{{count}} more XP to unlock this."),
           "ru": ("Ещё {{count}} XP — и оно ваше.", "Ещё {{count}} XP — и оно ваше.", "Ещё {{count}} XP — и оно ваше."),
           "tg": ("Боз {{count}} XP то кушода шудан.",),
           "zh": ("再获得 {{count}} XP 就能解锁。",)},
    "level": {"en": ("{{count}} more bond level to go.", "{{count}} more bond levels to go."),
              "ru": ("Ещё {{count}} уровень дружбы.", "Ещё {{count}} уровня дружбы.", "Ещё {{count}} уровней дружбы."),
              "tg": ("Боз {{count}} сатҳи дӯстӣ.",),
              "zh": ("亲密度再升 {{count}} 级。",)},
    "rules": {"en": ("{{count}} more rule to teach.", "{{count}} more rules to teach."),
              "ru": ("Осталось научить {{count}} правилу.", "Осталось научить {{count}} правилам.", "Осталось научить {{count}} правилам."),
              "tg": ("Боз {{count}} қоида барои омӯзондан.",),
              "zh": ("再教 {{count}} 条规则。",)},
    "places": {"en": ("{{count}} more place to open.", "{{count}} more places to open."),
               "ru": ("Осталось открыть {{count}} место.", "Осталось открыть {{count}} места.", "Осталось открыть {{count}} мест."),
               "tg": ("Боз {{count}} ҷой барои кушодан.",),
               "zh": ("再开启 {{count}} 个地点。",)},
}

COMMON = {
    "progress": ("Progress", "Прогресс", "Пешрафт", "进度"),
    "leftPercent": ("Now {{value}}% · goal {{target}}%.", "Сейчас {{value}}% · цель {{target}}%.",
                    "Ҳоло {{value}}% · ҳадаф {{target}}%.", "现在 {{value}}% · 目标 {{target}}%。"),
    "toast.one": ("Achievement unlocked!", "Достижение получено!", "Дастовард ба даст омад!", "解锁成就！"),
    "toast.view": ("See achievements", "К достижениям", "Дидани дастовардҳо", "查看成就"),
    "toast.close": ("Close", "Закрыть", "Пӯшидан", "关闭"),
    "page.subtitle": ("Every achievement comes from something you really did in Chinese.",
                      "Каждое достижение — за то, что вы действительно сделали на китайском.",
                      "Ҳар дастовард барои коре аст, ки шумо воқеан бо забони чинӣ кардед.",
                      "每个成就都来自你真正用中文做过的事。"),
    "page.close": ("Almost there", "Почти получено", "Қариб ба даст омад", "就差一点"),
    "page.closeHint": ("You've already started these.", "Вы уже начали их.", "Шумо инҳоро аллакай оғоз кардаед.", "这些你已经开始了。"),
    "page.tryNext": ("Try next", "Попробуйте дальше", "Минбаъд кӯшиш кунед", "下一步试试"),
    "page.tryNextHint": ("One real step each: these unlock the first time you do them.",
                         "По одному настоящему шагу: они открываются, как только вы сделаете это впервые.",
                         "Ҳар кадом як қадами воқеӣ: бори аввал ки иҷро кунед, кушода мешаванд.",
                         "每个只需真正做一次：第一次完成就会解锁。"),
    "page.achieved": ("Achieved", "Получено", "Ба даст омад", "已获得"),
    "page.toEarn": ("Still to earn", "Ещё впереди", "Ҳанӯз дар пеш", "尚未获得"),
    "page.go": ("Go", "Перейти", "Гузаштан", "去完成"),
    "page.done": ("Done", "Готово", "Тайёр", "已完成"),
    "page.all": ("All", "Все", "Ҳама", "全部"),
    "page.filter": ("Show", "Показать", "Нишон додан", "显示"),
    "dashboard.title": ("Next achievements", "Ближайшие достижения", "Дастовардҳои наздик", "下一个成就"),
    "dashboard.all": ("All achievements", "Все достижения", "Ҳамаи дастовардҳо", "全部成就"),
    "cat.start": ("First steps", "Первые шаги", "Қадамҳои аввал", "第一步"),
    "cat.places": ("Special places", "Особые места", "Ҷойҳои махсус", "特别的地方"),
    "cat.words": ("Words", "Слова", "Калимаҳо", "词汇"),
    "cat.characters": ("Characters", "Иероглифы", "Иероглифҳо", "汉字"),
    "cat.listening": ("Listening", "Аудирование", "Шунавоӣ", "听力"),
    "cat.speaking": ("Speaking", "Говорение", "Гуфтор", "口语"),
    "cat.reading": ("Reading", "Чтение", "Хониш", "阅读"),
    "cat.stories": ("Stories", "Истории", "Ҳикояҳо", "故事"),
    "cat.hsk": ("Lessons & HSK", "Уроки и HSK", "Дарсҳо ва HSK", "课程与 HSK"),
    "cat.review": ("Review", "Повторение", "Такрор", "复习"),
    "cat.habit": ("Habit", "Привычка", "Одат", "习惯"),
    "cat.companion": ("Companion", "Компаньон", "Ҳамроҳ", "伙伴"),
    "cat.world": ("World", "Мир", "Ҷаҳон", "世界"),
}
TOAST_MANY = {"en": ("{{count}} achievement unlocked!", "{{count}} achievements unlocked!"),
              "ru": ("Получено {{count}} достижение!", "Получено {{count}} достижения!", "Получено {{count}} достижений!"),
              "tg": ("{{count}} дастовард ба даст омад!",),
              "zh": ("解锁了 {{count}} 个成就！",)}

PLURAL_FORMS = {"en": ("one", "other"), "ru": ("one", "few", "many"), "tg": ("other",), "zh": ("other",)}


def plural(d, key, forms, lang):
    names = PLURAL_FORMS[lang]
    for name, text in zip(names, forms):
        d[f"{key}_{name}"] = text
    if lang == "ru":
        d[f"{key}_other"] = forms[2]  # fractional/fallback form
    if lang == "tg":
        d[f"{key}_one"] = forms[0]  # Tajik i18next rule has one/other; same wording


def build(lang):
    i = LANGS.index(lang)
    out = {"items": {}, "left": {}}
    for code, per in ITEMS.items():
        title, how, done = per[lang]
        out["items"][code] = {"title": title, "how": how, "done": done}
    for unit, per in LEFT.items():
        plural(out["left"], unit, per[lang], lang)
    for key, vals in COMMON.items():
        node = out
        *parents, leaf = key.split(".")
        for p in parents:
            node = node.setdefault(p, {})
        node[leaf] = vals[i]
    plural(out["toast"], "many", TOAST_MANY[lang], lang)
    return out


# Keys the UI builds dynamically (registered with check_i18n_keys.py).
KEYS = ([f"achievements.items.{c}.{f}" for c in ITEMS for f in ("title", "how", "done")]
        + [f"achievements.left.{u}" for u in LEFT]
        + [f"achievements.cat.{k.split('.', 1)[1]}" for k in COMMON if k.startswith("cat.")])


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["achievements"] = build(lang)
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated {lang}.json")
