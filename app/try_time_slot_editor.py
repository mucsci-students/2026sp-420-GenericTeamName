import sys
from PyQt6.QtWidgets import QApplication
from app.time_slot_editor import TimeSlotEditor

app = QApplication(sys.argv)
window = TimeSlotEditor()
window.show()
sys.exit(app.exec())