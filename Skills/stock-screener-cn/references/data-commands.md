# 数据获取命令速查

> 本文档将分析需求映射到 `westock-data`（数据查询）和 `westock-tool`（选股筛选）命令。执行前必须先加载对应 skill。

---

## 一、个股数据查询（westock-data）

### 1.1 代码搜索

| 需求 | 命令 |
|------|------|
| 按名称搜股票代码 | `westock-data search <关键词>` |
| 搜板块 | `westock-data search <关键词> --type sector` |
| 搜指数 | `westock-data search <关键词> --type index` |
| 搜ETF | `westock-data search <关键词> --type etf` |

> 用户给名称未给代码时，**必须先 search 拿代码再查行情**。

### 1.2 行情与K线

| 需求 | 命令 |
|------|------|
| 实时行情快照（批量） | `westock-data quote sh600519,sz000001` |
| 日K线 | `westock-data kline sh600519 --period day --limit 60` |
| 按日期范围K线 | `westock-data kline sh600519 --start 2026-01-01 --end 2026-07-19` |
| 分时数据 | `westock-data minute sh600519` |
| 技术指标 | `westock-data kline sh600519 --period day --limit 60`（返回含MACD/KDJ/RSI/布林带） |

### 1.3 财务与估值

| 需求 | 命令 |
|------|------|
| 三大财报 | `westock-data finance sh600519` |
| 机构一致预期 | `westock-data consensus sh600519` |
| 综合评分 | `westock-data score sh600519` |
| 公司基本信息 | `westock-data profile sh600519` |
| 股东结构 | `westock-data shareholder sh600519` |
| 分红派息 | `westock-data dividend sh600519` |

### 1.4 资金与筹码（仅A股）

| 需求 | 命令 |
|------|------|
| 资金流向 | `westock-data fund flow sh600519` |
| 大宗交易 | `westock-data fund block sh600519` |
| 龙虎榜 | `westock-data lhb --type institution` |
| 筹码分布 | `westock-data chip sh600519` |

### 1.5 消息与事件

| 需求 | 命令 |
|------|------|
| 个股新闻 | `westock-data news article sh600519 --limit 10` |
| 市场资讯 | `westock-data news market --market hs` |
| 公告列表 | `westock-data notice list sh600519 --limit 5` |
| 公告详情 | `westock-data notice detail <公告ID>` |
| 研报列表 | `westock-data report list sh600519 --limit 5` |
| 研报详情 | `westock-data report detail <研报ID>` |
| 脱水研报 | `westock-data dehydrated list` |
| 事件标签 | `westock-data events tags sh600519` |
| 风险事件 | `westock-data risk sh600519` |

### 1.6 板块与指数

| 需求 | 命令 |
|------|------|
| 板块成份股 | `westock-data sector constituent pt01801080` |
| 指数成份股 | `westock-data index constituent sh000300` |
| 大盘画像 | `westock-data market-overview --type all` |
| 涨跌分布 | `westock-data changedist` |

### 1.7 市场发现

| 需求 | 命令 |
|------|------|
| 热门股票 | `westock-data hot stock` |
| 热门资讯 | `westock-data hot news` |
| 投资日历 | `westock-data calendar --date 2026-07-19` |
| 停复牌 | `westock-data suspension --market hs` |
| 宏观指标 | `westock-data macro indicator core_indicators_cur` |

---

## 二、选股筛选（westock-tool）

### 2.1 条件选股（filter）

```bash
# 自定义条件（AND 用 intersect，OR 用 union）
westock-tool filter "intersect([PE_TTM > 0, PE_TTM < 30, ROETTM > 10])" --limit 30
# 排序
westock-tool filter "intersect([PE_TTM > 0, PE_TTM < 30])" --orderby ROETTM --desc
# 板块限定
westock-tool filter "intersect([PE_TTM > 0, PE_TTM < 30])" --universe 11010001
# 预设函数
westock-tool filter --preset LowPE --limit 30
westock-tool filter --list-presets   # 查看所有预设
```

> ⚠️ 多条件AND**必须**用 `intersect([...])`，不支持 `&`/`&&`/`AND`。PE/PB 筛选必须排除负值。

### 2.2 策略选股（strategy）

```bash
westock-tool strategy --list                    # 查看所有策略
westock-tool strategy macd_golden               # MACD金叉
westock-tool strategy macd_golden,kdj_golden    # 多策略并查
westock-tool strategy macd_golden --start 2026-07-01 --end 2026-07-19  # 区间
```

### 2.3 排行选股（ranking）

```bash
westock-tool ranking --list                     # 查看所有指标
westock-tool ranking CompScore --limit 10       # 综合评分TOP10
westock-tool ranking cap_main_5d --limit 20     # 主力5日净流入榜
westock-tool ranking fin_valuation --limit 10   # 估值排行
# 范围限定（核心能力）
westock-tool ranking CompScore --within-strategy macd_golden   # MACD金叉中评分最高
westock-tool ranking fin_valuation --within-label shareholder_central_state  # 央企里估值最低
```

### 2.4 事件选股（event）

```bash
westock-tool event --list                       # 查看所有事件
westock-tool event shareunlock_next_90          # 近90天解禁
westock-tool event buyback                      # 近期回购
westock-tool event block_past_30                # 近30天大宗交易
westock-tool event longhu_statis_past_15        # 近15天龙虎榜
westock-tool event earnings_forecast            # 业绩预告
```

### 2.5 标签选股（label）

```bash
westock-tool label --list                       # 查看所有标签
westock-tool label shareholder_central_state    # 央企
westock-tool label risk_st                      # ST股
westock-tool label valuation_lowpb              # 破净股
westock-tool label fin_high_roettm              # 高ROE
```

---

## 三、批量查询规范

- **行情/财务/风险等查询类命令**：支持逗号分隔批量（含跨市场），如 `westock-data quote sh600519,sz000001,hk00700`
- **选股类命令**：不支持批量，一次一个条件表达式
- **不支持批量的命令**：`search`、`minute`
- 对比多只股票时**必须用批量**，不要拆成多条独立命令再拼接

---

## 四、执行注意事项

1. **代码格式**：沪市 `sh+6位`、深市 `sz+6位`、北交所 `bj+6位`、港股 `hk+5位`、美股 `us+代码`
2. **字段差异**：沪深 `PE_TTM`/`PB`/`ROETTM`，港美 `PeTTM`/`PbLF`/`RoeWeighted`，切勿混用
3. **货币单位**：A股人民币、港股港元、美股美元，展示时标注正确货币
4. **数据时效**：股价/财务/研报等时效性数据，**必须执行命令**，不可凭记忆作答
5. **PE/PB负值**：亏损股 PE/PB 为负，筛选时必须 `PE_TTM > 0` 排除
