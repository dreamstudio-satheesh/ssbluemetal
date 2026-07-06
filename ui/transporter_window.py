"""Transporter management page."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from transporter import (
    search_transporters, get_transporter, add_transporter,
    update_transporter, delete_transporter,
)


class TransporterDialog(QDialog):
    def __init__(self, transporter_id: int = 0, parent=None):
        super().__init__(parent)
        self.transporter_id = transporter_id
        self.setWindowTitle("Edit Transporter" if transporter_id else "Add Transporter")
        self.setMinimumWidth(450)

        form = QFormLayout(self)
        form.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Transporter name *")
        self.name_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Name:", self.name_edit)

        self.mobile_edit = QLineEdit()
        self.mobile_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Mobile:", self.mobile_edit)

        self.address_edit = QLineEdit()
        self.address_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Address:", self.address_edit)

        self.gstin_edit = QLineEdit()
        self.gstin_edit.setPlaceholderText("GSTIN (if registered)")
        self.gstin_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("GSTIN:", self.gstin_edit)

        if transporter_id:
            t = get_transporter(transporter_id)
            if t:
                self.name_edit.setText(t["name"])
                self.mobile_edit.setText(t.get("mobile", ""))
                self.address_edit.setText(t.get("address", ""))
                self.gstin_edit.setText(t.get("gstin", ""))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Error", "Transporter name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "mobile": self.mobile_edit.text().strip(),
            "address": self.address_edit.text().strip(),
            "gstin": self.gstin_edit.text().strip(),
        }


class TransporterWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Transporters")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name, mobile, or GSTIN...")
        self.search_edit.setFixedWidth(400)
        self.search_edit.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        add_btn = QPushButton("+ Add Transporter")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(self._add_transporter)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Mobile", "Address", "GSTIN", "Added On", ""]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setColumnHidden(0, True)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self._refresh()

    def _refresh(self):
        query = self.search_edit.text()
        transporters = search_transporters(query)
        self.table.setRowCount(0)
        for t in transporters:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(t["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(t.get("mobile", "")))
            self.table.setItem(row, 3, QTableWidgetItem(t.get("address", "")))
            self.table.setItem(row, 4, QTableWidgetItem(t.get("gstin", "")))
            self.table.setItem(row, 5, QTableWidgetItem(t.get("created_at", "")[:10]))

            # Actions
            action_w = QWidget()
            action_layout = QHBoxLayout(action_w)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            tid = t["id"]
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            edit_btn.clicked.connect(lambda checked, tid=tid: self._edit_transporter(tid))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(50, 26)
            del_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, tid=tid: self._delete_transporter(tid))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, action_w)

    def _add_transporter(self):
        dialog = TransporterDialog(0, self)
        if dialog.exec() == QDialog.Accepted:
            add_transporter(**dialog.get_data())
            self._refresh()

    def _edit_transporter(self, transporter_id: int):
        dialog = TransporterDialog(transporter_id, self)
        if dialog.exec() == QDialog.Accepted:
            update_transporter(transporter_id, **dialog.get_data())
            self._refresh()

    def _delete_transporter(self, transporter_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Delete this transporter?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            delete_transporter(transporter_id)
            self._refresh()
