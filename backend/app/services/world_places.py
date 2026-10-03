"""The places of the living world on /real-chinese (services/world_map.py).

Content, not progress. Each place is a spot on the map that leads into a
system that already exists -- a Real Chinese scene, the World voice
conversations and cases (Location/Scenario rows), a Sound World place,
Chinese Internet items, or a gateway (Detective, Sound World, Internet,
lessons, Character DNA, the Vocabulary Ecosystem, the Passport).

`theme` are the curriculum words that make the place what it is (every one
exists in the vocabulary -- tests/world_map_test.py checks). Knowing them
is what makes a place richer: each `topic` lights up once the learner
really knows half its words, and a place still above the learner's HSK
level opens early once they know OPEN_BY_WORDS of its theme words.
A topic's `sentence` is a real sentence using those words; it opens as a
One Sentence lesson, which drills exactly them.

x/y place the node on the 100 x 62 map canvas.
"""

from __future__ import annotations

OPEN_BY_WORDS = 3  # theme words known that open a place before its level


def P(key, icon, district, x, y, min_level, *, scene=None, location=None, sound=None, internet=(), gateway=None,
      theme=(), topics=()):
    return {"key": key, "icon": icon, "district": district, "x": x, "y": y, "min_level": min_level, "scene": scene,
            "location": location, "sound": sound, "internet": tuple(internet), "gateway": gateway,
            "theme": tuple(theme), "topics": tuple(topics)}


def TOPIC(key, words, sentence):
    return {"key": key, "words": tuple(words), "sentence": sentence}


PLACES = [
    # ---- home quarter: where the companion lives, and where words are studied
    P("home", "🏠", "home", 10, 46, 1, location="home",
      theme=("家", "妈妈", "爸爸", "吃饭", "睡觉", "喜欢"),
      topics=(TOPIC("family", ("家", "妈妈", "爸爸"), "我家有爸爸、妈妈和我。"),
              TOPIC("daily", ("吃饭", "睡觉", "每天"), "我每天晚上七点吃饭，十点睡觉。"))),
    P("library", "📚", "home", 22, 56, 1, gateway="/lessons",
      theme=("学习", "书", "课", "汉语", "老师", "问题")),
    P("calligraphy", "🖌️", "home", 6, 28, 1, gateway="/hanzi",
      theme=("字", "写", "汉字", "笔", "读")),
    P("word_garden", "🌳", "home", 22, 36, 1, gateway="/ecosystem",
      theme=("词", "意思", "认识", "记", "说")),

    # ---- city centre
    P("street", "🏙️", "centre", 36, 44, 1, location="city-street", sound="street",
      theme=("左边", "右边", "前面", "后面", "附近", "往", "走", "路"),
      topics=(TOPIC("directions", ("左边", "右边", "往"), "往前走，银行在左边，饭馆在右边。"),
              TOPIC("nearby", ("附近", "前面", "后面"), "附近有一家饭馆，就在银行后面，书店前面。"))),
    P("restaurant", "🍜", "centre", 44, 56, 1, scene="restaurant", location="restaurant", sound="restaurant",
      internet=("hotpot-review", "dumpling-comments"),
      theme=("菜单", "菜", "米饭", "好吃", "服务员", "饭馆", "一共", "饿"),
      topics=(TOPIC("order", ("菜单", "菜", "米饭"), "请给我菜单，我想要一碗米饭和两个菜。"),
              TOPIC("price", ("一共", "多少", "钱"), "一共多少钱？"),
              TOPIC("taste", ("好吃", "菜", "饿"), "我饿了，这里什么菜好吃？"))),
    P("shop", "🏪", "centre", 36, 26, 1, scene="convenience-store", location="shop", sound="night_market",
      internet=("supermarket-deals",),
      theme=("多少", "钱", "块", "便宜", "贵", "买", "卖"),
      topics=(TOPIC("price", ("多少", "钱", "块"), "这个多少钱？十块钱。"),
              TOPIC("bargain", ("便宜", "贵"), "太贵了，便宜一点儿吧。"),
              TOPIC("buy_sell", ("买", "卖"), "你们这儿卖水果吗？我想买苹果。"))),
    P("shopping_district", "🛍️", "centre", 52, 34, 2, scene="shopping", sound="shopping",
      internet=("thermos-cup",),
      theme=("衣服", "颜色", "试", "打折", "鞋", "号", "红色", "黑色"),
      topics=(TOPIC("size", ("号", "大", "小"), "这件太小了，有没有大一号的？"),
              TOPIC("colour", ("颜色", "红色", "黑色"), "这件衣服有什么颜色？我喜欢红色，不喜欢黑色。"),
              TOPIC("discount", ("打折", "便宜"), "今天打折吗？能便宜一点儿吗？"))),
    P("internet_cafe", "📰", "centre", 58, 50, 1, gateway="/internet",
      theme=("手机", "新闻", "网上", "电脑", "照片")),
    P("detective", "🔎", "centre", 66, 58, 1, gateway="/detective",
      theme=("谁", "为什么", "看见", "知道", "可能")),
    P("sound_plaza", "🎧", "centre", 60, 22, 1, gateway="/sound-world",
      theme=("听", "声音", "说话", "听说", "清楚")),
    P("passport_office", "🪪", "centre", 48, 12, 1, gateway="/passport",
      theme=("护照", "中文", "能", "会", "可以")),

    # ---- campus & work
    P("university", "🏫", "campus", 22, 12, 2, scene="university", sound="school", internet=("class-group-chat",),
      theme=("大学", "同学", "上课", "考试", "作业", "教室", "介绍"),
      topics=(TOPIC("schedule", ("上课", "点", "时间"), "上课时间是下午两点。"),
              TOPIC("classroom", ("教室", "号"), "在三号教室上课。"),
              TOPIC("introduce", ("同学", "介绍"), "我来介绍一下，这是我的同学。"))),
    P("hospital", "🏥", "campus", 8, 10, 3, scene="hospital",
      theme=("医生", "医院", "药", "身体", "生病", "舒服", "发烧", "检查"),
      topics=(TOPIC("symptoms", ("舒服", "发烧", "身体"), "我身体不舒服，有点儿发烧。"),
              TOPIC("doctor", ("医生", "检查", "医院"), "医生在医院给我检查了一下。"),
              TOPIC("medicine", ("药", "次"), "这个药一天吃三次。"))),
    P("office", "💼", "campus", 34, 6, 4, scene="job-interview",
      theme=("工作", "公司", "经验", "面试", "经理", "负责"),
      topics=(TOPIC("interview", ("面试", "经验"), "我明天去面试，我有两年工作经验。"),
              TOPIC("work", ("工作", "公司", "经理"), "我在一家公司工作，我们经理很好。"))),

    # ---- travel
    P("train_station", "🚉", "travel", 74, 30, 2, scene="train-station", sound="train_station", internet=("metro-line",),
      theme=("火车", "票", "车站", "出发", "上车", "晚点", "火车站"),
      topics=(TOPIC("ticket", ("火车", "票"), "我要一张去北京的火车票。"),
              TOPIC("time", ("出发", "点"), "火车几点出发？"),
              TOPIC("boarding", ("上车", "号"), "我们在几号站台上车？"))),
    P("hotel", "🏨", "travel", 84, 46, 3, scene="hotel",
      theme=("房间", "住", "预订", "早饭", "包括", "钥匙"),
      topics=(TOPIC("check_in", ("房间", "住", "预订"), "我预订了一个房间，住两个晚上。"),
              TOPIC("breakfast", ("早饭", "包括"), "早饭包括在里面吗？"),
              TOPIC("help", ("钥匙", "帮"), "我的钥匙找不到了，你能帮我吗？"))),
    P("old_town", "🎭", "travel", 90, 24, 3, scene="travel", sound="street", internet=("park-info", "hiking-post"),
      theme=("旅游", "参观", "拍照", "导游", "门票", "风景"),
      topics=(TOPIC("sightseeing", ("参观", "旅游"), "我们去北京旅游，参观了很多地方。"),
              TOPIC("photos", ("拍照", "风景"), "这里风景很好，可以拍照吗？"),
              TOPIC("tickets", ("门票", "学生"), "学生门票多少钱？"))),
    P("airport", "✈️", "travel", 88, 6, 4, scene="airport", sound="airport",
      theme=("飞机", "机场", "护照", "行李", "起飞", "登机"),
      topics=(TOPIC("check_in", ("护照", "行李"), "这是我的护照和行李。"),
              TOPIC("flight", ("飞机", "起飞"), "飞机几点起飞？"))),
]

PATHS = [
    ("home", "library"), ("home", "word_garden"), ("word_garden", "calligraphy"), ("home", "street"),
    ("street", "restaurant"), ("street", "shop"), ("library", "restaurant"), ("restaurant", "internet_cafe"),
    ("internet_cafe", "detective"), ("shop", "shopping_district"), ("shopping_district", "internet_cafe"),
    ("shopping_district", "sound_plaza"), ("sound_plaza", "passport_office"), ("word_garden", "university"),
    ("university", "hospital"), ("university", "office"), ("office", "passport_office"),
    ("sound_plaza", "train_station"), ("train_station", "hotel"), ("train_station", "old_town"),
    ("old_town", "airport"), ("detective", "hotel"),
]

PLACE_BY_KEY = {p["key"]: p for p in PLACES}
# Old World location slug -> place (the dashboard's "next location" etc.).
PLACE_BY_LOCATION = {p["location"]: p["key"] for p in PLACES if p["location"]}
PLACE_BY_SCENE = {p["scene"]: p["key"] for p in PLACES if p["scene"]}
for _slug, _key in (("train-station", "train_station"), ("university", "university"), ("hospital", "hospital"),
                    ("hotel", "hotel"), ("airport", "airport")):
    PLACE_BY_LOCATION.setdefault(_slug, _key)
