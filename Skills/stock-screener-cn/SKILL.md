---
name: stock-screener-cn
description: A股趋势/短线交易风格的股票筛选分析系统，覆盖四大场景：快速选股（按条件/策略/排行/事件筛选股票）、深度个股分析（技术面+资金面+基本面+消息面四维度分析）、持仓监控预警（技术死叉/资金流出/减持解禁等风险预警）、行业对比（同行业估值/盈利/成长/资金多维度排名）。当用户提到选股、筛股、找股票、个股分析、股票诊断、持仓监控、持仓预警、行业对比、板块对比、股票推荐、买卖点分析、MACD/KDJ/RSI分析、主力资金分析、龙虎榜、短线选股、趋势选股等A股相关分析需求时触发。数据依赖 westock-data（行情/财务/资金/新闻查询）和 westock-tool（条件/策略/排行/事件/标签选股）技能。
---

# A股短线趋势分析系统

针对 A 股趋势/短线交易风格，提供选股、深度分析、持仓监控、行业对比四大功能。数据通过 `westock-data` 和 `westock-tool` 获取，分析结果按模板生成结构化报告。

**交易风格**：趋势/短线交易，重点捕捉技术信号启动点，快进快出。
**分析权重**：技术面40% + 资金面30% + 消息面20% + 基本面10%。

---

## 场景路由

根据用户意图路由到对应场景：

| 用户意图 | 场景 | 参考文档 |
|----------|------|----------|
| "帮我选股""筛选XX条件的股""MACD金叉的股""资金流入榜""找低估股" | 快速选股 | [references/screening-strategies.md](references/screening-strategies.md) |
| "分析XX股票""XX股怎么样""XX股能买吗""XX股买卖点" | 深度个股分析 | [references/analysis-framework.md](references/analysis-framework.md) |
| "监控我的持仓""持仓预警""XX股要不要卖""检查持仓风险" | 持仓监控预警 | [references/monitoring-rules.md](references/monitoring-rules.md) |
| "对比XX行业""XX板块哪些股好""行业内选股""同行业对比" | 行业对比 | [references/industry-comparison.md](references/industry-comparison.md) |

> 所有场景的数据获取命令速查见 [references/data-commands.md](references/data-commands.md)。

---

## 场景一：快速选股

### 工作流程

1. **明确条件**：确认用户的筛选维度（技术信号/资金面/基本面/事件/标签）
2. **构建命令**：根据条件选择 `westock-tool` 子命令（filter/strategy/ranking/event/label）
3. **执行筛选**：运行命令获取股票池
4. **二次精查**：用 `westock-data` 批量查询入选股的行情/财务/资金明细
5. **排雷过滤**：用 `westock-data risk` 排除ST/高质押/暴雷股
6. **生成报告**：按 [assets/report-screening.md](assets/report-screening.md) 模板输出

### 选股策略三层漏斗

短线选股核心逻辑：**技术信号启动 + 资金面确认 + 基本面排雷**。

- **信号层**：`westock-tool strategy macd_golden` 等技术策略
- **确认层**：`westock-tool ranking cap_main_5d --within-strategy macd_golden` 资金确认
- **排雷层**：`westock-data risk <批量代码>` 排除风险股

> 详细策略配置见 [references/screening-strategies.md](references/screening-strategies.md)。

---

## 场景二：深度个股分析

### 工作流程

1. **获取代码**：用户给名称时先 `westock-data search <名称>` 拿代码
2. **四维度分析**：
   - 技术面（权重40%）：`westock-data kline <代码> --period day --limit 60` → 趋势/指标/形态/买卖点
   - 资金面（权重30%）：`westock-data fund flow <代码>` + `lhb` + `chip` → 主力/龙虎榜/筹码
   - 基本面（权重10%）：`westock-data finance <代码>` + `risk <代码>` + `score <代码>` → 财务/估值/风险/评分
   - 消息面（权重20%）：`westock-data news article <代码>` + `notice list <代码>` + `report list <代码>` → 新闻/公告/研报
3. **综合评估**：四维度加权评分，按操作决策矩阵给出建议
4. **生成报告**：按 [assets/report-deep-analysis.md](assets/report-deep-analysis.md) 模板输出

> 详细分析框架见 [references/analysis-framework.md](references/analysis-framework.md)。

---

## 场景三：持仓监控预警

### 工作流程

1. **获取持仓**：确认用户持仓清单（代码列表）
2. **批量检查**（每日盘后执行）：
   - 技术检查：`westock-data kline <批量代码> --period day --limit 10` → 检查死叉/破位/量价异常
   - 资金检查：`westock-data fund flow <批量代码>` → 检查主力流出
   - 事件检查：`westock-tool event manager_sharechg,shareunlock_incoming,earnings_forecast` → 检查减持/解禁/业绩
   - 风险检查：`westock-data risk <批量代码>` → 检查风险事件
3. **预警分级**：🔴高危（减仓/清仓）/ ⚠️中危（关注）/ 💡提示（观察）/ ✅正常
4. **生成报告**：按 [assets/report-monitoring.md](assets/report-monitoring.md) 模板输出

> 详细预警规则见 [references/monitoring-rules.md](references/monitoring-rules.md)。

---

## 场景四：行业对比

### 工作流程

1. **确定行业**：`westock-data search <行业名> --type sector` 获取板块代码
2. **获取成份股**：`westock-data sector constituent <板块代码>` 获取成份股
3. **多维度对比**：
   - 估值对比：`westock-tool ranking fin_valuation --universe <板块代码>`
   - 盈利对比：`westock-tool ranking fin_profit --universe <板块代码>`
   - 技术对比：`westock-tool ranking TecScore --universe <板块代码>`
   - 资金对比：`westock-tool ranking cap_main_5d --universe <板块代码>`
   - 综合对比：`westock-tool ranking CompScore --universe <板块代码>`
4. **筛选标的**：行业内短线趋势 + 价值发现双维度筛选
5. **生成报告**：按 [assets/report-industry-compare.md](assets/report-industry-compare.md) 模板输出

> 详细对比方法论见 [references/industry-comparison.md](references/industry-comparison.md)。

---

## 数据调用规范

### 前置依赖

执行任何数据查询前，**必须先加载 `westock-data` 和/或 `westock-tool` 技能**。本 skill 不直接查询数据，而是通过这两个技能获取。

### 命令速查

完整命令映射见 [references/data-commands.md](references/data-commands.md)。关键规范：

1. **未知代码先 search**：用户给名称未给代码时，必须先 `westock-data search <名称>` 拿代码
2. **批量查询用逗号分隔**：`westock-data quote sh600519,sz000001,sh600036`，不要拆成多条
3. **选股用 westock-tool**：条件/策略/排行/事件/标签选股用 `westock-tool`，数据查询用 `westock-data`
4. **PE/PB筛选排除负值**：`intersect([PE_TTM > 0, PE_TTM < 30])`
5. **多条件AND用 intersect**：`intersect([条件1, 条件2])`，不支持 `&`/`&&`/`AND`

### 代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| 沪市/科创板 | sh + 6位 | sh600519、sh688981 |
| 深市 | sz + 6位 | sz000001 |
| 北交所 | bj + 6位 | bj430047 |

---

## 报告生成规范

### 模板使用

| 场景 | 模板 |
|------|------|
| 快速选股 | [assets/report-screening.md](assets/report-screening.md) |
| 深度个股分析 | [assets/report-deep-analysis.md](assets/report-deep-analysis.md) |
| 持仓监控预警 | [assets/report-monitoring.md](assets/report-monitoring.md) |
| 行业对比 | [assets/report-industry-compare.md](assets/report-industry-compare.md) |

### 输出要求

1. **涨跌颜色**：按中国股市惯例，🔴红涨🟢绿跌
2. **货币单位**：A股统一用¥（人民币）
3. **数据时效**：所有行情/财务数据必须执行命令获取，不可凭记忆作答
4. **风险提示**：每份报告末尾必须包含风险提示和免责声明
5. **操作建议**：短线交易必须给出明确的买入价/止损位/仓位建议

### 报告保存

生成的报告保存到用户工作目录（默认 `E:\Lazy` 或当前工作目录），文件名格式：
`{场景}_{股票或行业}_{YYYYMMDD}.md`，如 `深度分析_sh600519_20260719.md`

---

## 重要声明

1. 本技能仅提供基于公开市场数据的分析框架，不含投资建议
2. 数据来源于 westock-data / westock-tool（腾讯自选股接口），可能存在延迟
3. 以交易所官方数据为准
4. 投资有风险，决策需谨慎，本报告不构成证券投资咨询服务
