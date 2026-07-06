"""Invoice creation and list — the core billing screen."""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QDateEdit, QFormLayout, QGroupBox, QGridLayout, QFrame,
    QTextEdit, QTabWidget, QSplitter, QAbstractItemView,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QFont, QDoubleValidator

from customer import search_customers, get_all_customers
from product import get_all_products
from database import get_next_invoice_no
from invoice import (
    create_invoice, search_invoices, get_invoice, get_invoice_items,
    cancel_invoice,
)
from settings import get_company, get_db_setting
from printer import generate_invoice_pdf, open_pdf


class InvoiceWindow(QWidget):
    """Used for both New Invoice and Invoice List (tab-based)."""

    def __init__(self, list_mode: bool = False):
        super().__init__()
        self.list_mode = list_mode
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        if list_mode:
            self._build_list_ui(layout)
        else:
            self._build_billing_ui(layout)

    # ── BILLING UI ───────────────────────────────────────────────

    def _build_billing_ui(self, layout: QVBoxLayout):
        header = QLabel("New Invoice")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # ── Top: Invoice meta ──
        meta_grid = QGridLayout()
        meta_grid.setSpacing(10)

        meta_grid.addWidget(QLabel("Invoice No:"), 0, 0)
        self.inv_no_label = QLabel("...")
        self.inv_no_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.inv_no_label.setStyleSheet("color: #1a237e;")
        meta_grid.addWidget(self.inv_no_label, 0, 1)

        meta_grid.addWidget(QLabel("Date:"), 0, 2)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.date_edit.setFixedWidth(160)
        self.date_edit.setStyleSheet("padding: 4px 8px;")
        meta_grid.addWidget(self.date_edit, 0, 3)

        meta_grid.addWidget(QLabel("GST Type:"), 0, 4)
        self.gst_type_combo = QComboBox()
        self.gst_type_combo.addItems(["intra (CGST+SGST)", "inter (IGST)"])
        self.gst_type_combo.setFixedWidth(190)
        self.gst_type_combo.setStyleSheet("padding: 4px 8px;")
        meta_grid.addWidget(self.gst_type_combo, 0, 5)

        layout.addLayout(meta_grid)
        layout.addSpacing(8)

        # ── Customer ──
        cust_group = QGroupBox("Customer")
        cust_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 6px;
                        margin-top: 10px; padding-top: 16px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        cust_layout = QGridLayout(cust_group)
        cust_layout.setSpacing(8)

        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Search customer by name or mobile...")
        self.cust_search.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.cust_search.textChanged.connect(self._search_customers_ui)
        cust_layout.addWidget(self.cust_search, 0, 0, 1, 2)

        self.cust_combo = QComboBox()
        self.cust_combo.setMinimumWidth(300)
        self.cust_combo.setStyleSheet("padding: 4px 8px;")
        self.cust_combo.currentIndexChanged.connect(self._on_customer_selected)
        cust_layout.addWidget(self.cust_combo, 1, 0)

        self.cust_name_label = QLabel("")
        self.cust_mobile_label = QLabel("")
        self.cust_gstin_label = QLabel("")
        cust_layout.addWidget(self.cust_name_label, 2, 0)
        cust_layout.addWidget(self.cust_mobile_label, 2, 1)
        cust_layout.addWidget(self.cust_gstin_label, 3, 0)

        layout.addWidget(cust_group)
        layout.addSpacing(8)

        # ── Items Table ──
        items_group = QGroupBox("Invoice Items")
        items_group.setStyleSheet(cust_group.styleSheet())
        items_layout = QVBoxLayout(items_group)

        # Product selector row
        add_row = QHBoxLayout()
        self.item_product = QComboBox()
        self.item_product.setMinimumWidth(250)
        self.item_product.setStyleSheet("padding: 4px 8px;")
        add_row.addWidget(QLabel("Product:"))
        add_row.addWidget(self.item_product)

        self.item_qty = QDoubleSpinBox()
        self.item_qty.setRange(0.001, 999999)
        self.item_qty.setDecimals(3)
        self.item_qty.setValue(1)
        self.item_qty.setFixedWidth(120)
        self.item_qty.setStyleSheet("padding: 4px 8px;")
        add_row.addWidget(QLabel("Qty:"))
        add_row.addWidget(self.item_qty)

        self.item_rate = QDoubleSpinBox()
        self.item_rate.setRange(0, 999999)
        self.item_rate.setDecimals(2)
        self.item_rate.setPrefix("₹ ")
        self.item_rate.setFixedWidth(140)
        self.item_rate.setStyleSheet("padding: 4px 8px;")
        add_row.addWidget(QLabel("Rate:"))
        add_row.addWidget(self.item_rate)

        add_btn = QPushButton("+ Add")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 6px 18px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(self._add_item)
        add_row.addWidget(add_btn)

        add_row.addStretch()
        items_layout.addLayout(add_row)

        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(
            ["#", "Product", "Qty", "Unit", "Rate", "Amount", ""]
        )
        self.items_table.setAlternatingRowColors(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(40)
        self.items_table.setColumnHidden(0, True)
        self.items_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 4px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        items_layout.addWidget(self.items_table)

        layout.addWidget(items_group, 1)

        # ── Bottom: Totals + Actions ──
        bottom_layout = QHBoxLayout()

        # Totals
        totals_group = QGroupBox()
        totals_layout = QFormLayout(totals_group)
        totals_layout.setSpacing(6)

        self.subtotal_label = QLabel("₹ 0.00")
        self.subtotal_label.setFont(QFont("Segoe UI", 11))
        totals_layout.addRow("Subtotal:", self.subtotal_label)

        self.gst_rate_combo = QComboBox()
        self.gst_rate_combo.addItems(["GST 0%", "GST 5%", "GST 12%", "GST 18%"])
        self.gst_rate_combo.currentIndexChanged.connect(self._recalc_totals)
        totals_layout.addRow("GST Rate:", self.gst_rate_combo)

        # GST breakdown
        self.cgst_label = QLabel("₹ 0.00")
        self.cgst_label.setFont(QFont("Segoe UI", 9))
        self.cgst_label.setStyleSheet("color: #757575;")
        totals_layout.addRow("  CGST:", self.cgst_label)

        self.sgst_label = QLabel("₹ 0.00")
        self.sgst_label.setFont(QFont("Segoe UI", 9))
        self.sgst_label.setStyleSheet("color: #757575;")
        totals_layout.addRow("  SGST:", self.sgst_label)

        self.igst_label = QLabel("₹ 0.00")
        self.igst_label.setFont(QFont("Segoe UI", 9))
        self.igst_label.setStyleSheet("color: #757575;")
        totals_layout.addRow("  IGST:", self.igst_label)

        # Separator
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.HLine)
        sep_line.setStyleSheet("max-height: 1px; background: #e0e0e0;")
        totals_layout.addRow(sep_line)

        self.round_off_btn = QPushButton("Round Off")
        self.round_off_btn.setFixedWidth(100)
        self.round_off_btn.setStyleSheet("padding: 4px;")
        self.round_off_btn.clicked.connect(self._do_round_off)
        totals_layout.addRow("", self.round_off_btn)

        self.grand_total_label = QLabel("₹ 0.00")
        self.grand_total_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.grand_total_label.setStyleSheet("color: #1a237e;")
        totals_layout.addRow("Grand Total:", self.grand_total_label)

        bottom_layout.addWidget(totals_group)
        bottom_layout.addStretch()

        # Action buttons
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)

        save_btn = QPushButton("💾  Save Invoice")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        save_btn.clicked.connect(self._save_invoice)
        action_layout.addWidget(save_btn)

        self.print_btn = QPushButton("🖨️  Print Invoice")
        self.print_btn.setFixedHeight(44)
        self.print_btn.setEnabled(False)
        self.print_btn.setStyleSheet("""
            QPushButton { background: #ff9800; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #f57c00; }
            QPushButton:disabled { background: #ccc; }
        """)
        self.print_btn.clicked.connect(self._print_invoice)
        action_layout.addWidget(self.print_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(36)
        clear_btn.setStyleSheet("""
            QPushButton { background: #f5f5f5; padding: 6px 20px;
                          border: 1px solid #ccc; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        clear_btn.clicked.connect(self._clear_form)
        action_layout.addWidget(clear_btn)

        action_layout.addStretch()
        bottom_layout.addLayout(action_layout)

        layout.addLayout(bottom_layout)

        # Load data
        self._load_products()
        self._load_customers()
        self._generate_invoice_no()
        self._on_customer_selected()

    def _search_customers_ui(self):
        """Filter customer dropdown as user types."""
        query = self.cust_search.text()
        customers = search_customers(query)
        self.cust_combo.blockSignals(True)
        self.cust_combo.clear()
        for c in customers:
            label = f"{c['name']}  |  {c.get('mobile', '')}"
            self.cust_combo.addItem(label, c["id"])
        self.cust_combo.blockSignals(False)
        self._on_customer_selected()

    def _load_customers(self):
        customers = get_all_customers()
        self.cust_combo.clear()
        for c in customers:
            label = f"{c['name']}  |  {c.get('mobile', '')}"
            self.cust_combo.addItem(label, c["id"])

    def _load_products(self):
        products = get_all_products()
        self.item_product.clear()
        for p in products:
            label = f"{p['name']}  ({p['unit']})  @ ₹{p['rate']:.2f}"
            self.item_product.addItem(label, p["id"])
        # Auto-fill rate when product changes
        self.item_product.currentIndexChanged.connect(self._on_product_selected)
        self._on_product_selected()

    def _on_product_selected(self):
        idx = self.item_product.currentIndex()
        if idx >= 0:
            products = get_all_products()
            if idx < len(products):
                self.item_rate.setValue(products[idx]["rate"])

    def _on_customer_selected(self):
        idx = self.cust_combo.currentIndex()
        if idx >= 0:
            cid = self.cust_combo.itemData(idx)
            from customer import get_customer
            c = get_customer(cid) if cid else None
            if c:
                self.cust_name_label.setText(f"<b>{c['name']}</b>")
                self.cust_mobile_label.setText(f"📞 {c.get('mobile', '')}")
                self.cust_gstin_label.setText(f"GST: {c.get('gstin', 'N/A')}")
                return
        self.cust_name_label.setText("<i>No customer selected</i>")
        self.cust_mobile_label.setText("")
        self.cust_gstin_label.setText("")

    def _generate_invoice_no(self):
        company = get_company()
        prefix = company.get("invoice_prefix", "INV")
        self.inv_no = get_next_invoice_no(prefix)
        self.inv_no_label.setText(self.inv_no)

    def _add_item(self):
        idx = self.item_product.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a product.")
            return
        products = get_all_products()
        if idx >= len(products):
            return
        p = products[idx]
        qty = self.item_qty.value()
        rate = self.item_rate.value()
        amount = round(qty * rate, 2)

        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setItem(row, 0, QTableWidgetItem(str(p["id"])))
        self.items_table.setItem(row, 1, QTableWidgetItem(p["name"]))
        self.items_table.setItem(row, 2, QTableWidgetItem(f"{qty:.3f}"))
        self.items_table.setItem(row, 3, QTableWidgetItem(p.get("unit", "")))
        self.items_table.setItem(row, 4, QTableWidgetItem(f"{rate:.2f}"))
        self.items_table.setItem(row, 5, QTableWidgetItem(f"{amount:.2f}"))

        # Remove button
        rem_btn = QPushButton("✕")
        rem_btn.setFixedSize(30, 26)
        rem_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
        rem_btn.clicked.connect(lambda: self._remove_item(row))
        self.items_table.setCellWidget(row, 6, rem_btn)

        self._recalc_totals()

    def _remove_item(self, row: int):
        self.items_table.removeRow(row)
        self._recalc_totals()

    def _recalc_totals(self):
        subtotal = 0.0
        for row in range(self.items_table.rowCount()):
            amt_item = self.items_table.item(row, 5)
            if amt_item:
                subtotal += float(amt_item.text())

        gst_text = self.gst_rate_combo.currentText()
        gst_rate = float(gst_text.replace("GST ", "").replace("%", ""))
        gst_amount = round(subtotal * gst_rate / 100, 2)

        is_intra = self.gst_type_combo.currentIndex() == 0
        if is_intra:
            half = round(gst_amount / 2, 2)
            cgst = half
            sgst = gst_amount - half
            igst = 0.0
        else:
            cgst = 0.0
            sgst = 0.0
            igst = gst_amount

        grand = subtotal + gst_amount

        self._subtotal = subtotal
        self._gst_rate = gst_rate
        self._cgst = cgst
        self._sgst = sgst
        self._igst = igst
        self._round_off = 0.0
        self._grand = grand

        self.subtotal_label.setText(f"₹ {subtotal:,.2f}")
        self.cgst_label.setText(f"₹ {cgst:,.2f}")
        self.sgst_label.setText(f"₹ {sgst:,.2f}")
        self.igst_label.setText(f"₹ {igst:,.2f}")
        self.grand_total_label.setText(f"₹ {grand:,.2f}")

    def _do_round_off(self):
        rounded = round(self._grand)
        self._round_off = round(rounded - self._grand, 2)
        self._grand = rounded
        self.grand_total_label.setText(f"₹ {rounded:,.2f}")

    def _amount_in_words(self, amount: float) -> str:
        if amount == 0:
            return "Zero Rupees Only"
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                 "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def _under_1000(n):
            res = ""
            if n >= 100:
                res += units[n // 100] + " Hundred "
                n %= 100
            if 10 < n < 20:
                res += teens[n - 10] + " "
            else:
                if n >= 20:
                    res += tens[n // 10] + " "
                    n %= 10
                if n > 0:
                    res += units[n] + " "
            return res.strip()

        amt = int(round(amount))
        words = ""
        if amt >= 100000:
            lakhs = amt // 100000
            words += _under_1000(lakhs) + " Lakh "
            amt %= 100000
        if amt >= 1000:
            thousands = amt // 1000
            words += _under_1000(thousands) + " Thousand "
            amt %= 1000
        if amt > 0:
            words += _under_1000(amt)
        return words.strip() + " Rupees Only"

    def _save_invoice(self):
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "Add at least one item.")
            return

        idx = self.cust_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Select a customer.")
            return

        cid = self.cust_combo.itemData(idx)
        from customer import get_customer
        c = get_customer(cid) if cid else None
        if not c:
            QMessageBox.warning(self, "Error", "Invalid customer.")
            return

        items = []
        for row in range(self.items_table.rowCount()):
            items.append({
                "product_id": int(self.items_table.item(row, 0).text()),
                "product_name": self.items_table.item(row, 1).text(),
                "quantity": float(self.items_table.item(row, 2).text()),
                "unit": self.items_table.item(row, 3).text(),
                "rate": float(self.items_table.item(row, 4).text()),
                "amount": float(self.items_table.item(row, 5).text()),
            })

        inv_id = create_invoice(
            invoice_no=self.inv_no,
            customer_id=c["id"],
            customer_name=c["name"],
            customer_mobile=c.get("mobile", ""),
            customer_gstin=c.get("gstin", ""),
            invoice_date=self.date_edit.date().toString("yyyy-MM-dd"),
            gst_type="intra" if self.gst_type_combo.currentIndex() == 0 else "inter",
            subtotal=self._subtotal,
            gst_rate=self._gst_rate,
            cgst_amount=self._cgst,
            sgst_amount=self._sgst,
            igst_amount=self._igst,
            round_off=self._round_off,
            grand_total=self._grand,
            amount_in_words=self._amount_in_words(self._grand),
            notes="",
            items=items,
        )

        self._saved_invoice_id = inv_id
        self.print_btn.setEnabled(True)

        QMessageBox.information(
            self, "Saved",
            f"Invoice {self.inv_no} saved successfully.\nClick 'Print Invoice' to generate PDF."
        )

    def _print_invoice(self):
        if hasattr(self, '_saved_invoice_id') and self._saved_invoice_id:
            try:
                path = generate_invoice_pdf(self._saved_invoice_id)
                open_pdf(path)
            except Exception as e:
                QMessageBox.critical(self, "Print Error", str(e))

    def _clear_form(self):
        self.items_table.setRowCount(0)
        self.print_btn.setEnabled(False)
        self._generate_invoice_no()
        self._recalc_totals()
        if hasattr(self, '_saved_invoice_id'):
            del self._saved_invoice_id

    def refresh_for_new(self):
        self._clear_form()
        self._load_customers()
        self._load_products()

    # ── INVOICE LIST UI ──────────────────────────────────────────

    def _build_list_ui(self, layout: QVBoxLayout):
        header = QLabel("Invoice List")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # Search
        search_layout = QHBoxLayout()
        self.list_search = QLineEdit()
        self.list_search.setPlaceholderText("Search by invoice no, customer name, or mobile...")
        self.list_search.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.list_search.textChanged.connect(self._search_invoices)
        search_layout.addWidget(self.list_search, 1)

        self.list_date_from = QDateEdit()
        self.list_date_from.setCalendarPopup(True)
        self.list_date_from.setDate(date(date.today().year, date.today().month, 1))
        self.list_date_from.setStyleSheet("padding: 4px 8px;")
        search_layout.addWidget(QLabel("From:"))
        search_layout.addWidget(self.list_date_from)

        self.list_date_to = QDateEdit()
        self.list_date_to.setCalendarPopup(True)
        self.list_date_to.setDate(date.today())
        self.list_date_to.setStyleSheet("padding: 4px 8px;")
        search_layout.addWidget(QLabel("To:"))
        search_layout.addWidget(self.list_date_to)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._search_invoices)
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)
        layout.addSpacing(12)

        # Table
        self.list_table = QTableWidget()
        self.list_table.setColumnCount(7)
        self.list_table.setHorizontalHeaderLabels(
            ["Invoice #", "Customer", "Date", "Amount", "GST", "Status", ""]
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
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Interactive)
        header.resizeSection(0, 120)
        header.resizeSection(2, 90)
        header.resizeSection(3, 105)
        header.resizeSection(4, 55)
        header.resizeSection(5, 60)
        header.resizeSection(6, 195)
        layout.addWidget(self.list_table)

        self._search_invoices()

    def _search_invoices(self):
        query = self.list_search.text()
        date_from = self.list_date_from.date().toString("yyyy-MM-dd")
        date_to = self.list_date_to.date().toString("yyyy-MM-dd")
        invoices = search_invoices(query, date_from, date_to)

        self.list_table.setRowCount(0)
        for inv in invoices:
            row = self.list_table.rowCount()
            self.list_table.insertRow(row)
            self.list_table.setItem(row, 0, QTableWidgetItem(inv["invoice_no"]))
            self.list_table.setItem(row, 1, QTableWidgetItem(inv["customer_name"]))
            self.list_table.setItem(row, 2, QTableWidgetItem(inv["invoice_date"]))
            self.list_table.setItem(row, 3, QTableWidgetItem(f"₹ {inv['grand_total']:,.2f}"))
            self.list_table.setItem(row, 4, QTableWidgetItem(f"{inv['gst_rate']}%"))
            self.list_table.setItem(row, 5, QTableWidgetItem(inv["status"].title()))

            # Actions
            action_w = QWidget()
            al = QHBoxLayout(action_w)
            al.setContentsMargins(2, 2, 2, 2)
            al.setSpacing(4)

            inv_id = inv["id"]
            view_btn = QPushButton("View")
            view_btn.setFixedSize(50, 26)
            view_btn.setStyleSheet("background: #3f51b5; color: white; border: none; border-radius: 3px;")
            view_btn.clicked.connect(lambda checked, iid=inv_id: self._view_invoice(iid))
            al.addWidget(view_btn)

            if inv["status"] == "active":
                dc_btn = QPushButton("DC")
                dc_btn.setFixedSize(36, 26)
                dc_btn.setStyleSheet("background: #4caf50; color: white; border: none; border-radius: 3px;")
                dc_btn.clicked.connect(lambda checked, iid=inv_id: self._create_dc_from_invoice(iid))
                al.addWidget(dc_btn)

                rc_btn = QPushButton("RC")
                rc_btn.setFixedSize(36, 26)
                rc_btn.setStyleSheet("background: #ff9800; color: white; border: none; border-radius: 3px;")
                rc_btn.clicked.connect(lambda checked, iid=inv_id: self._create_receipt_from_invoice(iid))
                al.addWidget(rc_btn)

                cancel_btn = QPushButton("Cancel")
                cancel_btn.setFixedSize(55, 26)
                cancel_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
                cancel_btn.clicked.connect(lambda checked, iid=inv_id: self._cancel_invoice(iid))
                al.addWidget(cancel_btn)

            self.list_table.setCellWidget(row, 6, action_w)

    def _view_invoice(self, invoice_id: int):
        try:
            path = generate_invoice_pdf(invoice_id)
            open_pdf(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _cancel_invoice(self, invoice_id: int):
        ok = QMessageBox.question(
            self, "Confirm", "Cancel this invoice?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok == QMessageBox.Yes:
            cancel_invoice(invoice_id)
            self._search_invoices()

    def _create_dc_from_invoice(self, invoice_id: int):
        from ui.delivery_challan_window import CreateDeliveryChallanDialog
        dialog = CreateDeliveryChallanDialog(self)
        # Pre-select the invoice in the dialog
        dialog.inv_search_input.setText("")
        # Find and select this invoice in the combo
        for i in range(dialog.inv_combo.count()):
            if dialog.inv_combo.itemData(i) == invoice_id:
                dialog.inv_combo.setCurrentIndex(i)
                break
        if dialog.exec() == QDialog.Accepted:
            self._search_invoices()

    def _create_receipt_from_invoice(self, invoice_id: int):
        from ui.receipt_window import CreateReceiptDialog
        dialog = CreateReceiptDialog(self)
        dialog.inv_search_input.setText("")
        for i in range(dialog.inv_combo.count()):
            if dialog.inv_combo.itemData(i) == invoice_id:
                dialog.inv_combo.setCurrentIndex(i)
                break
        if dialog.exec() == QDialog.Accepted:
            self._search_invoices()

    def refresh_list(self):
        self._search_invoices()
