# -*- coding: utf-8 -*-
"""Adds the stored-notification strings (topbar bell) to all four locale
files (en/ru/tg/zh). Idempotent: re-running overwrites the same keys with
the same text. Run from frontend/: python scripts/add_notifications_i18n.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")

T = {
    "en": {
        "follow": "{{name}} followed you.",
        "someone": "Someone",
        "generic": "New notification",
        "unread": "Unread",
        "reminders": "Reminders",
        "loadError": "Couldn't load notifications. Try again in a moment.",
        "bellUnread_one": "Notifications: {{count}} unread",
        "bellUnread_other": "Notifications: {{count}} unread",
    },
    "ru": {
        "follow": "{{name}} теперь подписан(а) на вас.",
        "someone": "Кто-то",
        "generic": "Новое уведомление",
        "unread": "Не прочитано",
        "reminders": "Напоминания",
        "loadError": "Не удалось загрузить уведомления. Попробуйте чуть позже.",
        "bellUnread_one": "Уведомления: {{count}} непрочитанное",
        "bellUnread_few": "Уведомления: {{count}} непрочитанных",
        "bellUnread_many": "Уведомления: {{count}} непрочитанных",
        "bellUnread_other": "Уведомления: {{count}} непрочитанных",
    },
    "tg": {
        "follow": "{{name}} шуморо пайравӣ кард.",
        "someone": "Касе",
        "generic": "Огоҳиномаи нав",
        "unread": "Хонда нашуда",
        "reminders": "Ёдраскуниҳо",
        "loadError": "Огоҳиномаҳо бор нашуданд. Каме баъдтар боз кӯшиш кунед.",
        "bellUnread_one": "Огоҳиномаҳо: {{count}} хонда нашуда",
        "bellUnread_other": "Огоҳиномаҳо: {{count}} хонда нашуда",
    },
    "zh": {
        "follow": "{{name}} 关注了你。",
        "someone": "有人",
        "generic": "新通知",
        "unread": "未读",
        "reminders": "提醒",
        "loadError": "通知加载失败，请稍后再试。",
        "bellUnread_other": "通知：{{count}} 条未读",
    },
}

for lang, strings in T.items():
    path = os.path.join(LOCALES, f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("notifications", {}).update(strings)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{lang}: notifications has {len(data['notifications'])} keys")
