import os, sys

sys.stdout.reconfigure(encoding="utf-8")

d1 = r"E:/Lazy/MarcoAI/AIData/Strategy/TPO31"
d2 = os.path.join("E:/Lazy", "李明学的大A", "Data", "StrategyD1")


def read_lines(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            return raw.decode(enc).splitlines()
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="ignore").splitlines()


def tpo31_codes(d, f):
    return {l.split("|")[0].strip() for l in read_lines(os.path.join(d, f)) if l.strip()}


def strategyd1_codes(d, f):
    return {l.split("|")[1].strip() for l in read_lines(os.path.join(d, f)) if l.strip()}


fs1_2026 = sorted([f for f in os.listdir(d1) if f.startswith("2026")])
fs2_2026 = sorted([f for f in os.listdir(d2) if f.startswith("2026")])
set1, set2 = set(fs1_2026), set(fs2_2026)
common = sorted(set1 & set2)

exact_match = []
diff = []
for f in common:
    c1 = tpo31_codes(d1, f)
    c2 = strategyd1_codes(d2, f)
    if c1 == c2:
        exact_match.append(f)
    else:
        diff.append(f)

print("共同日期:", len(common))
print("股票完全一致:", len(exact_match))
print("股票有差异:", len(diff))

tpo_hit = sum(1 for f in common if tpo31_codes(d1, f))
d1_hit = sum(1 for f in common if strategyd1_codes(d2, f))
print(f"TPO31 有命中的日期: {tpo_hit}")
print(f"StrategyD1 有命中的日期: {d1_hit}")

# 统计差异方向
tpo_more = d1_more = both = 0
for f in diff:
    c1 = tpo31_codes(d1, f)
    c2 = strategyd1_codes(d2, f)
    o1, o2 = c1 - c2, c2 - c1
    if o1 and not o2:
        tpo_more += 1
    elif o2 and not o1:
        d1_more += 1
    else:
        both += 1
print(f"\n差异方向: TPO31多={tpo_more}, D1多={d1_more}, 互有={both}")

print("\n=== 前 15 个差异日期详情 ===")
for f in diff[:15]:
    c1 = tpo31_codes(d1, f)
    c2 = strategyd1_codes(d2, f)
    o1, o2 = sorted(c1 - c2), sorted(c2 - c1)
    print(f"{f}: TPO31={len(c1)} D1={len(c2)}")
    if o1:
        print(f"  仅TPO31: {o1}")
    if o2:
        print(f"  仅D1: {o2}")
