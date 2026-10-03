# -*- coding: utf-8 -*-
"""Chinese Stories as a reading library: every UI string of the library,
book page, reader and reading help in all four locales (en/ru/tg/zh),
plus the Passport events and Companion memory that come from reading.
The stories themselves are Chinese content files, not UI strings.

Replaces the whole `stories` block (the single-page story strings are
gone with that page). Idempotent. Run from frontend/: python scripts/add_library_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")
LANGS = ("en", "ru", "tg", "zh")

TOPICS = {
    "daily": ("Daily life", "Повседневность", "Ҳаёти ҳаррӯза", "日常生活"),
    "family": ("Family", "Семья", "Оила", "家庭"),
    "friends": ("Friends", "Друзья", "Дӯстон", "朋友"),
    "school": ("School", "Учёба", "Таҳсил", "校园"),
    "food": ("Food", "Еда", "Хӯрок", "美食"),
    "shopping": ("Shopping", "Покупки", "Харид", "购物"),
    "travel": ("Travel", "Путешествия", "Сафар", "旅行"),
    "city": ("City", "Город", "Шаҳр", "城市"),
    "work": ("Work", "Работа", "Кор", "工作"),
    "culture": ("Culture", "Культура", "Фарҳанг", "文化"),
    "nature": ("Nature", "Природа", "Табиат", "自然"),
    "history": ("History", "История", "Таърих", "历史"),
    "relationships": ("Relationships", "Отношения", "Муносибатҳо", "情感"),
    "adventure": ("Adventure", "Приключения", "Моҷаро", "冒险"),
    "mystery": ("Mystery", "Загадки", "Асрор", "悬疑"),
    "humor": ("Humour", "Юмор", "Ҳаҷв", "幽默"),
    "society": ("Society", "Общество", "Ҷамъият", "社会"),
    "science": ("Science", "Наука", "Илм", "科学"),
}


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


# Plural strings: en (one, other), ru (one, few, many), tg (one/other), zh (other).
def P(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh, "_plural": True}


S = {
    "eyebrow": L("Chinese Stories", "Китайские истории", "Ҳикояҳои чинӣ", "中文故事"),
    "title": L("Read Chinese books", "Читайте книги на китайском", "Китобҳои чиниро хонед", "读中文书"),
    "subtitle": L("A library of books written in Chinese for every HSK level. Read the Chinese first — tap a word or select a sentence whenever you need help.",
                  "Библиотека книг на китайском для каждого уровня HSK. Сначала читайте по-китайски — нажмите на слово или выделите предложение, когда нужна помощь.",
                  "Китобхонаи китобҳо бо забони чинӣ барои ҳар сатҳи HSK. Аввал бо чинӣ хонед — ҳар вақте ки кӯмак лозим аст, калимаро пахш кунед ё ҷумларо ҷудо кунед.",
                  "为每个 HSK 等级准备的中文书库。先读中文——需要帮助时，点一个词或选一句话。"),
    "kpi": {
        "completed": L("Books read", "Прочитано книг", "Китобҳои хондашуда", "已读完"),
        "reading": L("Reading now", "Читаю сейчас", "Ҳоло мехонам", "正在读"),
        "library": L("In the library", "В библиотеке", "Дар китобхона", "书库藏书"),
        "level": L("Your level", "Ваш уровень", "Сатҳи шумо", "你的等级"),
    },
    "continue": {
        "title": L("Continue reading", "Продолжить чтение", "Хонданро идома диҳед", "继续阅读"),
        "cta": L("Continue reading", "Продолжить чтение", "Идомаи хондан", "继续阅读"),
    },
    "recommended": {
        "title": L("Recommended for you", "Рекомендуем вам", "Барои шумо тавсия", "为你推荐"),
        "cta": L("Open the book", "Открыть книгу", "Китобро кушодан", "打开这本书"),
    },
    "levels": L("HSK levels", "Уровни HSK", "Сатҳҳои HSK", "HSK 等级"),
    "status": {
        "locked": L("Available at HSK {{level}}", "Доступно с HSK {{level}}", "Аз HSK {{level}} дастрас", "HSK {{level}} 开放"),
        "completed": L("Read", "Прочитано", "Хонда шуд", "已读完"),
    },
    "lockedHow": L("These books open when you reach this level on your HSK journey.",
                   "Эти книги откроются, когда вы дойдёте до этого уровня на своём пути HSK.",
                   "Ин китобҳо вақте кушода мешаванд, ки шумо дар роҳи HSK ба ин сатҳ мерасед.",
                   "当你在 HSK 之路上达到这个等级时，这些书就会开放。"),
    "lockedCta": L("Continue your HSK journey", "Продолжить путь HSK", "Идомаи роҳи HSK", "继续你的 HSK 之路"),
    "filter": {
        "label": L("Filter books", "Фильтр книг", "Филтри китобҳо", "筛选图书"),
        "all": L("All", "Все", "Ҳама", "全部"),
        "new": L("Not started", "Не начаты", "Оғоз нашуда", "未开始"),
        "in_progress": L("In progress", "Читаю", "Дар ҷараён", "在读"),
        "completed": L("Read", "Прочитаны", "Хонда шуд", "已读完"),
        "topic": L("Topic", "Тема", "Мавзӯъ", "主题"),
        "anyTopic": L("All topics", "Все темы", "Ҳамаи мавзӯъҳо", "全部主题"),
        "time": L("Reading time", "Время чтения", "Вақти хондан", "阅读时间"),
        "time_any": L("Any length", "Любая длина", "Ҳар дарозӣ", "不限"),
        "time_short": L("Up to {{count}} min", "До {{count}} мин", "То {{count}} дақ", "{{count}} 分钟以内"),
        "time_long": L("Over {{count}} min", "Больше {{count}} мин", "Зиёда аз {{count}} дақ", "{{count}} 分钟以上"),
    },
    "empty": L("No books at this level yet — more are being added to the library.",
               "На этом уровне пока нет книг — библиотека пополняется.",
               "Дар ин сатҳ ҳоло китоб нест — китобхона пур карда мешавад.",
               "这个等级还没有书——书库正在不断增加新书。"),
    "emptyFilter": L("No books match these filters.", "Нет книг с такими фильтрами.", "Бо ин филтрҳо китоб нест.", "没有符合条件的书。"),
    "why": L("Reading connected Chinese turns separate words into real understanding. Every book is written in Chinese for its level; translations are help you ask for, not the text.",
             "Чтение связного текста превращает отдельные слова в настоящее понимание. Каждая книга написана по-китайски для своего уровня; перевод — это помощь по запросу, а не текст.",
             "Хондани матни пайваста калимаҳои алоҳидаро ба фаҳмиши воқеӣ табдил медиҳад. Ҳар китоб барои сатҳи худ бо забони чинӣ навишта шудааст; тарҷума кӯмак аст, на худи матн.",
             "阅读连贯的中文，能把零散的词变成真正的理解。每本书都是为相应等级用中文写的；翻译只是你需要时的帮助，而不是正文。"),
    "card": {
        "chapters": P(("{{count}} chapter", "{{count}} chapters"), ("{{count}} глава", "{{count}} главы", "{{count}} глав"),
                      "{{count}} боб", "{{count}} 章"),
        "minutes": P(("≈ {{count}} min", "≈ {{count}} min"), ("≈ {{count}} мин", "≈ {{count}} мин", "≈ {{count}} мин"),
                     "≈ {{count}} дақ", "约 {{count}} 分钟"),
        "newWords": P(("{{count}} new word", "{{count}} new words"), ("{{count}} новое слово", "{{count}} новых слова", "{{count}} новых слов"),
                      "{{count}} калимаи нав", "{{count}} 个生词"),
        "where": L("Chapter {{chapter}} of {{total}} · {{percent}}%", "Глава {{chapter}} из {{total}} · {{percent}}%",
                   "Боби {{chapter}} аз {{total}} · {{percent}}%", "第 {{chapter}} 章 / 共 {{total}} 章 · {{percent}}%"),
    },
    "topic": {k: L(*v) for k, v in TOPICS.items()},
    "difficulty": {
        "easy": L("Easier", "Полегче", "Осонтар", "较容易"),
        "medium": L("Medium", "Средняя", "Миёна", "中等"),
        "challenging": L("Challenging", "Посложнее", "Душвортар", "有挑战"),
    },
    "back": L("Library", "Библиотека", "Китобхона", "书库"),
    "book": {
        "start": L("Start reading", "Начать читать", "Хонданро оғоз кунед", "开始阅读"),
        "continue": L("Continue reading", "Продолжить чтение", "Идомаи хондан", "继续阅读"),
        "again": L("Read again", "Перечитать", "Боз хондан", "再读一遍"),
        "chapters": L("Chapters", "Главы", "Бобҳо", "章节"),
        "minutes": L("Minutes", "Минуты", "Дақиқа", "分钟"),
        "difficulty": L("For its level", "Для своего уровня", "Барои сатҳи худ", "在本级中"),
        "check": L("Check your understanding", "Проверить понимание", "Фаҳмишро санҷед", "检查理解"),
        "words": L("Words in this book ({{count}})", "Слова книги ({{count}})", "Калимаҳои китоб ({{count}})", "本书词语（{{count}}）"),
        "wordsHint": L("Tap a word for its meaning and characters, and to add it to your review.",
                       "Нажмите на слово, чтобы увидеть значение и иероглифы и добавить его в повторение.",
                       "Калимаро пахш кунед, то маъно ва иероглифҳояшро бинед ва ба такрор илова кунед.",
                       "点一个词，看它的意思和汉字，并加入复习。"),
        "sentences": P(("{{count}} sentence", "{{count}} sentences"), ("{{count}} предложение", "{{count}} предложения", "{{count}} предложений"),
                       "{{count}} ҷумла", "{{count}} 句"),
    },
    "state": {
        "new": L("New", "Новые", "Нав", "生词"),
        "review": L("Review", "Повторить", "Такрор", "待复习"),
        "learning": L("Learning", "Изучаю", "Меомӯзам", "学习中"),
        "known": L("Known", "Знаю", "Медонам", "已掌握"),
    },
    "done": {
        "title": L("Book completed!", "Книга прочитана!", "Китоб хонда шуд!", "读完了这本书！"),
        "body": L("You read the whole book in Chinese — here is what you did along the way.",
                  "Вы прочитали всю книгу по-китайски — вот что вы сделали по пути.",
                  "Шумо тамоми китобро бо чинӣ хондед — ана он чи дар роҳ кардед.",
                  "你用中文读完了整本书——下面是你一路上做的事。"),
        "next": L("Next story", "Следующая история", "Ҳикояи навбатӣ", "下一个故事"),
        "library": L("Back to the library", "В библиотеку", "Ба китобхона", "回到书库"),
    },
    "stats": {
        "chapters": L("Chapters read", "Глав прочитано", "Бобҳои хондашуда", "读完的章节"),
        "chaptersValue": L("{{count}} of {{total}}", "{{count}} из {{total}}", "{{count}} аз {{total}}", "{{count}} / {{total}}"),
        "words": L("Words of this book you know", "Слова книги, которые вы знаете", "Калимаҳои китоб, ки медонед", "你认识的本书词语"),
        "wordsValue": L("{{count}} of {{total}}", "{{count}} из {{total}}", "{{count}} аз {{total}}", "{{count}} / {{total}}"),
        "explained": L("Times you asked for help", "Запросов помощи", "Дархостҳои кӯмак", "求助次数"),
        "lookedUp": L("Words looked up", "Слов посмотрено", "Калимаҳои дидашуда", "查过的词"),
        "listened": L("Times listened", "Прослушиваний", "Шунидан", "听的次数"),
        "rounds": L("Comprehension rounds", "Проверок понимания", "Санҷишҳои фаҳмиш", "理解练习"),
    },
    "reader": {
        "toBook": L("Book", "К книге", "Ба китоб", "回到本书"),
        "chapterOf": L("Chapter {{n}} of {{total}}", "Глава {{n}} из {{total}}", "Боби {{n}} аз {{total}}", "第 {{n}} 章 / 共 {{total}} 章"),
        "listen": L("Listen", "Слушать", "Гӯш кардан", "听"),
        "stop": L("Stop", "Стоп", "Бас", "停止"),
        "pinyin": L("Pinyin", "Пиньинь", "Пинин", "拼音"),
        "hint": L("Tap a word to look it up. Select a sentence for help.",
                  "Нажмите на слово, чтобы узнать его. Выделите предложение, чтобы получить помощь.",
                  "Калимаро пахш кунед, то маънояшро бинед. Барои кӯмак ҷумларо ҷудо кунед.",
                  "点一个词查看意思。选中一句话获得帮助。"),
        "legend": L("Word colours", "Отметки слов", "Аломатҳои калимаҳо", "词语标记"),
        "prev": L("Previous chapter", "Предыдущая глава", "Боби қаблӣ", "上一章"),
        "next": L("Next chapter", "Следующая глава", "Боби навбатӣ", "下一章"),
        "finish": L("I've read this chapter", "Я прочитал(а) главу", "Ман бобро хондам", "这一章我读完了"),
        "finishLast": L("Finish the book", "Закончить книгу", "Китобро тамом кардан", "读完这本书"),
    },
    "help": {
        "title": L("Reading help", "Помощь в чтении", "Кӯмак дар хондан", "阅读帮助"),
        "close": L("Close", "Закрыть", "Пӯшидан", "关闭"),
        "actions": L("Help with the selected text", "Помощь с выделенным текстом", "Кӯмак бо матни ҷудошуда", "选中文字的帮助"),
        "explain": L("Explain", "Объяснить", "Шарҳ", "讲解"),
        "pinyin": L("Pinyin", "Пиньинь", "Пинин", "拼音"),
        "translate": L("Translate", "Перевод", "Тарҷума", "翻译"),
        "words": L("Words", "Слова", "Калимаҳо", "词语"),
        "grammar": L("Grammar", "Грамматика", "Грамматика", "语法"),
        "loading": L("Looking at it…", "Разбираем…", "Дида мебароем…", "正在分析……"),
        "translation": L("Translation", "Перевод", "Тарҷума", "翻译"),
        "fromBook": L("from the book", "из книги", "аз китоб", "书中译文"),
        "fromAi": L("AI", "ИИ", "ЗС", "AI"),
        "noTranslation": L("No translation is available right now — the words below explain it piece by piece.",
                           "Перевод сейчас недоступен — слова ниже объясняют фразу по частям.",
                           "Ҳоло тарҷума дастрас нест — калимаҳои поён онро қисм ба қисм шарҳ медиҳанд.",
                           "现在没有译文——下面的词语会一个一个解释。"),
        "meaning": L("What it means", "Смысл", "Маъно", "意思"),
        "points": L("Notes", "Пояснения", "Шарҳҳо", "要点"),
        "example": L("Example", "Пример", "Мисол", "例句"),
        "aiNote": L("Explained by AI from the ChineseVerse word list — it can make mistakes.",
                    "Объяснение ИИ на основе словаря ChineseVerse — в нём возможны ошибки.",
                    "Шарҳи ЗС дар асоси луғати ChineseVerse — хато ҳам мешавад.",
                    "由 AI 根据 ChineseVerse 词表讲解，可能有错误。"),
        "aiOffline": L("The AI explanation isn't available right now. Everything below comes from the ChineseVerse curriculum.",
                       "Объяснение ИИ сейчас недоступно. Всё ниже — из учебной программы ChineseVerse.",
                       "Шарҳи ЗС ҳоло дастрас нест. Ҳама чизи поён аз барномаи таълимии ChineseVerse аст.",
                       "AI 讲解现在不可用。下面的内容都来自 ChineseVerse 课程。"),
        "aiLimit": L("You've asked for many AI explanations this hour. The curriculum help below still works.",
                     "За этот час вы запросили много объяснений ИИ. Помощь из учебной программы ниже по-прежнему работает.",
                     "Дар ин соат шумо шарҳҳои зиёди ЗС пурсидед. Кӯмаки барномаи таълимии поён ҳамчунон кор мекунад.",
                     "这一小时你请求了很多 AI 讲解。下面的课程帮助仍然可用。"),
        "wordList": L("Word by word", "По словам", "Калима ба калима", "逐词"),
        "grammarApp": L("Grammar in this text", "Грамматика в тексте", "Грамматика дар матн", "文中的语法"),
        "listen": L("Listen", "Слушать", "Гӯш кардан", "听"),
        "askAi": L("Explain with AI", "Объяснить с ИИ", "Шарҳ бо ЗС", "用 AI 讲解"),
        "save": L("Add new words to review", "Добавить новые слова в повторение", "Калимаҳои навро ба такрор илова кунед", "把生词加入复习"),
        "saved": P(("{{count}} word added to your review", "{{count}} words added to your review"),
                   ("{{count}} слово добавлено в повторение", "{{count}} слова добавлено в повторение", "{{count}} слов добавлено в повторение"),
                   "{{count}} калима ба такрор илова шуд", "{{count}} 个词已加入复习"),
        "practice": L("Practise this chapter", "Практика по главе", "Машқи боб", "练习这一章"),
        "name": L("name", "имя", "ном", "名字"),
        "sentence": L("Its sentence", "Предложение", "Ҷумлааш", "所在的句子"),
        "explainSentence": L("Explain this sentence", "Объяснить предложение", "Шарҳи ин ҷумла", "讲解这句话"),
    },
}

EXTRA = {
    "companionMemory.kind.reading_word": L(
        "{{name}} noticed you keep looking up {{word}} while reading — let's review it.",
        "{{name}} заметил(а), что вы часто ищете {{word}} при чтении — давайте повторим его.",
        "{{name}} пай бурд, ки ҳангоми хондан {{word}}-ро зуд-зуд мекобед — биёед онро такрор кунем.",
        "{{name}}发现你读故事时常常查“{{word}}”——我们复习一下吧。"),
    "companionMemory.action.reading_word": L("Review it", "Повторить", "Такрор кардан", "去复习"),
    "passport.event.level_book": L("Your first HSK {{level}} book: 《{{title}}》",
                                   "Ваша первая книга HSK {{level}}: 《{{title}}》",
                                   "Китоби аввалини HSK {{level}}-и шумо: 《{{title}}》",
                                   "你的第一本 HSK {{level}} 书：《{{title}}》"),
}
EXTRA_PLURAL = {
    "passport.event.books_read": P(("You have read {{count}} book", "You have read {{count}} books"),
                                   ("Прочитана {{count}} книга", "Прочитано {{count}} книги", "Прочитано {{count}} книг"),
                                   "{{count}} китоб хонда шуд", "已经读完 {{count}} 本书"),
}

FORMS = {"en": ("one", "other"), "ru": ("one", "few", "many"), "tg": ("one", "other"), "zh": ("other",)}


def put_plural(d, key, value, lang):
    forms = value[lang]
    if isinstance(forms, str):
        forms = (forms,) * len(FORMS[lang])
    for name, text in zip(FORMS[lang], forms):
        d[f"{key}_{name}"] = text
    if lang == "ru":
        d[f"{key}_other"] = forms[-1]


def build(node, lang):
    out = {}
    for k, v in node.items():
        if isinstance(v, dict) and v.get("_plural"):
            put_plural(out, k, v, lang)
        elif isinstance(v, dict) and set(v) == set(LANGS):
            out[k] = v[lang]
        else:
            out[k] = build(v, lang)
    return out


def set_path(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def keys(node, prefix="stories"):
    for k, v in node.items():
        if isinstance(v, dict) and (v.get("_plural") or set(v) == set(LANGS)):
            yield f"{prefix}.{k}"
        else:
            yield from keys(v, f"{prefix}.{k}")


# Every key this UI builds dynamically (registered with check_i18n_keys.py).
KEYS = list(keys(S)) + list(EXTRA) + list(EXTRA_PLURAL)


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["stories"] = build(S, lang)
        for k, v in EXTRA.items():
            set_path(data, k, v[lang])
        for k, v in EXTRA_PLURAL.items():
            *parents, leaf = k.split(".")
            node = data
            for p in parents:
                node = node.setdefault(p, {})
            put_plural(node, leaf, v, lang)
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated {lang}.json")
