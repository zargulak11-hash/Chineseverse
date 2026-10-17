# -*- coding: utf-8 -*-
"""Translations of the server's "the AI is unavailable" answers
(apiErrors.js): roleplay and "Explain my answer" said them in English to
every learner, exactly when the AI was down. Idempotent.
Run from frontend/: python scripts/add_ai_offline_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "apiErrors.aiRoleplayOff": L(
        "AI conversations aren't available on this server right now. The scripted Real Chinese scenes still work.",
        "Разговоры с ИИ сейчас недоступны на этом сервере. Сценки «Живого китайского» работают как обычно.",
        "Суҳбат бо ИИ ҳоло дар ин сервер дастрас нест. Саҳнаҳои «Чинии зинда» мисли пештара кор мекунанд.",
        "此服务器暂时无法进行 AI 对话。“真实中文”里的情景对话仍可正常使用。"),
    "apiErrors.aiRoleplayLater": L(
        "AI conversations aren't available right now. Try again later.",
        "Разговоры с ИИ сейчас недоступны. Попробуйте позже.",
        "Суҳбат бо ИИ ҳоло дастрас нест. Баъдтар кӯшиш кунед.",
        "AI 对话暂时不可用，请稍后再试。"),
    "apiErrors.aiPartnerSilent": L(
        "Your conversation partner didn't answer. Send your message again in a moment.",
        "Собеседник не ответил. Отправьте сообщение ещё раз чуть позже.",
        "Ҳамсуҳбат ҷавоб надод. Паёми худро каме баъдтар боз фиристед.",
        "对话伙伴没有回应，请稍后再发送一次。"),
    "apiErrors.aiExplainOff": L(
        "AI explanations aren't available right now — the explanation above still applies.",
        "Объяснения ИИ сейчас недоступны — объяснение выше по-прежнему верно.",
        "Шарҳҳои ИИ ҳоло дастрас нестанд — шарҳи боло дуруст боқӣ мемонад.",
        "AI 讲解暂时不可用——上面的说明依然有效。"),
    "apiErrors.aiExplainFailed": L(
        "The explanation couldn't be written right now. Try again in a moment.",
        "Не удалось написать объяснение. Попробуйте ещё раз чуть позже.",
        "Шарҳ навишта нашуд. Каме баъдтар боз кӯшиш кунед.",
        "暂时无法生成讲解，请稍后再试。"),
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
