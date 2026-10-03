"""User-facing rename: "Learning DNA" / "ДНК" -> "Learning Compass".

EN "Learning Compass", RU "Компас обучения", TG "Қутбнамои омӯзиш",
ZH "学习指南针". Only the visible text changes; keys (nav.dna, pages.dna.*),
the /dna route and the backend's Learning DNA internals keep their names.
Character DNA (charDna.*, ecosystem.openDna) is a different feature -- the
anatomy of one character -- and keeps its name.

Run from frontend/:  python scripts/rename_learning_compass.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")

S = {
    "nav.dna": {
        "en": "Learning Compass", "ru": "Компас обучения", "tg": "Қутбнамои омӯзиш", "zh": "学习指南针"},
    "landing.tagline": {
        "en": "Talk your way through a Chinese city with a companion by your side. Every conversation is practice; every practice sharpens your Learning Compass.",
        "ru": "Пройдите китайский город вместе со своим компаньоном. Каждый разговор — практика, а каждая практика уточняет ваш компас обучения.",
        "tg": "Дар шаҳри чинӣ ҳамроҳи ҳамроҳи худ гап занед. Ҳар сӯҳбат — машқ аст; ҳар машқ қутбнамои омӯзиши шуморо дақиқтар мекунад.",
        "zh": "与你的伙伴一起穿行于一座中文城市。每一次对话都是练习；每一次练习都让你的学习指南针更精准。"},
    "landing.featDnaTitle": {
        "en": "Learning Compass", "ru": "Компас обучения", "tg": "Қутбнамои омӯзиш", "zh": "学习指南针"},
    "landing.featDuelsTitle": {
        "en": "Live Duels", "ru": "Живые дуэли", "tg": "Дуэлҳои зинда", "zh": "实时对战"},
    "dashboard.viewDna": {
        "en": "Open your Learning Compass", "ru": "Открыть компас обучения", "tg": "Кушодани қутбнамои омӯзиш",
        "zh": "查看学习指南针"},
    "dashboard.learningDnaOverall": {
        "en": "Learning Compass overall", "ru": "Компас обучения в целом", "tg": "Қутбнамои омӯзиш — умумӣ",
        "zh": "学习指南针总览"},
    "dashboard.prosConsDna": {
        "en": "Strengths and weak spots", "ru": "Сильные и слабые стороны", "tg": "Тарафҳои қавӣ ва заиф",
        "zh": "优势与弱项"},
    "dashboard.fullDna": {
        "en": "Full Learning Compass", "ru": "Весь компас обучения", "tg": "Қутбнамои пурра", "zh": "完整学习指南针"},
    "pages.vocabulary.subtitle": {
        "en": "Real HSK 3.0 words. Practice a level to build mastery — results feed your Learning Compass, quests and review queue.",
        "ru": "Настоящие слова HSK 3.0. Практикуйте уровень, чтобы освоить их — результаты влияют на компас обучения, задания и повторение.",
        "tg": "Калимаҳои воқеии HSK 3.0. Барои азхудкунӣ сатҳро машқ кунед — натиҷаҳо ба қутбнамои омӯзиш, супоришҳо ва такрор таъсир мерасонанд.",
        "zh": "真实的 HSK 3.0 词汇。练习一个级别来提高掌握度——结果会计入你的学习指南针、任务和复习队列。"},
    "pages.dna.title": {
        "en": "Your Learning Compass", "ru": "Ваш компас обучения", "tg": "Қутбнамои омӯзиши шумо", "zh": "你的学习指南针"},
    "pages.dna.loading": {
        "en": "Reading your Learning Compass…", "ru": "Сверяем ваш компас обучения…",
        "tg": "Қутбнамои омӯзиши шумо хонда мешавад…", "zh": "正在校准你的学习指南针…"},
    "pages.quests.subtitle": {
        "en": "Generated from your Learning Compass every day. Complete them to feed your companion.",
        "ru": "Создаются по вашему компасу обучения каждый день. Выполняйте их, чтобы порадовать компаньона.",
        "tg": "Ҳар рӯз аз рӯи қутбнамои омӯзиши шумо тавлид мешаванд. Барои хушнуд кардани ҳамроҳатон онҳоро иҷро кунед.",
        "zh": "每天根据你的学习指南针生成。完成它们来喂养你的伙伴。"},
    "pages.lessonDetail.saved": {
        "en": "Saved — Learning Compass updated.", "ru": "Сохранено — компас обучения обновлён.",
        "tg": "Захира шуд — қутбнамои омӯзиш навсозӣ шуд.", "zh": "已保存——学习指南针已更新。"},
    "pages.conversation.completed": {
        "en": "You made it through the whole conversation. That counts toward your Learning Compass.",
        "ru": "Вы прошли весь разговор целиком. Это учитывается в вашем компасе обучения.",
        "tg": "Шумо тамоми сӯҳбатро анҷом додед. Ин дар қутбнамои омӯзиши шумо ҳисоб мешавад.",
        "zh": "你完成了整段对话，这会计入你的学习指南针。"},
    "companionReact.cause.skill_up": {
        "en": "{{name}} noticed: your {{skill}} just grew on your Learning Compass!",
        "ru": "{{name}} заметил: навык «{{skill}}» на вашем компасе обучения вырос!",
        "tg": "{{name}} пай бурд: маҳорати «{{skill}}» дар қутбнамои омӯзиши шумо афзуд!",
        "zh": "{{name}}发现：你的学习指南针上「{{skill}}」提高了！"},
    "companionMemory.action.weak_skill": {
        "en": "Open my Learning Compass", "ru": "Мой компас обучения", "tg": "Қутбнамои омӯзиши ман",
        "zh": "查看学习指南针"},
    "detective.profile.skills": {
        "en": "Tuned to your Learning Compass: reading {{reading}}, listening {{listening}}",
        "ru": "По вашему компасу обучения: чтение {{reading}}, аудирование {{listening}}",
        "tg": "Мувофиқи қутбнамои омӯзиши шумо: хондан {{reading}}, шунидан {{listening}}",
        "zh": "根据你的学习指南针：阅读{{reading}}，听力{{listening}}"},
    "internet.howReading": {
        "en": "Reading on your Learning Compass: {{reading}}", "ru": "Чтение на вашем компасе обучения: {{reading}}",
        "tg": "Хондан дар қутбнамои омӯзиши шумо: {{reading}}", "zh": "你的学习指南针·阅读：{{reading}}"},
    "internet.helper.dna": {
        "en": "Learning Compass — vocabulary {{vocabulary}}, reading {{reading}}.",
        "ru": "Компас обучения — словарь {{vocabulary}}, чтение {{reading}}.",
        "tg": "Қутбнамои омӯзиш — луғат {{vocabulary}}, хондан {{reading}}.",
        "zh": "学习指南针——词汇{{vocabulary}}，阅读{{reading}}。"},
    "passport.evidence.dna": {
        "en": "Learning Compass {{skill}}: {{value}}/100", "ru": "Компас обучения, {{skill}}: {{value}}/100",
        "tg": "Қутбнамои омӯзиш, {{skill}}: {{value}}/100", "zh": "学习指南针·{{skill}}：{{value}}/100"},
    "passport.openDna": {
        "en": "Open Learning Compass", "ru": "Открыть компас обучения", "tg": "Кушодани қутбнамои омӯзиш",
        "zh": "查看学习指南针"},
    "world.adaptNoEvidence": {
        "en": "No Learning Compass evidence yet — the city uses your HSK level as it is.",
        "ru": "Данных компаса обучения пока нет — город использует ваш уровень HSK как есть.",
        "tg": "Ҳоло далели қутбнамои омӯзиш нест — шаҳр сатҳи HSK-и шуморо ҳамон тавр истифода мебарад.",
        "zh": "还没有学习指南针数据——城市先按你的HSK级别安排。"},
}


def main():
    for lang in ("en", "ru", "tg", "zh"):
        path = os.path.join(LOCALES, f"{lang}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, values in S.items():
            node = data
            *parents, leaf = key.split(".")
            for part in parents:
                node = node[part]
            assert leaf in node, (lang, key)
            node[leaf] = values[lang]
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"renamed {len(S)} strings in 4 locales")


if __name__ == "__main__":
    main()
