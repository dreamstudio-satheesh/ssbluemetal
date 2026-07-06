"""Blank Invoice page — prints a blank form for handwritten use."""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QMessageBox, QGroupBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from database import get_next_invoice_no
from printer import generate_blank_invoice_pdf, open_pdf
from settings import get_company


class BlankInvoiceWindow(QWidget):
    """Simple page that prints a blank invoice form for handwriting."""

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Blank Invoice")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)

        subtitle = QLabel("Print a blank invoice form for handwritten use")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #757575;")
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        # Info card
        info_card = QGroupBox()
        info_card.setStyleSheet("""
            QGroupBox {
                background: #e8eaf6;
                border: 1px solid #c5cae9;
                border-radius: 6px;
                padding: 16px;
                font-size: 10pt;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_label = QLabel(
            "This page prints a blank invoice form with your company letterhead.\n"
            "No data is saved to the database. You can fill in customer details,\n"
            "items, and amounts by hand after printing."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #1a237e; font-size: 10pt;")
        info_layout.addWidget(info_label)
        layout.addWidget(info_card)
        layout.addSpacing(20)

        # Form fields
        form_group = QGroupBox("Invoice Details")
        form_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 11pt; color: #1a237e;
                border: 1px solid #e0e0e0; border-radius: 6px;
                margin-top: 12px; padding: 20px 16px 16px 16px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 10px;
                background: white;
            }
        """)
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(12)

        # Invoice no row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Invoice No:"))
        self.inv_no_label = QLabel()
        self.inv_no_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.inv_no_label.setStyleSheet("color: #1a237e;")
        row1.addWidget(self.inv_no_label)
        row1.addStretch()
        form_layout.addLayout(row1)

        # Date row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setFixedWidth(180)
        self.date_edit.setStyleSheet("padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px;")
        row2.addWidget(self.date_edit)
        row2.addStretch()
        form_layout.addLayout(row2)

        layout.addWidget(form_group)
        layout.addSpacing(20)

        # Print button
        btn_layout = QHBoxLayout()
        print_btn = QPushButton("🖨️  Print Blank Invoice")
        print_btn.setFixedHeight(48)
        print_btn.setMinimumWidth(280)
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.setStyleSheet("""
            QPushButton {
                background: #ff9800; color: white; padding: 10px 30px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #f57c00; }
        """)
        print_btn.clicked.connect(self._print_blank)
        btn_layout.addWidget(print_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def refresh_for_new(self):
        """Called when navigating to this page — refresh the invoice number."""
        try:
            next_no = get_next_invoice_no()
        except Exception:
            next_no = "—"
        self.inv_no_label.setText(next_no)

    def _print_blank(self):
        """Generate and open the blank invoice PDF."""
        inv_no = self.inv_no_label.text()
        inv_date = self.date_edit.date().toString("yyyy-MM-dd")

        try:
            pdf_path = generate_blank_invoice_pdf(
                invoice_no=inv_no,
                invoice_date=inv_date,
            )
            open_pdf(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")
