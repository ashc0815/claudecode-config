# 员工报销智能助手 - Agent 架构设计

## 架构哲学
Manus 风格：Planner → Executor → Verifier 循环
- Agent 数量固定（3个），能力通过 Tool 无限扩展
- 反对按职能分 Agent（那只是工具封装，不是真正的 Agent）

## 三个 Agent

### Planner Agent
- 输入：任务目标 + 当前状态 + 可用工具列表
- 输出：动态步骤序列（Plan），含每步的 tool、input、expected_output、fallback
- 关键能力：感知失败后 Replan

### Executor Agent
- 逐步执行 Plan，调用 Tools，维护执行上下文
- 不做决策，只做执行

### Verifier Agent
- 步骤级验证 + 一致性验证 + 目标级验证 + 风险验证
- 决策：完成 / Replan / 人工介入

## 工具集（Tools）
| 工具 | 功能 |
|------|------|
| ocr_tool | 发票图片识别 |
| tax_verify_tool | 发票真伪验证（税务总局接口） |
| policy_rag_tool | 政策检索与合规判断 |
| duplicate_check_tool | 重复报销检测 |
| risk_engine_tool | 风险评分（规则引擎 + ML 混合） |
| concur_api_tool | SAP Concur 操作 |
| notification_tool | 通知员工/审批人 |

## 风险分级
- 低风险（0-30）：自动通过
- 中风险（31-70）：标记，建议人工复核
- 高风险（71-100）：阻止，必须人工审核

## 实施路线
- Phase 1 MVP：OCR + 发票验真 + 重复检测 + 基础风险规则
- Phase 2：Policy RAG + ML 异常检测
- Phase 3：全流程 + 审计追踪 + 分析洞察
- Phase 4：反馈循环 + 模型迭代

## KPIs
- 首次提交通过率：60% → 85%
- 平均审批时长：5天 → 2天
- 违规检出率提升 50%
