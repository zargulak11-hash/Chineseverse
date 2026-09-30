# -*- coding: utf-8 -*-
"""Adds the Admin Users (database source, auth method, activity, paging)
strings to pages.adminUsers in all four locale files. Idempotent.
Run from frontend/: python scripts/add_admin_users_i18n.py
"""
import json
import os

LOCALES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "locales")

T = {
    "en": {
        "dbLocal": "LOCAL DATABASE", "dbProduction": "PRODUCTION DATABASE", "dbTest": "TEST DATABASE",
        "dbSource": "{{engine}} · {{name}}", "servedBy": "served by {{host}}",
        "dbNote": "Local and production are separate databases. This page lists only the database above; open Admin → Users on the other environment to see its users.",
        "adminCount": "Admins: {{count}}", "regularCount": "Regular users: {{count}}",
        "searchPlaceholder": "Search by name or email", "noMatches": "No users match \"{{query}}\".",
        "pageRange": "{{from}}–{{to}} of {{total}}", "prev": "Previous", "next": "Next",
        "colAuth": "Sign-in", "authGoogle": "Google", "authPassword": "Password", "googleId": "Google ID",
        "colProgress": "HSK / progress", "hskMastery": "HSK {{level}} · {{mastery}}%", "xp": "{{xp}} XP",
        "noProgress": "No progress yet", "colLastActivity": "Last activity", "never": "Never",
        "colRole": "Role", "roleAdmin": "Admin", "roleUser": "User",
        "authNote": "Sign-in shows Google once an account is linked to Google. Google accounts created before linking existed show Password until their next Google sign-in. Last activity is the latest recorded learning activity; there is no separate login log.",
    },
    "ru": {
        "dbLocal": "ЛОКАЛЬНАЯ БАЗА ДАННЫХ", "dbProduction": "БАЗА ДАННЫХ PRODUCTION", "dbTest": "ТЕСТОВАЯ БАЗА ДАННЫХ",
        "dbSource": "{{engine}} · {{name}}", "servedBy": "сервер {{host}}",
        "dbNote": "Локальная и production — это разные базы данных. Здесь показана только база выше; чтобы увидеть пользователей другой среды, откройте Админ → Пользователи там.",
        "adminCount": "Админов: {{count}}", "regularCount": "Обычных пользователей: {{count}}",
        "searchPlaceholder": "Поиск по имени или email", "noMatches": "Нет пользователей по запросу «{{query}}».",
        "pageRange": "{{from}}–{{to}} из {{total}}", "prev": "Назад", "next": "Далее",
        "colAuth": "Вход", "authGoogle": "Google", "authPassword": "Пароль", "googleId": "Google ID",
        "colProgress": "HSK / прогресс", "hskMastery": "HSK {{level}} · {{mastery}}%", "xp": "{{xp}} XP",
        "noProgress": "Прогресса пока нет", "colLastActivity": "Последняя активность", "never": "Никогда",
        "colRole": "Роль", "roleAdmin": "Админ", "roleUser": "Пользователь",
        "authNote": "Вход через Google отображается, когда аккаунт привязан к Google. Google-аккаунты, созданные до появления привязки, показываются как «Пароль» до следующего входа через Google. Последняя активность — последнее записанное учебное действие; отдельного журнала входов нет.",
    },
    "tg": {
        "dbLocal": "ПОЙГОҲИ МАЪЛУМОТИ ЛОКАЛӢ", "dbProduction": "ПОЙГОҲИ МАЪЛУМОТИ PRODUCTION", "dbTest": "ПОЙГОҲИ МАЪЛУМОТИ САНҶИШӢ",
        "dbSource": "{{engine}} · {{name}}", "servedBy": "сервер {{host}}",
        "dbNote": "Локалӣ ва production пойгоҳҳои маълумоти алоҳидаанд. Ин саҳифа танҳо пойгоҳи болоро нишон медиҳад; барои дидани корбарони муҳити дигар, дар он ҷо Админ → Корбарон-ро кушоед.",
        "adminCount": "Админҳо: {{count}}", "regularCount": "Корбарони оддӣ: {{count}}",
        "searchPlaceholder": "Ҷустуҷӯ аз рӯи ном ё email", "noMatches": "Барои «{{query}}» корбар ёфт нашуд.",
        "pageRange": "{{from}}–{{to}} аз {{total}}", "prev": "Қаблӣ", "next": "Минбаъда",
        "colAuth": "Воридшавӣ", "authGoogle": "Google", "authPassword": "Парол", "googleId": "Google ID",
        "colProgress": "HSK / пешрафт", "hskMastery": "HSK {{level}} · {{mastery}}%", "xp": "{{xp}} XP",
        "noProgress": "Ҳоло пешрафт нест", "colLastActivity": "Фаъолияти охирин", "never": "Ҳеҷ гоҳ",
        "colRole": "Нақш", "roleAdmin": "Админ", "roleUser": "Корбар",
        "authNote": "Воридшавӣ бо Google вақте нишон дода мешавад, ки ҳисоб ба Google пайваст аст. Ҳисобҳои Google, ки пеш аз пайдо шудани пайвастшавӣ сохта шудаанд, то воридшавии навбатӣ бо Google ҳамчун «Парол» нишон дода мешаванд. Фаъолияти охирин — охирин амали таълимии сабтшуда; журнали алоҳидаи воридшавӣ вуҷуд надорад.",
    },
    "zh": {
        "dbLocal": "本地数据库", "dbProduction": "生产数据库", "dbTest": "测试数据库",
        "dbSource": "{{engine}} · {{name}}", "servedBy": "服务器 {{host}}",
        "dbNote": "本地和生产是两个独立的数据库。本页只列出上方这个数据库的用户；要查看另一个环境的用户，请在那个环境打开 管理 → 用户。",
        "adminCount": "管理员：{{count}}", "regularCount": "普通用户：{{count}}",
        "searchPlaceholder": "按用户名或邮箱搜索", "noMatches": "没有与“{{query}}”匹配的用户。",
        "pageRange": "第 {{from}}–{{to}} 个，共 {{total}} 个", "prev": "上一页", "next": "下一页",
        "colAuth": "登录方式", "authGoogle": "Google", "authPassword": "密码", "googleId": "Google ID",
        "colProgress": "HSK / 进度", "hskMastery": "HSK {{level}} · {{mastery}}%", "xp": "{{xp}} XP",
        "noProgress": "暂无进度", "colLastActivity": "最近活动", "never": "从未",
        "colRole": "角色", "roleAdmin": "管理员", "roleUser": "用户",
        "authNote": "账号关联 Google 后，登录方式显示为 Google。在关联功能出现之前创建的 Google 账号，在下次用 Google 登录前会显示为“密码”。最近活动是最近一次记录的学习活动；系统没有单独的登录记录。",
    },
}

for loc, entries in T.items():
    path = os.path.join(LOCALES, f"{loc}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("pages", {}).setdefault("adminUsers", {}).update(entries)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"updated {loc}.json")
