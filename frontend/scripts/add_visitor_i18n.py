# -*- coding: utf-8 -*-
"""Adds the strings of the first-visit pass -- the landing page's "where to
start" steps, the app download link in the navigation, and the download
page's troubleshooting -- into all four locale files, as new lines inside
their existing sections. Idempotent: keys already present are skipped.
Run from frontend/: python scripts/add_visitor_i18n.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_recall_i18n import LANGS, LOCALES, put  # noqa: E402


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


S = {
    # ---- Navigation (components/Sidebar.jsx, Topbar.jsx search) ----
    "nav.downloadApp": L("Android app", "Приложение Android", "Барномаи Android", "安卓应用"),
    # ---- Landing: where to start (pages/Landing.jsx) ----
    "landing.startEyebrow": L("Where to start", "С чего начать", "Аз куҷо оғоз кардан", "从哪里开始"),
    "landing.startTitle": L("How learning works", "Как проходит обучение", "Омӯзиш чӣ тавр мегузарад", "学习流程"),
    "landing.startIntro": L(
        "ChineseVerse is a free Mandarin Chinese course — from your first tones to HSK 9, on the website and in the Android app. Four steps take you from here to your first lesson.",
        "ChineseVerse — бесплатный курс китайского языка: от первых тонов до HSK 9, на сайте и в приложении для Android. Четыре шага — и вы на первом уроке.",
        "ChineseVerse — курси ройгони забони чинӣ: аз оҳангҳои аввалин то HSK 9, дар сомона ва дар барномаи Android. Чор қадам — ва шумо дар дарси аввал ҳастед.",
        "ChineseVerse 是一门免费的汉语课程——从第一个声调学到 HSK 9，网站和安卓应用都能用。四步就能开始第一课。"),
    "landing.step1Title": L("Create your account", "Создайте аккаунт", "Ҳисоб эҷод кунед", "创建账户"),
    "landing.step1Text": L(
        "Sign up with a username, email and password — or continue with Google. It takes a minute.",
        "Зарегистрируйтесь с именем пользователя, email и паролем — или войдите через Google. Это займёт минуту.",
        "Бо номи корбар, почтаи электронӣ ва парол сабти ном шавед — ё тавассути Google ворид шавед. Ин як дақиқа вақт мегирад.",
        "用用户名、邮箱和密码注册，或者直接用 Google 登录。只需一分钟。"),
    "landing.step2Title": L("Pick a companion and your level", "Выберите компаньона и уровень",
                            "Ҳамроҳ ва сатҳи худро интихоб кунед", "选择伙伴和起点"),
    "landing.step2Text": L(
        "Choose the animal who learns with you. Start from zero, or take a short test that finds your HSK level.",
        "Выберите животное, которое будет учиться с вами. Начните с нуля или пройдите короткий тест, который определит ваш уровень HSK.",
        "Ҳайвонеро интихоб кунед, ки бо шумо меомӯзад. Аз сифр оғоз кунед ё санҷиши кӯтоҳеро супоред, ки сатҳи HSK-и шуморо муайян мекунад.",
        "选一只陪你学习的小动物。可以从零开始，也可以做个简短测试，确定你的 HSK 等级。"),
    "landing.step3Title": L("Learn lesson by lesson", "Учитесь урок за уроком", "Дарс ба дарс омӯзед", "一课一课地学"),
    "landing.step3Text": L(
        "Each lesson teaches words, characters and grammar, then a practice round checks what you remember. All lessons are under Lessons, and Home always shows your next step.",
        "Каждый урок даёт слова, иероглифы и грамматику, а затем практика проверяет, что вы запомнили. Все уроки — в разделе «Уроки», а на «Главной» всегда виден следующий шаг.",
        "Ҳар дарс калимаҳо, иероглифҳо ва грамматикаро меомӯзонад, баъд машқ месанҷад, ки шумо чиро дар хотир доред. Ҳамаи дарсҳо дар бахши «Дарсҳо» ҳастанд ва «Асосӣ» ҳамеша қадами навбатиро нишон медиҳад.",
        "每节课教词语、汉字和语法，再用一轮练习检查你记住了多少。所有课程都在“课程”里，“主页”总会显示下一步。"),
    "landing.step4Title": L("Review and track your progress", "Повторяйте и следите за прогрессом",
                            "Такрор кунед ва пешрафтро пайгирӣ намоед", "复习并跟踪进度"),
    "landing.step4Text": L(
        "Words you get wrong come back in Review until they stick. Progress shows your streak, XP and every level you have finished.",
        "Слова, в которых вы ошиблись, возвращаются в «Повторение», пока не запомнятся. В «Прогрессе» — ваша серия дней, XP и пройденные уровни.",
        "Калимаҳое, ки дар онҳо хато кардед, дар «Такрор» бармегарданд, то дар хотир монанд. «Пешрафт» силсилаи рӯзҳо, XP ва сатҳҳои анҷомдодаро нишон медиҳад.",
        "答错的词会回到“复习”里，直到你记住为止。“进度”页显示连续学习天数、经验值和已完成的等级。"),
    "landing.haveAccount": L("Already learning with ChineseVerse?", "Уже учитесь в ChineseVerse?",
                             "Аллакай дар ChineseVerse меомӯзед?", "已经在 ChineseVerse 学习了？"),
    # ---- Download: troubleshooting (pages/Download.jsx) ----
    "download.helpTitle": L("If something goes wrong", "Если что-то пошло не так", "Агар чизе нашавад", "遇到问题怎么办"),
    "download.help1Q": L("The download doesn't start or stops halfway", "Загрузка не начинается или обрывается",
                         "Боргирӣ оғоз намешавад ё нимароҳ қатъ мешавад", "下载没有开始或中途停止"),
    "download.help1A": L(
        "Check your internet connection and tap “Download Android App” again. If the browser blocks the file, open this page in Chrome, or download the file from “All versions”.",
        "Проверьте подключение к интернету и снова нажмите «Скачать для Android». Если браузер блокирует файл, откройте эту страницу в Chrome или скачайте файл со страницы «Все версии».",
        "Пайвастшавӣ ба интернетро санҷед ва боз «Боргирӣ барои Android»-ро пахш кунед. Агар браузер файлро манъ кунад, ин саҳифаро дар Chrome кушоед ё файлро аз «Ҳамаи версияҳо» боргирӣ кунед.",
        "检查网络连接，然后再点一次“下载 Android 应用”。如果浏览器拦截了文件，请用 Chrome 打开本页，或从“所有版本”下载。"),
    "download.help2Q": L("I can't find the downloaded file", "Не могу найти скачанный файл",
                         "Файли боргиришударо ёфта наметавонам", "找不到下载的文件"),
    "download.help2A": L(
        "Open your browser's downloads (in Chrome: menu ⋮ → Downloads) or the Files app → Downloads. The file is called {{file}}.",
        "Откройте загрузки браузера (в Chrome: меню ⋮ → «Скачанные файлы») или приложение «Файлы» → «Загрузки». Файл называется {{file}}.",
        "Боргириҳои браузерро кушоед (дар Chrome: менюи ⋮ → «Боргириҳо») ё барномаи «Файлҳо» → «Боргириҳо». Номи файл {{file}} аст.",
        "打开浏览器的下载列表（Chrome：菜单 ⋮ → 下载内容），或“文件”应用 → 下载。文件名是 {{file}}。"),
    "download.help3Q": L("Android won't let me install it", "Android не даёт установить приложение",
                         "Android насб карданро иҷозат намедиҳад", "安卓不让我安装"),
    "download.help3A": L(
        "Open Settings → Apps → Special app access → Install unknown apps, choose the browser or file manager you used, and turn on “Allow from this source”. Menu names differ a little between phone brands.",
        "Откройте «Настройки» → «Приложения» → «Специальный доступ» → «Установка неизвестных приложений», выберите браузер или файловый менеджер, которым пользовались, и включите «Разрешить установку из этого источника». Названия пунктов немного отличаются у разных производителей.",
        "«Танзимот» → «Барномаҳо» → «Дастрасии махсус» → «Насби барномаҳои номаълум»-ро кушоед, браузер ё мудири файлҳоеро, ки истифода бурдед, интихоб кунед ва «Иҷозат аз ин манбаъ»-ро фаъол созед. Номи бандҳо дар телефонҳои гуногун каме фарқ мекунад.",
        "打开“设置”→“应用”→“特殊应用权限”→“安装未知应用”，选择你用来下载的浏览器或文件管理器，打开“允许来自此来源的应用”。不同品牌手机的菜单名称略有不同。"),
    "download.help4Q": L("“App not installed” or “problem parsing the package”",
                         "«Приложение не установлено» или «Ошибка при синтаксическом анализе пакета»",
                         "«Барнома насб нашуд» ё «Хатогӣ ҳангоми таҳлили баста»",
                         "“未安装应用”或“解析软件包时出现问题”"),
    "download.help4A": L(
        "The file is probably incomplete: delete it and download it again. Check that your phone runs Android {{android}} or newer and has enough free space. If an earlier test version of ChineseVerse is installed, uninstall it first.",
        "Скорее всего, файл скачался не полностью: удалите его и скачайте заново. Убедитесь, что на телефоне Android {{android}} или новее и достаточно свободного места. Если установлена ранняя тестовая версия ChineseVerse, сначала удалите её.",
        "Эҳтимол файл пурра боргирӣ нашудааст: онро нест кунед ва аз нав боргирӣ кунед. Санҷед, ки дар телефон Android {{android}} ё навтар ва ҷои кофии холӣ ҳаст. Агар версияи санҷишии пешинаи ChineseVerse насб бошад, аввал онро нест кунед.",
        "文件可能没有下载完整：删除后重新下载。确认手机是 Android {{android}} 或更新版本，并有足够的存储空间。如果装过 ChineseVerse 的早期测试版，请先卸载。"),
    "download.help5Q": L("Google Play Protect warns about the app", "Google Play Защита предупреждает о приложении",
                         "Google Play Protect дар бораи барнома огоҳ мекунад", "Google Play 保护机制发出警告"),
    "download.help5A": L(
        "Play Protect warns about apps that don't come from Google Play. If you downloaded the file from this page, tap “More details” → “Install anyway”. You can compare the SHA-256 checksum under “File details”.",
        "Play Защита предупреждает о приложениях не из Google Play. Если вы скачали файл с этой страницы, нажмите «Подробнее» → «Всё равно установить». Контрольную сумму SHA-256 можно сверить в разделе «О файле».",
        "Play Protect дар бораи барномаҳое, ки аз Google Play нестанд, огоҳ мекунад. Агар файлро аз ҳамин саҳифа боргирӣ карда бошед, «Тафсилоти бештар» → «Ба ҳар ҳол насб кардан»-ро пахш кунед. Ҷамъи санҷишии SHA-256-ро дар «Маълумот дар бораи файл» муқоиса кардан мумкин аст.",
        "Play 保护机制会对不是来自 Google Play 的应用发出警告。如果文件是从本页下载的，点“更多详情”→“仍然安装”。可以在“文件信息”里核对 SHA-256 校验值。"),
    "download.help6Q": L("I can't sign in in the app", "Не получается войти в приложении",
                         "Ба барнома ворид шуда наметавонам", "在应用里无法登录"),
    "download.help6A": L(
        "The app signs in with your ChineseVerse username and password and needs an internet connection. If you created your account with Google, it has no password yet — keep using the website for now.",
        "Приложение входит по имени пользователя и паролю ChineseVerse и требует подключения к интернету. Если вы создали аккаунт через Google, у него пока нет пароля — пока продолжайте учиться на сайте.",
        "Барнома бо номи корбар ва пароли ChineseVerse ворид мешавад ва интернет лозим аст. Агар ҳисобро тавассути Google эҷод карда бошед, он ҳанӯз парол надорад — то он вақт дар сомона омӯзишро идома диҳед.",
        "应用用 ChineseVerse 的用户名和密码登录，并需要联网。如果你的账户是用 Google 创建的，它还没有密码——目前请继续在网站上学习。"),
    "download.helpFallback": L(
        "Still stuck? Everything in the app also works right here on the website, with the same account.",
        "Ничего не помогло? Всё, что есть в приложении, работает и здесь, на сайте, с тем же аккаунтом.",
        "Ҳеҷ чиз кӯмак накард? Ҳар чизе ки дар барнома ҳаст, дар ҳамин сомона бо ҳамон ҳисоб кор мекунад.",
        "还是不行？应用里的一切在网站上同样能用，账户也是同一个。"),
    "download.helpWebsite": L("Continue on the website", "Продолжить на сайте", "Дар сомона идома додан", "在网站上继续"),
}
KEYS = list(S)

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
