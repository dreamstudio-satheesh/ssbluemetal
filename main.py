"""Kal Quarry Billing — Entry point."""

import sys
import hashlib
import os

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QHBoxLayout, QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

# Ensure the billing directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_connection
from settings import load_json_settings, save_json_settings
from ui.main_window import MainWindow


class LoginDialog(QDialog):
    """Simple optional login dialog."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kal Quarry Billing — Login")
        self.setFixedSize(380, 300)
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QLineEdit { padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("🏗️  Kal Quarry")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #1a237e;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Stone Quarry Billing Software")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #757575; font-size: 12px; margin-bottom: 12px;")
        layout.addWidget(subtitle)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self._do_login)
        layout.addWidget(self.password)

        btn = QPushButton(" Login")
        btn.setFixedHeight(40)
        btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; border: none; border-radius: 4px;
                          font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        btn.clicked.connect(self._do_login)
        layout.addWidget(btn)

        # Skip login option
        skip_layout = QHBoxLayout()
        skip_layout.addStretch()
        self.skip_check = QCheckBox("Skip login (single user)")
        self.skip_check.setStyleSheet("color: #757575;")
        skip_layout.addWidget(self.skip_check)
        layout.addLayout(skip_layout)

        self._login_success = False

    def _do_login(self):
        # Check skip
        if self.skip_check.isChecked():
            save_json_settings({"skip_login": True})
            self._login_success = True
            self.accept()
            return

        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Enter username and password.")
            return

        hash_val = hashlib.sha256(password.encode()).hexdigest()
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, hash_val),
        ).fetchone()

        if row:
            self._login_success = True
            self._user = dict(row)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials.")

    def is_authenticated(self) -> bool:
        return self._login_success


def main():
    # Init database
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Kal Quarry Billing")
    app.setStyle("Fusion")

    # Global stylesheet
    app.setStyleSheet("""
        QToolTip { background: #1a237e; color: white; border: none; padding: 4px 8px; }
        QScrollBar:vertical { width: 8px; background: #f0f0f0; }
        QScrollBar::handle:vertical { background: #ccc; border-radius: 4px; min-height: 30px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """)

    # Optional login
    settings = load_json_settings()
    if not settings.get("skip_login", False):
        login = LoginDialog()
        if login.exec() != QDialog.Accepted or not login.is_authenticated():
            sys.exit(0)

    # Main window
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
