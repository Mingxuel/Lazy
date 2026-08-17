"""
策略看板本地服务（快捷命令后端）
=============================
用 Python 标准库 http.server 起一个本地 HTTP 服务，同时：
    - GET  /                     返回 StrategyDashboard.html（策略看板）
    - POST /api/cmd              执行侧边栏快捷命令（更新数据 / 更新同花顺板块）
       请求体: {"cmd": "UPDATE_DATA" | "UPDATE_THS", "strategy": "TPO_3"}
       返回体: {"ok": true, "output": "...", "running": false}

用法:
    python AICode/MarcoAPI/StrategyService.py           # 默认端口 8765
    python AICode/MarcoAPI/StrategyService.py --port 9000

启动后在浏览器打开 http://localhost:8765/ 即可使用。
"""

import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))

from AICode.MarcoAPI.StrategyUI import (
    CMD_UPDATE_DATA, CMD_UPDATE_THS,
    GENERATE_STRATEGY_UI, _list_strategies,
)

HOST = "127.0.0.1"
PORT = 8765

# git 工作目录 = 项目根（StrategyService.py 位于 AICode/MarcoAPI/，其上两级为项目根）
GIT_REPO_DIR = os.path.dirname(os.path.dirname(_root))
GIT_COMMIT_MSG = "Updated"


def GIT_SYNC() -> str:
    """git 同步：git add . -> git commit -m "Updated" -> git push"""
    steps = [
        ("git add .", ["git", "add", "."]),
        (f'git commit -m "{GIT_COMMIT_MSG}"', ["git", "commit", "-m", GIT_COMMIT_MSG]),
        ("git push", ["git", "push"]),
    ]
    logs = []
    for label, cmd in steps:
        logs.append(f"$ {label}")
        try:
            r = subprocess.run(cmd, cwd=GIT_REPO_DIR, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
        except subprocess.TimeoutExpired:
            logs.append("  [超时]")
            return "\n".join(logs)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out:
            logs.append(out)
        if err:
            logs.append(err)
        if r.returncode != 0:
            logs.append(f"  [失败，返回码 {r.returncode}]")
            return "\n".join(logs)
    logs.append("git 同步完成")
    return "\n".join(logs)

# 生成策略看板 HTML 文本（用于 GET / 返回）
def _dashboard_html() -> str:
    out = GENERATE_STRATEGY_UI(open_browser=False)
    if not out:
        return "<html><body><h1>无策略数据</h1></body></html>"
    with open(out, "r", encoding="utf-8") as f:
        return f.read()


class StrategyHandler(BaseHTTPRequestHandler):
    """策略看板 HTTP 请求处理器"""

    def log_message(self, fmt, *args):  # 精简控制台日志
        print("[%s] %s" % (self.address_string(), fmt % args))

    # ---- CORS ----
    def _send_headers(self, status=200, ctype="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _send_json(self, data: dict, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_headers(status)
        self.wfile.write(body)

    # ---- 预检 ----
    def do_OPTIONS(self):
        self._send_headers(204)

    # ---- 页面 ----
    def do_GET(self):
        if self.path in ("/", "/StrategyDashboard.html", "/index.html"):
            html = _dashboard_html().encode("utf-8")
            self._send_headers(200, "text/html; charset=utf-8")
            self.wfile.write(html)
        else:
            self._send_json({"ok": False, "error": f"未找到 {self.path}"}, 404)

    # ---- 命令 ----
    def do_POST(self):
        if self.path != "/api/cmd":
            self._send_json({"ok": False, "error": f"未找到 {self.path}"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            self._send_json({"ok": False, "error": f"请求体解析失败: {exc}"}, 400)
            return

        cmd = payload.get("cmd", "")
        strategy = payload.get("strategy") or ""

        if cmd == "UPDATE_DATA":
            try:
                output = CMD_UPDATE_DATA()
                self._send_json({"ok": True, "output": output, "running": False})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc), "running": False}, 500)
            return

        if cmd == "UPDATE_THS":
            if not strategy:
                self._send_json({"ok": False, "error": "未指定策略"}, 400)
                return
            try:
                output = CMD_UPDATE_THS(strategy)
                self._send_json({"ok": True, "output": output, "running": False})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc), "running": False}, 500)
            return

        if cmd == "GIT_SYNC":
            try:
                output = GIT_SYNC()
                self._send_json({"ok": True, "output": output, "running": False})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc), "running": False}, 500)
            return

        # 未知命令：返回可用命令列表
        self._send_json({
            "ok": False,
            "error": f"未知命令: {cmd}",
            "available": ["UPDATE_DATA", "UPDATE_THS", "GIT_SYNC"],
            "strategies": _list_strategies(),
        }, 400)


def main():
    parser = argparse.ArgumentParser(description="策略看板本地服务")
    parser.add_argument("--host", default=HOST, help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=PORT, help="监听端口，默认 8765")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), StrategyHandler)
    print(f"策略看板服务已启动: http://{args.host}:{args.port}/")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
