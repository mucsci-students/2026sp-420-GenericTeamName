"""
toast.py
================
Brief non-blocking status messages anchored near the bottom center of a host widget.
:date: 05/03/2026
:author: Shane del Villar
:class: CMSC 420
================
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QWidget


def show_toast(host: QWidget, message: str, duration_ms: int = 2600) -> None:
    """host should be MainWindow centralWidget so the toast reads over schedule content."""
    if host is None or not message.strip():
        return

    toast = QLabel(message.strip(), host)
    toast.setObjectName("toastLabel")
    toast.setWordWrap(True)
    toast.setMaximumWidth(min(560, host.width() - 40))
    toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
    toast.adjustSize()
    toast.setStyleSheet(
        """
        QLabel#toastLabel {
            background-color: rgba(30, 41, 59, 0.93);
            color: #f8fafc;
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 13px;
        }
        """
    )

    cw = host.width()
    ch = host.height()
    mw = toast.width()
    mh = toast.height()
    left = max(12, (cw - mw) // 2)
    edge = 32 if ch <= 820 else 44
    top = max(12, ch - mh - edge)

    toast.move(left, top)
    toast.raise_()
    toast.show()

    QTimer.singleShot(duration_ms, toast.deleteLater)
