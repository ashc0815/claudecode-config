# Memory

## User Profile
- 语言偏好：中文交流
- 领域背景：SAP Concur 实施与审计专家
- 工作方向：企业报销流程智能化、AI Agent 架构设计

## Agent 架构设计偏好
- 偏好 Manus 风格架构：Planner → Executor → Verifier 循环
- 反对按职能定义 Agent（如 Invoice Agent、Policy Agent），认为这只是工具封装
- 核心原则：Agent 数量固定（3个），能力通过 Tool 无限扩展
- 详细设计见：[expense-reimbursement-agent.md](./expense-reimbursement-agent.md)

## 当前项目：员工报销智能助手
- 场景：帮助员工正确填写报销单，实时解答政策问题，提高首次通过率
- 核心痛点：合规风险（违规/重复/虚假发票）
- 集成系统：SAP Concur API、OCR 服务、国家税务总局发票验真 API、RAG 知识库
- 架构文件：[expense-reimbursement-agent.md](./expense-reimbursement-agent.md)

## 工作流程偏好
- **架构内容存档规则**：重要的架构设计、架构调整、优化方案等内容需保存到 Kiro Memory
- **存档触发场景**：
  - Plan mode 产出的架构设计
  - 用户看完架构后提出的调整意见
  - 架构的进一步优化和迭代
- **不存档内容**：日常对话、临时问题、非架构相关的技术讨论
- **存档价值**：方便 recall，避免重复生成，节省时间和 token

## 架构设计流程
- **使用 AskUserQuestion 工具**：在设计架构时主动提问澄清需求
- **多维度验证**：
  - 合理性：架构是否符合业务场景和用户背景
  - 准确性：技术选型和设计细节是否正确
  - Latency：响应时间是否满足实际使用需求
  - 可扩展性：是否易于后续迭代和功能扩展
- **迭代优化**：基于用户反馈持续改进架构设计
- **参考最新 Agent 架构**：
  - Manus：Planner → Executor → Verifier 三角色循环架构
  - OpenClaw：开源 Agent 框架的设计模式
  - Claude Code：工具调用和代码执行能力
  - Codex：代码生成和理解能力
  - 持续关注业界最新 Agent 架构演进，吸收最佳实践
