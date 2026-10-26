# -*- coding: utf-8 -*-
"""Adds the strings of Google sign-in inside the Android app
(components/NativeGoogleButton.jsx: Android's own account picker, then the
same POST /api/auth/google as the website) and the server's "Google isn't
set up" answer (apiErrors.js) to all four locale files. Idempotent: keys
already present are skipped.
Run from frontend/: python scripts/add_google_app_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    "auth.continueGoogle": L("Continue with Google", "Продолжить с Google", "Идома бо Google", "使用 Google 继续"),
    "auth.googleAppSigningIn": L("Signing in with Google…", "Входим через Google…", "Бо Google ворид шуда истодааст…", "正在通过 Google 登录…"),
    "auth.googleAppCancelled": L(
        "Google sign-in was cancelled. You can try again or sign in another way.",
        "Вход через Google отменён. Можно попробовать снова или войти другим способом.",
        "Воридшавӣ бо Google бекор карда шуд. Метавонед бори дигар кӯшиш кунед ё бо роҳи дигар ворид шавед.",
        "已取消 Google 登录。你可以再试一次，或用其他方式登录。"),
    "auth.googleAppNoAccount": L(
        "There's no Google account on this phone yet. Add one in the phone's Settings → Accounts, then try again — or sign in with your username and password.",
        "На этом телефоне пока нет аккаунта Google. Добавьте его в настройках телефона → «Аккаунты» и попробуйте снова — или войдите по имени пользователя и паролю.",
        "Дар ин телефон ҳоло ҳисоби Google нест. Онро дар танзимоти телефон → «Ҳисобҳо» илова кунед ва бори дигар кӯшиш кунед — ё бо номи корбар ва парол ворид шавед.",
        "这部手机上还没有 Google 账号。请在手机“设置”→“账号”中添加后再试，或者用用户名和密码登录。"),
    "auth.googleAppNetwork": L(
        "Couldn't reach Google. Check your internet connection and try again.",
        "Не удалось связаться с Google. Проверьте подключение к интернету и попробуйте снова.",
        "Ба Google пайваст шуда натавонистем. Пайвасти интернетро санҷед ва бори дигар кӯшиш кунед.",
        "无法连接 Google。请检查网络连接后再试。"),
    "auth.googleAppNotConfigured": L(
        "Google sign-in isn't set up for this version of the app yet. Please sign in with your username and password for now.",
        "Вход через Google для этой версии приложения пока не настроен. Пока войдите по имени пользователя и паролю.",
        "Воридшавӣ бо Google барои ин версияи барнома ҳоло танзим нашудааст. Ҳоло бо номи корбар ва парол ворид шавед.",
        "这个版本的应用还没有配置 Google 登录。请暂时使用用户名和密码登录。"),
    "auth.googleAppFailed": L(
        "Google sign-in didn't work. Please try again.",
        "Не удалось войти через Google. Попробуйте снова.",
        "Воридшавӣ бо Google нашуд. Лутфан бори дигар кӯшиш кунед.",
        "Google 登录没有成功，请再试一次。"),
    # routers/auth.py _verify_google: 501 when GOOGLE_CLIENT_ID is unset.
    "apiErrors.googleServerOff": L(
        "Google sign-in isn't available on the server right now. Please sign in with your username and password.",
        "Вход через Google сейчас недоступен на сервере. Войдите по имени пользователя и паролю.",
        "Воридшавӣ бо Google ҳоло дар сервер дастрас нест. Бо номи корбар ва парол ворид шавед.",
        "服务器目前无法使用 Google 登录。请用用户名和密码登录。"),
}


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read()
        # Keep the file's own line endings (the locales are LF in git today).
        eol = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.split(eol)
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        text = eol.join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
