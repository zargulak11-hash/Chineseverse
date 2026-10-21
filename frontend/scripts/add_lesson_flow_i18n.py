# -*- coding: utf-8 -*-
"""Adds the strings of the guided lesson (pages/LessonDetail.jsx,
components/LessonSteps.jsx, backend services/lesson_flow.py) into all four
locale files. Idempotent: keys already present are skipped; the new
top-level "lessonFlow" section is created once.
Run from frontend/: python scripts/add_lesson_flow_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "practice.title.lesson_step": L("Lesson · {{step}}", "Урок · {{step}}", "Дарс · {{step}}", "课程 · {{step}}"),
    # ---- the stages ----
    "lessonFlow.stage.learn": L("Learn", "Изучить", "Омӯзиш", "学习"),
    "lessonFlow.stage.listen": L("Listen", "Слушать", "Шунидан", "听"),
    "lessonFlow.stage.build": L("Build", "Составить", "Сохтан", "组句"),
    "lessonFlow.stage.recall": L("Recall", "Вспомнить", "Ба ёд овардан", "回想"),
    "lessonFlow.stage.apply": L("Apply", "Применить", "Истифода", "运用"),
    "lessonFlow.stage.check": L("Check", "Проверка", "Санҷиш", "检测"),
    "lessonFlow.stagesLabel": L("Steps of the lesson", "Шаги урока", "Қадамҳои дарс", "课程步骤"),
    "lessonFlow.stepsDone": L("Steps done", "Шагов пройдено", "Қадамҳои иҷрошуда", "已完成步骤"),
    "lessonFlow.goal": L("After this lesson: {{goal}}", "После урока вы сможете: {{goal}}", "Пас аз ин дарс: {{goal}}",
                         "学完这一课：{{goal}}"),
    "lessonFlow.what.listen": L(
        "Hear the lesson's sounds, words and phrases and pick what you heard — from single tones to whole phrases.",
        "Слушайте звуки, слова и фразы урока и выбирайте, что услышали, — от отдельных тонов до целых фраз.",
        "Овозҳо, калимаҳо ва ибораҳои дарсро гӯш кунед ва он чиро, ки шунидед, интихоб кунед — аз оҳангҳои алоҳида то ибораҳои пурра.",
        "听这一课的声音、词语和句子，选出你听到的——从单个声调到完整的句子。"),
    "lessonFlow.what.build": L(
        "Fill in the missing word, then put the pieces of a phrase in the right order.",
        "Вставьте пропущенное слово, затем расставьте части фразы в правильном порядке.",
        "Калимаи гумшударо гузоред, баъд қисмҳои ибораро бо тартиби дуруст ҷой диҳед.",
        "先填上缺少的词，再把句子的各个部分按正确的顺序排好。"),
    "lessonFlow.what.recall": L(
        "Type words from memory, recognise their meanings, and find the phrase for a meaning — without the answer in front of you.",
        "Напишите слова по памяти, узнайте их значения и найдите фразу по смыслу — без подсказки перед глазами.",
        "Калимаҳоро аз хотир нависед, маъноашонро шиносед ва иборае ёбед, ки ба маъно мувофиқ аст — бе ҷавоби тайёр дар пеши чашм.",
        "凭记忆写出词语，认出它们的意思，再根据意思找出句子——答案不会先给你看。"),
    "lessonFlow.what.apply": L(
        "Use the lesson in a situation: answer what someone says, choose what to say, and build a phrase with no help at all.",
        "Используйте урок в ситуации: ответьте собеседнику, выберите, что сказать, и составьте фразу совсем без подсказок.",
        "Дарсро дар вазъият истифода баред: ба гуфтаи касе ҷавоб диҳед, интихоб кунед, ки чӣ гӯед, ва иборае бе ҳеҷ ёрӣ созед.",
        "在情景中运用这一课：回答别人说的话，选择该说什么，再完全不靠提示组一个句子。"),
    "lessonFlow.what.check": L(
        "The lesson's own check. It is graded on the server; with 70% or more the lesson is completed and the next one opens.",
        "Итоговая проверка урока. Её оценивает сервер; при 70% и выше урок засчитывается и открывается следующий.",
        "Санҷиши ниҳоии дарс. Онро сервер баҳо медиҳад; бо 70% ва бештар дарс анҷомёфта ҳисоб мешавад ва дарси навбатӣ кушода мешавад.",
        "这一课的检测，由服务器评分；得到 70% 以上，这一课就完成了，下一课随之开放。"),
    "lessonFlow.why.listen": L(
        "Why: you understand a phrase only when you recognise it by ear, not only on paper.",
        "Зачем: фразу понимаешь только тогда, когда узнаёшь её на слух, а не только на бумаге.",
        "Барои чӣ: иборо танҳо вақте мефаҳмед, ки онро бо гӯш шинохта тавонед, на танҳо дар коғаз.",
        "为什么：能听出来，才算真的懂了这句话，而不只是看得懂。"),
    "lessonFlow.why.build": L(
        "Why: Chinese word order carries the meaning. Building phrases yourself is how you start to speak them.",
        "Зачем: в китайском смысл держится на порядке слов. Составляя фразы сами, вы начинаете их говорить.",
        "Барои чӣ: дар забони чинӣ маъно ба тартиби калимаҳо вобаста аст. Вақте ибораҳоро худатон месозед, гуфтани онҳоро сар мекунед.",
        "为什么：汉语的意思靠词序表达。自己动手组句，才能开始说出来。"),
    "lessonFlow.why.recall": L(
        "Why: recalling without seeing the answer is what makes words stay. What you miss comes back in Review.",
        "Зачем: вспоминание без подсказки и закрепляет слова. То, что вы не вспомнили, вернётся в «Повторении».",
        "Барои чӣ: ба ёд овардан бе дидани ҷавоб калимаҳоро дар хотир нигоҳ медорад. Он чи ки ба ёд наоварда метавонед, дар «Такрор» бармегардад.",
        "为什么：不看答案地回想，才能真正记住。没想起来的内容会在“复习”里再出现。"),
    "lessonFlow.why.apply": L(
        "Why: the goal is to use Chinese in real situations, by yourself.",
        "Зачем: цель — самостоятельно пользоваться китайским в настоящих ситуациях.",
        "Барои чӣ: мақсад — мустақилона дар вазъиятҳои воқеӣ забони чиниро истифода бурдан аст.",
        "为什么：目标是在真实情景里自己用中文。"),
    "lessonFlow.hints.full": L(
        "You'll see pinyin and each word's meaning on the pieces — the help is reduced as you go.",
        "На частях фразы будут пиньинь и значение каждого слова — подсказок постепенно станет меньше.",
        "Дар қисмҳо пинйин ва маънои ҳар калима нишон дода мешавад — ёрӣ тадриҷан кам мешавад.",
        "每个部分都标有拼音和词义，提示会慢慢减少。"),
    "lessonFlow.hints.some": L(
        "The pieces show each word's meaning, not its pinyin — read the characters.",
        "На частях будет значение слова, но без пиньиня — читайте иероглифы.",
        "Дар қисмҳо маънои калима ҳаст, вале пинйин нест — иероглифҳоро хонед.",
        "每个部分只标词义，不标拼音——请读汉字。"),
    "lessonFlow.hints.none": L(
        "At your level the pieces come without pinyin or meanings — only the phrase's meaning is given.",
        "На вашем уровне части даются без пиньиня и значений — дан только смысл всей фразы.",
        "Дар сатҳи шумо қисмҳо бе пинйин ва маъно дода мешаванд — танҳо маънои тамоми ибора ҳаст.",
        "按你的水平，各部分不标拼音也不标词义，只给出整句的意思。"),
    "lessonFlow.start": L("Start", "Начать", "Оғоз", "开始"),
    "lessonFlow.again": L("Practise again", "Ещё раз", "Боз машқ кунед", "再练一次"),
    "lessonFlow.best": L("Best: {{score}}%", "Лучший: {{score}}%", "Беҳтарин: {{score}}%", "最好：{{score}}%"),
    "lessonFlow.nextStage": L("Next step", "Следующий шаг", "Қадами навбатӣ", "下一步"),
    "lessonFlow.notAvailable": L(
        "This lesson has too little material for this step — go on to the next one.",
        "В этом уроке слишком мало материала для этого шага — переходите к следующему.",
        "Дар ин дарс барои ин қадам мавод кам аст — ба қадами навбатӣ гузаред.",
        "这一课的内容不够做这一步，请继续下一步。"),
    "lessonFlow.passNote": L(
        "A step counts as done at {{score}}% or more. You can repeat it any time; mistakes go to Review.",
        "Шаг засчитывается при {{score}}% и выше. Повторять можно сколько угодно; ошибки попадают в «Повторение».",
        "Қадам бо {{score}}% ва бештар иҷрошуда ҳисоб мешавад. Ҳар вақт такрор кардан мумкин аст; хатоҳо ба «Такрор» мераванд.",
        "得到 {{score}}% 以上，这一步就算完成。可以随时再练；错题会进入“复习”。"),
    "lessonFlow.sideHow": L(
        "Go through the steps in order. You can always go back to Learn.",
        "Проходите шаги по порядку. К «Изучить» всегда можно вернуться.",
        "Қадамҳоро бо тартиб гузаред. Ба «Омӯзиш» ҳамеша баргаштан мумкин аст.",
        "按顺序完成各步，随时可以回到“学习”。"),
    "lessonFlow.checkEarly": L(
        "Tip: the steps before this one prepare you for the check.",
        "Совет: шаги перед проверкой готовят к ней.",
        "Маслиҳат: қадамҳои пеш аз санҷиш шуморо ба он омода мекунанд.",
        "提示：前面的步骤会帮你准备好这次检测。"),
    "lessonFlow.knownTitle": L("You're already above HSK {{level}}", "Ваш уровень уже выше HSK {{level}}",
                               "Сатҳи шумо аллакай аз HSK {{level}} болотар аст", "你的水平已经超过 HSK {{level}}"),
    "lessonFlow.knownBody": L(
        "The steps are optional for you: go straight to the check, and come back to a step only if you need it.",
        "Шаги для вас необязательны: переходите сразу к проверке и возвращайтесь к шагу, только если нужно.",
        "Қадамҳо барои шумо ҳатмӣ нестанд: рост ба санҷиш гузаред ва танҳо агар лозим шавад, ба қадам баргардед.",
        "这些步骤对你来说是可选的：可以直接去检测，需要时再回来练。"),
    "lessonFlow.toCheck": L("Go to the check", "К проверке", "Ба санҷиш", "去检测"),
    # ---- Learn ----
    "lessonFlow.pinyinFirstTitle": L("New to Chinese sounds?", "Впервые слышите китайские звуки?", "Бори аввал бо овозҳои чинӣ шинос мешавед?",
                                     "第一次接触汉语发音？"),
    "lessonFlow.pinyinFirstBody": L(
        "The pinyin course explains how the letters and the four tones work — it makes this lesson much easier.",
        "Курс пиньиня объясняет, как устроены буквы и четыре тона, — с ним этот урок станет намного проще.",
        "Курси пинйин шарҳ медиҳад, ки ҳарфҳо ва чор оҳанг чӣ тавр кор мекунанд — бо он ин дарс хеле осонтар мешавад.",
        "拼音课程会讲清字母和四个声调，学了以后这一课会容易得多。"),
    "lessonFlow.pinyinFirstGo": L("Open the pinyin course", "Открыть курс пиньиня", "Курси пинйинро кушоед", "打开拼音课程"),
    "lessonFlow.phraseOf": L("Phrase {{n}} of {{total}}", "Фраза {{n}} из {{total}}", "Ибораи {{n}} аз {{total}}", "第 {{n}} 句，共 {{total}} 句"),
    "lessonFlow.hear": L("Listen", "Прослушать", "Гӯш кардан", "听"),
    "lessonFlow.noTranslation": L(
        "This example has no translation in the lesson — its words are explained one by one below.",
        "У этого примера в уроке нет перевода — ниже объяснено каждое слово.",
        "Ин мисол дар дарс тарҷума надорад — дар поён ҳар калима алоҳида шарҳ дода шудааст.",
        "这个例句在课文里没有翻译，下面逐词解释。"),
    "lessonFlow.template": L(
        "A frame: put your own word where the dots are.",
        "Это шаблон: вместо многоточия подставьте своё слово.",
        "Ин қолаб аст: ба ҷойи нуқтаҳо калимаи худро гузоред.",
        "这是一个句型：在省略号处填上你自己的词。"),
    "lessonFlow.wordByWord": L("Word by word", "Слово за словом", "Калима ба калима", "逐词解释"),
    "lessonFlow.replyTitle": L("How to answer", "Как ответить", "Чӣ тавр ҷавоб додан", "怎么回答"),
    "lessonFlow.prevPhrase": L("Previous", "Назад", "Қаблӣ", "上一句"),
    "lessonFlow.nextPhrase": L("Next phrase", "Следующая фраза", "Ибораи навбатӣ", "下一句"),
    "lessonFlow.toListen": L("Now listen", "Теперь слушать", "Акнун гӯш кунед", "开始听"),
    "lessonFlow.openGrammar": L("Open this grammar point", "Открыть это правило", "Ин қоидаро кушоед", "查看这个语法点"),
    "lessonFlow.wholeText": L("The whole lesson text", "Весь текст урока", "Тамоми матни дарс", "完整课文"),
    # ---- the questions ----
    "lessonFlow.ask.build": L("Put the pieces in order to make the phrase.", "Расставьте части по порядку, чтобы получилась фраза.",
                              "Қисмҳоро бо тартиб ҷой диҳед, то ибора ҳосил шавад.", "把各个部分按顺序排成句子。"),
    "lessonFlow.ask.buildFinal": L("On your own: build the phrase — no hints this time.", "Сами: составьте фразу — на этот раз без подсказок.",
                                   "Мустақилона: иборо созед — ин дафъа бе ёрӣ.", "自己完成：组成句子——这次没有提示。"),
    "lessonFlow.ask.listenMeaning": L("Listen. What does it mean?", "Послушайте. Что это значит?", "Гӯш кунед. Ин чӣ маъно дорад?", "听一听，是什么意思？"),
    "lessonFlow.ask.listenPhrase": L("Listen. Which phrase did you hear?", "Послушайте. Какую фразу вы услышали?",
                                     "Гӯш кунед. Кадом иборо шунидед?", "听一听，你听到的是哪一句？"),
    "lessonFlow.ask.gap": L("Which word fills the gap?", "Какое слово пропущено?", "Кадом калима ҷойи холиро пур мекунад?", "空白处应该填哪个词？"),
    "lessonFlow.ask.meaning": L("Which phrase means this?", "Какая фраза это значит?", "Кадом ибора ҳамин маъноро дорад?", "哪一句是这个意思？"),
    "lessonFlow.ask.situation": L("You want to say this. What do you say in Chinese?", "Вы хотите сказать это. Что вы скажете по-китайски?",
                                  "Шумо мехоҳед инро гӯед. Ба забони чинӣ чӣ мегӯед?", "你想表达这个意思，用中文怎么说？"),
    "lessonFlow.ask.reply": L("What do you answer?", "Что вы ответите?", "Шумо чӣ ҷавоб медиҳед?", "你怎么回答？"),
    "lessonFlow.someoneSays": L("Someone says to you", "Вам говорят", "Ба шумо мегӯянд", "有人对你说"),
    "lessonFlow.means": L("Meaning: «{{text}}»", "Значение: «{{text}}»", "Маъно: «{{text}}»", "意思：“{{text}}”"),
    "lessonFlow.gapHint": L("The missing word means «{{text}}».", "Пропущенное слово значит «{{text}}».",
                            "Калимаи гумшуда маънои «{{text}}»-ро дорад.", "缺少的词意思是“{{text}}”。"),
    "lessonFlow.wordsMean": L("Its words mean: {{list}}", "Слова в ней значат: {{list}}", "Калимаҳои он маъно доранд: {{list}}",
                              "句中的词：{{list}}"),
    "lessonFlow.pattern": L("Pattern", "Схема", "Қолаб", "句型"),
    "lessonFlow.yourSentence": L("Your phrase", "Ваша фраза", "Ибораи шумо", "你的句子"),
    "lessonFlow.tapPieces": L("Tap the pieces below in order.", "Нажимайте на части ниже по порядку.",
                              "Ба қисмҳои поён бо тартиб пахш кунед.", "按顺序点下面的部分。"),
    "lessonFlow.takeBack": L("Take back {{text}}", "Убрать {{text}}", "{{text}}-ро баргардонед", "撤回 {{text}}"),
    "lessonFlow.pieces": L("Pieces to place", "Части фразы", "Қисмҳои ибора", "待排列的部分"),
    "lessonFlow.check": L("Check", "Проверить", "Санҷидан", "检查"),
    "lessonFlow.clear": L("Start over", "Сначала", "Аз нав", "重新排"),
    # ---- why an answer was wrong ----
    "lessonFlow.why.order": L(
        "You built: {{given}}. The phrase is: {{expected}}.",
        "Вы составили: {{given}}. Правильно: {{expected}}.",
        "Шумо сохтед: {{given}}. Дуруст: {{expected}}.",
        "你排的是：{{given}}。正确的是：{{expected}}。"),
    "lessonFlow.why.orderGeneral": L(
        "In Chinese, word order carries the meaning: usually who → when → where → does what → to what.",
        "В китайском смысл передаёт порядок слов: обычно кто → когда → где → что делает → с чем.",
        "Дар забони чинӣ маъноро тартиби калимаҳо мерасонад: одатан кӣ → кай → дар куҷо → чӣ мекунад → бо чӣ.",
        "汉语靠词序表达意思：一般是 谁 → 什么时候 → 在哪儿 → 做什么 → 什么。"),
    "lessonFlow.why.pattern": L("This phrase follows the pattern {{pattern}}.", "Эта фраза строится по схеме {{pattern}}.",
                                "Ин ибора аз рӯи қолаби {{pattern}} сохта мешавад.", "这个句子用的句型是 {{pattern}}。"),
    "lessonFlow.why.gap": L(
        "{{picked}} means «{{pickedMeaning}}». The phrase needs {{answer}} — «{{answerMeaning}}».",
        "{{picked}} значит «{{pickedMeaning}}». Во фразе нужно {{answer}} — «{{answerMeaning}}».",
        "{{picked}} маънои «{{pickedMeaning}}»-ро дорад. Дар ибора {{answer}} лозим аст — «{{answerMeaning}}».",
        "{{picked}} 的意思是“{{pickedMeaning}}”。这里应该用 {{answer}}——“{{answerMeaning}}”。"),
    "lessonFlow.why.heard": L(
        "You heard {{answer}} ({{pinyin}}), not {{picked}}. Play it again and listen to the difference.",
        "Прозвучало {{answer}} ({{pinyin}}), а не {{picked}}. Послушайте ещё раз и найдите разницу.",
        "{{answer}} ({{pinyin}}) садо дод, на {{picked}}. Боз гӯш кунед ва фарқро ёбед.",
        "你听到的是 {{answer}}（{{pinyin}}），不是 {{picked}}。再听一遍，找出不同。"),
    "lessonFlow.why.heardNoPy": L(
        "You heard {{answer}}, not {{picked}}. Play it again and listen to the difference.",
        "Прозвучало {{answer}}, а не {{picked}}. Послушайте ещё раз и найдите разницу.",
        "{{answer}} садо дод, на {{picked}}. Боз гӯш кунед ва фарқро ёбед.",
        "你听到的是 {{answer}}，不是 {{picked}}。再听一遍，找出不同。"),
    "lessonFlow.why.reply": L("To «{{asked}}» the answer is {{answer}}.", "На «{{asked}}» отвечают: {{answer}}.",
                              "Ба «{{asked}}» чунин ҷавоб медиҳанд: {{answer}}.", "对“{{asked}}”应该回答：{{answer}}。"),
    "lessonFlow.why.pickedMeans": L("{{picked}} means «{{meaning}}».", "{{picked}} значит «{{meaning}}».",
                                    "{{picked}} маънои «{{meaning}}»-ро дорад.", "{{picked}} 的意思是“{{meaning}}”。"),
    "lessonFlow.why.notThis": L("{{picked}} says something else.", "{{picked}} — это о другом.", "{{picked}} дар бораи чизи дигар аст.",
                                "{{picked}} 说的是别的意思。"),
    "lessonFlow.why.say": L("Here you say: {{answer}}.", "Здесь говорят: {{answer}}.", "Дар ин ҷо мегӯянд: {{answer}}.", "这里应该说：{{answer}}。"),
    "lessonFlow.rule.particle_end": L(
        "{{word}} turns a sentence into a question and always comes at the very end.",
        "{{word}} делает предложение вопросом и всегда стоит в самом конце.",
        "{{word}} ҷумларо саволӣ мекунад ва ҳамеша дар охири он меояд.",
        "“{{word}}”把句子变成问句，总是放在句子最后。"),
    "lessonFlow.rule.subject_first": L(
        "Who does it comes first: the phrase starts with {{word}}.",
        "Сначала тот, кто действует: фраза начинается с {{word}}.",
        "Аввал иҷрокунанда меояд: ибора бо {{word}} сар мешавад.",
        "做事的人放在最前面：这句话以“{{word}}”开头。"),
    "lessonFlow.rule.bu_before": L(
        "不 and 没 stand right before the word they negate: {{word}}.",
        "不 и 没 стоят прямо перед словом, которое отрицают: {{word}}.",
        "不 ва 没 рост пеш аз калимае меоянд, ки онро инкор мекунанд: {{word}}.",
        "“不”和“没”直接放在被否定的词前面：{{word}}。"),
    "lessonFlow.rule.hen_before": L(
        "很 comes right before the adjective: {{word}}.",
        "很 стоит прямо перед прилагательным: {{word}}.",
        "很 рост пеш аз сифат меояд: {{word}}.",
        "“很”直接放在形容词前面：{{word}}。"),
    "lessonFlow.rule.time_early": L(
        "Time words like {{word}} come early — before the verb, not at the end.",
        "Слова времени, как {{word}}, стоят рано — перед глаголом, а не в конце.",
        "Калимаҳои вақт, мисли {{word}}, барвақт меоянд — пеш аз феъл, на дар охир.",
        "像“{{word}}”这样的时间词放在前面——动词之前，不放在句尾。"),
    "lessonFlow.rule.de_between": L(
        "的 joins the owner and the thing: owner + 的 + thing ({{word}}).",
        "的 связывает владельца и предмет: владелец + 的 + предмет ({{word}}).",
        "的 соҳиб ва чизро мепайвандад: соҳиб + 的 + чиз ({{word}}).",
        "“的”连接所有者和事物：所有者 + 的 + 事物（{{word}}）。"),
    "lessonFlow.rule.le_after": L(
        "了 comes right after the action that is done: {{word}}.",
        "了 стоит сразу после завершённого действия: {{word}}.",
        "了 рост баъд аз амали анҷомёфта меояд: {{word}}.",
        "“了”放在已经完成的动作后面：{{word}}。"),
    # ---- the lesson played through (components/LessonSteps.jsx TeachCard, pages/Practice.jsx, LessonDetail.jsx) ----
    "practice.title.lesson_play": L("Lesson", "Урок", "Дарс", "课程"),
    "lessonPlay.newPhrase": L("New phrase", "Новая фраза", "Ибораи нав", "新句子"),
    "lessonPlay.newWord": L("New word", "Новое слово", "Калимаи нав", "新词"),
    "lessonPlay.gotIt": L("Got it — continue", "Понятно — дальше", "Фаҳмидам — идома", "明白了，继续"),
    "lessonPlay.example": L("In a sentence", "В предложении", "Дар ҷумла", "例句"),
    "lessonPlay.leave": L("Leave the lesson", "Выйти из урока", "Аз дарс баромадан", "退出课程"),
    "lessonPlay.progress": L("Step {{n}} of {{total}}", "Шаг {{n}} из {{total}}", "Қадами {{n}} аз {{total}}", "第 {{n}} 步，共 {{total}} 步"),
    "lessonPlay.doneTitle": L("Lesson complete!", "Урок пройден!", "Дарс анҷом ёфт!", "课程完成！"),
    "lessonPlay.doneBody": L(
        "You can now use what's below. The words you missed come back in Review, and the next lesson is open.",
        "Теперь вы можете использовать то, что ниже. Слова с ошибками вернутся в «Повторении», а следующий урок открыт.",
        "Акнун шумо он чиро, ки дар поён аст, истифода бурда метавонед. Калимаҳои хатогӣ дар «Такрор» бармегарданд ва дарси навбатӣ кушода шуд.",
        "现在你可以用下面这些表达了。答错的词会在“复习”里再出现，下一课也已开放。"),
    "lessonPlay.notYetTitle": L("Almost — one more go", "Почти — ещё раз", "Қариб — боз як бор", "差一点——再来一次"),
    "lessonPlay.notYetBody": L(
        "The lesson counts at {{score}}% of the exercises right. Play it again: the teaching screens come first each time.",
        "Урок засчитывается при {{score}}% верных ответов. Пройдите его ещё раз: объяснения снова будут в начале.",
        "Дарс бо {{score}}% ҷавобҳои дуруст ҳисоб мешавад. Онро боз гузаред: шарҳҳо боз дар аввал меоянд.",
        "答对 {{score}}% 的练习才算完成这一课。再学一遍吧，讲解会重新出现。"),
    "lessonPlay.learned": L("In this lesson", "В этом уроке", "Дар ин дарс", "这一课学了"),
    "lessonPlay.again": L("Play the lesson again", "Пройти урок ещё раз", "Дарсро боз гузаштан", "再学一遍"),
    "lessonPlay.youWillLearn": L("You'll learn", "Вы выучите", "Шумо меомӯзед", "你会学到"),
    "lessonPlay.howItGoes": L(
        "{{screens}} short steps: each new phrase is shown and explained, then you practise it straight away — by ear, by meaning and by putting it together. Earlier phrases come back as you go.",
        "{{screens}} коротких шагов: каждую новую фразу сначала покажут и объяснят, потом вы сразу её тренируете — на слух, по смыслу и собирая из частей. Пройденные фразы будут возвращаться.",
        "{{screens}} қадами кӯтоҳ: ҳар ибораи нав аввал нишон дода ва шарҳ дода мешавад, баъд шумо фавран онро машқ мекунед — бо гӯш, аз рӯи маъно ва бо ҷамъ кардани қисмҳо. Ибораҳои гузашта дар роҳ бармегарданд.",
        "共 {{screens}} 个小步骤：每个新句子先展示、讲解，然后马上练习——听、看意思、拼句子。前面学过的句子会再次出现。"),
    "lessonPlay.start": L("Start the lesson", "Начать урок", "Дарсро оғоз кунед", "开始学习"),
    "lessonPlay.tryAgain": L("Try the lesson again", "Пройти урок снова", "Дарсро боз санҷед", "再试一次"),
    "lessonPlay.playAgain": L("Play it again", "Пройти ещё раз", "Боз гузаштан", "再学一遍"),
    "lessonPlay.testOut": L("I know this — test me", "Я это знаю — проверьте", "Инро медонам — маро санҷед", "我会了——直接测试"),
    "lessonPlay.testOutBody": L(
        "Your level is above this lesson: take the lesson's test directly. With 70% or more it counts as done.",
        "Ваш уровень выше этого урока: пройдите сразу тест урока. При 70% и выше урок засчитывается.",
        "Сатҳи шумо аз ин дарс болотар аст: рост санҷиши дарсро супоред. Бо 70% ва бештар дарс ҳисоб мешавад.",
        "你的水平高于这一课：可以直接做本课测试，得到 70% 以上即算完成。"),
    "lessonPlay.sideHow": L(
        "Lessons open one after another. A lesson counts only when you pass it — reading it is not enough.",
        "Уроки открываются по порядку. Урок засчитывается, только когда вы его пройдёте, — просто прочитать недостаточно.",
        "Дарсҳо паи ҳам кушода мешаванд. Дарс танҳо вақте ҳисоб мешавад, ки онро гузаред — танҳо хондан кифоя нест.",
        "课程按顺序开放。只有通过了才算完成，光看是不够的。"),
    "lessonPlay.reference": L("Lesson reference", "Справка по уроку", "Маълумотномаи дарс", "课程参考"),
    "lessonPlay.referenceBody": L(
        "Everything this lesson contains, to look things up. You learn it in the lesson itself.",
        "Всё, что есть в уроке, — чтобы подсмотреть. Учится это в самом уроке.",
        "Ҳама чизе, ки дар дарс ҳаст — барои нигоҳ кардан. Омӯзиш дар худи дарс мегузарад.",
        "本课的全部内容，方便查阅。真正的学习在课程里进行。"),
    "lessonPlay.drills": L("Practise one skill", "Тренировать один навык", "Як малакаро машқ кардан", "单项练习"),
    "lessonPlay.drillsBody": L(
        "Extra rounds on this lesson's material, one skill at a time.",
        "Дополнительные раунды по материалу урока — по одному навыку.",
        "Даврҳои иловагӣ аз маводи ин дарс — як малака дар як вақт.",
        "用本课的内容做额外练习，每次练一项技能。"),
}
KEYS = list(S)
NEW_SECTIONS = ("lessonFlow", "lessonPlay")


def section(name, lang):
    """A new top-level object built from the dotted keys under `name`."""
    out = {}
    for dotted, value in S.items():
        head, rest = dotted.split(".", 1)
        if head != name:
            continue
        node = out
        *parents, leaf = rest.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value[lang]
    return out


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read()
        nl = "\r\n" if "\r\n" in raw else "\n"  # keep the file's own line endings
        lines = raw.split(nl)
        for name in NEW_SECTIONS:
            if f'  "{name}": {{' not in lines:
                end = max(i for i, line in enumerate(lines) if line == "}")
                body = json.dumps({name: section(name, lang)}, ensure_ascii=False, indent=2).split("\n")[1:-1]
                lines[end - 1] = lines[end - 1].rstrip(",") + ","
                lines[end:end] = body
        # Every key (put skips the ones already there), so keys added to the
        # script later also reach a section created by an earlier run.
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        text = nl.join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
