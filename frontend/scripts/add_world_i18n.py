# -*- coding: utf-8 -*-
"""Adds the strings of the living world on /real-chinese (Живой китайский)
to all four locale files (en/ru/tg/zh). Idempotent; keeps 2-space indent
and CRLF. Run from frontend/: python scripts/add_world_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


def P(en1, en, ru1, ru2, ru5, tg, zh):
    return {"en": {"_one": en1, "_other": en}, "ru": {"_one": ru1, "_few": ru2, "_many": ru5, "_other": ru2},
            "tg": {"_one": tg, "_other": tg}, "zh": {"_other": zh}}


# key -> (name, description, enter-label or None) per locale
PLACES = {
    "home": (L("Home", "Дом", "Хона", "家"),
             L("Where your companion waits — family and daily life in Chinese.", "Здесь ждёт ваш компаньон — семья и быт по-китайски.",
               "Ҳамроҳи шумо дар ин ҷо интизор аст — оила ва ҳаёти рӯзмарра бо забони чинӣ.", "你的伙伴在这里等你——用中文聊家人和日常生活。"), None),
    "library": (L("Library", "Библиотека", "Китобхона", "图书馆"),
                L("Lessons, the HSK path and One Sentence lessons — the quiet heart of the city.",
                  "Уроки, путь HSK и уроки из одного предложения — тихое сердце города.",
                  "Дарсҳо, роҳи HSK ва дарсҳои якҷумлагӣ — дили ороми шаҳр.", "课程、HSK学习路线和一句话课堂——城市安静的中心。"),
                L("Go to lessons", "К урокам", "Ба дарсҳо", "去上课")),
    "calligraphy": (L("Calligraphy hall", "Зал каллиграфии", "Толори хушнависӣ", "书法馆"),
                    L("Characters, their structure and stroke order — and the ones that trip you up.",
                      "Иероглифы, их строение и порядок черт — и те, что даются трудно.",
                      "Иероглифҳо, сохтор ва тартиби хатҳояшон — ва онҳое, ки душворанд.", "汉字、结构和笔顺——还有你常写错的字。"),
                    L("Study characters", "Изучать иероглифы", "Омӯхтани иероглифҳо", "学习汉字")),
    "word_garden": (L("Word garden", "Сад слов", "Боғи калимаҳо", "词语花园"),
                    L("Watch Chinese words grow from characters in your Vocabulary Ecosystem.",
                      "Смотрите, как слова растут из иероглифов в экосистеме слов.",
                      "Бубинед, ки калимаҳо аз иероглифҳо дар экосистемаи калимаҳо чӣ тавр месабзанд.", "在词汇生态里看词语怎样从汉字长出来。"),
                    L("Open the Ecosystem", "Открыть экосистему", "Кушодани экосистема", "打开词汇生态")),
    "street": (L("City street", "Городская улица", "Кӯчаи шаҳр", "城市街道"),
               L("Ask for directions and find your way — left, right, nearby.", "Спросите дорогу и найдите путь — налево, направо, рядом.",
                 "Роҳро пурсед ва ёбед — чап, рост, наздик.", "问路、找路——左边、右边、附近。"), None),
    "restaurant": (L("Restaurant", "Ресторан", "Тарабхона", "饭馆"),
                   L("Order, ask the price, pay — and talk with the waiter in Chinese.", "Закажите, узнайте цену, расплатитесь — и поговорите с официантом.",
                     "Фармоиш диҳед, нархро пурсед, пардохт кунед — ва бо пешхизмат гап занед.", "点菜、问价、付钱——用中文和服务员聊天。"), None),
    "shop": (L("Corner shop", "Магазин у дома", "Мағозаи наздик", "便利店"),
             L("Prices, money and buying the everyday things.", "Цены, деньги и покупка повседневных вещей.",
               "Нархҳо, пул ва харидани чизҳои ҳаррӯза.", "价格、钱和买日用品。"), None),
    "shopping_district": (L("Shopping district", "Торговый квартал", "Маҳаллаи савдо", "购物街"),
                          L("Sizes, colours and discounts — shop like a local.", "Размеры, цвета и скидки — покупайте как местные.",
                            "Андоза, ранг ва тахфиф — мисли сокинон харид кунед.", "尺码、颜色、打折——像本地人一样购物。"), None),
    "internet_cafe": (L("Internet café", "Интернет-кафе", "Интернет-қаҳвахона", "网吧"),
                      L("News, posts, reviews and chats — real online Chinese, adapted for you.",
                        "Новости, посты, отзывы и чаты — настоящий онлайн-китайский, адаптированный для вас.",
                        "Хабарҳо, паёмҳо, назарҳо ва чатҳо — чинии онлайни воқеӣ, барои шумо мутобиқ.", "新闻、帖子、点评、聊天——为你改写的真实网络中文。"),
                      L("Open Chinese Internet", "Открыть китайский интернет", "Кушодани интернети чинӣ", "打开中文网络")),
    "detective": (L("Detective agency", "Детективное агентство", "Агентии детективӣ", "侦探社"),
                  L("Mysteries solved by reading and listening to Chinese clues.", "Загадки, которые раскрываются чтением и слушанием улик на китайском.",
                    "Сирҳое, ки бо хондан ва шунидани далелҳои чинӣ ҳал мешаванд.", "通过读和听中文线索来破案。"),
                  L("Open a case", "Открыть дело", "Кушодани парванда", "开始破案")),
    "sound_plaza": (L("Sound plaza", "Площадь звуков", "Майдони садоҳо", "声音广场"),
                    L("Stand in busy places and follow the voices around you — from slow to native speed.",
                      "Окажитесь в людных местах и следите за голосами вокруг — от медленной речи до носителей.",
                      "Дар ҷойҳои серодам истед ва овозҳои атрофро пайгирӣ кунед — аз оҳиста то суръати забондонҳо.",
                      "站在热闹的地方，听身边的人说话——从慢速到母语速度。"),
                    L("Go to Sound World", "В Мир звуков", "Ба Олами садоҳо", "去声音世界")),
    "passport_office": (L("Passport office", "Паспортный стол", "Идораи шиноснома", "护照办公室"),
                        L("Your Chinese Passport: what you can really do, with the evidence and your story.",
                          "Ваш китайский паспорт: что вы действительно умеете, с доказательствами и вашей историей.",
                          "Шиносномаи чинии шумо: шумо воқеан чӣ карда метавонед, бо далелҳо ва таърихатон.",
                          "你的中文护照：你真正能做什么，有依据，也有你的故事。"),
                        L("Open my Passport", "Открыть паспорт", "Кушодани шиноснома", "打开我的护照")),
    "university": (L("University", "Университет", "Донишгоҳ", "大学"),
                   L("Classes, classrooms and classmates — campus life in Chinese.", "Занятия, аудитории и однокурсники — студенческая жизнь по-китайски.",
                     "Дарсҳо, синфхонаҳо ва ҳамкурсон — ҳаёти донишҷӯӣ бо забони чинӣ.", "上课、教室、同学——用中文过校园生活。"), None),
    "hospital": (L("Hospital", "Больница", "Беморхона", "医院"),
                 L("Describe how you feel and understand the doctor.", "Опишите самочувствие и поймите врача.",
                   "Ҳолатонро тасвир кунед ва духтурро фаҳмед.", "说说哪里不舒服，听懂医生的话。"), None),
    "office": (L("Office tower", "Бизнес-центр", "Маркази корӣ", "写字楼"),
               L("Job interviews and working life.", "Собеседования и рабочая жизнь.", "Мусоҳибаҳои корӣ ва ҳаёти корӣ.", "求职面试和工作生活。"), None),
    "train_station": (L("Train station", "Вокзал", "Истгоҳи роҳи оҳан", "火车站"),
                      L("Tickets, departure times and platforms.", "Билеты, время отправления и платформы.",
                        "Чиптаҳо, вақти ҳаракат ва платформаҳо.", "车票、发车时间和站台。"), None),
    "hotel": (L("Hotel", "Гостиница", "Меҳмонхона", "酒店"),
              L("Check in, breakfast and asking for help.", "Заселение, завтрак и просьбы о помощи.",
                "Ҷойгиршавӣ, наҳорӣ ва хоҳиши кӯмак.", "办入住、问早饭、请人帮忙。"), None),
    "old_town": (L("Old town", "Старый город", "Шаҳри қадим", "古城"),
                 L("Sightseeing with a guide, photos, tickets and local customs.", "Экскурсии с гидом, фото, билеты и местные обычаи.",
                   "Гардиш бо роҳбалад, аксҳо, чиптаҳо ва урфу одати маҳаллӣ.", "跟导游游览、拍照、买门票、了解风俗。"), None),
    "airport": (L("Airport", "Аэропорт", "Фурудгоҳ", "机场"),
                L("Check in, luggage and flights — and what to do when plans change.", "Регистрация, багаж и рейсы — и что делать, если планы меняются.",
                  "Бақайдгирӣ, бағоҷ ва парвозҳо — ва чӣ бояд кард, агар нақшаҳо тағйир ёбанд.", "值机、行李、航班——计划有变时怎么办。"), None),
}

TOPICS = {
    "family": L("Family", "Семья", "Оила", "家人"), "daily": L("Daily routine", "Распорядок дня", "Тартиби рӯз", "日常生活"),
    "directions": L("Directions", "Направления", "Самтҳо", "方向"), "nearby": L("What's nearby", "Что рядом", "Чӣ наздик аст", "附近有什么"),
    "order": L("Ordering", "Заказ", "Фармоиш", "点菜"), "price": L("Asking the price", "Узнать цену", "Пурсидани нарх", "问价钱"),
    "taste": L("Taste & recommendations", "Вкус и советы", "Таъм ва тавсия", "口味和推荐"),
    "bargain": L("Bargaining", "Торг", "Савдо кардан", "讲价"), "buy_sell": L("Buying & selling", "Купить и продать", "Харидан ва фурӯхтан", "买和卖"),
    "size": L("Sizes", "Размеры", "Андозаҳо", "尺码"), "colour": L("Colours", "Цвета", "Рангҳо", "颜色"), "discount": L("Discounts", "Скидки", "Тахфифҳо", "打折"),
    "schedule": L("Class times", "Расписание", "Ҷадвали дарсҳо", "上课时间"), "classroom": L("Classrooms", "Аудитории", "Синфхонаҳо", "教室"),
    "introduce": L("Introductions", "Знакомство", "Шиносоӣ", "介绍"), "symptoms": L("How you feel", "Самочувствие", "Ҳолати шумо", "身体感觉"),
    "doctor": L("At the doctor's", "У врача", "Назди духтур", "看医生"), "medicine": L("Medicine", "Лекарства", "Доруҳо", "吃药"),
    "interview": L("Interviews", "Собеседование", "Мусоҳиба", "面试"), "work": L("At work", "На работе", "Дар кор", "工作"),
    "ticket": L("Tickets", "Билеты", "Чиптаҳо", "买票"), "time": L("Departure times", "Время отправления", "Вақти ҳаракат", "发车时间"),
    "boarding": L("Boarding", "Посадка", "Саворшавӣ", "上车"), "check_in": L("Checking in", "Регистрация и заселение", "Бақайдгирӣ", "登记入住"),
    "breakfast": L("Breakfast", "Завтрак", "Наҳорӣ", "早饭"), "help": L("Asking for help", "Просьба о помощи", "Хоҳиши кӯмак", "请人帮忙"),
    "sightseeing": L("Sightseeing", "Достопримечательности", "Гардиш", "参观游览"), "photos": L("Photos & views", "Фото и виды", "Акс ва манзара", "拍照看风景"),
    "tickets": L("Entry tickets", "Входные билеты", "Чиптаҳои даромад", "门票"), "flight": L("Flights", "Рейсы", "Парвозҳо", "航班"),
}

S = {
    "world.title": L("Your living Chinese city", "Ваш живой китайский город", "Шаҳри зиндаи чинии шумо", "你的中文城市"),
    "world.subtitle": L(
        "Every place is a real way to use Chinese. Places open, light up and fill with people as you learn — the city grows because you do.",
        "Каждое место — настоящий способ говорить по-китайски. Места открываются, оживают и наполняются людьми по мере учёбы — город растёт, потому что растёте вы.",
        "Ҳар ҷой роҳи воқеии истифодаи забони чинӣ аст. Ҷойҳо бо омӯзиши шумо кушода мешаванд, равшан мешаванд ва пур аз одамон мешаванд — шаҳр меафзояд, зеро шумо меафзоед.",
        "每个地方都是使用中文的真实场景。随着你的学习，地方会开放、点亮、热闹起来——城市因你的成长而成长。"),
    "world.loading": L("Walking into the city…", "Входим в город…", "Ба шаҳр медароем…", "正在走进城市……"),
    "world.mapLabel": L("Map of your Chinese city", "Карта вашего китайского города", "Харитаи шаҳри чинии шумо", "你的中文城市地图"),
    "world.passportLink": L("Open your Chinese Passport", "Открыть китайский паспорт", "Кушодани шиносномаи чинӣ", "打开中文护照"),
    "world.explored": L("Places explored", "Изучено мест", "Ҷойҳои омӯхташуда", "已探索地点"),
    "world.scenesDone": L("Scenes completed", "Пройдено сцен", "Саҳнаҳои тамомшуда", "已完成场景"),
    "world.skillsShown": L("Skills shown", "Навыков подтверждено", "Малакаҳои исботшуда", "已证明能力"),
    "world.allPlaces": L("All places", "Все места", "Ҳамаи ҷойҳо", "所有地点"),
    "world.pickPlace": L("Tap a place on the map.", "Нажмите на место на карте.", "Ҷойро дар харита пахш кунед.", "点击地图上的地点。"),
    "world.companionTitle": L("{{name}} travels with you", "{{name}} путешествует с вами", "{{name}} бо шумо сафар мекунад", "{{name}}和你一起旅行"),
    "world.district.home": L("Home quarter", "Домашний квартал", "Маҳаллаи хона", "家附近"),
    "world.district.centre": L("City centre", "Центр города", "Маркази шаҳр", "市中心"),
    "world.district.campus": L("Campus & work", "Кампус и работа", "Донишгоҳ ва кор", "校园和工作"),
    "world.district.travel": L("Travel", "Путешествия", "Сафар", "出行"),
    "world.status.locked": L("Locked", "Закрыто", "Пӯшида", "未开放"),
    "world.status.open": L("Open", "Открыто", "Кушода", "已开放"),
    "world.status.explored": L("Explored", "Изучено", "Омӯхта шуд", "已探索"),
    "world.status.mastered": L("Mastered", "Освоено", "Азхудшуда", "已掌握"),
    "world.wordsKnown": L("{{known}}/{{total}} words known", "знакомо слов: {{known}}/{{total}}", "{{known}}/{{total}} калима маълум", "已会{{known}}/{{total}}个词"),
    "world.companion.locked": L("This place opens at HSK {{level}} — or sooner, once you really know words like {{words}}.",
                                "Это место откроется на HSK {{level}} — или раньше, когда вы по-настоящему выучите слова вроде {{words}}.",
                                "Ин ҷо дар HSK {{level}} кушода мешавад — ё барвақттар, вақте калимаҳое мисли {{words}}-ро воқеан омӯзед.",
                                "这里在HSK {{level}}级开放——如果你真正学会{{words}}这些词，会更早开放。"),
    "world.companion.fresh": L("A new place — let's take a look around together.", "Новое место — давайте осмотримся вместе.",
                               "Ҷои нав — биёед якҷоя атрофро бубинем.", "新地方——我们一起去看看吧。"),
    "world.companion.freshTopics": L("We haven't been here yet. Your words already light up {{lit}} of {{total}} topics here.",
                                     "Мы здесь ещё не были. Ваши слова уже открывают {{lit}} из {{total}} тем.",
                                     "Мо ҳанӯз дар ин ҷо набудем. Калимаҳои шумо аллакай {{lit}} аз {{total}} мавзӯъро равшан мекунанд.",
                                     "我们还没来过这里。你学过的词已经点亮了{{total}}个话题中的{{lit}}个。"),
    "world.companion.openedByWords": L("You opened this place early — by learning its words. Let's use them!",
                                       "Вы открыли это место раньше срока — выучив его слова. Давайте их применим!",
                                       "Шумо ин ҷоро пеш аз мӯҳлат кушодед — бо омӯхтани калимаҳояш. Биёед онҳоро истифода барем!",
                                       "你学会了这里的词，提前打开了这个地方。我们来用用吧！"),
    "world.companion.explored": L("We've been here — your best conversation was {{score}}%. One more to master it?",
                                  "Мы уже были здесь — ваш лучший результат {{score}}%. Ещё разок, чтобы освоить?",
                                  "Мо дар ин ҷо будем — беҳтарин натиҷаи шумо {{score}}%. Боз як бор барои азхудкунӣ?",
                                  "我们来过这里——你最好的成绩是{{score}}%。再来一次就能掌握了？"),
    "world.companion.exploredOther": L("We've been here before — there's more to discover.", "Мы здесь уже бывали — есть что открыть ещё.",
                                       "Мо пештар дар ин ҷо будем — боз чизҳои нав ҳаст.", "我们来过这里——还有更多可以发现。"),
    "world.companion.mastered": L("You've mastered this place — {{score}}% and most of its words. I'm proud of you!",
                                  "Вы освоили это место — {{score}}% и большинство его слов. Я горжусь вами!",
                                  "Шумо ин ҷоро аз худ кардед — {{score}}% ва аксари калимаҳояш. Ман аз шумо фахр мекунам!",
                                  "你已经掌握了这里——{{score}}%，大部分词也会了。我为你骄傲！"),
    "world.toOpen": L("How to open it", "Как открыть", "Чӣ тавр кушодан", "怎样打开"),
    "world.toOpenText": L("Reach HSK {{level}}, or really learn a few of these words:", "Достигните HSK {{level}} или по-настоящему выучите несколько этих слов:",
                          "Ба HSK {{level}} расед ё чанд калимаи зеринро воқеан омӯзед:", "达到HSK {{level}}级，或者真正学会下面几个词："),
    "world.learnThem": L("Learn them in a One Sentence lesson", "Выучить в уроке из одного предложения", "Дар дарси якҷумлагӣ омӯзед", "用一句话课堂学会它们"),
    "world.tapWords": L("Tap a word to explore it.", "Нажмите на слово, чтобы разобрать его.", "Барои омӯхтан калимаро пахш кунед.", "点击词语查看。"),
    "world.sceneStart": L("Start the conversation", "Начать разговор", "Оғози сӯҳбат", "开始对话"),
    "world.sceneAgain": L("Talk again", "Поговорить снова", "Боз гап задан", "再聊一次"),
    "world.sceneDetails": L("What you'll practise", "Что вы потренируете", "Шумо чиро машқ мекунед", "要练什么"),
    "world.sceneRecord": P("Best {{best}}% after {{count}} conversation", "Best {{best}}% after {{count}} conversations",
                           "Лучший результат {{best}}% за {{count}} разговор", "Лучший результат {{best}}% за {{count}} разговора",
                           "Лучший результат {{best}}% за {{count}} разговоров", "Беҳтарин {{best}}% пас аз {{count}} сӯҳбат",
                           "{{count}}次对话，最佳{{best}}%"),
    "world.sceneNew": P("{{count}} exchange at your level", "{{count}} exchanges at your level", "{{count}} реплика на вашем уровне",
                        "{{count}} реплики на вашем уровне", "{{count}} реплик на вашем уровне", "{{count}} гуфтугӯ дар сатҳи шумо",
                        "按你的水平共{{count}}轮对话"),
    "world.people": L("People to talk to", "С кем поговорить", "Бо кӣ гап задан", "可以聊天的人"),
    "world.talked": L("talked", "говорили", "гап задед", "聊过"),
    "world.topics": L("What you can talk about here", "О чём здесь можно говорить", "Дар ин ҷо дар бораи чӣ гап задан мумкин", "在这里能聊什么"),
    "world.topicLit": L("ready", "готово", "омода", "可以聊"),
    "world.topicDim": L("learn its words", "выучите слова", "калимаҳоро омӯзед", "先学这些词"),
    "world.alsoHere": L("Also here", "Ещё здесь", "Инчунин дар ин ҷо", "这里还有"),
    "world.listenHere": L("Listen to the people here", "Послушать людей здесь", "Ба одамони ин ҷо гӯш диҳед", "听听这里的人说话"),
    "world.adaptTitle": L("How the city adapts to you", "Как город подстраивается под вас", "Шаҳр чӣ тавр ба шумо мутобиқ мешавад", "城市怎样适应你"),
    "world.adapt.speech.faster": L("People speak faster and more naturally — your listening is {{value}}.", "Люди говорят быстрее и естественнее — ваше аудирование {{value}}.",
                                   "Одамон тезтар ва табиӣтар гап мезананд — шунавоии шумо {{value}}.", "大家说得更快、更自然——你的听力是{{value}}。"),
    "world.adapt.speech.standard": L("People speak at your level's normal pace.", "Люди говорят в обычном темпе для вашего уровня.",
                                     "Одамон бо суръати муқаррарии сатҳи шумо гап мезананд.", "大家按你这个级别的正常语速说话。"),
    "world.adapt.speech.slower": L("People speak more slowly to support your listening ({{value}}).", "Люди говорят медленнее, чтобы помочь аудированию ({{value}}).",
                                   "Одамон барои кӯмак ба шунавоӣ оҳистатар гап мезананд ({{value}}).", "大家说得慢一些，帮助你练听力（{{value}}）。"),
    "world.adapt.words.richer": L("Scenes bring more new words — your vocabulary is {{value}}.", "В сценах больше новых слов — ваш словарь {{value}}.",
                                  "Саҳнаҳо калимаҳои нави бештар меоранд — луғати шумо {{value}}.", "场景里新词更多——你的词汇是{{value}}。"),
    "world.adapt.words.standard": L("Scenes bring the usual number of new words.", "В сценах обычное число новых слов.",
                                    "Саҳнаҳо шумораи муқаррарии калимаҳои нав доранд.", "场景里的新词数量正常。"),
    "world.adapt.words.familiar": L("Scenes stay with familiar words and fewer new ones ({{value}}).", "В сценах больше знакомых слов и меньше новых ({{value}}).",
                                    "Саҳнаҳо бештар калимаҳои шинос ва камтар нав доранд ({{value}}).", "场景以熟悉的词为主，新词少一些（{{value}}）。"),
    "world.adapt.grammar.stretch": L("You meet the next level's sentence patterns — grammar {{value}}.", "Вы встречаете конструкции следующего уровня — грамматика {{value}}.",
                                     "Шумо бо қолибҳои сатҳи навбатӣ вомехӯред — грамматика {{value}}.", "你会遇到下一级的句型——语法{{value}}。"),
    "world.adapt.grammar.standard": L("Sentence patterns match your level.", "Конструкции соответствуют вашему уровню.",
                                      "Қолибҳои ҷумла ба сатҳи шумо мувофиқанд.", "句型符合你的级别。"),
    "world.adapt.grammar.controlled": L("Patterns stay simple and get reinforced ({{value}}).", "Конструкции проще и закрепляются ({{value}}).",
                                        "Қолибҳо соддатаранд ва мустаҳкам карда мешаванд ({{value}}).", "句型简单一些，并加强练习（{{value}}）。"),
    "world.adaptNoEvidence": L("No Learning DNA evidence yet — the city uses your HSK level as it is.",
                               "Данных ДНК обучения пока нет — город использует ваш уровень HSK как есть.",
                               "Ҳоло далели ДНК-и омӯзиш нест — шаҳр сатҳи HSK-и шуморо ҳамон тавр истифода мебарад.",
                               "还没有学习DNA数据——城市先按你的HSK级别安排。"),
    "world.howTitle": L("How the city grows", "Как растёт город", "Шаҳр чӣ тавр меафзояд", "城市怎样成长"),
    "world.how": L("Places open with your HSK level — or earlier when you really know {{count}} of their words. Topics light up as their words become yours, and every completed conversation is recorded on the map and in your Passport.",
                   "Места открываются с уровнем HSK — или раньше, когда вы по-настоящему знаете {{count}} их слова. Темы оживают, когда слова становятся вашими, а каждый пройденный разговор отмечается на карте и в паспорте.",
                   "Ҷойҳо бо сатҳи HSK кушода мешаванд — ё барвақттар, вақте {{count}} калимаашонро воқеан донед. Мавзӯъҳо бо азхудшавии калимаҳо равшан мешаванд ва ҳар сӯҳбати тамомшуда дар харита ва шиноснома сабт мешавад.",
                   "地点随HSK级别开放——如果你真正学会其中{{count}}个词，会更早开放。话题会随着词语成为你的而点亮，每次完成的对话都会记录在地图和护照上。"),
    "world.openCount": L("{{open}} of {{total}} places open", "Открыто мест: {{open}} из {{total}}", "{{open}} аз {{total}} ҷой кушода", "已开放{{open}}/{{total}}个地点"),
}

for key, (name, desc, enter) in PLACES.items():
    S[f"world.place.{key}.name"] = name
    S[f"world.place.{key}.desc"] = desc
    if enter:
        S[f"world.place.{key}.enter"] = enter
for key, label in TOPICS.items():
    S[f"world.topic.{key}"] = label


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
            value = per[loc]
            if isinstance(value, dict):
                parent, leaf = key.rsplit(".", 1)
                for suffix, text in value.items():
                    set_path(data, f"{parent}.{leaf}{suffix}", text)
            else:
                set_path(data, key, value)
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated {loc}.json")
