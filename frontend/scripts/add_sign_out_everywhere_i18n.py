# -*- coding: utf-8 -*-
"""Adds the Settings card "Sign out of all other devices"
(pages/Settings.jsx OtherDevices; POST /api/me/sessions/revoke) to all four
locale files. Idempotent: keys already present are skipped.
Run from frontend/: python scripts/add_sign_out_everywhere_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "settings.otherDevicesTitle": L(
        "Other devices", "Другие устройства", "Дастгоҳҳои дигар", "其他设备"),
    "settings.otherDevicesSub": L(
        "Signed in on a shared or lost phone or computer? Sign out everywhere except here. Your password stays the same.",
        "Вы входили с чужого или потерянного телефона или компьютера? Выйдите везде, кроме этого устройства. Пароль останется прежним.",
        "Аз телефон ё компютери бегона ё гумшуда ворид шуда будед? Ба ғайр аз ин ҷо, аз ҳама ҷо бароед. Пароли шумо ҳамон мемонад.",
        "曾在共用或丢失的手机、电脑上登录？可以退出除本设备外的所有设备。你的密码不会改变。"),
    "settings.otherDevicesSubmit": L(
        "Sign out of all other devices", "Выйти на всех других устройствах",
        "Аз ҳамаи дастгоҳҳои дигар баромадан", "退出所有其他设备"),
    "settings.otherDevicesBusy": L(
        "Signing out…", "Выходим…", "Баромада истодаем…", "正在退出…"),
    "settings.otherDevicesDone": L(
        "Done: every other device is signed out. You're still signed in here.",
        "Готово: все другие устройства вышли из аккаунта. Здесь вы по-прежнему в аккаунте.",
        "Тайёр: ҳамаи дастгоҳҳои дигар аз ҳисоб баромаданд. Дар ин ҷо шумо ҳоло ҳам ворид ҳастед.",
        "完成：所有其他设备都已退出。你在这里仍保持登录。"),
}


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read()
        # Keep the file's own line endings.
        eol = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.split(eol)
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        text = eol.join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
