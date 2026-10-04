"""User-facing rename: "Chinese Passport" -> "My Chinese Journey".

EN "My Chinese Journey", RU "Мой китайский путь", TG "Роҳи омӯзиши чинии
ман", ZH "我的中文之旅". Only the visible text changes; keys (nav.passport,
passport.*), the /passport route, the /api/passport endpoint and the
backend's passport internals keep their names so bookmarks and links keep
working. The World map's "Passport office" is a place in the city (its
lesson vocabulary is 护照), not the feature's name, and keeps its name.

Run from frontend/:  python scripts/rename_my_chinese_journey.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALES = os.path.join(HERE, "..", "src", "locales")

OPEN = {
    "en": "Open My Chinese Journey", "ru": "Открыть «Мой китайский путь»",
    "tg": "Кушодани «Роҳи омӯзиши чинии ман»", "zh": "打开我的中文之旅"}

S = {
    "nav.passport": {
        "en": "My Chinese Journey", "ru": "Мой китайский путь", "tg": "Роҳи омӯзиши чинии ман", "zh": "我的中文之旅"},
    "passport.title": {
        "en": "My Chinese Journey", "ru": "Мой китайский путь", "tg": "Роҳи омӯзиши чинии ман", "zh": "我的中文之旅"},
    "passport.fromDna": {
        "en": "See the evidence in My Chinese Journey",
        "ru": "Подробности — в разделе «Мой китайский путь»",
        "tg": "Далелҳо — дар «Роҳи омӯзиши чинии ман»",
        "zh": "在“我的中文之旅”里查看依据"},
    "passport.howTitle": {
        "en": "How My Chinese Journey works", "ru": "Как работает «Мой китайский путь»",
        "tg": "«Роҳи омӯзиши чинии ман» чӣ тавр кор мекунад", "zh": "“我的中文之旅”怎么判断"},
    "passport.how": {
        "en": "Every ability is judged from your graded answers and records, never from points. With fewer than {{min}} answers, it says so instead of guessing.",
        "ru": "Каждый навык оценивается по проверенным ответам и записям, а не по очкам. Если ответов меньше {{min}}, раздел так и говорит, а не гадает.",
        "tg": "Ҳар малака аз рӯи ҷавобҳои санҷидашуда ва сабтҳо баҳо дода мешавад, на аз рӯи хол. Агар ҷавобҳо аз {{min}} кам бошанд, тахмин намекунад.",
        "zh": "每项能力都根据你的答题和学习记录判断，从不看积分。答题少于{{min}}次时会直接说明，而不是猜测。"},
    "intro.passport.what": {
        "en": "My Chinese Journey: a record of what you can really do — places used, cases solved, words and characters mastered.",
        "ru": "«Мой китайский путь»: запись того, что вы действительно умеете — пройденные места, раскрытые дела, освоенные слова и иероглифы.",
        "tg": "«Роҳи омӯзиши чинии ман»: сабти он чи ки воқеан метавонед — ҷойҳои истифодашуда, парвандаҳои ҳалшуда, калимаҳо ва иероглифҳои азхудшуда.",
        "zh": "我的中文之旅：记录你真正能做到的事——去过的地方、破过的案、掌握的词和汉字。"},
    "companionMemory.kind.passport_milestone": {
        "en": "A new page in My Chinese Journey: {{event}}",
        "ru": "Новая страница в разделе «Мой китайский путь»: {{event}}",
        "tg": "Саҳифаи нав дар «Роҳи омӯзиши чинии ман»: {{event}}",
        "zh": "我的中文之旅翻开了新的一页：{{event}}"},
    "companionMemory.action.passport_milestone": OPEN,
    "world.passportLink": OPEN,
    "world.place.passport_office.enter": OPEN,
    "world.place.passport_office.desc": {
        "en": "My Chinese Journey: what you can really do, with the evidence and your story.",
        "ru": "«Мой китайский путь»: что вы действительно умеете, с доказательствами и вашей историей.",
        "tg": "«Роҳи омӯзиши чинии ман»: шумо воқеан чӣ карда метавонед, бо далелҳо ва таърихатон.",
        "zh": "我的中文之旅：你真正能做什么，有依据，也有你的故事。"},
    "world.how": {
        "en": "Each place opens when your HSK level reaches it — the same level your Dashboard and HSK path show. Inside an open place, topics light up as their words become yours, and every completed conversation is recorded on the map and in My Chinese Journey.",
        "ru": "Каждое место открывается, когда ваш уровень HSK до него дорастает, — тот же уровень, что на главной и на пути HSK. В открытом месте темы оживают, когда слова становятся вашими, а каждый пройденный разговор отмечается на карте и в разделе «Мой китайский путь».",
        "tg": "Ҳар ҷой вақте кушода мешавад, ки сатҳи HSK-и шумо ба он мерасад — ҳамон сатҳе, ки дар саҳифаи асосӣ ва роҳи HSK нишон дода мешавад. Дар ҷои кушода мавзӯъҳо бо азхудшавии калимаҳо равшан мешаванд ва ҳар сӯҳбати тамомшуда дар харита ва дар «Роҳи омӯзиши чинии ман» сабт мешавад.",
        "zh": "每个地方在你的HSK级别达到时开放——就是首页和HSK路线上显示的级别。在开放的地方，话题会随着词语成为你的而点亮，每次完成的对话都会记录在地图和“我的中文之旅”里。"},
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
