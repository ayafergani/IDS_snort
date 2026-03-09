from GUI.configuration import InterfaceParametresIDS
from snort_module.rules import fetch_rules_from_db
from PyQt6.QtWidgets import QApplication

app = QApplication([])
window = InterfaceParametresIDS()
window.show()

fetch_rules_from_db(window)
app.exec()