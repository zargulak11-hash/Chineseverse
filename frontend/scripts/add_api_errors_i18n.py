# -*- coding: utf-8 -*-
"""Translations of the server answers a learner meets in normal use that
apiErrors.js did not map yet -- One Sentence's input checks, "already in
your review", practice, roleplay, Tone Coach, Sound World, exams. Found by
listing every `detail` the API can return. Idempotent.
Run from frontend/: python scripts/add_api_errors_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "apiErrors.sentenceInput": L(
        "Enter a Chinese sentence (at least two characters).",
        "Введите предложение на китайском (не меньше двух иероглифов).",
        "Ҷумлаи чинӣ ворид кунед (ақаллан ду иероглиф).",
        "请输入一个中文句子（至少两个汉字）。"),
    "apiErrors.sentenceNoWords": L(
        "No HSK words were found in this sentence. Try another one.",
        "В этом предложении не нашлось слов HSK. Попробуйте другое.",
        "Дар ин ҷумла калимаҳои HSK ёфт нашуданд. Ҷумлаи дигарро санҷед.",
        "这个句子里没有找到 HSK 词语，请换一句试试。"),
    "apiErrors.sentenceTooShort": L(
        "This sentence is too short to build a lesson from.",
        "Это предложение слишком короткое, чтобы сделать из него урок.",
        "Ин ҷумла барои сохтани дарс хеле кӯтоҳ аст.",
        "这个句子太短，没法生成一节课。"),
    "apiErrors.sentenceNotChinese": L(
        "Write the sentence in Chinese characters.",
        "Напишите предложение китайскими иероглифами.",
        "Ҷумларо бо иероглифҳои чинӣ нависед.",
        "请用汉字写这个句子。"),
    "apiErrors.selectChinese": L(
        "Select some Chinese text first.", "Сначала выделите китайский текст.",
        "Аввал матни чиниро ҷудо кунед.", "请先选中一段中文。"),
    "apiErrors.alreadyInReview": L(
        "This word is already in your review.", "Это слово уже в повторении.",
        "Ин калима аллакай дар такрор аст.", "这个词已经在复习里了。"),
    "apiErrors.wordNotPractisable": L(
        "This word can't be practised here.", "Это слово здесь нельзя потренировать.",
        "Ин калимаро дар ин ҷо машқ кардан мумкин нест.", "这个词不能在这里练习。"),
    "apiErrors.charNotInCurriculum": L(
        "This character isn't in the ChineseVerse curriculum yet.",
        "Этого иероглифа пока нет в программе ChineseVerse.",
        "Ин иероглиф ҳоло дар барномаи ChineseVerse нест.",
        "ChineseVerse 课程里还没有这个汉字。"),
    "apiErrors.giveOneChar": L(
        "Give one Chinese character.", "Укажите один китайский иероглиф.",
        "Як иероглифи чинӣ нишон диҳед.", "请输入一个汉字。"),
    "apiErrors.chapterNothing": L(
        "This chapter has nothing to practise yet.", "В этой главе пока нечего тренировать.",
        "Дар ин боб ҳоло чизе барои машқ нест.", "这一章还没有可练习的内容。"),
    "apiErrors.noWordsAtLevel": L(
        "There are no words to practise at this level yet.", "На этом уровне пока нет слов для тренировки.",
        "Дар ин сатҳ ҳоло калима барои машқ нест.", "这个等级还没有可练习的词语。"),
    "apiErrors.caseNotReady": L(
        "There aren't enough words at your level to build this case yet.",
        "На вашем уровне пока недостаточно слов, чтобы собрать это дело.",
        "Дар сатҳи шумо ҳоло калимаҳо барои сохтани ин парванда кофӣ нестанд.",
        "你目前的等级词语还不够，暂时无法生成这个案件。"),
    "apiErrors.placeNotReady": L(
        "There aren't enough words at your level to build this place yet.",
        "На вашем уровне пока недостаточно слов, чтобы открыть это место.",
        "Дар сатҳи шумо ҳоло калимаҳо барои сохтани ин макон кофӣ нестанд.",
        "你目前的等级词语还不够，暂时无法生成这个地点。"),
    "apiErrors.itemGone": L(
        "This item no longer exists.", "Этого больше нет.", "Ин дигар вуҷуд надорад.", "此内容已不存在。"),
    "apiErrors.answerFirst": L(
        "Answer the question first.", "Сначала ответьте на вопрос.", "Аввал ба савол ҷавоб диҳед.", "请先回答这个问题。"),
    "apiErrors.answerBeforeSpeaking": L(
        "Answer the question before saying it aloud.", "Сначала ответьте на вопрос, потом произнесите вслух.",
        "Аввал ба савол ҷавоб диҳед, баъд онро баланд гӯед.", "请先回答问题，再大声说出来。"),
    "apiErrors.alreadySpoken": L(
        "You've already practised saying this one.", "Вы уже проговорили этот вопрос.",
        "Шумо инро аллакай талаффуз кардаед.", "这一题你已经说过了。"),
    "apiErrors.nothingToSay": L(
        "This question has nothing to say aloud.", "В этом вопросе нечего произносить вслух.",
        "Дар ин савол чизе барои баланд гуфтан нест.", "这道题没有需要说出来的内容。"),
    "apiErrors.nothingToExplain": L(
        "This answer was right — there is nothing to explain.", "Ответ верный — объяснять нечего.",
        "Ҷавоб дуруст буд — чизе барои шарҳ нест.", "这个答案是对的，没有需要讲解的。"),
    "apiErrors.cantExplain": L(
        "This kind of question can't be explained here.", "Такой вопрос здесь объяснить нельзя.",
        "Ин навъи саволро дар ин ҷо шарҳ додан мумкин нест.", "这类题目无法在这里讲解。"),
    "apiErrors.typeAnswer": L(
        "Type your answer for this question.", "Введите ответ на этот вопрос.",
        "Ҷавоби ин саволро нависед.", "请输入这道题的答案。"),
    "apiErrors.writeSomething": L(
        "Write something to say.", "Напишите, что хотите сказать.", "Чизе нависед, ки гӯед.", "请写下你想说的话。"),
    "apiErrors.saySomething": L(
        "Say something before finishing.", "Скажите что-нибудь, прежде чем завершить.",
        "Пеш аз анҷом чизе гӯед.", "结束前请先说点什么。"),
    "apiErrors.conversationComplete": L(
        "This conversation is complete — finish it to see your summary.",
        "Разговор завершён — закончите его, чтобы увидеть итоги.",
        "Суҳбат анҷом ёфт — онро ба охир расонед, то натиҷаро бинед.",
        "对话已经结束——点“完成”查看总结。"),
    "apiErrors.conversationFinished": L(
        "This conversation is finished.", "Этот разговор уже закончен.", "Ин суҳбат аллакай анҷом ёфтааст.", "这段对话已经结束了。"),
    "apiErrors.recordingLength": L(
        "The recording should be between a moment and 5 seconds long.",
        "Запись должна длиться от мгновения до 5 секунд.",
        "Сабт бояд аз як лаҳза то 5 сония бошад.",
        "录音时长应在片刻到 5 秒之间。"),
    "apiErrors.speedLocked": L(
        "This speed isn't unlocked yet.", "Эта скорость ещё не открыта.", "Ин суръат ҳоло кушода нашудааст.", "这个语速还没有解锁。"),
    "apiErrors.examOver": L(
        "This exam attempt is over.", "Эта попытка экзамена завершена.", "Ин кӯшиши имтиҳон анҷом ёфт.", "这次考试已经结束。"),
    "apiErrors.examInProgress": L(
        "An exam attempt is already in progress.", "Попытка экзамена уже идёт.", "Кӯшиши имтиҳон аллакай идома дорад.", "已经有一场考试正在进行。"),
    "apiErrors.examNotOpen": L(
        "This exam isn't open yet: finish the level's lessons first.",
        "Экзамен пока закрыт: сначала пройдите уроки уровня.",
        "Имтиҳон ҳоло баста аст: аввал дарсҳои сатҳро анҷом диҳед.",
        "考试还没开放：请先完成这个等级的课程。"),
}

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
