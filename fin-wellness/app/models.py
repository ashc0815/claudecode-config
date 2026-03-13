"""Pydantic models for Fin-Wellness.

Covers: transactions, accounts, assets, goals, commitments, user profile.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──


class AccountType(str, Enum):
    cash = "cash"               # 现金/活期
    savings = "savings"         # 定期
    credit_card = "credit_card" # 信用卡
    investment = "investment"   # 投资账户
    loan = "loan"               # 贷款
    other = "other"


class TransactionType(str, Enum):
    expense = "expense"     # 支出
    income = "income"       # 收入
    transfer = "transfer"   # 转账（不影响净资产）


class GoalStatus(str, Enum):
    active = "active"
    completed = "completed"
    paused = "paused"
    abandoned = "abandoned"


class CommitmentStatus(str, Enum):
    active = "active"
    achieved = "achieved"
    missed = "missed"
    adjusted = "adjusted"


# ── Core Models ──


class Account(BaseModel):
    """A financial account (bank card, investment, loan, etc.)."""
    id: Optional[str] = None
    name: str                                      # e.g. "招商银行储蓄卡"
    account_type: AccountType
    balance: float = 0.0
    currency: str = "CNY"
    institution: str = ""                          # e.g. "招商银行"
    is_asset: bool = True                          # False for liabilities (credit card debt, loans)
    notes: str = ""


class Transaction(BaseModel):
    """A single financial transaction."""
    id: Optional[str] = None
    date: date
    amount: float
    tx_type: TransactionType
    category: str = ""                             # e.g. "餐饮.外卖", "交通.打车"
    subcategory: str = ""
    description: str = ""                          # 备注
    account_id: str = ""                           # 关联账户
    counterparty: str = ""                         # 对方（商户/人）
    source: str = ""                               # 来源: "alipay_csv", "wechat_csv", "manual", "ocr"
    tags: list[str] = Field(default_factory=list)  # 用户自定义标签
    ai_category_confidence: float = 0.0            # AI 分类置信度


class Asset(BaseModel):
    """An investment asset (fund, stock, etc.) with current value."""
    id: Optional[str] = None
    name: str                                      # e.g. "沪深300指数基金"
    asset_type: str = ""                           # fund, stock, bond, crypto, real_estate
    ticker: str = ""                               # 基金代码 e.g. "110020"
    shares: float = 0.0                            # 持有份额
    cost_basis: float = 0.0                        # 成本
    current_value: float = 0.0                     # 当前市值
    last_updated: Optional[datetime] = None
    account_id: str = ""


# ── Goal & Commitment (微行动循环) ──


class Goal(BaseModel):
    """A financial goal (long-term)."""
    id: Optional[str] = None
    title: str                                     # e.g. "6个月攒下 ¥30,000 应急金"
    target_amount: Optional[float] = None
    current_amount: float = 0.0
    deadline: Optional[date] = None
    status: GoalStatus = GoalStatus.active
    created_at: Optional[datetime] = None


class Commitment(BaseModel):
    """A micro-action commitment from the Suggest→Commit→Follow-up loop.

    Unlike Goals (long-term), Commitments are small, weekly, actionable.
    e.g. "这周二和周四带饭" or "这周不点超过¥30的外卖"
    """
    id: Optional[str] = None
    goal_id: Optional[str] = None                  # 关联长期目标（可选）
    action: str                                    # "周二/周四带饭"
    category: str = ""                             # 关联消费分类
    expected_saving: float = 0.0                   # 预计节省
    start_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None                # 默认一周
    status: CommitmentStatus = CommitmentStatus.active
    follow_up_result: str = ""                     # AI 跟进结果
    actual_saving: float = 0.0                     # 实际节省


# ── User Profile (记忆层-长期) ──


class UserProfile(BaseModel):
    """Long-term user profile for personalized AI interactions."""
    risk_tolerance: str = "moderate"               # conservative, moderate, aggressive
    income_range: str = ""                         # 月收入范围（用户自愿提供）
    family_size: int = 1
    financial_anxiety_level: str = "medium"        # low, medium, high → 影响 AI 语气
    preferred_check_frequency: str = "weekly"      # daily, weekly, monthly
    privacy_level: str = "strict"                  # strict: 全本地 | relaxed: 允许云备份
    category_preferences: dict[str, str] = Field(default_factory=dict)  # 分类偏好
    do_not_mention: list[str] = Field(default_factory=list)  # 用户不想被提及的话题


# ── Response Models ──


class NetWorthSnapshot(BaseModel):
    """Net worth at a point in time."""
    date: date
    total_assets: float          # 总资产
    total_liabilities: float     # 总负债
    net_worth: float             # 净资产 = 资产 - 负债
    cash_and_savings: float      # 现金+活期+定期
    investments: float           # 投资
    breakdown: dict[str, float] = Field(default_factory=dict)


class AnomalyReport(BaseModel):
    """An anomaly discovered by the AI."""
    category: str                # 异常分类
    description: str             # "本月外卖比常态高 38%"
    explanation: str             # "主要集中在加班日"
    suggestion: str              # "试试周二/周四带饭"
    expected_impact: str         # "每月能省 ¥400"
    severity: str = "info"       # info, mild, notable → 不用 warning/critical 避免焦虑


class WeeklyReview(BaseModel):
    """Weekly financial review."""
    week_start: date
    week_end: date
    total_income: float
    total_expense: float
    net_flow: float              # 收入 - 支出
    top_categories: list[dict]   # [{"category": "餐饮", "amount": 1200, "vs_avg": "+15%"}]
    commitments_review: list[dict]  # 本周承诺完成情况
    anomalies: list[AnomalyReport]
    encouragement: str           # AI 鼓励语（永远正面）
    next_suggestion: Optional[str] = None  # 下周微行动建议
