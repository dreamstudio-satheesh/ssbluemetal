"""Driver management page."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from driver import (
    search_drivers, get_driver, add_driver, update_driver, delete_driver,
)


class DriverDialog(QDialog):
    def __init__(self, driver_id: int = 0, parent=None):
        super().__init__(parent)
        self.driver_id = driver_id
        self.setWindowTitle("Edit Driver" if driver_id else "Add Driver")
        self.setMinimumWidth(450)

        form = QFormLayout(self)
        form.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Driver name *")
        self.name_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Name:", self.name_edit)

        self.mobile_edit = QLineEdit()
        self.mobile_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Mobile:", self.mobile_edit)

        self.license_edit = QLineEdit()
        self.license_edit.setPlaceholderText("Driving license number")
        self.license_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("License No:", self.license_edit)

        self.address_edit = QLineEdit()
        self.address_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Address:", self.address_edit)

        if driver_id:
            d = get_driver(driver_id)
            if d:
                self.name_edit.setText(d["name"])
                self.mobile_edit.setText(d.get("mobile", ""))
                self.license_edit.setText(d.get("license_no", ""))
                self.address_edit.setText(d.get("address", ""))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Error", "Driver name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "mobile": self.mobile_edit.text().strip(),
            "license_no": self.license_edit.text().strip(),
            "address": self.address_edit.text().strip(),
        }


class DriverWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Drivers")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name, mobile, or license...")
        self.search_edit.setFixedWidth(400)
        self.search_edit.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        add_btn = QPushButton("+ Add Driver")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(self._add_driver)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Name", "Mobile", "License No", "Address", "Added On", ""]
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
        drivers = search_drivers(query)
        self.table.setRowCount(0)
        for d in drivers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(d["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(d.get("mobile", "")))
            self.table.setItem(row, 3, QTableWidgetItem(d.get("license_no", "")))
            self.table.setItem(row, 4, QTableWidgetItem(d.get("address", "")))
            self.table.setItem(row, 5, QTableWidgetItem(d.get("created_at", "")[:10]))

            # Actions
            action_w = QWidget()
            action_layout = QHBoxLayout(action_w)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            did = d["id"]
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            edit_btn.clicked.connect(lambda checked, did=did: self._edit_driver(did))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(50, 26)
            del_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, did=did: self._delete_driver(did))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, action_w)

    def _add_driver(self):
        dialog = DriverDialog(0, self)
        if dialog.exec() == QDialog.Accepted:
            add_driver(**dialog.get_data())
            self._refresh()

    def _edit_driver(self, driver_id: int):
        dialog = DriverDialog(driver_id, self)
        if dialog.exec() == QDialog.Accepted:
            update_driver(driver_id, **dialog.get_data())
            self._refresh()

    def _delete_driver(self, driver_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Delete this driver?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            delete_driver(driver_id)
            self._refresh()
