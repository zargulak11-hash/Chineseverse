# -*- coding: utf-8 -*-
"""Adds the strings of account recovery -- "Forgot password?" with an
emailed link (pages/ForgotPassword.jsx, ResetPassword.jsx), "Set a password
with Google" in Settings, and their server errors (apiErrors.js) -- into
all four locale files, and rewrites the two existing strings that told a
Google account it could never have a password. Idempotent: new keys
already present are skipped, rewritten values are set to the same text.
Run from frontend/: python scripts/add_account_recovery_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, _line, _object, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    # ---- Login / Forgot password / Reset password ----
    "auth.forgotLink": L("Forgot password?", "Забыли пароль?", "Паролро фаромӯш кардед?", "忘记密码？"),
    "auth.forgotTitle": L("Reset your password", "Сброс пароля", "Барқарор кардани парол", "重置密码"),
    "auth.forgotSub": L(
        "Enter the email address of your account. We'll send you a link to choose a new password.",
        "Введите email вашего аккаунта. Мы пришлём ссылку, по которой можно задать новый пароль.",
        "Почтаи электронии ҳисоби худро ворид кунед. Мо пайвандеро мефиристем, ки бо он пароли нав интихоб мекунед.",
        "输入你账户的邮箱地址，我们会发送一个设置新密码的链接。"),
    "auth.forgotSubmit": L("Send the link", "Отправить ссылку", "Фиристодани пайванд", "发送链接"),
    "auth.forgotSending": L("Sending…", "Отправляем…", "Фиристода истодааст…", "正在发送…"),
    "auth.forgotSentTitle": L("Check your email", "Проверьте почту", "Почтаи худро санҷед", "请查看邮箱"),
    "auth.forgotSent": L(
        "If an account uses {{email}}, a link to reset its password is on its way. It works once, for 30 minutes. Nothing after a few minutes? Check the spam folder, or ask again.",
        "Если к {{email}} привязан аккаунт, ссылка для сброса пароля уже в пути. Она сработает один раз в течение 30 минут. Письма нет через несколько минут? Проверьте папку «Спам» или запросите снова.",
        "Агар {{email}} ба ҳисобе тааллуқ дошта бошад, пайванди барқарор кардани парол фиристода шуд. Он як маротиба ва дар давоми 30 дақиқа кор мекунад. Пас аз чанд дақиқа мактуб наомад? Ҷузвдони «Спам»-ро санҷед ё бори дигар дархост кунед.",
        "如果有账户使用 {{email}}，重置密码的链接已经发出。链接只能使用一次，30 分钟内有效。几分钟后还没收到？请查看垃圾邮件文件夹，或重新申请。"),
    "auth.forgotAgain": L("Send another link", "Отправить ещё раз", "Боз фиристодан", "再发一次"),
    "auth.forgotUnavailableTitle": L("Password reset isn't available right now", "Сброс пароля сейчас недоступен",
                                     "Барқарории парол ҳоло дастрас нест", "目前无法重置密码"),
    "auth.forgotUnavailable": L(
        "This server can't send email at the moment, so a reset link can't be sent. If you signed up with Google, sign in with Google and set a password in Settings.",
        "Сервер сейчас не может отправлять письма, поэтому ссылку для сброса не отправить. Если вы регистрировались через Google, войдите через Google и задайте пароль в настройках.",
        "Сервер ҳоло мактуб фиристода наметавонад, бинобар ин пайванди барқарорӣ фиристода намешавад. Агар тавассути Google сабти ном шуда бошед, бо Google ворид шавед ва паролро дар «Танзимот» муқаррар кунед.",
        "服务器目前无法发送邮件，所以没法发送重置链接。如果你是用 Google 注册的，请用 Google 登录，然后在“设置”里设置密码。"),
    "auth.resetTitle": L("Choose a new password", "Новый пароль", "Пароли нав интихоб кунед", "设置新密码"),
    "auth.resetSub": L(
        "Use at least 6 characters. Your other devices will be signed out.",
        "Не короче 6 символов. На других устройствах вы выйдете из аккаунта.",
        "Ақаллан 6 аломат. Дар дастгоҳҳои дигар шумо аз ҳисоб хориҷ мешавед.",
        "至少 6 个字符。你在其他设备上的登录会失效。"),
    "auth.resetSubmit": L("Save the new password", "Сохранить пароль", "Нигоҳ доштани пароли нав", "保存新密码"),
    "auth.resetSaving": L("Saving…", "Сохраняем…", "Нигоҳ дошта истодааст…", "正在保存…"),
    "auth.resetChecking": L("Checking the link…", "Проверяем ссылку…", "Пайванд санҷида мешавад…", "正在检查链接…"),
    "auth.resetDoneTitle": L("Your password is changed", "Пароль изменён", "Парол иваз шуд", "密码已更改"),
    "auth.resetDone": L(
        "You're signed in. Use the new password from now on — on the website and in the app.",
        "Вы вошли в аккаунт. Теперь используйте новый пароль — на сайте и в приложении.",
        "Шумо ворид шудед. Акнун пароли навро истифода баред — дар сомона ва дар барнома.",
        "你已登录。今后请使用新密码——网站和应用都一样。"),
    "auth.resetContinue": L("Continue learning", "Продолжить обучение", "Идомаи омӯзиш", "继续学习"),
    "auth.resetBadTitle": L("This link can't be used", "Эта ссылка не работает", "Ин пайванд кор намекунад", "此链接无法使用"),
    "auth.resetNoToken": L(
        "This page opens from the link in the reset email. Ask for a new link if you need one.",
        "Эта страница открывается по ссылке из письма для сброса пароля. Если нужно, запросите новую ссылку.",
        "Ин саҳифа аз пайванди мактуби барқарории парол кушода мешавад. Агар лозим бошад, пайванди нав дархост кунед.",
        "此页面需要通过重置邮件里的链接打开。如有需要，请重新申请链接。"),
    "auth.resetNewLink": L("Ask for a new link", "Запросить новую ссылку", "Дархости пайванди нав", "重新申请链接"),
    # ---- Settings: set a password with Google ----
    "settings.googlePasswordTitle": L("Set a password with Google", "Задать пароль через Google",
                                      "Муқаррар кардани парол бо Google", "通过 Google 设置密码"),
    "settings.googlePasswordSub": L(
        "Your account is linked to Google. Choose a password and confirm with Google — then you can also sign in with your username and this password, for example in the Android app.",
        "Ваш аккаунт связан с Google. Придумайте пароль и подтвердите через Google — после этого можно входить по имени пользователя и этому паролю, например в приложении для Android.",
        "Ҳисоби шумо ба Google пайваст аст. Парол интихоб кунед ва бо Google тасдиқ намоед — баъд бо номи корбар ва ҳамин парол ворид шудан мумкин аст, масалан дар барномаи Android.",
        "你的账户已关联 Google。设置一个密码并用 Google 确认后，也可以用用户名和这个密码登录，比如在安卓应用里。"),
    "settings.googlePasswordStep": L(
        "Enter the new password twice, then press the Google button to confirm it's you.",
        "Введите новый пароль дважды, затем нажмите кнопку Google, чтобы подтвердить, что это вы.",
        "Пароли навро ду маротиба ворид кунед, баъд тугмаи Google-ро пахш кунед, то тасдиқ шавад, ки ин шумоед.",
        "输入两次新密码，然后点 Google 按钮确认是你本人。"),
    "settings.googlePasswordSaving": L("Saving…", "Сохраняем…", "Нигоҳ дошта истодааст…", "正在保存…"),
    "settings.googlePasswordDone": L(
        "Password set. You can now sign in with your username and this password. Your other devices have been signed out.",
        "Пароль задан. Теперь можно входить по имени пользователя и этому паролю. На других устройствах выполнен выход.",
        "Парол муқаррар шуд. Акнун бо номи корбар ва ҳамин парол ворид шудан мумкин аст. Дар дастгоҳҳои дигар шумо хориҷ шудед.",
        "密码已设置。现在可以用用户名和这个密码登录。你在其他设备上的登录已失效。"),
    "settings.googlePasswordApp": L(
        "Setting a password with Google works on the website: open chineseverse.qobus.tj in a browser and go to Settings. Or sign out and use “Forgot password?” on the sign-in screen.",
        "Задать пароль через Google можно на сайте: откройте chineseverse.qobus.tj в браузере и перейдите в настройки. Или выйдите и воспользуйтесь «Забыли пароль?» на экране входа.",
        "Муқаррар кардани парол бо Google дар сомона кор мекунад: chineseverse.qobus.tj-ро дар браузер кушоед ва ба «Танзимот» гузаред. Ё хориҷ шавед ва дар экрани воридшавӣ «Паролро фаромӯш кардед?»-ро истифода баред.",
        "通过 Google 设置密码需要在网站上进行：用浏览器打开 chineseverse.qobus.tj，进入“设置”。也可以退出登录，在登录界面使用“忘记密码？”。"),
    # ---- Server errors (apiErrors.js) ----
    "apiErrors.resetUnavailable": L(
        "Password reset by email isn't available right now.", "Сброс пароля по почте сейчас недоступен.",
        "Барқарории парол тавассути почта ҳоло дастрас нест.", "目前无法通过邮件重置密码。"),
    "apiErrors.resetInvalid": L(
        "This reset link is invalid or was already used. Ask for a new one.",
        "Ссылка недействительна или уже использована. Запросите новую.",
        "Ин пайванд нодуруст аст ё аллакай истифода шудааст. Пайванди нав дархост кунед.",
        "此链接无效或已被使用，请重新申请。"),
    "apiErrors.resetExpired": L(
        "This reset link has expired. Ask for a new one — it works for 30 minutes.",
        "Срок действия ссылки истёк. Запросите новую — она действует 30 минут.",
        "Мӯҳлати ин пайванд гузашт. Пайванди нав дархост кунед — он 30 дақиқа кор мекунад.",
        "此链接已过期。请重新申请——新链接 30 分钟内有效。"),
    "apiErrors.googleNotLinked": L(
        "Your account isn't linked to a Google account.", "Ваш аккаунт не связан с Google.",
        "Ҳисоби шумо ба Google пайваст нест.", "你的账户没有关联 Google。"),
    "apiErrors.googleWrongAccount": L(
        "That Google account isn't the one linked to your ChineseVerse account. Choose the right one.",
        "Этот аккаунт Google не связан с вашим аккаунтом ChineseVerse. Выберите нужный.",
        "Ин ҳисоби Google ба ҳисоби ChineseVerse-и шумо пайваст нест. Ҳисоби дурустро интихоб кунед.",
        "这个 Google 账户不是与你的 ChineseVerse 账户关联的那个，请选择正确的账户。"),
    "apiErrors.googleConfirmAgain": L(
        "Please confirm with Google again.", "Подтвердите через Google ещё раз.",
        "Лутфан бо Google бори дигар тасдиқ кунед.", "请再次用 Google 确认。"),
}

# Existing strings whose advice is now wrong: a Google account can get a
# password after all.
REPLACE = {
    "settings.passwordProviderHint": L(
        "Signed up with Google or GitHub and never had a password? Use “Set a password with Google” below, or “Forgot password?” on the sign-in page.",
        "Регистрировались через Google или GitHub и пароля у вас не было? Воспользуйтесь «Задать пароль через Google» ниже или «Забыли пароль?» на странице входа.",
        "Тавассути Google ё GitHub сабти ном шуда будед ва парол надоштед? Аз «Муқаррар кардани парол бо Google» дар поён ё «Паролро фаромӯш кардед?» дар саҳифаи воридшавӣ истифода баред.",
        "用 Google 或 GitHub 注册、从来没有密码？请使用下方的“通过 Google 设置密码”，或登录页的“忘记密码？”。"),
    "download.help6A": L(
        "The app signs in with your ChineseVerse username and password and needs an internet connection. Created your account with Google? Set a password first: on the website, Settings → “Set a password with Google”, or “Forgot password?” on the sign-in screen.",
        "Приложение входит по имени пользователя и паролю ChineseVerse и требует подключения к интернету. Создали аккаунт через Google? Сначала задайте пароль: на сайте в «Настройки» → «Задать пароль через Google» или через «Забыли пароль?» на экране входа.",
        "Барнома бо номи корбар ва пароли ChineseVerse ворид мешавад ва интернет лозим аст. Ҳисобро тавассути Google эҷод кардаед? Аввал парол муқаррар кунед: дар сомона «Танзимот» → «Муқаррар кардани парол бо Google» ё «Паролро фаромӯш кардед?» дар экрани воридшавӣ.",
        "应用用 ChineseVerse 的用户名和密码登录，并需要联网。账户是用 Google 创建的？请先设置密码：在网站“设置”→“通过 Google 设置密码”，或在登录界面使用“忘记密码？”。"),
}


def replace(lines, dotted, value):
    parent, leaf = dotted.rsplit(".", 1)
    lo, hi = _object(lines, parent)
    pad = " " * (2 * (parent.count(".") + 2))
    i = next(i for i in range(lo, hi) if lines[i].startswith(f'{pad}"{leaf}":'))
    lines[i] = _line(len(pad), leaf, value, lines[i].endswith(","))


if __name__ == "__main__":
    for lang in LANGS:
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.read().split("\r\n")
        for dotted, value in S.items():
            put(lines, dotted, value[lang])
        for dotted, value in REPLACE.items():
            replace(lines, dotted, value[lang])
        text = "\r\n".join(lines)
        json.loads(text)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"updated {lang}.json")
