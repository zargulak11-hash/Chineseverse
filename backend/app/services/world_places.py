"""The places of the living world on /real-chinese (services/world_map.py).

Content, not progress. Each place is a spot on the map that leads into a
system that already exists -- a Real Chinese scene, the World voice
conversations and cases (Location/Scenario rows), a Sound World place,
Chinese Internet items, or a gateway (Detective, Sound World, Internet,
lessons, Character DNA, the Vocabulary Ecosystem, the Passport, Review,
Duels, the Daily Voice Companion). `links` are further systems worth
opening from a place; unlike the gateway they never count as having been
there (another place already owns that evidence).

`theme` are the curriculum words that make the place what it is (every one
exists in the vocabulary -- tests/world_map_test.py checks). Knowing them
is what makes a place richer: each `topic` lights up once the learner
really knows half its words, and a place still above the learner's HSK
level opens early once they know OPEN_BY_WORDS of its theme words.
A topic's `sentence` is a real sentence using those words; it opens as a
One Sentence lesson, which drills exactly them -- and learning it there
counts as having been to that place.

x/y place the node on the MAP canvas (CANVAS_W x CANVAS_H). The city has
districts, and a river crosses it west to east (RIVER, a polyline the map
draws as water); roads that cross it get bridges.
"""

from __future__ import annotations

OPEN_BY_WORDS = 3  # theme words known that open a place before its level

CANVAS_W, CANVAS_H = 240, 160

# The districts in the order the place list shows them.
DISTRICTS = ("home", "campus", "centre", "health", "transport", "riverside", "food", "culture", "shopping")

# The river's centre line, west to east.
RIVER = ((0, 100), (30, 96), (60, 101), (90, 97), (120, 92), (150, 95), (180, 90), (210, 86), (240, 89))


def P(key, icon, district, x, y, min_level, *, scene=None, location=None, sound=None, internet=(), gateway=None,
      links=(), theme=(), topics=()):
    return {"key": key, "icon": icon, "district": district, "x": x, "y": y, "min_level": min_level, "scene": scene,
            "location": location, "sound": sound, "internet": tuple(internet), "gateway": gateway,
            "links": tuple(links), "theme": tuple(theme), "topics": tuple(topics)}


def TOPIC(key, words, sentence):
    return {"key": key, "words": tuple(words), "sentence": sentence}


PLACES = [
    # ---- residential quarter: where the companion lives
    P("home", "🏠", "home", 24, 66, 1, location="home",
      theme=("家", "妈妈", "爸爸", "吃饭", "睡觉", "喜欢"),
      topics=(TOPIC("family", ("家", "妈妈", "爸爸"), "我家有爸爸、妈妈和我。"),
              TOPIC("daily", ("吃饭", "睡觉", "每天"), "我每天晚上七点吃饭，十点睡觉。"))),
    P("word_garden", "🌳", "home", 10, 50, 1, gateway="/ecosystem",
      theme=("词", "意思", "认识", "记", "说")),
    P("cafe", "☕", "home", 46, 56, 1, links=("/assistant",),
      theme=("咖啡", "杯", "喝", "牛奶", "糖", "热"),
      topics=(TOPIC("coffee", ("咖啡", "杯"), "我要一杯咖啡。"),
              TOPIC("milk", ("牛奶", "糖"), "请加一点儿牛奶，不要糖。"))),

    # ---- education: campus, library and books
    P("university", "🏫", "campus", 36, 16, 2, scene="university", sound="school", internet=("class-group-chat",),
      theme=("大学", "同学", "上课", "考试", "作业", "教室", "介绍"),
      topics=(TOPIC("schedule", ("上课", "点", "时间"), "上课时间是下午两点。"),
              TOPIC("classroom", ("教室", "号"), "在三号教室上课。"),
              TOPIC("introduce", ("同学", "介绍"), "我来介绍一下，这是我的同学。"))),
    P("library", "📚", "campus", 60, 30, 1, gateway="/lessons",
      theme=("学习", "书", "课", "汉语", "老师", "问题")),
    P("bookstore", "📖", "campus", 18, 32, 1, gateway="/vocabulary",
      theme=("书", "书店", "本", "小说", "买", "推荐", "作家"),
      topics=(TOPIC("buy_book", ("本", "书"), "我想买这本书。"),
              TOPIC("recommend", ("小说", "推荐"), "你能给我推荐一本小说吗？"))),

    # ---- downtown: streets, shops, offices and services
    P("street", "🏙️", "centre", 72, 60, 1, location="city-street", sound="street",
      theme=("左边", "右边", "前面", "后面", "附近", "往", "走", "路"),
      topics=(TOPIC("directions", ("左边", "右边", "往"), "往前走，银行在左边，饭馆在右边。"),
              TOPIC("nearby", ("附近", "前面", "后面"), "附近有一家饭馆，就在银行后面，书店前面。"))),
    P("shop", "🏪", "centre", 86, 74, 1, scene="convenience-store", location="shop", sound="night_market",
      internet=("supermarket-deals",),
      theme=("多少", "钱", "块", "便宜", "贵", "买", "卖"),
      topics=(TOPIC("price", ("多少", "钱", "块"), "这个多少钱？十块钱。"),
              TOPIC("bargain", ("便宜", "贵"), "太贵了，便宜一点儿吧。"),
              TOPIC("buy_sell", ("买", "卖"), "你们这儿卖水果吗？我想买苹果。"))),
    P("internet_cafe", "📰", "centre", 94, 46, 1, gateway="/internet",
      theme=("手机", "新闻", "网上", "电脑", "照片")),
    P("detective", "🔎", "centre", 116, 52, 1, gateway="/detective",
      theme=("谁", "为什么", "看见", "知道", "可能")),
    P("sound_plaza", "🎧", "centre", 108, 70, 1, gateway="/sound-world",
      theme=("听", "声音", "说话", "听说", "清楚")),
    P("passport_office", "🪪", "centre", 96, 14, 1, gateway="/passport",
      theme=("护照", "中文", "能", "会", "可以")),
    P("post_office", "📮", "centre", 76, 30, 2, links=("/sentence",),
      theme=("邮局", "寄", "信", "地址", "快递", "收"),
      topics=(TOPIC("send", ("寄", "信"), "我要寄一封信。"),
              TOPIC("address", ("地址", "写"), "请把地址写在这里。"))),
    P("bank", "🏦", "centre", 118, 26, 2,
      theme=("银行", "钱", "换", "卡", "人民币", "存", "取"),
      topics=(TOPIC("exchange", ("换", "钱"), "我想在银行换钱。"),
              TOPIC("card", ("卡", "取"), "我用卡取了一些人民币。"))),
    P("police_station", "🚓", "centre", 138, 40, 2, links=("/detective",),
      theme=("警察", "丢", "帮助", "找", "钱包", "手机"),
      topics=(TOPIC("lost", ("丢", "钱包"), "我的钱包丢了。"),
              TOPIC("police_help", ("警察", "帮助"), "警察帮助我找到了手机。"))),
    P("office", "💼", "centre", 140, 12, 4, scene="job-interview",
      theme=("工作", "公司", "经验", "面试", "经理", "负责"),
      topics=(TOPIC("interview", ("面试", "经验"), "我明天去面试，我有两年工作经验。"),
              TOPIC("work", ("工作", "公司", "经理"), "我在一家公司工作，我们经理很好。"))),

    # ---- healthcare
    P("hospital", "🏥", "health", 166, 62, 3, scene="hospital",
      theme=("医生", "医院", "药", "身体", "生病", "舒服", "发烧", "检查"),
      topics=(TOPIC("symptoms", ("舒服", "发烧", "身体"), "我身体不舒服，有点儿发烧。"),
              TOPIC("doctor", ("医生", "检查", "医院"), "医生在医院给我检查了一下。"),
              TOPIC("medicine", ("药", "次"), "这个药一天吃三次。"))),
    P("pharmacy", "💊", "health", 146, 76, 2,
      theme=("药", "感冒", "头疼", "次", "药店", "身体"),
      topics=(TOPIC("cold", ("感冒", "药"), "我感冒了，想买点儿药。"),
              TOPIC("dosage", ("次", "吃"), "一天吃两次，饭后吃。"))),

    # ---- transport
    P("metro", "🚇", "transport", 162, 40, 1, links=("/sound-world",),
      theme=("地铁", "站", "坐", "换", "出口", "方向"),
      topics=(TOPIC("ride", ("坐", "地铁"), "我每天坐地铁去学校。"),
              TOPIC("transfer", ("换", "站"), "在下一站换车。"))),
    P("train_station", "🚉", "transport", 188, 24, 2, scene="train-station", sound="train_station", internet=("metro-line",),
      theme=("火车", "票", "车站", "出发", "上车", "晚点", "火车站"),
      topics=(TOPIC("ticket", ("火车", "票"), "我要一张去北京的火车票。"),
              TOPIC("time", ("出发", "点"), "火车几点出发？"),
              TOPIC("boarding", ("上车", "号"), "我们在几号站台上车？"))),
    P("bus_station", "🚌", "transport", 206, 46, 2,
      theme=("公共汽车", "车站", "等", "分钟", "路", "下车"),
      topics=(TOPIC("wait", ("等", "分钟"), "我等了二十分钟公共汽车。"),
              TOPIC("route", ("路", "车站"), "去火车站坐几路车？"))),
    P("airport", "✈️", "transport", 222, 14, 4, scene="airport", sound="airport",
      theme=("飞机", "机场", "护照", "行李", "起飞", "登机"),
      topics=(TOPIC("check_in", ("护照", "行李"), "这是我的护照和行李。"),
              TOPIC("flight", ("飞机", "起飞"), "飞机几点起飞？"))),
    P("hotel", "🏨", "transport", 226, 66, 3, scene="hotel",
      theme=("房间", "住", "预订", "早饭", "包括", "钥匙"),
      topics=(TOPIC("check_in", ("房间", "住", "预订"), "我预订了一个房间，住两个晚上。"),
              TOPIC("breakfast", ("早饭", "包括"), "早饭包括在里面吗？"),
              TOPIC("help", ("钥匙", "帮"), "我的钥匙找不到了，你能帮我吗？"))),

    # ---- along the river: parks, gardens and the water
    P("park", "🌸", "riverside", 40, 82, 1, gateway="/review",
      theme=("公园", "散步", "花", "天气", "漂亮", "树"),
      topics=(TOPIC("walk", ("散步", "公园"), "我们去公园散步吧。"),
              TOPIC("weather", ("天气", "花"), "今天天气很好，花很漂亮。"))),
    P("riverside", "🌉", "riverside", 126, 80, 2,
      theme=("河", "桥", "船", "水", "游", "边"),
      topics=(TOPIC("boat", ("船", "河"), "我们坐船过河。"),
              TOPIC("bridge", ("桥", "走"), "从这座桥走过去就到了。"))),
    P("sports_center", "🏸", "riverside", 194, 72, 2, gateway="/duels",
      theme=("运动", "跑步", "游泳", "锻炼", "比赛", "身体"),
      topics=(TOPIC("exercise", ("运动", "锻炼"), "我每天锻炼身体，很喜欢运动。"),
              TOPIC("match", ("比赛", "游泳"), "明天有游泳比赛。"))),
    P("bamboo_garden", "🎋", "riverside", 14, 118, 2, links=("/ecosystem",),
      theme=("竹子", "鱼", "鸟", "安静", "风", "画"),
      topics=(TOPIC("nature", ("鱼", "鸟"), "花园里有很多鱼和鸟。"),
              TOPIC("wind", ("安静", "风"), "这里很安静，只有风的声音。"))),

    # ---- food district, south of the river
    P("restaurant", "🍜", "food", 56, 120, 1, scene="restaurant", location="restaurant", sound="restaurant",
      internet=("hotpot-review", "dumpling-comments"),
      theme=("菜单", "菜", "米饭", "好吃", "服务员", "饭馆", "一共", "饿"),
      topics=(TOPIC("order", ("菜单", "菜", "米饭"), "请给我菜单，我想要一碗米饭和两个菜。"),
              TOPIC("price", ("一共", "多少", "钱"), "一共多少钱？"),
              TOPIC("taste", ("好吃", "菜", "饿"), "我饿了，这里什么菜好吃？"))),
    P("food_street", "🥟", "food", 34, 138, 1, internet=("dinner-chat",),
      theme=("饺子", "包子", "小吃", "辣", "甜", "尝"),
      topics=(TOPIC("snack", ("小吃", "尝"), "这儿的小吃你一定要尝尝。"),
              TOPIC("spicy", ("辣", "甜"), "这个菜有点儿辣，那个很甜。"))),
    P("market", "🥬", "food", 76, 142, 1, links=("/sound-world",),
      theme=("水果", "蔬菜", "斤", "新鲜", "买", "便宜", "苹果"),
      topics=(TOPIC("quantity", ("斤", "水果"), "我要两斤水果。"),
              TOPIC("fresh", ("新鲜", "蔬菜"), "这些蔬菜很新鲜。"))),

    # ---- the traditional quarter: tea, temples, calligraphy, old streets
    P("tea_house", "🍵", "culture", 100, 124, 1, links=("/voice-companion",),
      theme=("茶", "喝", "杯", "热", "朋友", "聊", "绿茶"),
      topics=(TOPIC("order_tea", ("茶", "杯", "喝"), "我想喝一杯热茶。"),
              TOPIC("tea_chat", ("朋友", "说话"), "我常常和朋友在这里喝茶说话。"))),
    P("calligraphy", "🖌️", "culture", 104, 148, 1, gateway="/hanzi",
      theme=("字", "写", "汉字", "笔", "读")),
    P("museum", "🏛️", "culture", 126, 112, 3, links=("/hanzi", "/ecosystem"),
      theme=("博物馆", "历史", "介绍", "参观", "古代", "照片"),
      topics=(TOPIC("visit", ("博物馆", "参观"), "我们周末去博物馆参观吧。"),
              TOPIC("history", ("历史", "介绍"), "老师给我们介绍了这里的历史。"))),
    P("temple", "🏯", "culture", 130, 144, 3, links=("/hanzi",),
      theme=("历史", "文化", "安静", "传统", "参观", "古老"),
      topics=(TOPIC("culture", ("历史", "文化"), "这里有很长的历史和文化。"),
              TOPIC("quiet", ("安静", "说话"), "这里很安静，请小声说话。"))),
    P("hutong", "🏘️", "culture", 150, 126, 2, internet=("water-notice",),
      theme=("邻居", "院子", "住", "老", "北京", "旁边"),
      topics=(TOPIC("neighbours", ("邻居", "住"), "我的邻居住在旁边。"),
              TOPIC("courtyard", ("院子", "老"), "这个老院子很漂亮。"))),
    P("old_town", "🎭", "culture", 162, 148, 3, scene="travel", sound="street", internet=("park-info", "hiking-post"),
      theme=("旅游", "参观", "拍照", "导游", "门票", "风景"),
      topics=(TOPIC("sightseeing", ("参观", "旅游"), "我们去北京旅游，参观了很多地方。"),
              TOPIC("photos", ("拍照", "风景"), "这里风景很好，可以拍照吗？"),
              TOPIC("tickets", ("门票", "学生"), "学生门票多少钱？"))),

    # ---- shopping and entertainment
    P("shopping_district", "🛍️", "shopping", 188, 114, 2, scene="shopping", sound="shopping",
      internet=("thermos-cup",),
      theme=("衣服", "颜色", "试", "打折", "鞋", "号", "红色", "黑色"),
      topics=(TOPIC("size", ("号", "大", "小"), "这件太小了，有没有大一号的？"),
              TOPIC("colour", ("颜色", "红色", "黑色"), "这件衣服有什么颜色？我喜欢红色，不喜欢黑色。"),
              TOPIC("discount", ("打折", "便宜"), "今天打折吗？能便宜一点儿吗？"))),
    P("mall", "🏬", "shopping", 216, 122, 2,
      theme=("商店", "楼", "电梯", "逛", "层", "商场"),
      topics=(TOPIC("floor", ("楼", "电梯"), "坐电梯到三楼。"),
              TOPIC("browse", ("逛", "商店"), "周末我喜欢逛商店。"))),
    P("cinema", "🎬", "shopping", 194, 142, 2,
      theme=("电影", "电影院", "票", "开始", "部", "演员"),
      topics=(TOPIC("movie_tickets", ("电影", "票"), "我买了两张电影票。"),
              TOPIC("showtime", ("开始", "点"), "电影几点开始？"))),
    P("ktv", "🎤", "shopping", 224, 146, 3, gateway="/voice-companion",
      theme=("唱歌", "歌", "跳舞", "首", "声音", "高兴"),
      topics=(TOPIC("sing", ("唱", "歌"), "我们一起唱一首歌吧。"),
              TOPIC("dance", ("跳舞", "高兴"), "大家一起跳舞，很高兴。"))),
]

PATHS = [
    # residential and campus
    ("home", "word_garden"), ("home", "cafe"), ("home", "park"), ("word_garden", "bookstore"),
    ("bookstore", "university"), ("university", "library"), ("library", "cafe"), ("library", "post_office"),
    ("cafe", "street"),
    # downtown
    ("street", "shop"), ("street", "internet_cafe"), ("internet_cafe", "post_office"),
    ("post_office", "passport_office"), ("passport_office", "bank"), ("bank", "office"), ("bank", "police_station"),
    ("internet_cafe", "detective"), ("detective", "police_station"), ("shop", "sound_plaza"),
    ("sound_plaza", "detective"), ("sound_plaza", "riverside"),
    # healthcare and transport
    ("police_station", "metro"), ("riverside", "pharmacy"), ("pharmacy", "hospital"), ("hospital", "metro"),
    ("metro", "train_station"), ("train_station", "airport"), ("train_station", "bus_station"),
    ("bus_station", "hotel"), ("hospital", "sports_center"), ("sports_center", "hotel"),
    # across the river (bridges)
    ("park", "restaurant"), ("park", "bamboo_garden"), ("riverside", "museum"), ("sports_center", "shopping_district"),
    # south bank: food, the traditional quarter, shopping
    ("bamboo_garden", "food_street"), ("restaurant", "food_street"), ("restaurant", "market"),
    ("restaurant", "tea_house"), ("market", "calligraphy"), ("tea_house", "museum"), ("tea_house", "calligraphy"),
    ("calligraphy", "temple"), ("museum", "hutong"), ("temple", "old_town"), ("hutong", "old_town"),
    ("hutong", "shopping_district"), ("shopping_district", "mall"), ("shopping_district", "cinema"),
    ("mall", "ktv"), ("cinema", "ktv"), ("cinema", "old_town"),
]

PLACE_BY_KEY = {p["key"]: p for p in PLACES}
# Old World location slug -> place (the dashboard's "next location" etc.).
PLACE_BY_LOCATION = {p["location"]: p["key"] for p in PLACES if p["location"]}
PLACE_BY_SCENE = {p["scene"]: p["key"] for p in PLACES if p["scene"]}
# A topic sentence learned as a One Sentence lesson -> the place it belongs to.
PLACE_BY_SENTENCE: dict[str, str] = {}
for _p in PLACES:
    for _t in _p["topics"]:
        PLACE_BY_SENTENCE.setdefault(_t["sentence"], _p["key"])
for _slug, _key in (("train-station", "train_station"), ("university", "university"), ("hospital", "hospital"),
                    ("hotel", "hotel"), ("airport", "airport")):
    PLACE_BY_LOCATION.setdefault(_slug, _key)
