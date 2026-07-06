"""Customer management page with vehicle management."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox, QGroupBox,
    QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from customer import (
    search_customers, get_customer, add_customer, update_customer, delete_customer,
    get_customer_vehicles, add_customer_vehicle, update_customer_vehicle,
    delete_customer_vehicle,
)


class VehicleDialog(QDialog):
    def __init__(self, customer_id: int, vehicle_id: int = 0, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.vehicle_id = vehicle_id
        self.setWindowTitle("Edit Vehicle" if vehicle_id else "Add Vehicle")
        self.setMinimumWidth(400)

        form = QFormLayout(self)
        form.setSpacing(10)

        self.vehicle_no = QLineEdit()
        self.vehicle_no.setPlaceholderText("e.g., TN38 AB 1234")
        self.vehicle_no.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Vehicle No:", self.vehicle_no)

        self.vehicle_type = QComboBox()
        self.vehicle_type.addItems(["Tipper", "Lorry", "Tractor", "Mini Loader", "Other"])
        self.vehicle_type.setStyleSheet("padding: 4px 8px;")
        form.addRow("Type:", self.vehicle_type)

        self.capacity = QLineEdit()
        self.capacity.setPlaceholderText("e.g., 20 Ton")
        self.capacity.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Capacity:", self.capacity)

        if vehicle_id:
            from customer import get_customer_vehicles
            vehicles = get_customer_vehicles(customer_id)
            for v in vehicles:
                if v["id"] == vehicle_id:
                    self.vehicle_no.setText(v["vehicle_no"])
                    idx = self.vehicle_type.findText(v.get("vehicle_type", "Tipper"))
                    if idx >= 0:
                        self.vehicle_type.setCurrentIndex(idx)
                    self.capacity.setText(v.get("capacity", ""))
                    break

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate(self):
        if not self.vehicle_no.text().strip():
            QMessageBox.warning(self, "Error", "Vehicle number is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "vehicle_no": self.vehicle_no.text().strip(),
            "vehicle_type": self.vehicle_type.currentText(),
            "capacity": self.capacity.text().strip(),
        }


class CustomerDialog(QDialog):
    def __init__(self, customer_id: int = 0, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.setWindowTitle("Edit Customer" if customer_id else "Add Customer")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Customer details form ──
        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Customer name *")
        self.name_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Name:", self.name_edit)

        self.mobile_edit = QLineEdit()
        self.mobile_edit.setPlaceholderText("Mobile number")
        self.mobile_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Mobile:", self.mobile_edit)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Address")
        self.address_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("Address:", self.address_edit)

        self.gstin_edit = QLineEdit()
        self.gstin_edit.setPlaceholderText("GSTIN (if registered)")
        self.gstin_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        form.addRow("GSTIN:", self.gstin_edit)

        layout.addLayout(form)

        # ── Vehicles section ──
        vehicle_group = QGroupBox("Vehicles")
        vehicle_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px;
                        margin-top: 10px; padding-top: 16px; background: #fafafa; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        v_layout = QVBoxLayout(vehicle_group)

        self.vehicle_table = QTableWidget()
        self.vehicle_table.setColumnCount(4)
        self.vehicle_table.setHorizontalHeaderLabels(["ID", "Vehicle No", "Type", "Capacity"])
        self.vehicle_table.setAlternatingRowColors(True)
        self.vehicle_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.vehicle_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.vehicle_table.verticalHeader().setVisible(False)
        self.vehicle_table.verticalHeader().setDefaultSectionSize(32)
        self.vehicle_table.setColumnHidden(0, True)
        self.vehicle_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 4px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.vehicle_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        v_layout.addWidget(self.vehicle_table)

        # Vehicle buttons
        v_btn_layout = QHBoxLayout()
        add_v_btn = QPushButton("+ Add Vehicle")
        add_v_btn.setStyleSheet("background: #4caf50; color: white; padding: 4px 14px; border: none; border-radius: 3px; font-weight: bold;")
        add_v_btn.clicked.connect(self._add_vehicle)
        v_btn_layout.addWidget(add_v_btn)

        edit_v_btn = QPushButton("Edit")
        edit_v_btn.setStyleSheet("background: #2196f3; color: white; padding: 4px 14px; border: none; border-radius: 3px;")
        edit_v_btn.clicked.connect(self._edit_vehicle)
        v_btn_layout.addWidget(edit_v_btn)

        del_v_btn = QPushButton("Delete")
        del_v_btn.setStyleSheet("background: #f44336; color: white; padding: 4px 14px; border: none; border-radius: 3px;")
        del_v_btn.clicked.connect(self._delete_vehicle)
        v_btn_layout.addWidget(del_v_btn)

        v_btn_layout.addStretch()
        v_layout.addLayout(v_btn_layout)

        layout.addWidget(vehicle_group)

        # ── OK/Cancel ──
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Load customer data if editing
        if customer_id:
            c = get_customer(customer_id)
            if c:
                self.name_edit.setText(c["name"])
                self.mobile_edit.setText(c.get("mobile", ""))
                self.address_edit.setText(c.get("address", ""))
                self.gstin_edit.setText(c.get("gstin", ""))

        self._refresh_vehicles()

    def _validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Error", "Customer name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "mobile": self.mobile_edit.text().strip(),
            "address": self.address_edit.text().strip(),
            "gstin": self.gstin_edit.text().strip(),
        }

    def _refresh_vehicles(self):
        self.vehicle_table.setRowCount(0)
        if not self.customer_id:
            return
        vehicles = get_customer_vehicles(self.customer_id)
        for v in vehicles:
            row = self.vehicle_table.rowCount()
            self.vehicle_table.insertRow(row)
            self.vehicle_table.setItem(row, 0, QTableWidgetItem(str(v["id"])))
            self.vehicle_table.setItem(row, 1, QTableWidgetItem(v["vehicle_no"]))
            self.vehicle_table.setItem(row, 2, QTableWidgetItem(v.get("vehicle_type", "")))
            self.vehicle_table.setItem(row, 3, QTableWidgetItem(v.get("capacity", "")))

    def _add_vehicle(self):
        if not self.customer_id:
            QMessageBox.warning(self, "Error", "Save the customer first, then add vehicles.")
            return
        dialog = VehicleDialog(self.customer_id, 0, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            add_customer_vehicle(self.customer_id, **data)
            self._refresh_vehicles()

    def _edit_vehicle(self):
        row = self.vehicle_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select a vehicle to edit.")
            return
        vid = int(self.vehicle_table.item(row, 0).text())
        dialog = VehicleDialog(self.customer_id, vid, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            update_customer_vehicle(vid, **data)
            self._refresh_vehicles()

    def _delete_vehicle(self):
        row = self.vehicle_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select a vehicle to delete.")
            return
        vid = int(self.vehicle_table.item(row, 0).text())
        ok = QMessageBox.question(self, "Confirm", "Delete this vehicle?",
                                  QMessageBox.Yes | QMessageBox.No)
        if ok == QMessageBox.Yes:
            delete_customer_vehicle(vid)
            self._refresh_vehicles()


class CustomerWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Customers")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name or mobile...")
        self.search_edit.setFixedWidth(350)
        self.search_edit.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        add_btn = QPushButton("+ Add Customer")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(self._add_customer)
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
            QTableWidget::item { padding: 6px; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self._refresh()

    def _refresh(self):
        query = self.search_edit.text()
        customers = search_customers(query)
        self.table.setRowCount(0)
        for c in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(c["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("mobile", "")))
            self.table.setItem(row, 3, QTableWidgetItem(c.get("address", "")))
            self.table.setItem(row, 4, QTableWidgetItem(c.get("gstin", "")))
            self.table.setItem(row, 5, QTableWidgetItem(c.get("created_at", "")[:10]))

            # Actions
            action_w = QWidget()
            action_layout = QHBoxLayout(action_w)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            cid = c["id"]
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            edit_btn.clicked.connect(lambda checked, cid=cid: self._edit_customer(cid))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(50, 26)
            del_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, cid=cid: self._delete_customer(cid))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, action_w)

    def _add_customer(self):
        dialog = CustomerDialog(0, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            cid = add_customer(**data)
            # After saving customer, open edit dialog so user can add vehicles
            self._edit_customer(cid)

    def _edit_customer(self, customer_id: int):
        dialog = CustomerDialog(customer_id, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            update_customer(customer_id, **data)
            self._refresh()

    def _delete_customer(self, customer_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Delete this customer?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            delete_customer(customer_id)
            self._refresh()
