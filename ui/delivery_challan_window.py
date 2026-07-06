"""Delivery Challan list page and create dialog."""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QFormLayout, QGroupBox, QGridLayout, QDialog,
    QTextEdit, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from delivery_challan import (
    create_delivery_challan, search_delivery_challans,
    get_delivery_challan, get_delivery_challan_items,
    cancel_delivery_challan,
)
from database import get_next_dc_no
from invoice import get_invoice, get_invoice_items, search_invoices
from settings import get_company
from printer import generate_delivery_challan_pdf, open_pdf
from vehicle import get_all_vehicles
from driver import get_all_drivers
from transporter import get_all_transporters


class DeliveryChallanWindow(QWidget):
    """Delivery Challan list page (shown in sidebar)."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Delivery Challans")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()

        self.list_search = QLineEdit()
        self.list_search.setPlaceholderText("Search by DC No, Invoice No, Customer...")
        self.list_search.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.list_search.textChanged.connect(self._search)
        toolbar.addWidget(self.list_search, 1)

        self.list_date_from = QDateEdit()
        self.list_date_from.setCalendarPopup(True)
        self.list_date_from.setDate(date(date.today().year, date.today().month, 1))
        self.list_date_from.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(QLabel("From:"))
        toolbar.addWidget(self.list_date_from)

        self.list_date_to = QDateEdit()
        self.list_date_to.setCalendarPopup(True)
        self.list_date_to.setDate(date.today())
        self.list_date_to.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(QLabel("To:"))
        toolbar.addWidget(self.list_date_to)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._search)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        create_btn = QPushButton("+ Create DC from Invoice")
        create_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        create_btn.clicked.connect(self._open_create_dialog)
        toolbar.addWidget(create_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        # Table
        self.list_table = QTableWidget()
        self.list_table.setColumnCount(8)
        self.list_table.setHorizontalHeaderLabels(
            ["DC No", "Invoice Ref", "Customer", "Date", "Vehicle", "Items", "Status", ""]
        )
        self.list_table.setAlternatingRowColors(True)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.verticalHeader().setVisible(False)
        self.list_table.verticalHeader().setDefaultSectionSize(40)
        self.list_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        header = self.list_table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Interactive)
        header.setSectionResizeMode(7, QHeaderView.Interactive)
        header.resizeSection(0, 120)
        header.resizeSection(1, 120)
        header.resizeSection(3, 100)
        header.resizeSection(4, 100)
        header.resizeSection(5, 60)
        header.resizeSection(6, 60)
        header.resizeSection(7, 110)
        layout.addWidget(self.list_table)

        self._search()

    def _search(self):
        query = self.list_search.text()
        date_from = self.list_date_from.date().toString("yyyy-MM-dd")
        date_to = self.list_date_to.date().toString("yyyy-MM-dd")
        challans = search_delivery_challans(query, date_from, date_to)

        self.list_table.setRowCount(0)
        for dc in challans:
            row = self.list_table.rowCount()
            self.list_table.insertRow(row)
            self.list_table.setItem(row, 0, QTableWidgetItem(dc["dc_no"]))
            self.list_table.setItem(row, 1, QTableWidgetItem(dc["invoice_no"]))
            self.list_table.setItem(row, 2, QTableWidgetItem(dc["customer_name"]))
            self.list_table.setItem(row, 3, QTableWidgetItem(dc["challan_date"]))
            self.list_table.setItem(row, 4, QTableWidgetItem(dc.get("vehicle_no", "")))
            # Count items
            items = get_delivery_challan_items(dc["id"])
            self.list_table.setItem(row, 5, QTableWidgetItem(str(len(items))))
            self.list_table.setItem(row, 6, QTableWidgetItem(dc["status"].title()))

            # Actions
            action_w = QWidget()
            al = QHBoxLayout(action_w)
            al.setContentsMargins(2, 2, 2, 2)
            al.setSpacing(4)

            dc_id = dc["id"]
            print_btn = QPushButton("Print")
            print_btn.setFixedSize(50, 26)
            print_btn.setStyleSheet("background: #ff9800; color: white; border: none; border-radius: 3px;")
            print_btn.clicked.connect(lambda checked, did=dc_id: self._print_dc(did))
            al.addWidget(print_btn)

            if dc["status"] == "active":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setFixedSize(55, 26)
                cancel_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
                cancel_btn.clicked.connect(lambda checked, did=dc_id: self._cancel_dc(did))
                al.addWidget(cancel_btn)

            self.list_table.setCellWidget(row, 7, action_w)

    def _print_dc(self, dc_id: int):
        try:
            path = generate_delivery_challan_pdf(dc_id)
            open_pdf(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _cancel_dc(self, dc_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Cancel this delivery challan?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            cancel_delivery_challan(dc_id)
            self._search()

    def _open_create_dialog(self):
        dialog = CreateDeliveryChallanDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._search()

    def refresh_list(self):
        self._search()


class CreateDeliveryChallanDialog(QDialog):
    """Dialog to create a Delivery Challan from an existing invoice."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Delivery Challan from Invoice")
        self.setMinimumSize(750, 600)
        self.resize(800, 650)

        self._saved_dc_id = None
        self._items = []
        self._invoice_data = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Select Invoice ──
        inv_group = QGroupBox("Select Invoice")
        inv_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px;
                        margin-top: 10px; padding-top: 16px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        inv_layout = QVBoxLayout(inv_group)

        inv_search_layout = QHBoxLayout()
        self.inv_search_input = QLineEdit()
        self.inv_search_input.setPlaceholderText("Search by Invoice No or Customer...")
        self.inv_search_input.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.inv_search_input.textChanged.connect(self._search_invoices_ui)
        inv_search_layout.addWidget(self.inv_search_input, 1)

        self.inv_combo = QComboBox()
        self.inv_combo.setMinimumWidth(350)
        self.inv_combo.setStyleSheet("padding: 4px 8px;")
        self.inv_combo.currentIndexChanged.connect(self._on_invoice_selected)
        inv_search_layout.addWidget(self.inv_combo)
        inv_layout.addLayout(inv_search_layout)

        self.inv_info_label = QLabel("<i>Select an invoice to load items</i>")
        self.inv_info_label.setStyleSheet("color: #757575; padding: 4px;")
        inv_layout.addWidget(self.inv_info_label)

        layout.addWidget(inv_group)

        # ── DC Meta ──
        meta_group = QGroupBox("Delivery Challan Details")
        meta_group.setStyleSheet(inv_group.styleSheet())
        meta_layout = QFormLayout(meta_group)
        meta_layout.setSpacing(8)

        self.dc_no_label = QLabel("...")
        self.dc_no_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.dc_no_label.setStyleSheet("color: #1a237e;")
        meta_layout.addRow("DC No:", self.dc_no_label)

        self.dc_date = QDateEdit()
        self.dc_date.setCalendarPopup(True)
        self.dc_date.setDate(date.today())
        self.dc_date.setStyleSheet("padding: 4px 8px;")
        meta_layout.addRow("Challan Date:", self.dc_date)

        layout.addWidget(meta_group)

        # ── Transport Details ──
        transport_group = QGroupBox("Transport Details")
        transport_group.setStyleSheet(inv_group.styleSheet())
        transport_layout = QGridLayout(transport_group)
        transport_layout.setSpacing(8)

        # Vehicle
        transport_layout.addWidget(QLabel("Vehicle No:"), 0, 0)
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setMinimumWidth(200)
        self.vehicle_combo.setStyleSheet("padding: 4px 8px;")
        self.vehicle_combo.setEditable(True)
        transport_layout.addWidget(self.vehicle_combo, 0, 1)

        # Driver
        transport_layout.addWidget(QLabel("Driver:"), 0, 2)
        self.driver_combo = QComboBox()
        self.driver_combo.setMinimumWidth(200)
        self.driver_combo.setStyleSheet("padding: 4px 8px;")
        self.driver_combo.setEditable(True)
        transport_layout.addWidget(self.driver_combo, 0, 3)

        # Transporter
        transport_layout.addWidget(QLabel("Transporter:"), 1, 0)
        self.transporter_combo = QComboBox()
        self.transporter_combo.setMinimumWidth(200)
        self.transporter_combo.setStyleSheet("padding: 4px 8px;")
        self.transporter_combo.setEditable(True)
        transport_layout.addWidget(self.transporter_combo, 1, 1)

        # Delivery address
        transport_layout.addWidget(QLabel("Delivery Address:"), 1, 2)
        self.delivery_address = QLineEdit()
        self.delivery_address.setPlaceholderText("Leave blank to use customer address")
        self.delivery_address.setStyleSheet("padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px;")
        transport_layout.addWidget(self.delivery_address, 1, 3)

        layout.addWidget(transport_group)

        # ── Items Table ──
        items_group = QGroupBox("Items (loaded from invoice)")
        items_group.setStyleSheet(inv_group.styleSheet())
        items_layout = QVBoxLayout(items_group)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["#", "Product", "Qty", "Unit", "Rate", "Amount"]
        )
        self.items_table.setAlternatingRowColors(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(36)
        self.items_table.setColumnHidden(0, True)
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.items_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 4px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        items_layout.addWidget(self.items_table)

        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel("Notes:"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes for this delivery challan")
        self.notes_input.setStyleSheet("padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px;")
        notes_layout.addWidget(self.notes_input, 1)
        items_layout.addLayout(notes_layout)

        layout.addWidget(items_group, 1)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton("💾  Save Delivery Challan")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton { background: #f5f5f5; padding: 8px 20px;
                          border: 1px solid #ccc; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        # Load data
        self._load_vehicles()
        self._load_drivers()
        self._load_transporters()
        self._generate_dc_no()
        self._search_invoices_ui()

    def _load_vehicles(self):
        self.vehicle_combo.clear()
        self.vehicle_combo.addItem("", "")
        for v in get_all_vehicles():
            label = f"{v['vehicle_no']}  ({v.get('owner_name', '')})"
            self.vehicle_combo.addItem(label, v["id"])

    def _load_drivers(self):
        self.driver_combo.clear()
        self.driver_combo.addItem("", "")
        for d in get_all_drivers():
            label = f"{d['name']}  |  {d.get('mobile', '')}"
            self.driver_combo.addItem(label, d["id"])

    def _load_transporters(self):
        self.transporter_combo.clear()
        self.transporter_combo.addItem("", "")
        for t in get_all_transporters():
            label = f"{t['name']}{'  |  ' + t.get('gstin', '') if t.get('gstin') else ''}"
            self.transporter_combo.addItem(label, t["id"])

    def _generate_dc_no(self):
        company = get_company()
        prefix = company.get("invoice_prefix", "INV")
        self.dc_no = get_next_dc_no(prefix)
        self.dc_no_label.setText(self.dc_no)

    def _search_invoices_ui(self):
        query = self.inv_search_input.text()
        invoices = search_invoices(query, status="active")
        self.inv_combo.blockSignals(True)
        self.inv_combo.clear()
        for inv in invoices:
            label = f"{inv['invoice_no']}  —  {inv['customer_name']}  (₹{inv['grand_total']:,.2f})"
            self.inv_combo.addItem(label, inv["id"])
        self.inv_combo.blockSignals(False)
        self._on_invoice_selected()

    def _on_invoice_selected(self):
        idx = self.inv_combo.currentIndex()
        if idx < 0:
            self._invoice_data = None
            self._items = []
            self.items_table.setRowCount(0)
            self.inv_info_label.setText("<i>Select an invoice to load items</i>")
            self.save_btn.setEnabled(False)
            return

        inv_id = self.inv_combo.itemData(idx)
        inv = get_invoice(inv_id)
        if not inv:
            return

        self._invoice_data = inv
        self.inv_info_label.setText(
            f"Customer: <b>{inv['customer_name']}</b>  |  "
            f"Date: {inv['invoice_date']}  |  "
            f"Total: ₹{inv['grand_total']:,.2f}"
        )
        self.inv_info_label.setStyleSheet("color: #1a237e; padding: 4px;")

        # Load items from invoice
        invoice_items = get_invoice_items(inv_id)
        self._items = []
        self.items_table.setRowCount(0)
        for item in invoice_items:
            self._items.append({
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "description": item.get("description", ""),
                "quantity": item["quantity"],
                "unit": item["unit"],
                "rate": item["rate"],
                "amount": item["amount"],
            })
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            self.items_table.setItem(row, 0, QTableWidgetItem(str(item["product_id"])))
            self.items_table.setItem(row, 1, QTableWidgetItem(item["product_name"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"{item['quantity']:.3f}"))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.get("unit", "")))
            self.items_table.setItem(row, 4, QTableWidgetItem(f"{item['rate']:.2f}"))
            self.items_table.setItem(row, 5, QTableWidgetItem(f"{item['amount']:.2f}"))

        self.save_btn.setEnabled(True)

    def _save(self):
        if not self._invoice_data:
            QMessageBox.warning(self, "Error", "Please select an invoice.")
            return

        inv = self._invoice_data

        # Get transport details
        vehicle_no = ""
        vidx = self.vehicle_combo.currentIndex()
        if vidx > 0:
            vehicle_no = self.vehicle_combo.currentText().split("  (")[0]
        else:
            vehicle_no = self.vehicle_combo.currentText()

        driver_name = ""
        driver_mobile = ""
        didx = self.driver_combo.currentIndex()
        if didx > 0:
            driver_text = self.driver_combo.currentText()
            parts = driver_text.split("  |  ")
            driver_name = parts[0]
            driver_mobile = parts[1] if len(parts) > 1 else ""
        else:
            driver_name = self.driver_combo.currentText()

        transporter_name = ""
        tgs = ""
        tidx = self.transporter_combo.currentIndex()
        if tidx > 0:
            ttext = self.transporter_combo.currentText()
            if "  |  " in ttext:
                parts = ttext.split("  |  ")
                transporter_name = parts[0]
                tgs = parts[1] if len(parts) > 1 else ""
            else:
                transporter_name = ttext

        vehicle_owner = ""
        if vidx > 0:
            vehicles = get_all_vehicles()
            if vidx - 1 < len(vehicles):
                vehicle_owner = vehicles[vidx - 1].get("owner_name", "")

        try:
            dc_id = create_delivery_challan(
                dc_no=self.dc_no,
                invoice_no=inv["invoice_no"],
                customer_id=inv["customer_id"],
                customer_name=inv["customer_name"],
                customer_mobile=inv.get("customer_mobile", ""),
                customer_gstin=inv.get("customer_gstin", ""),
                challan_date=self.dc_date.date().toString("yyyy-MM-dd"),
                vehicle_no=vehicle_no,
                vehicle_owner=vehicle_owner,
                driver_name=driver_name,
                driver_mobile=driver_mobile,
                transporter_name=transporter_name,
                transporter_gstin=tgs,
                delivery_address=self.delivery_address.text(),
                notes=self.notes_input.text(),
                items=self._items,
            )
            self._saved_dc_id = dc_id
            QMessageBox.information(
                self, "Saved",
                f"Delivery Challan {self.dc_no} saved successfully!",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save delivery challan:\n{str(e)}")
