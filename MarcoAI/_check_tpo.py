import os, sys

sys.stdout.reconfigure(encoding="utf-8")
base = r"E:/Lazy/MarcoAI/AIData/Strategy"


def read_rows(s, f):
    raw = open(os.path.join(base, s, f), "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="ignore")
    return [l.split("|") for l in text.splitlines() if l.strip()]


# 抽查 20260109 的 000960.SZ，对比三策略的市值列（第3列）
f = "20260109"
for s in ["TPO31", "TPO32", "TPO33"]:
    for row in read_rows(s, f):
        if row[0] == "000960.SZ":
            print(f"{s}: 市值={row[2]} 卖出日={row[3]} 收盘={row[7]}")

# 找三个策略都有且市值不同的日期
print("\n=== 寻找三个策略市值不同的股票 ===")
diff_found = 0
for f in sorted(os.listdir(os.path.join(base, "TPO31"))):
    r31 = {r[0]: r for r in read_rows("TPO31", f)}
    r32 = {r[0]: r for r in read_rows("TPO32", f)}
    r33 = {r[0]: r for r in read_rows("TPO33", f)}
    all_codes = set(r31) & set(r32) & set(r33)
    for c in all_codes:
        m31, m32, m33 = r31[c][2], r32[c][2], r33[c][2]
        if not (m31 == m32 == m33):
            if diff_found < 5:
                print(f"{f} {c}: TPO31市值={m31} TPO32市值={m32} TPO33市值={m33}")
            diff_found += 1
print(f"市值有差异的股票总数: {diff_found}")
