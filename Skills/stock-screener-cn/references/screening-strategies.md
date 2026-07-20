# 短线趋势选股策略库

> 针对 A 股趋势/短线交易风格的选股策略配置。所有策略通过 `westock-tool` 执行。

---

## 一、选股策略总览

短线趋势交易的核心逻辑：**技术信号启动 + 资金面确认 + 基本面排雷**。

三层漏斗模型：
1. **信号层**：技术指标/形态触发（MACD金叉、均线多头发散、放量突破等）
2. **确认层**：资金面共振（主力净流入、龙虎榜、机构接盘等）
3. **排雷层**：基本面过滤（排除ST、排除高质押、排除业绩暴雷等）

---

## 二、技术信号策略（信号层）

### 2.1 指标信号类

| 策略名 | 含义 | 命令 |
|--------|------|------|
| `macd_golden` | MACD金叉 | `westock-tool strategy macd_golden` |
| `kdj_golden` | KDJ金叉 | `westock-tool strategy kdj_golden` |
| `rsi_oversold` | RSI超卖反弹 | `westock-tool strategy rsi_oversold` |
| `boll_bt_upper` | 布林带上轨突破 | `westock-tool strategy boll_bt_upper` |

> 完整策略清单执行 `westock-tool strategy --list` 获取。

### 2.2 均线/形态类

| 策略名 | 含义 | 命令 |
|--------|------|------|
| `ma_long` | 均线多头发散 | `westock-tool strategy ma_long` |
| `morning_star` | 早晨之星 | `westock-tool strategy morning_star` |
| `red_three_solider` | 红三兵 | `westock-tool strategy red_three_solider` |

### 2.3 多信号共振

```bash
# MACD金叉 + KDJ金叉 双共振
westock-tool strategy macd_golden,kdj_golden

# 区间内每天命中变化（用于追踪信号持续性）
westock-tool strategy macd_golden --start 2026-07-10 --end 2026-07-19
```

---

## 三、资金面确认策略（确认层）

### 3.1 资金流入排行

```bash
# 主力5日净流入TOP20
westock-tool ranking cap_main_5d --limit 20

# 主力当日净流入榜
westock-tool ranking cap_main_net --limit 20

# 主力连续流入天数排行（--min-MainInDays 控制阈值）
westock-tool ranking cap_in_days --min-MainInDays 3
```

> ⚠️ `--min-<字段>` 的字段名与指标代码不一致，必须查 `westock-tool ranking --list` 对照表。

### 3.2 资金策略信号

| 策略名 | 含义 | 命令 |
|--------|------|------|
| `major_force` | 主力抢筹 | `westock-tool strategy major_force` |
| `institution_chasing` | 机构接盘 | `westock-tool strategy institution_chasing` |

### 3.3 事件型资金信号

```bash
# 近30天大宗交易（机构调仓信号）
westock-tool event block_past_30

# 近15天龙虎榜统计（游资活跃度）
westock-tool event longhu_statis_past_15

# 龙虎榜明细（机构席位）
westock-data lhb --type institution
```

---

## 四、基本面排雷策略（排雷层）

短线交易虽以技术面为主，但必须排除基本面雷区。

### 4.1 排除条件

```bash
# 排除ST股：先获取非ST池
westock-tool label risk_st --limit 200   # 获取ST股名单（用于反向排除）

# 排除高质押率：用风险事件查询
westock-data risk sh600519   # 查单股风险

# 排除业绩暴雷：查业绩预告
westock-tool event earnings_forecast   # 近期业绩预告股池
```

### 4.2 正向筛选（可选）

```bash
# 业绩预增（短线催化剂）
westock-tool strategy profit_preannounce

# 高ROE（基本面兜底）
westock-tool label fin_high_roettm

# 降本增效（基本面改善）
westock-tool label fin_healthy_growth
```

---

## 五、组合选股策略（核心）

### 5.1 技术信号 + 评分排序

```bash
# MACD金叉股中综合评分最高TOP10
westock-tool ranking CompScore --within-strategy macd_golden --limit 10

# 均线多头发散股中估值最低
westock-tool ranking fin_valuation --within-strategy ma_long --limit 10
```

### 5.2 技术信号 + 资金确认

```bash
# MACD金叉 + 主力资金流入排行
westock-tool ranking cap_main_5d --within-strategy macd_golden --limit 20

# 机构接盘股中技术评分最高
westock-tool ranking TecScore --within-strategy institution_chasing --limit 10
```

### 5.3 事件驱动 + 技术确认

```bash
# 近期回购股中技术评分最高（回购利好+技术面好）
westock-tool ranking TecScore --within-event buyback --limit 10

# 业绩预增股中资金流入最多
westock-tool ranking cap_main_net --within-event earnings_forecast --limit 10
```

### 5.4 板块内精选

```bash
# 某板块内MACD金叉且评分最高
westock-tool ranking CompScore --within-strategy macd_golden --universe 11010001 --limit 10

# 某板块内资金流入TOP10
westock-tool ranking cap_main_5d --universe 11010001 --limit 10
```

> 板块代码通过 `westock-data search <板块名> --type sector` 获取。

---

## 六、预设函数快捷选股

```bash
# 查看所有预设函数
westock-tool filter --list-presets

# 低PE股
westock-tool filter --preset LowPE --limit 30

# 高股息股
westock-tool filter --preset HighDividend

# MACD金叉预设
westock-tool filter --preset MACDGolden
```

> 预设函数是带默认阈值的复合条件，适合快速筛选；自定义阈值用 filter 表达式。

---

## 七、选股结果二次分析

选股得到代码列表后，用 `westock-data` 做二次精查：

```bash
# 批量查行情
westock-data quote sh600519,sz000001,sh600036

# 批量查财务
westock-data finance sh600519,sz000001,sh600036

# 批量查风险
westock-data risk sh600519,sz000001,sh600036

# 批量查资金流向
westock-data fund flow sh600519,sz000001,sh600036
```

> 批量查询用逗号分隔，**不要**拆成多条独立命令再拼接。

---

## 八、选股流程模板

### 标准短线选股流程

1. **信号筛选**：`westock-tool strategy macd_golden` → 获取金叉股池
2. **资金确认**：`westock-tool ranking cap_main_5d --within-strategy macd_golden --limit 20` → 资金流入TOP20
3. **排雷过滤**：`westock-data risk <批量代码>` → 排除高质押/ST/暴雷
4. **二次精查**：`westock-data quote/finance/fund flow <批量代码>` → 行情/财务/资金明细
5. **生成报告**：按 `assets/report-screening.md` 模板输出选股结果报告

### 事件驱动选股流程

1. **事件筛选**：`westock-tool event buyback` → 回购股池
2. **技术确认**：`westock-tool ranking TecScore --within-event buyback --limit 10` → 技术评分TOP10
3. **资金确认**：`westock-data fund flow <批量代码>` → 资金流向明细
4. **消息确认**：`westock-data news article <代码>` + `westock-data notice list <代码>` → 最新消息
5. **生成报告**：按 `assets/report-screening.md` 模板输出
