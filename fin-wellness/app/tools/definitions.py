"""Claude tool_use definitions for the AI orchestrator.

These are the tools the AI can call. It NEVER invents financial data —
all numbers come from these tools.
"""

TOOLS = [
    {
        "name": "get_monthly_summary",
        "description": "获取指定月份的收支汇总。包括各分类支出总额、收入总额。不传参数则返回当月。",
        "input_schema": {
            "type": "object",
            "properties": {
                "year_month": {
                    "type": "string",
                    "description": "月份，格式 YYYY-MM。例如 '2026-03'。不传则为当月。",
                }
            },
        },
    },
    {
        "name": "get_transactions",
        "description": "查询交易流水明细。可按日期范围、分类、类型筛选。",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                "category": {"type": "string", "description": "分类名，如 '餐饮' 或 '餐饮.外卖'"},
                "tx_type": {"type": "string", "enum": ["expense", "income", "transfer"]},
                "limit": {"type": "integer", "description": "最多返回条数，默认50", "default": 50},
            },
        },
    },
    {
        "name": "get_net_worth",
        "description": "计算当前净资产。返回总资产、总负债、净资产、各账户明细。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "detect_anomalies",
        "description": "检测本月消费异常。对比历史均值，找出偏差较大的分类。返回异常列表和解释。",
        "input_schema": {
            "type": "object",
            "properties": {
                "year_month": {"type": "string", "description": "要检测的月份 YYYY-MM，默认当月"},
                "threshold_pct": {"type": "number", "description": "偏差阈值百分比，默认25", "default": 25},
            },
        },
    },
    {
        "name": "get_category_trend",
        "description": "获取某分类过去N个月的趋势。用于解释'为什么这个月多了/少了'。",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "分类名，如 '餐饮.外卖'"},
                "months": {"type": "integer", "description": "看几个月的趋势，默认6", "default": 6},
            },
            "required": ["category"],
        },
    },
    {
        "name": "get_active_commitments",
        "description": "获取当前进行中的微行动承诺。用于跟进用户是否完成了上周的承诺。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_commitment",
        "description": "创建一个新的微行动承诺。当用户接受AI的建议时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "具体行动，如 '周二/周四带饭'"},
                "category": {"type": "string", "description": "关联的消费分类"},
                "expected_saving": {"type": "number", "description": "预期每周节省金额"},
                "goal_id": {"type": "string", "description": "关联的长期目标ID（可选）"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "update_commitment_status",
        "description": "更新微行动承诺的状态。跟进时标记完成或未完成。",
        "input_schema": {
            "type": "object",
            "properties": {
                "commitment_id": {"type": "string"},
                "status": {"type": "string", "enum": ["achieved", "missed", "adjusted"]},
                "actual_saving": {"type": "number", "description": "实际节省金额"},
                "follow_up_result": {"type": "string", "description": "跟进结果描述"},
            },
            "required": ["commitment_id", "status"],
        },
    },
    {
        "name": "get_active_goals",
        "description": "获取用户当前的长期财务目标。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_goal",
        "description": "创建一个长期财务目标。如 '6个月攒下3万应急金'。",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "目标描述"},
                "target_amount": {"type": "number", "description": "目标金额"},
                "deadline": {"type": "string", "description": "截止日期 YYYY-MM-DD"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "generate_weekly_review",
        "description": "生成本周财务周报。包括收支汇总、承诺完成情况、异常发现、鼓励语。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_user_profile",
        "description": "获取用户画像（风险偏好、焦虑等级、偏好设置等）。用于调整语气和建议方式。",
        "input_schema": {"type": "object", "properties": {}},
    },
]
