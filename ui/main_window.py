"""Main application window with sidebar navigation."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QSizePolicy, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QAction

from invoice import get_dashboard_data
from database import backup_database, close
from ui.customer_window import CustomerWindow
from ui.invoice_window import InvoiceWindow
from ui.delivery_challan_window import DeliveryChallanWindow
from ui.receipt_window import ReceiptWindow
from ui.reports_window import ReportsWindow
from settings import get_company, save_company, get_db_setting, set_db_setting


class SidebarButton(QPushButton):
    def __init__(self, text: str, page_index: int, parent=None):
        super().__init__(text, parent)
        self.page_index = page_index
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 20px;
                border: none;
                border-radius: 0;
                background: transparent;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background: #2a3a5c;
            }
            QPushButton:checked {
                background: #3f51b5;
                color: white;
                font-weight: bold;
            }
        """)


class CardWidget(QFrame):
    """Simple info card with title and value."""
    def __init__(self, title: str, value: str, color: str = "#3f51b5", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            CardWidget {{
                background: white;
                border-radius: 8px;
                border-left: 4px solid {color};
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 9))
        self.title_label.setStyleSheet("color: #757575;")
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S.S. Blue Metal")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background: #1a237e;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App title in sidebar
        title_label = QLabel("🏗️  S.S. BLUE METAL")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: white; padding: 20px 16px;")
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #3f51b5; max-height: 1px;")
        sidebar_layout.addWidget(sep)

        # Navigation buttons (inside scroll area)
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setStyleSheet("QScrollArea { background: transparent; }"
                                 "QScrollBar:vertical { width: 4px; background: transparent; }"
                                 "QScrollBar::handle:vertical { background: #3f51b5; border-radius: 2px; }"
                                 "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.nav_buttons = []
        nav_items = [
            ("📊  Dashboard", 0),
            ("👤  Customers", 1),
            ("📦  Products", 2),
            ("🧾  New Invoice", 3),
            ("📋  Invoice List", 4),
            ("📊  Reports", 5),
            ("⚙️  Settings", 6),
            ("🚚  Delivery Challans", 7),
            ("🧾  Receipts", 8),
        ]
        self._nav_group = []
        for text, idx in nav_items:
            btn = SidebarButton(text, idx)
            btn.clicked.connect(self._on_nav_click)
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        nav_scroll.setWidget(nav_container)
        sidebar_layout.addWidget(nav_scroll, 1)

        # Backup button at bottom
        backup_btn = QPushButton("💾  Backup DB")
        backup_btn.setFixedHeight(44)
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.setFont(QFont("Segoe UI", 10))
        backup_btn.setStyleSheet("""
            QPushButton {
                text-align: left; padding: 10px 20px;
                border: none; border-radius: 0;
                background: transparent; color: #e0e0e0;
            }
            QPushButton:hover { background: #2a3a5c; }
        """)
        backup_btn.clicked.connect(self._backup_db)
        sidebar_layout.addWidget(backup_btn)

        main_layout.addWidget(sidebar)

        # ── Content Area ──
        content_frame = QFrame()
        content_frame.setStyleSheet("background: #f5f5f5;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        # Add pages in index order 0-9 to match sidebar nav indices
        self.dashboard_widget = self._build_dashboard()
        self.stack.addWidget(self.dashboard_widget)         # 0

        self.customer_window = CustomerWindow()
        self.stack.addWidget(self.customer_window)          # 1

        self.products_widget = self._build_products_page()
        self.stack.addWidget(self.products_widget)          # 2

        self.invoice_window = InvoiceWindow()
        self.stack.addWidget(self.invoice_window)           # 3

        self.invoice_list_window = InvoiceWindow(list_mode=True)
        self.stack.addWidget(self.invoice_list_window)      # 4

        self.reports_window = ReportsWindow()
        self.stack.addWidget(self.reports_window)           # 5

        self.settings_widget = self._build_settings_page()
        self.stack.addWidget(self.settings_widget)          # 6

        self.delivery_challan_window = DeliveryChallanWindow()
        self.stack.addWidget(self.delivery_challan_window)  # 7

        self.receipt_window = ReceiptWindow()
        self.stack.addWidget(self.receipt_window)           # 8

        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_frame, 1)

        # Default to dashboard
        self.nav_buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)

    def _on_nav_click(self):
        btn = self.sender()
        for b in self.nav_buttons:
            b.setChecked(b is btn)
        self.stack.setCurrentIndex(btn.page_index)

        # Refresh the page content if applicable
        if btn.page_index == 0:
            self._refresh_dashboard()
        elif btn.page_index == 3:
            self.invoice_window.refresh_for_new()
        elif btn.page_index == 4:
            self.invoice_list_window.refresh_list()
        elif btn.page_index == 5:
            self.reports_window.refresh()
        elif btn.page_index == 7:
            self.delivery_challan_window.refresh_list()
        elif btn.page_index == 8:
            self.receipt_window.refresh_list()

    # ── Dashboard ────────────────────────────────────────────────

    def _build_dashboard(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Dashboard")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(16)

        # Cards grid
        self.dash_cards = {}
        card_grid = QGridLayout()
        card_grid.setSpacing(16)

        cards_data = [
            ("today_sales", "Today's Sales", "₹ 0", "#4caf50"),
            ("total_customers", "Total Customers", "0", "#2196f3"),
            ("total_products", "Products", "0", "#ff9800"),
            ("total_invoices", "Invoices", "0", "#9c27b0"),
        ]
        for i, (key, title, val, color) in enumerate(cards_data):
            card = CardWidget(title, val, color)
            card_grid.addWidget(card, i // 2, i % 2)
            self.dash_cards[key] = card.value_label

        layout.addLayout(card_grid)
        layout.addSpacing(24)

        # Recent invoices
        recent_label = QLabel("Recent Invoices")
        recent_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(recent_label)
        layout.addSpacing(8)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(
            ["Invoice #", "Customer", "Date", "Amount", "Status"]
        )
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.verticalHeader().setDefaultSectionSize(40)
        self.recent_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.recent_table)

        return w

    def _refresh_dashboard(self):
        data = get_dashboard_data()
        self.dash_cards["today_sales"].setText(f"₹ {data['today_sales']:,.2f}")
        self.dash_cards["total_customers"].setText(str(data["total_customers"]))
        self.dash_cards["total_products"].setText(str(data["total_products"]))
        self.dash_cards["total_invoices"].setText(str(data["total_invoices"]))

        self.recent_table.setRowCount(0)
        for inv in data["recent_invoices"]:
            row = self.recent_table.rowCount()
            self.recent_table.insertRow(row)
            self.recent_table.setItem(row, 0, QTableWidgetItem(inv["invoice_no"]))
            self.recent_table.setItem(row, 1, QTableWidgetItem(inv["customer_name"]))
            self.recent_table.setItem(row, 2, QTableWidgetItem(inv["invoice_date"]))
            self.recent_table.setItem(row, 3, QTableWidgetItem(f"₹ {inv['grand_total']:,.2f}"))
            self.recent_table.setItem(row, 4, QTableWidgetItem("Active"))

    # ── Products Page ────────────────────────────────────────────

    def _build_products_page(self):
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QDialogButtonBox,
        )
        from product import search_products, add_product, update_product, delete_product

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Products / Materials")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("Search products...")
        self.prod_search.setFixedWidth(300)
        self.prod_search.setStyleSheet("padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;")
        self.prod_search.textChanged.connect(self._refresh_products)
        toolbar.addWidget(self.prod_search)

        toolbar.addStretch()

        add_btn = QPushButton("+ Add Product")
        add_btn.setStyleSheet("""
            QPushButton { background: #4caf50; color: white; padding: 8px 20px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #388e3c; }
        """)
        add_btn.clicked.connect(lambda: self._product_dialog())
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)
        layout.addSpacing(12)

        self.prod_table = QTableWidget()
        self.prod_table.setColumnCount(7)
        self.prod_table.setHorizontalHeaderLabels(
            ["ID", "Name", "Description", "Unit", "HSN Code", "Rate (₹)", ""]
        )
        self.prod_table.setAlternatingRowColors(True)
        self.prod_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prod_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prod_table.verticalHeader().setVisible(False)
        self.prod_table.verticalHeader().setDefaultSectionSize(44)
        self.prod_table.setColumnHidden(0, True)
        self.prod_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e0e0e0; border-radius: 4px; }
            QHeaderView::section { background: #3f51b5; color: white; padding: 6px; font-weight: bold; }
            QTableWidget::item { padding: 4px; }
        """)
        self.prod_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.prod_table)

        self._refresh_products()
        return w

    def _refresh_products(self):
        from product import search_products, delete_product
        query = self.prod_search.text()
        products = search_products(query)
        self.prod_table.setRowCount(0)
        for p in products:
            row = self.prod_table.rowCount()
            self.prod_table.insertRow(row)
            self.prod_table.setItem(row, 0, QTableWidgetItem(str(p["id"])))
            self.prod_table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.prod_table.setItem(row, 2, QTableWidgetItem(p.get("description", "")))
            self.prod_table.setItem(row, 3, QTableWidgetItem(p.get("unit", "")))
            self.prod_table.setItem(row, 4, QTableWidgetItem(p.get("hsn_code", "")))
            self.prod_table.setItem(row, 5, QTableWidgetItem(f"{p['rate']:.2f}"))

            # Action buttons
            action_w = QWidget()
            action_layout = QHBoxLayout(action_w)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(50, 26)
            edit_btn.setStyleSheet("background: #2196f3; color: white; border: none; border-radius: 3px;")
            pid = p["id"]
            edit_btn.clicked.connect(lambda checked, pid=pid: self._product_dialog(pid))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Del")
            del_btn.setFixedSize(50, 26)
            del_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 3px;")
            del_btn.clicked.connect(lambda checked, pid=pid: self._delete_product(pid))
            action_layout.addWidget(del_btn)

            self.prod_table.setCellWidget(row, 6, action_w)

    def _product_dialog(self, product_id: int = 0):
        from PySide6.QtWidgets import QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QDialogButtonBox, QLineEdit, QTextEdit
        from product import get_product, add_product, update_product

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Product" if product_id else "Add Product")
        dialog.setMinimumWidth(450)

        form = QFormLayout(dialog)
        form.setSpacing(12)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., 20mm Blue Metal")
        form.addRow("Product Name:", name_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("Optional description")
        form.addRow("Description:", desc_edit)

        unit_combo = QComboBox()
        unit_combo.addItems(["Ton", "Kg", "Cubic Feet", "Load", "Unit", "Litre"])
        form.addRow("Unit:", unit_combo)

        hsn_edit = QLineEdit()
        hsn_edit.setPlaceholderText("e.g., 2517")
        form.addRow("HSN Code:", hsn_edit)

        rate_spin = QDoubleSpinBox()
        rate_spin.setRange(0, 999999)
        rate_spin.setDecimals(2)
        rate_spin.setPrefix("₹ ")
        rate_spin.setFixedWidth(200)
        form.addRow("Rate:", rate_spin)

        if product_id:
            p = get_product(product_id)
            if p:
                name_edit.setText(p["name"])
                desc_edit.setText(p.get("description", ""))
                idx = unit_combo.findText(p.get("unit", "Ton"))
                if idx >= 0:
                    unit_combo.setCurrentIndex(idx)
                hsn_edit.setText(p.get("hsn_code", ""))
                rate_spin.setValue(p["rate"])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(dialog, "Error", "Product name is required.")
                return
            if product_id:
                update_product(product_id, name, unit_combo.currentText(),
                               rate_spin.value(), desc_edit.text(), hsn_edit.text())
            else:
                add_product(name, unit_combo.currentText(), rate_spin.value(),
                            desc_edit.text(), hsn_edit.text())
            self._refresh_products()

    def _delete_product(self, product_id: int):
        from product import delete_product
        ok = QMessageBox.question(self, "Confirm", "Delete this product?",
                                  QMessageBox.Yes | QMessageBox.No)
        if ok == QMessageBox.Yes:
            delete_product(product_id)
            self._refresh_products()

    # ── Settings Page ────────────────────────────────────────────

    def _build_settings_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Company Settings")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)
        layout.addSpacing(16)

        from PySide6.QtWidgets import QFormLayout, QLineEdit, QTextEdit, QGroupBox, QPushButton, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        company = get_company()

        self.settings_fields = {}
        self.settings_db_fields = {}  # fields stored in settings table (not company)
        fields = [
            ("address", "Address", lambda: QTextEdit()),
            ("gstin", "GSTIN", QLineEdit),
            ("phone", "Phone", QLineEdit),
            ("email", "Email", QLineEdit),
            ("website", "Website", QLineEdit),
            ("pan", "PAN", QLineEdit),
            ("bank_name", "Bank Name", QLineEdit),
            ("bank_account", "Account Number", QLineEdit),
            ("bank_ifsc", "IFSC Code", QLineEdit),
            ("invoice_prefix", "Invoice Prefix", QLineEdit),
            ("footer_line1", "Footer Line 1", QLineEdit),
            ("footer_line2", "Footer Line 2", QLineEdit),
        ]

        for key, label, widget_type in fields:
            wgt = widget_type()
            if isinstance(wgt, QTextEdit):
                wgt.setFixedHeight(60)
            elif isinstance(wgt, QLineEdit):
                wgt.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;")
            form.addRow(f"{label}:", wgt)
            if key in company:
                val = company[key] or ""
                if isinstance(wgt, QTextEdit):
                    wgt.setPlainText(val)
                else:
                    wgt.setText(val)
            self.settings_fields[key] = wgt

        # Terms & Conditions (stored in settings table, editable)
        form.addRow("", QLabel(""))  # spacer
        terms_label = QLabel("Terms & Conditions (for invoice print):")
        terms_label.setStyleSheet("font-weight: bold; color: #1a237e; margin-top: 8px;")
        form.addRow(terms_label)
        self.terms_edit = QTextEdit()
        self.terms_edit.setFixedHeight(100)
        self.terms_edit.setStyleSheet("padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 9pt;")
        self.terms_edit.setPlainText(get_db_setting("terms",
            "1. All disputes subject to Coimbatore jurisdiction.\n"
            "2. Payment due within 15 days from invoice date.\n"
            "3. Interest @ 18% p.a. charged on overdue payments.\n"
            "4. Goods once sold will not be taken back."))
        form.addRow("Terms:", self.terms_edit)

        form.addRow("", QLabel(""))  # spacer

        save_btn = QPushButton("💾  Save Settings")
        save_btn.setStyleSheet("""
            QPushButton { background: #3f51b5; color: white; padding: 10px 30px;
                          border: none; border-radius: 4px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #303f9f; }
        """)
        save_btn.clicked.connect(self._save_settings)
        form.addRow(save_btn)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        return w

    def _save_settings(self):
        data = {}
        for key, wgt in self.settings_fields.items():
            if isinstance(wgt, QTextEdit):
                data[key] = wgt.toPlainText()
            else:
                data[key] = wgt.text()
        save_company(data)
        # Save terms to settings table
        set_db_setting("terms", self.terms_edit.toPlainText())
        QMessageBox.information(self, "Saved", "Company settings saved successfully.")

    # ── Backup ───────────────────────────────────────────────────

    def _backup_db(self):
        try:
            path = backup_database()
            QMessageBox.information(self, "Backup Complete", f"Database backed up to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    # ── Override close ───────────────────────────────────────────

    def closeEvent(self, event):
        close()
        event.accept()
