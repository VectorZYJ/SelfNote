# ----------------- 模块导入 -----------------
import sys
import os
import json
from platformdirs import user_data_dir
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QSizeGrip, QGraphicsDropShadowEffect, QSystemTrayIcon,
    QMenu
)
from PySide6.QtGui import QFont, QMouseEvent, QColor, QIcon, QAction
from PySide6.QtCore import Qt


# ----------------- 全局路径配置 -----------------

def resource_path(relative_path):
    """获取程序内部资源的绝对路径 (icon)"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


APP_NAME = "StickyNoteApp"
APP_AUTHOR = "YourName"
APP_DATA_DIR = user_data_dir(APP_NAME, APP_AUTHOR)
os.makedirs(APP_DATA_DIR, exist_ok=True)

# 推荐在macOS上使用 .png 格式作为托盘图标
ICON_FILE = resource_path("icon.png")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "note_config.json")


# ----------------- 主窗口类 -----------------
class StickyNote(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("桌面便签")
        self.base_window_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window | Qt.Tool
        self.setWindowFlags(self.base_window_flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_start_position = None

        self._create_ui()
        self._load_note()  # <--- 现在调用 _load_note 是安全的
        self._create_tray_icon()

    def _create_ui(self):
        """创建并布局窗口中的所有UI控件。"""
        container = QWidget(self)
        self.setCentralWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(25)
        self.title_bar.setStyleSheet("background-color: #F8F8F0;")

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(5, 0, 0, 0)
        title_layout.setSpacing(5)

        # macOS 规范：按钮在左上角
        quit_button = QPushButton("❌")
        quit_button.setFixedSize(22, 22)
        quit_button.clicked.connect(self.close)
        quit_button.setStyleSheet("""
            QPushButton { font-size: 10px; border: none; background-color: transparent; color: #888; }
            QPushButton:hover { background-color: #E81123; color: white; border-radius: 4px; }
        """)
        title_layout.addWidget(quit_button)

        self.pin_button = QPushButton("📌")
        self.pin_button.setCheckable(True)
        self.pin_button.clicked.connect(self._toggle_always_on_top)
        self.pin_button.setFixedSize(22, 22)
        self.pin_button.setStyleSheet("""
            QPushButton { font-size: 14px; border: 1px solid transparent; background-color: transparent; padding-bottom: 2px; }
            QPushButton:hover { background-color: #E0E0E0; border-radius: 4px; }
            QPushButton:checked { background-color: #0078D7; border-radius: 4px; }
        """)
        title_layout.addWidget(self.pin_button)

        title_layout.addStretch()
        main_layout.addWidget(self.title_bar)

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Helvetica Neue", 12))
        self.text_edit.setPlaceholderText("在这里输入内容...")
        self.text_edit.setStyleSheet("border: none; padding: 5px;")
        main_layout.addWidget(self.text_edit, stretch=1)

        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(5, 0, 0, 0)

        bottom_layout.addStretch()

        save_button = QPushButton("保存")
        save_button.clicked.connect(self._save_note)
        save_button.setStyleSheet("""
            QPushButton { background-color: transparent; border: 1px solid #E0E0E0; padding: 4px 8px; font-size: 11px; color: #555; }
            QPushButton:hover { background-color: #F0F0F0; }
            QPushButton:pressed { background-color: #E0E0E0; }
        """)
        bottom_layout.addWidget(save_button)

        grip = QSizeGrip(self)
        bottom_layout.addWidget(grip, 0, Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(bottom_container)

        container.setStyleSheet("""
            QWidget { background-color: #FFFFF0; border: 1px solid #E0E0E0; }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(1, 1)
        container.setGraphicsEffect(shadow)

    # --- 后台逻辑方法 ---
    def _create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(ICON_FILE))
        self.tray_icon.setToolTip("桌面便签")
        tray_menu = QMenu()
        toggle_action = QAction("显示/隐藏便签", self)
        toggle_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(toggle_action)
        tray_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def _load_note(self):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.text_edit.setPlainText(config.get("content", ""))
                geometry = config.get("geometry")
                if geometry:
                    self.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
                else:
                    self.resize(280, 280)
                is_on_top = config.get("always_on_top", False)
                self.pin_button.setChecked(is_on_top)
                # (改动) 现在调用这个函数是安全的，因为它不再调用 self.show()
                self._update_pin_button_state(is_on_top)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.resize(280, 280)
            self._update_pin_button_state(False)

    def _save_note(self):
        geo = self.geometry()
        config = {
            "content": self.text_edit.toPlainText(),
            "geometry": {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()},
            "always_on_top": self.pin_button.isChecked()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存失败: {e}")

    # --- (改动) 修复置顶BUG的核心 ---

    def _toggle_always_on_top(self):
        """
        当用户点击“置顶”按钮时调用。
        """
        is_on_top = self.pin_button.isChecked()
        # 1. 更新窗口标志
        self._update_pin_button_state(is_on_top)
        # 2. (新增) 立即调用 show() 来让窗口标志的更改生效
        self.show()

    def _update_pin_button_state(self, is_on_top):
        """
        核心函数：只负责设置窗口标志，不负责显示。
        """
        if is_on_top:
            self.setWindowFlags(self.base_window_flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.base_window_flags)

        # 重新应用透明背景属性
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # (改动) 移除了 self.show()。这是修复启动BUG的关键。

    # --- 鼠标事件 (拖动已修复) ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_position is not None:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start_position = None
        event.accept()


# ----------------- 程序入口 -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    note = StickyNote()
    note.setMinimumSize(150, 120)

    # 注意：这里没有 note.show()，程序启动后窗口默认隐藏

    sys.exit(app.exec())