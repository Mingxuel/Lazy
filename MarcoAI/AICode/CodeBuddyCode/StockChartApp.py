"""
扁平化 TradingView 风格股票图表应用
使用 PyQt6 + finplot 实现高性能 K 线图表
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTabWidget, QTextEdit, QHBoxLayout,
    QStatusBar, QFileDialog, QLabel, QFrame, QDockWidget,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QProcess
from PyQt6.QtGui import QFont

import finplot as fplt

# 添加项目根目录到 sys.path，使可以从 MarcoAPI 导入
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from AICode.MarcoAPI.BaoStockAPI import (
    UPDATE_ORIGIN_DATA, COMPLETION_PROGRESS, FREQUENCY_5M
)


class TradingViewApp(QMainWindow):
    """TradingView 扁平化风格股票分析应用"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analyst")
        self.setMinimumSize(1200, 800)

        self.stock_data = {}
        self.current_stock = None

        # 更新任务状态
        self._update_process = None
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_progress)
        self._is_updating = False

        self.setup_flat_theme()
        self.create_activity_bar()
        self.create_main_area()
        self.create_right_panel()
        self.create_bottom_panel()
        self.create_status_bar()
        self.load_sample_data()

    def setup_flat_theme(self):
        """扁平化 TradingView 暗色主题"""
        self.setStyleSheet("""
            QMainWindow { background-color: #131722; }
            QWidget { background-color: #131722; color: #d1d4dc; }
            QStatusBar {
                background-color: #1e222d; color: #787b86;
                font-size: 12px; border-top: 1px solid #2a2e39;
            }
            QStatusBar::item { border: none; }
            QTabWidget::pane { border: none; background-color: #131722; }
            QTabBar::tab {
                background-color: #1e222d; color: #787b86;
                padding: 8px 20px; border: none;
                border-bottom: 2px solid transparent;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #d1d4dc;
                border-bottom: 2px solid #2962ff;
            }
            QTabBar::tab:hover { color: #d1d4dc; }
            QPushButton {
                background-color: transparent;
                color: #787b86; border: none;
                font-size: 20px;
            }
            QPushButton:hover { color: #d1d4dc; }
            QPushButton:pressed { color: #2962ff; }
            QTextEdit {
                background-color: #131722; color: #d1d4dc;
                border: none; font-family: 'Consolas'; font-size: 13px;
            }
            QScrollBar:vertical {
                background-color: #131722; width: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #2a2e39; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QLabel { color: #d1d4dc; }
            QFrame { border: none; }
            QProgressBar {
                background-color: #1e222d; border: none;
                height: 8px; text-align: center;
                color: #d1d4dc; font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #2962ff;
            }
        """)

    def create_activity_bar(self):
        """创建扁平化左侧栏"""
        activity_bar = QFrame()
        activity_bar.setFixedWidth(100)
        activity_bar.setStyleSheet("QFrame { background-color: #1e222d; border-right: 1px solid #2a2e39; }")

        layout = QVBoxLayout(activity_bar)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        icons = [
            ("📊", "图表"),
            ("🔍", "搜索"),
        ]
        for icon_text, tooltip in icons:
            btn = QPushButton(icon_text)
            btn.setToolTip(tooltip)
            btn.setFixedSize(80, 64)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)

        # 分隔线
        sep = QFrame()
        sep.setFixedSize(60, 1)
        sep.setStyleSheet("QFrame { background-color: #2a2e39; }")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # UPDATE ORIGIN 5M 按钮
        self.update_btn = QPushButton("🔄")
        self.update_btn.setToolTip("UPDATE ORIGIN 5M")
        self.update_btn.setFixedSize(80, 64)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(self.start_update_5m)
        layout.addWidget(self.update_btn)

        # 停止按钮
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setToolTip("停止更新")
        self.stop_btn.setFixedSize(80, 64)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_update)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #f23645; border: none; font-size: 20px; }
            QPushButton:hover { color: #ff6b7a; }
            QPushButton:disabled { color: #3a3a3a; }
        """)
        layout.addWidget(self.stop_btn)

        layout.addStretch()

        dock = QDockWidget("", self)
        dock.setWidget(activity_bar)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def create_main_area(self):
        """创建主区域 - 带 Tab 的图表编辑器"""
        self.main_tabs = QTabWidget()
        self.main_tabs.setTabsClosable(False)
        self.main_tabs.setMovable(True)
        self.main_tabs.setDocumentMode(True)

        # 欢迎页面
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.addStretch()
        welcome_label = QLabel("欢迎使用 Stock Analyst")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; color: #555555;")
        welcome_layout.addWidget(welcome_label)
        sub_label = QLabel("通过快捷键 Ctrl+O 打开 CSV 数据文件")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setStyleSheet("font-size: 14px; color: #444444;")
        welcome_layout.addWidget(sub_label)
        welcome_layout.addStretch()
        self.main_tabs.addTab(welcome_widget, "🏠 欢迎")

        self.setCentralWidget(self.main_tabs)

    def create_right_panel(self):
        """创建右侧进度面板"""
        self.right_dock = QDockWidget("", self)
        self.right_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.right_dock.setTitleBarWidget(QWidget())

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        # 标题
        title = QLabel("🔄 UPDATE ORIGIN 5M")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #d1d4dc;")
        right_layout.addWidget(title)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        right_layout.addWidget(self.progress_bar)

        # 进度文本
        self.progress_label = QLabel("[?/?] 等待启动...")
        self.progress_label.setStyleSheet("font-size: 12px; color: #787b86;")
        right_layout.addWidget(self.progress_label)

        # 完成列表标题
        list_title = QLabel("已更新个股:")
        list_title.setStyleSheet("font-size: 12px; color: #787b86; margin-top: 8px;")
        right_layout.addWidget(list_title)

        # 完成列表
        self.completed_list = QTextEdit()
        self.completed_list.setReadOnly(True)
        self.completed_list.setMaximumHeight(300)
        right_layout.addWidget(self.completed_list)

        right_layout.addStretch()

        self.right_dock.setWidget(right_widget)
        self.right_dock.setMinimumWidth(220)
        self.right_dock.setMaximumWidth(320)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)

    def create_bottom_panel(self):
        """创建底部面板 (Bottom Panel) """
        self.bottom_dock = QDockWidget("", self)
        self.bottom_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.bottom_dock.setTitleBarWidget(QWidget())

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        bottom_tabs = QTabWidget()
        bottom_tabs.setDocumentMode(True)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumHeight(200)
        self.terminal.append(">>> Stock Analyst Terminal Ready")
        self.terminal.append(">>> 点击左侧 🔄 按钮开始更新 5分钟数据")
        bottom_tabs.addTab(self.terminal, "💻 终端")

        output_widget = QTextEdit()
        output_widget.setReadOnly(True)
        output_widget.setMaximumHeight(200)
        output_widget.append("[Info] 应用已启动")
        bottom_tabs.addTab(output_widget, "📋 输出")

        bottom_layout.addWidget(bottom_tabs)

        self.bottom_dock.setWidget(bottom_widget)
        self.bottom_dock.setMinimumHeight(100)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)

    def create_status_bar(self):
        """创建状态栏"""
        status = QStatusBar()
        status.showMessage("就绪 | Stock Analyst v1.0 | finplot + PyQt6")
        self.setStatusBar(status)

    def load_sample_data(self):
        """生成示例股票数据"""
        self.terminal.append(">>> 正在生成示例数据...")

        sample_codes = ["AAPL", "GOOGL", "MSFT", "AMZN", "JPM", "GS"]
        for code in sample_codes:
            np.random.seed(hash(code) % (2**31))
            n = 200
            base_price = 100 + np.random.rand() * 200
            prices = base_price + np.cumsum(np.random.randn(n) * 2)

            end_date = datetime.now()
            dates = [end_date - timedelta(days=i) for i in range(n)]
            dates.reverse()

            df = pd.DataFrame({
                'Open': prices * (1 + np.random.randn(n) * 0.005),
                'High': prices * (1 + np.abs(np.random.randn(n)) * 0.015),
                'Low': prices * (1 - np.abs(np.random.randn(n)) * 0.015),
                'Close': prices * (1 + np.random.randn(n) * 0.008),
                'Volume': np.abs(np.random.randn(n) * 1000000 + 5000000),
            })
            df['Date'] = pd.to_datetime(dates)
            df.set_index('Date', inplace=True)
            df['High'] = df[['Open', 'Close', 'High']].max(axis=1)
            df['Low'] = df[['Open', 'Close', 'Low']].min(axis=1)
            self.stock_data[code] = df

        self.terminal.append(">>> 示例数据加载完成")

    def plot_stock(self, code, tab_text):
        """绘制 K 线图"""
        df = self.stock_data[code]
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        ax, ax2 = fplt.create_plot_widget(
            master=chart_container, rows=2, init_zoom_periods=100
        )
        chart_container.axs = [ax, ax2]
        chart_layout.addWidget(ax.ax_widget)

        fplt.candlestick_ochl(df[['Open', 'Close', 'High', 'Low']], ax=ax)
        fplt.volume_ocv(df[['Open', 'Close', 'Volume']], ax=ax2)

        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        fplt.plot(df['MA5'], ax=ax, legend='MA5', color='#f0d050')
        fplt.plot(df['MA10'], ax=ax, legend='MA10', color='#f0a0a0')
        fplt.plot(df['MA20'], ax=ax, legend='MA20', color='#60d0f0')

        fplt.refresh()
        self.main_tabs.addTab(chart_container, tab_text)
        self.main_tabs.setCurrentWidget(chart_container)

    def open_file(self):
        """打开 CSV 文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "打开股票数据", "", "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if path:
            try:
                df = pd.read_csv(path, index_col=0, parse_dates=True)
                code = os.path.basename(path).split('.')[0]
                self.stock_data[code] = df
                self.plot_stock(code, f"📈 {code}")
                self.statusBar().showMessage(f"已打开: {path}")
                self.terminal.append(f">>> 从文件加载: {code}")
            except Exception as e:
                self.terminal.append(f">>> 加载失败: {str(e)}")

    def refresh_data(self):
        """刷新数据"""
        if self.current_stock:
            self.statusBar().showMessage(f"刷新 {self.current_stock} ...")
            self.terminal.append(f">>> 刷新 {self.current_stock}")
            old_tabs = []
            for i in range(self.main_tabs.count()):
                if f"{self.current_stock}" in self.main_tabs.tabText(i):
                    old_tabs.append(i)
            for i in reversed(old_tabs):
                self.main_tabs.removeTab(i)
            self.plot_stock(self.current_stock, f"📈 {self.current_stock}")

    # ──────── UPDATE ORIGIN 5M 功能 ────────

    def start_update_5m(self):
        """启动 5分钟数据更新"""
        if self._is_updating:
            self.terminal.append(">>> 更新任务已在运行中")
            return

        self.terminal.append(">>> 🚀 启动 UPDATE ORIGIN 5M ...")
        self._is_updating = True
        self.update_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("[?/?] 启动中...")
        self.completed_list.clear()
        self.statusBar().showMessage("🔄 UPDATE ORIGIN 5M 运行中...")

        # 使用 QProcess 运行脚本（主线程安全，自带信号）
        self._update_process = QProcess(self)
        self._update_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self._update_process.readyReadStandardOutput.connect(
            self._on_process_output
        )
        self._update_process.finished.connect(self._on_process_finished)

        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'MarcoAPI', 'BaoStockAPI.py'
        )
        self._update_process.start(sys.executable, [script_path, FREQUENCY_5M])

        # 立即轮询一次进度，然后每 60 秒轮询
        self._poll_progress()
        self._poll_timer.start(60000)

    def _on_process_output(self):
        """读取 QProcess 输出（主线程安全）"""
        data = self._update_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        for line in data.splitlines():
            if line.strip():
                self.terminal.append(f">>> {line.rstrip()}")

    def _on_process_finished(self, exit_code, exit_status):
        """进程结束回调"""
        self.terminal.append(f">>> 子进程已退出 (exit code: {exit_code})")
        self._poll_timer.stop()
        self._cleanup_update_state()

    def stop_update(self):
        """停止更新"""
        if self._update_process and self._update_process.state() != QProcess.ProcessState.NotRunning:
            self._update_process.terminate()
            if not self._update_process.waitForFinished(5000):
                self._update_process.kill()
                self._update_process.waitForFinished(2000)
            self.terminal.append(">>> ⛔ 更新任务已停止")
            self.statusBar().showMessage("⛔ 更新已停止")

        self._poll_timer.stop()
        self._cleanup_update_state()

    def _cleanup_update_state(self):
        """清理更新状态"""
        self._is_updating = False
        self.update_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_process = None

    def _poll_progress(self):
        """轮询 COMPLETION_PROGRESS 更新进度面板"""
        try:
            progress_text, completed_codes = COMPLETION_PROGRESS(FREQUENCY_5M)
            # progress_text 格式: "[X/Y]"
            count_str = progress_text.strip("[]")
            parts = count_str.split("/")
            if len(parts) == 2:
                done = int(parts[0])
                total = int(parts[1])
                pct = int(done / total * 100) if total > 0 else 0
                self.progress_bar.setValue(pct)
                self.progress_label.setText(f"[{done}/{total}] 已完成 {pct}%")

                self.completed_list.clear()
                self.completed_list.append("\n".join(completed_codes))

                # 检查是否全部完成
                if done >= total and done > 0:
                    self._poll_timer.stop()
                    self.terminal.append(f">>> ✅ 全部完成! {progress_text}")
                    self.statusBar().showMessage(f"✅ 更新完成 {progress_text}")
                    self._cleanup_update_state()
                    return

                # 检查进程是否已结束（但可能未完成）
                if self._update_process and self._update_process.state() == QProcess.ProcessState.NotRunning:
                    self.terminal.append(f">>> ℹ️ 更新进程已退出 ({progress_text})")
                    self._poll_timer.stop()
                    self._cleanup_update_state()

        except Exception as e:
            self.terminal.append(f">>> 轮询进度异常: {e}")

    def toggle_bottom_panel(self):
        """切换底部面板可见性"""
        visible = self.bottom_dock.isVisible()
        self.bottom_dock.setVisible(not visible)


def main():
    """应用入口"""
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = TradingViewApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
