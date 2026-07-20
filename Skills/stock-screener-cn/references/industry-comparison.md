# 行业对比方法论

> 同行业公司的横向对比分析框架，找出相对强势/低估标的。适用于 A 股趋势/短线交易风格。

---

## 一、对比分析流程

```
确定行业 → 获取成份股 → 多维度对比 → 筛选标的 → 生成报告
```

---

## 二、确定行业与成份股

### 2.1 搜索行业板块

```bash
# 按关键词搜板块
westock-data search 半导体 --type sector
westock-data search 新能源 --type sector
westock-data search 银行 --type sector
```

### 2.2 获取板块成份股

```bash
# 获取板块成份股（pt代码从上一步搜索获得）
westock-data sector constituent pt01801080

# 获取指数成份股（如沪深300）
westock-data index constituent sh000300
```

### 2.3 获取板块信息

```bash
westock-data sector info pt01801080
```

---

## 三、多维度对比

### 3.1 估值对比

```bash
# 批量查行情（含PE/PB/市值）
westock-data quote sh600519,sz000001,sh600036

# 批量查财务（含详细估值指标）
westock-data finance sh600519,sz000001,sh600036

# 行业内估值排行
westock-tool ranking fin_valuation --universe 11010001 --limit 20
```

对比指标：
- **PE_TTM**：市盈率，越低越"便宜"（需结合成长性）
- **PB**：市净率，越低越"便宜"
- **PS_TTM**：市销率，适合高成长公司
- **总市值**：规模对比

### 3.2 盈利能力对比

```bash
# 批量查财务
westock-data finance sh600519,sz000001,sh600036

# 行业内盈利排行
westock-tool ranking fin_profit --universe 11010001 --limit 20
```

对比指标：
- **ROETTM**：净资产收益率，越高盈利能力越强
- **净利率**：盈利质量
- **毛利率**：竞争力体现
- **营收增长率**：成长性

### 3.3 成长性对比

```bash
# 行业内成长排行
westock-tool ranking fin_growth --universe 11010001 --limit 20
```

对比指标：
- **营收同比增长率**：收入成长
- **净利润同比增长率**：利润成长
- **营收复合增长率**：持续成长性

### 3.4 技术面对比（短线重点）

```bash
# 批量查K线
westock-data kline sh600519,sz000001,sh600036 --period day --limit 20

# 行业内技术评分排行
westock-tool ranking TecScore --universe 11010001 --limit 20

# 行业内综合评分排行
westock-tool ranking CompScore --universe 11010001 --limit 20
```

对比指标：
- **近期涨跌幅**：相对强弱
- **技术评分**：技术面综合评价
- **综合评分**：基本面+技术面综合
- **均线位置**：趋势对比

### 3.5 资金面对比

```bash
# 行业内资金流入排行
westock-tool ranking cap_main_5d --universe 11010001 --limit 20

# 批量查资金流向
westock-data fund flow sh600519,sz000001,sh600036
```

对比指标：
- **主力净流入**：资金关注度
- **主力流入天数**：资金持续性
- **龙虎榜上榜次数**：游资/机构活跃度

---

## 四、筛选标的

### 4.1 短线趋势选股（行业内）

```bash
# 行业内MACD金叉
westock-tool ranking CompScore --within-strategy macd_golden --universe 11010001 --limit 10

# 行业内资金流入TOP10
westock-tool ranking cap_main_5d --universe 11010001 --limit 10

# 行业内综合评分TOP10
westock-tool ranking CompScore --universe 11010001 --limit 10
```

### 4.2 价值发现选股（行业内）

```bash
# 行业内估值最低TOP10
westock-tool ranking fin_valuation --universe 11010001 --limit 10

# 行业内ROE最高
westock-tool ranking fin_profit --universe 11010001 --limit 10

# 行业内成长最快
westock-tool ranking fin_growth --universe 11010001 --limit 10
```

### 4.3 综合筛选（推荐）

```bash
# 行业内技术信号 + 资金确认
westock-tool ranking cap_main_5d --within-strategy macd_golden --universe 11010001 --limit 10

# 行业内低估值 + 高评分
westock-tool ranking CompScore --universe 11010001 --limit 20  # 先拿高评分池
# 再用 filter 在该板块内筛低估值
westock-tool filter "intersect([PE_TTM > 0, PE_TTM < 20])" --universe 11010001 --orderby ROETTM --desc
```

---

## 五、行业景气度判断

### 5.1 板块整体表现

```bash
# 板块行情
westock-data sector info pt01801080

# 大盘画像
westock-data market-overview --type all

# 涨跌分布
westock-data changedist
```

### 5.2 宏观环境

```bash
# 核心宏观指标
westock-data macro indicator core_indicators_cur

# 特定宏观指标
westock-data macro indicator gdp --year 2026
westock-data macro indicator cpi --year 2026
westock-data macro indicator pmi --year 2026
```

### 5.3 行业新闻/研报

```bash
# 行业资讯
westock-data news market --market hs

# 热门资讯
westock-data hot news
```

---

## 六、报告生成

对比分析完成后，按 `assets/report-industry-compare.md` 模板生成报告，包含：
1. 行业概览（板块走势、景气度）
2. 成份股对比表（估值/盈利/成长/技术/资金多维度排名）
3. 重点标的推荐（短线趋势 + 价值发现双维度）
4. 风险提示
