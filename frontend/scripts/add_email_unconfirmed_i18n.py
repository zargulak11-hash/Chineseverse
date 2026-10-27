# -*- coding: utf-8 -*-
"""Adds the answer Google/GitHub sign-in gives when an account with the
same email exists but its address was never proven (routers/auth.py
UNCONFIRMED_EMAIL_DETAIL; GitHub returns it as ?auth_error=
github_email_unconfirmed), and the sign-up limit's 429
(services/signup_throttle.py), to all four locale files. Idempotent: keys
already present are skipped.
Run from frontend/: python scripts/add_email_unconfirmed_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


MESSAGE = L(
    "This email already has a ChineseVerse account. Sign in with its password, or use \"Forgot password?\" to confirm the address is yours, then try again.",
    "С этим email уже есть аккаунт ChineseVerse. Войдите по его паролю или нажмите «Забыли пароль?», чтобы подтвердить, что адрес ваш, и попробуйте снова.",
    "Бо ин email аллакай ҳисоби ChineseVerse мавҷуд аст. Бо пароли он ворид шавед ё «Паролро фаромӯш кардед?»-ро пахш кунед, то тасдиқ кунед, ки ин суроға аз они шумост, ва боз кӯшиш кунед.",
    "该邮箱已有一个 ChineseVerse 账号。请用它的密码登录，或点击“忘记密码？”确认这个邮箱属于你，然后再试一次。",
)

S = {
    "apiErrors.emailUnconfirmed": MESSAGE,
    "auth.oauthErrors.github_email_unconfirmed": MESSAGE,
    # services/signup_throttle.py: 429 from POST /api/auth/register.
    "apiErrors.signupLimited": L(
        "Too many sign-ups from this network. Please try again later.",
        "Слишком много регистраций из этой сети. Попробуйте позже.",
        "Аз ин шабака бақайдгириҳо хеле зиёданд. Лутфан баъдтар боз кӯшиш кунед.",
        "此网络的注册次数过多，请稍后再试。",
    ),
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
