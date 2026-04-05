import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize
from PyQt6.QtGui import QPixmap, QIcon

# ================= IMPORT DES INTERFACES =================
from GUI.dashboard import SimplePage

try:
    from GUI.alerte import AlertInterface
except:
    AlertInterface = QWidget

try:
    from GUI.traficreseaux import TrafficAnalyzerInterface
except:
    TrafficAnalyzerInterface = QWidget

try:
    from GUI.configuration import InterfaceParametresIDS

    ConfigurationPage = InterfaceParametresIDS
except:
    ConfigurationPage = QWidget

try:
    from GUI.Rapport import RapportInterface
except:
    RapportInterface = QWidget

try:
    from GUI.ML import DetectionConfidenceWidget

    MLInterface = DetectionConfidenceWidget
except:
    MLInterface = QWidget


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IDS - Système de Détection d'Intrusion")

        # Obtenir la taille de l'écran
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Prendre tout l'écran disponible
        self.setGeometry(screen_geometry)

        # Layout principal sans marges
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ================= SIDEBAR =================
        self.sidebar = QFrame()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border-right: 1px solid #335889;
            }
        """)

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 10, 5, 10)
        self.sidebar_layout.setSpacing(5)

        # Toggle button
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                color: white; 
                font-size: 20px; 
                border: none;
                padding: 8px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3A5FA0;
                border-radius: 8px;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(self.toggle_btn)

        # Title
        title = QLabel("🛡️ IDS MENU")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #335889; max-height: 1px;")
        self.sidebar_layout.addWidget(separator)

        # ================= STACK =================
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("""
            QStackedWidget {
                background-color: #1E2E4F;
            }
        """)

        # ================= PAGES =================
        print("📱 Chargement des interfaces...")

        self.dashboard_page = SimplePage()
        self.alert_page = AlertInterface()
        self.traffic_page = TrafficAnalyzerInterface()
        self.ml_page = MLInterface()
        self.config_page = ConfigurationPage()
        self.report_page = RapportInterface()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.alert_page)
        self.stack.addWidget(self.traffic_page)
        self.stack.addWidget(self.ml_page)
        self.stack.addWidget(self.config_page)
        self.stack.addWidget(self.report_page)

        # Menu items
        menu_items = [
            ("dashboard.png", "📊 Dashboard", lambda: self.stack.setCurrentWidget(self.dashboard_page)),
            ("alert.png", "⚠️ Alertes", lambda: self.stack.setCurrentWidget(self.alert_page)),
            ("analysee.png", "📈 Analyse", lambda: self.stack.setCurrentWidget(self.traffic_page)),
            ("ml.png", "🤖 ML", lambda: self.stack.setCurrentWidget(self.ml_page)),
            ("para.png", "⚙️ Paramètres", lambda: self.stack.setCurrentWidget(self.config_page)),
            ("report.png", "📄 Rapports", lambda: self.stack.setCurrentWidget(self.report_page)),
        ]

        for image_name, text, callback in menu_items:
            btn = self.create_menu_button(image_name, text, callback)
            self.sidebar_layout.addWidget(btn)

        self.sidebar_layout.addStretch()

        # Version
        version_label = QLabel("v1.0 | IDS")
        version_label.setStyleSheet("color: #8899AA; font-size: 10px; padding: 10px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(version_label)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stack, 1)

        self.stack.setCurrentWidget(self.dashboard_page)

        print("✅ Interface principale chargée")

    def create_menu_button(self, image_name, text, callback):
        btn = QPushButton(f"  {text}")
        btn.setMinimumHeight(40)

        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                padding: 8px 12px;
                text-align: left;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3A5FA0;
            }
            QPushButton:pressed {
                background-color: #253456;
            }
        """)

        icon_size = 22
        try:
            pixmap = QPixmap(image_name)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    icon_size, icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                icon = QIcon()
                icon.addPixmap(scaled_pixmap)
                btn.setIcon(icon)
                btn.setIconSize(QSize(icon_size, icon_size))
        except:
            pass

        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(callback)

        return btn

    def toggle_sidebar(self):
        current_width = self.sidebar.width()
        new_width = 70 if current_width > 100 else 200

        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(300)
        self.anim.setStartValue(current_width)
        self.anim.setEndValue(new_width)

        self.anim2 = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.anim2.setDuration(300)
        self.anim2.setStartValue(current_width)
        self.anim2.setEndValue(new_width)

        self.anim.start()
        self.anim2.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())