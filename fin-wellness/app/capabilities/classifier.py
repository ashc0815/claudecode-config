"""Smart transaction classifier — rules first, AI fallback.

Priority:
  1. Keyword matching (fast, free, 70%+ accuracy)
  2. User corrections (remembered in mid-term memory)
  3. Claude AI fallback (for ambiguous items)
"""

import json
import logging
from typing import Optional

from .. import db

logger = logging.getLogger(__name__)

# ── Keyword Rules (covers ~70% of transactions) ──

KEYWORD_RULES: list[tuple[list[str], str]] = [
    # 餐饮
    (["美团", "饿了么", "外卖"], "餐饮.外卖"),
    (["星巴克", "瑞幸", "manner", "咖啡"], "餐饮.咖啡"),
    (["海底捞", "西贝", "必胜客", "肯德基", "麦当劳", "餐厅", "火锅", "烧烤"], "餐饮.堂食"),
    (["盒马", "叮咚买菜", "美团买菜", "山姆", "超市", "菜场", "果蔬"], "餐饮.买菜"),

    # 交通
    (["滴滴", "花小猪", "高德打车", "T3出行", "曹操出行", "打车"], "交通.打车"),
    (["地铁", "公交", "一卡通"], "交通.公共"),
    (["中国铁路", "12306", "火车票", "高铁"], "交通.火车"),
    (["航空", "机票", "飞机", "携程机票"], "交通.机票"),
    (["加油", "中国石化", "中国石油", "停车"], "交通.自驾"),

    # 购物
    (["淘宝", "天猫", "京东", "拼多多", "唯品会"], "购物.网购"),
    (["优衣库", "ZARA", "H&M", "耐克", "阿迪"], "购物.服饰"),

    # 住房
    (["房租", "租金"], "住房.房租"),
    (["物业", "水费", "电费", "燃气", "暖气"], "住房.水电物业"),

    # 娱乐
    (["电影", "猫眼", "万达影城"], "娱乐.电影"),
    (["Steam", "游戏", "PS", "Switch", "任天堂"], "娱乐.游戏"),
    (["爱奇艺", "腾讯视频", "优酷", "B站", "Netflix", "会员"], "娱乐.视频会员"),
    (["网易云", "QQ音乐", "Spotify", "Apple Music"], "娱乐.音乐"),

    # 医疗健康
    (["药店", "药房", "大药房"], "医疗.药品"),
    (["医院", "门诊", "挂号"], "医疗.就医"),
    (["体检", "健康"], "医疗.体检"),

    # 教育
    (["课程", "网课", "培训", "学费"], "教育.课程"),
    (["当当", "京东图书", "微信读书", "得到", "书"], "教育.书籍"),

    # 通讯
    (["中国移动", "中国联通", "中国电信", "话费", "流量"], "通讯.话费"),

    # 收入
    (["工资", "薪水", "salary"], "工资"),
    (["奖金", "bonus"], "奖金"),
    (["理财收益", "基金分红", "利息"], "投资收益"),
    (["报销", "退款"], "报销退款"),

    # 转账
    (["转账", "还款", "信用卡还款"], "转账"),
    (["余额宝", "零钱通", "活期"], "理财转入"),
]


def classify_transaction(
    description: str,
    counterparty: str = "",
) -> tuple[str, float]:
    """Classify a transaction by description and counterparty.

    Returns (category, confidence).
    """
    text = f"{description} {counterparty}".lower()

    # 1. Check user corrections (mid-term memory)
    user_override = _check_user_corrections(text)
    if user_override:
        return user_override, 0.95

    # 2. Keyword matching
    for keywords, category in KEYWORD_RULES:
        for kw in keywords:
            if kw.lower() in text:
                return category, 0.85

    # 3. If no match, return empty (AI will handle in orchestrator if needed)
    return "", 0.0


def _check_user_corrections(text: str) -> Optional[str]:
    """Check if user has corrected this type of transaction before.

    Uses the habit_profile table (mid-term memory) to remember user preferences.
    """
    try:
        habits = db.get_habits(category="classifier_corrections")
        for h in habits:
            correction = h.get("value", {})
            keywords = correction.get("keywords", [])
            for kw in keywords:
                if kw.lower() in text:
                    return correction.get("category", "")
    except Exception:
        pass
    return None


def learn_correction(description: str, counterparty: str, correct_category: str):
    """Learn from user's category correction.

    When user says "这笔不是外卖，是工作餐", we remember.
    """
    keywords = []
    if counterparty:
        keywords.append(counterparty)
    # Extract meaningful words from description
    for word in description.split():
        if len(word) >= 2:
            keywords.append(word)

    if keywords:
        db.update_habit(
            category="classifier_corrections",
            metric=f"correction_{correct_category}",
            value={"keywords": keywords, "category": correct_category},
        )
        logger.info("Learned correction: %s → %s", keywords, correct_category)
