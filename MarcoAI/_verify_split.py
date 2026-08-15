import sys, importlib

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"e:/Lazy")

# 验证两个模块导入
import AICode.MarcoAPI.Update.SZ200Strategy as S
import AICode.MarcoAPI.Update.SZ200Target as T

print("SZ200Strategy 有(策略):", all(hasattr(S, f) for f in ["UPDATE_TARGET_TPO31","UPDATE_TARGET_TPO32","UPDATE_TARGET_TPO33","GENERATE_TARGET_TPO"]))
print("SZ200Strategy 无(候选池):", not hasattr(S, "GENERATE_TARGET_CANDIDATE"))
print("SZ200Target 有(候选池):", all(hasattr(T, f) for f in ["UPDATE_TARGET_TPO31","UPDATE_TARGET_TPO32","UPDATE_TARGET_TPO33","GENERATE_TARGET_CANDIDATE"]))
print("SZ200Target 无(策略worker):", not hasattr(T, "GENERATE_TARGET_TPO"))

# 检查 Update1D 是否引用 SZ200Strategy 的 TARGET 函数
import AICode.MarcoAPI.Update.Update1D as U
print("Update1D 导入成功:", hasattr(U, "UPDATE_ALL"))
