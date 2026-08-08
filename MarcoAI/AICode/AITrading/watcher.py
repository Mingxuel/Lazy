# -*- coding: utf-8 -*-
"""
auto_trade.py 文件监控 & 自动化测试小助理

监控目标文件: auto_trade.py, api.py
检测到变化 → 跑 test_auto_trade.py → 输出结果

用法:
  python -B watcher.py              前台运行, 按 Ctrl+C 停止
  python -B watcher.py --bg         后台运行, 日志写入 watcher.log, 结果写入 test_results.txt
  python -B watcher.py --once       只跑一次测试

输出:
  test_results.txt           最近一次测试的完整输出
  test_status.txt            单行状态: PASS 或 FAIL (方便轮询)
  watcher_YYYYMMDD.log       运行日志
"""
import os, sys, time, json, subprocess, logging
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_FILES = [
    os.path.join(SCRIPT_DIR, 'auto_trade.py'),
    os.path.join(SCRIPT_DIR, 'api.py'),
]
TEST_SCRIPT = os.path.join(SCRIPT_DIR, 'test_auto_trade.py')
RESULT_FILE = os.path.join(SCRIPT_DIR, 'test_results.txt')
STATUS_FILE = os.path.join(SCRIPT_DIR, 'test_status.txt')
LOG_FILE = os.path.join(SCRIPT_DIR, f'watcher_{datetime.now().strftime("%Y%m%d")}.log')

PYTHON = r'C:\Users\Mingxuel\AppData\Local\Microsoft\WindowsApps\python.exe'
POLL_INTERVAL = 3       # 轮询间隔 (秒)
DEBOUNCE_SEC = 2        # 变化后等待 (秒, 等待文件写完)

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'),
              logging.StreamHandler()]
)
log = logging.getLogger('watcher')

# ===== Run Tests =====
def run_tests():
    """运行测试, 写入结果文件, 返回 (success: bool, output: str)"""
    log.info("🔍 开始运行自动化测试...")
    t0 = time.perf_counter()

    try:
        result = subprocess.run(
            [PYTHON, '-B', TEST_SCRIPT, '--quick'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        output = "❌ 测试超时 (60s)!"
        success = False
    except Exception as e:
        output = f"❌ 测试启动失败: {e}"
        success = False

    elapsed = (time.perf_counter() - t0) * 1000

    # 写入结果文件
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 耗时: {elapsed:.0f}ms\n")
        f.write(f"# 结果: {'✅ PASS' if success else '❌ FAIL'}\n")
        f.write("=" * 60 + "\n")
        f.write(output)

    # 写入状态标记
    with open(STATUS_FILE, 'w') as f:
        f.write(f"PASS {datetime.now().strftime('%H:%M:%S')}" if success
                else f"FAIL {datetime.now().strftime('%H:%M:%S')}")

    if success:
        log.info(f"  ✅ 全部通过 ({elapsed:.0f}ms)")
    else:
        log.error(f"  ❌ 测试失败 ({elapsed:.0f}ms)")
        # 打印失败摘要
        for line in output.split('\n'):
            if 'FAIL' in line or 'ERROR' in line or '❌' in line:
                log.error(f"     {line.strip()}")

    return success, output

# ===== Watcher =====
def watch_forever():
    """轮询文件变化, 变化后自动跑测试"""
    log.info("=" * 50)
    log.info("  🦞 auto_trade.py 文件监控测试助手 启动")
    log.info("=" * 50)
    log.info(f"  监控文件: {len(WATCH_FILES)} 个")
    for f in WATCH_FILES:
        log.info(f"    - {os.path.basename(f)}")
    log.info(f"  测试脚本: {os.path.basename(TEST_SCRIPT)}")
    log.info(f"  轮询间隔: {POLL_INTERVAL}s")
    log.info(f"  结果文件: {os.path.basename(RESULT_FILE)}")
    log.info("  最终状态: test_status.txt (PASS/FAIL)")
    log.info("")

    # 启动时先跑一次, 建立基线
    run_tests()

    # 记录文件当前时间戳
    def get_mtimes():
        return {f: os.path.getmtime(f) if os.path.exists(f) else 0 for f in WATCH_FILES}

    last_mtimes = get_mtimes()
    test_count = 1
    log.info("🟢 开始监控文件变化...")

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            current_mtimes = get_mtimes()

            # 检查是否有文件被修改
            changed = [
                f for f in WATCH_FILES
                if current_mtimes.get(f, 0) > last_mtimes.get(f, 0) + 0.1
            ]

            if changed:
                # 去抖: 等 2 秒让文件写完
                log.info(f"📝 检测到文件变化: {[os.path.basename(f) for f in changed]}, "
                         f"{DEBOUNCE_SEC}s后跑测试...")
                time.sleep(DEBOUNCE_SEC)

                # 刷新时间戳 (避免重复触发)
                last_mtimes = get_mtimes()

                # 清 pyc (防止缓存坑)
                pyc_dir = os.path.join(SCRIPT_DIR, '__pycache__')
                if os.path.isdir(pyc_dir):
                    for fn in os.listdir(pyc_dir):
                        if 'auto_trade' in fn or 'api' in fn:
                            os.remove(os.path.join(pyc_dir, fn))
                            log.info(f"  已删除 pyc: {fn}")

                test_count += 1
                success, _ = run_tests()
                log.info(f"  (第 {test_count} 次测试)")

                # 不通过时再跑一次完整版 (含WF重训)
                if not success:
                    log.warning("⚠️ 快速测试失败, 正在运行完整测试 (含WF重训)...")
                    result_full = subprocess.run(
                        [PYTHON, '-B', TEST_SCRIPT],
                        cwd=SCRIPT_DIR,
                        capture_output=True, text=True, timeout=120,
                    )
                    full_output = result_full.stdout + result_full.stderr
                    full_success = result_full.returncode == 0
                    log.info(f"  完整测试: {'✅ PASS' if full_success else '❌ FAIL'}")
                    if not full_success:
                        log.error("🚨 完整测试也失败了! 请检查代码!")

            # 更新基线时间戳
            last_mtimes = {f: max(last_mtimes.get(f, 0), current_mtimes.get(f, 0))
                           for f in WATCH_FILES}

        except KeyboardInterrupt:
            log.info("\n🛑 用户中断, 退出监控")
            break
        except Exception as e:
            log.error(f"监控异常: {e}", exc_info=True)
            time.sleep(5)

# ===== Main =====
if __name__ == '__main__':
    if '--once' in sys.argv:
        # 单次运行
        success, _ = run_tests()
        print(f"\n{'✅ PASS' if success else '❌ FAIL'}")
        sys.exit(0 if success else 1)
    else:
        watch_forever()
