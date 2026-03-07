import sys
from PyQt6.QtWidgets import (
    QApplication, QPushButton, QWidget, QVBoxLayout, QLabel,
    QFrame, QGridLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QRect, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup,
    pyqtProperty, QTimer
)
from PyQt6.QtGui import QPalette, QColor, QPixmap


# ================= ANIMATED LABEL =================
class AnimatedLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self._scale = 0.25
        self.update_style()

    def getScale(self):
        return self._scale

    def setScale(self, value):
        self._scale = value
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                color: #9b59b6;
                font-size: {int(28 * self._scale)}px;
                font-weight: bold;
                font-style: italic;
                font-family: 'Segoe UI';
                padding: 20px;
                background-color: none;
                border-radius: 15px;
            }}
        """)

    scale = pyqtProperty(float, getScale, setScale)


# ================= FRAME AVEC EFFET DE FOCUS =================
class FocusableFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animation pour le focus
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor("#9b59b6"))
        self.shadow_effect.setOffset(0, 0)
        self.shadow_effect.setEnabled(False)
        
        self.setGraphicsEffect(self.shadow_effect)
        
        # Animation pour l'effet de focus
        self.focus_anim = QPropertyAnimation(self.shadow_effect, b"blurRadius")
        self.focus_anim.setDuration(150)
        self.focus_anim.setStartValue(20)
        self.focus_anim.setEndValue(30)
        self.focus_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Timer pour retirer le focus automatiquement
        self.focus_timer = QTimer()
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self.remove_focus)
        
        # Animation de clic
        self.click_anim = QPropertyAnimation(self, b"geometry")
        self.click_anim.setDuration(200)
        self.click_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
    def mousePressEvent(self, event):
        # Animation de clic
        rect = self.geometry()
        smaller = rect.adjusted(3, 3, -3, -3)
        normal = rect
        
        self.click_anim.setStartValue(smaller)
        self.click_anim.setKeyValueAt(0.3, normal)
        self.click_anim.setEndValue(normal)
        self.click_anim.start()
        
        # Appliquer l'effet de focus UNIQUEMENT pour ce cadre
        self.apply_focus()
        
        # Empêcher la propagation de l'événement à d'autres widgets
        event.accept()
        
    def apply_focus(self):
        # Activer l'ombre et l'animer immédiatement
        self.shadow_effect.setEnabled(True)
        
        # Animation plus rapide pour l'ombre
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self.focus_anim.start()
        
        # Ajouter une bordure de focus
        current_style = self.styleSheet()
        self.setStyleSheet(current_style + """
            QFrame {
                border: 2px solid rgba(155, 89, 182, 0.8);
            }
        """)
        
        # Timer pour retirer le focus après 1 seconde
        self.focus_timer.start(1000)
        
    def remove_focus(self):
        # Désactiver l'ombre progressivement
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.focus_anim.start()
        
        # Restaurer le style original
        QTimer.singleShot(150, self.restore_style)
        
    def restore_style(self):
        # Restaurer le style sans bordure
        current_style = self.styleSheet()
        base_style = current_style.replace("border: 2px solid rgba(155, 89, 182, 0.8);", "")
        self.setStyleSheet(base_style)
        self.shadow_effect.setEnabled(False)


# ================= MAIN WINDOW =================
class SimplePage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Intrusion Detection System")

        screen = QApplication.primaryScreen()
        size = screen.size()

        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height())

        # Background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1E2E4F"))
        self.setPalette(palette)

        # ================= LEFT MENU =================
        menu_width = int(size.width() * 0.18)
        menu_height = size.height() - 20

        self.left_menu = QFrame(self)
        self.left_menu.setGeometry(10, 10, menu_width, menu_height)
        self.left_menu.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border: none;
                padding: 15px;
            }
        """)

        menu_layout = QVBoxLayout(self.left_menu)
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Essayez de charger l'image, mais ne plantez pas si elle n'existe pas
        try:
            pixmap = QPixmap("ids1.png")
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo_label.setPixmap(scaled_pixmap)
        except:
            pass  # Ignorer si l'image n'existe pas

        logo_label.setFixedSize(190, 120)
        logo_label.setStyleSheet("""
            QLabel {
                border-radius: 60px;
                background-color: #1E2E4F;
                border: 3px solid #31487A;
            }
        """)

        menu_layout.addWidget(logo_label)

        menu_title = QLabel("IDS DETECTION")
        menu_title.setStyleSheet("""
            color: #9b59b6;
            font-size: 20px;
            font-weight: bold;
        """)
        menu_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(menu_title)

        buttons_info = [
            ("📊", "Dashboard"),
            ("⚠️", "Alertes"),
            ("🔍", "Analyse du Trafic"),
            ("🤖", "Machine Learning"),
            ("⚙️", "Paramètres"),
            ("📈", "Rapports")
        ]
        for icon, text in buttons_info:
            btn = self.create_menu_button(icon, text)
            menu_layout.addWidget(btn)

        menu_layout.addStretch()

        # ================= MAIN FRAME =================
        cadre_width = int(size.width() * 0.8)
        cadre_height = size.height() - 87

        self.cadre = QFrame(self)
        self.cadre.setGeometry(size.width() - cadre_width - 5, 4, cadre_width, cadre_height)
        self.cadre.setStyleSheet("""
            QFrame {
                background-color: #335889;
                border-radius: 30px;
                padding: 20px;
            }
        """)

        main_layout = QVBoxLayout(self.cadre)

        # ================= TITLE =================
        self.title = AnimatedLabel("Intrusion Detection System (IDS)")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title)

        # Opacity effect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.title.setGraphicsEffect(self.opacity_effect)

        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(2000)
        self.opacity_anim.setKeyValueAt(0, 0.5)
        self.opacity_anim.setKeyValueAt(0.5, 1)
        self.opacity_anim.setKeyValueAt(1, 0.5)
        self.opacity_anim.setLoopCount(-1)

        # Scale animation
        self.scale_anim = QPropertyAnimation(self.title, b"scale")
        self.scale_anim.setDuration(2000)
        self.scale_anim.setKeyValueAt(0, 0.95)
        self.scale_anim.setKeyValueAt(0.5, 1.0)
        self.scale_anim.setKeyValueAt(1, 0.95)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.scale_anim.setLoopCount(-1)

        # Group animation
        self.group = QParallelAnimationGroup()
        self.group.addAnimation(self.opacity_anim)
        self.group.addAnimation(self.scale_anim)
        self.group.start()

        # ================= GRID AVEC 4 CADRES =================
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # Création des 4 cadres avec focus
        self.cadre1 = self.create_inner_frame("Nombre total de paquets analysés", "50 paquets")
        self.cadre2 = self.create_inner_frame("Nombre d'attaques détectées", "23 attaques\n+3 dernière heure")
        self.cadre3 = self.create_inner_frame("Niveau de risque global", "75%\n🔴 Élevé")
        self.cadre4 = self.create_inner_frame("Graphique trafic en temps réel", "")

        grid_layout.addWidget(self.cadre1, 0, 0)
        grid_layout.addWidget(self.cadre2, 0, 1)
        grid_layout.addWidget(self.cadre3, 1, 0)
        grid_layout.addWidget(self.cadre4, 1, 1)

        main_layout.addLayout(grid_layout)

    # ================= MENU BUTTON =================
    def create_menu_button(self, icon, text):
        btn = QPushButton(f"  {icon}  {text}")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4166;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
                border-radius: 10px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #A7EBF2;
                color: #1E2E4F;
            }
        """)
        return btn

    # ================= INNER FRAME =================
    def create_inner_frame(self, title_text, content_text):
        # Utiliser la classe FocusableFrame pour les 4 cadres
        frame = FocusableFrame()
        
        frame.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border-radius: 20px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)

        title = QLabel(title_text)
        title.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            border-bottom: 2px solid #335889;
        """)
        layout.addWidget(title)

        content = QLabel(content_text)
        content.setStyleSheet("""
            color: white;
            font-size: 16px;
        """)
        content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)

        layout.addStretch()
        return frame


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimplePage()
    window.show()
    sys.exit(app.exec())