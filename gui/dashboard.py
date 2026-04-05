import sys
import os
from datetime import datetime, timedelta

# Ajouter le chemin parent pour pouvoir importer depuis data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QFrame, QGridLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QRect, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, pyqtProperty, QTimer, QSize
)
from PyQt6.QtGui import QPalette, QColor, QFont

# ================= IMPORTS MATPLOTLIB =================
import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Import du DatabaseManager
from data.dashboard import DatabaseManager


# ================= HISTOGRAMME =================
class TrafficHistogram(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(5.5, 3.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        self.ax.set_facecolor("#1E2E4F")
        self.fig.patch.set_facecolor("#1E2E4F")
        self.fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.18)

        # Ajustement: hauteur adaptable mais avec limites
        self.setMinimumHeight(250)
        self.setMaximumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.update_histogram([0] * 24)

    def update_histogram(self, data):
        self.ax.clear()
        self.ax.set_facecolor("#1E2E4F")

        heures = list(range(24))
        couleurs = ['#44FF44' if val == 0 else '#FF4444' for val in data]

        bars = self.ax.bar(heures, data, color=couleurs, width=0.65,
                          edgecolor='white', linewidth=0.5, alpha=0.9)

        self.ax.set_title("ÉTAT DU TRAFIC - 24 DERNIÈRES HEURES",
                          color="white", fontsize=11, fontweight='bold', pad=8)

        self.ax.set_xlabel("HEURES", color="white", fontsize=9, fontweight='bold', labelpad=5)
        self.ax.set_ylabel("STATUT", color="white", fontsize=9, fontweight='bold', labelpad=5)

        heures_labels = [f"{h:02d}h" for h in range(24)]
        indices_a_afficher = [0, 3, 6, 9, 12, 15, 18, 21, 23]
        heures_a_afficher = [heures_labels[i] for i in indices_a_afficher]

        self.ax.set_xticks(indices_a_afficher)
        self.ax.set_xticklabels(heures_a_afficher, color='white', fontsize=8, rotation=0)
        self.ax.tick_params(axis='y', colors='white', labelsize=8)

        self.ax.set_ylim(-0.1, 1.1)
        self.ax.set_yticks([0, 1])
        self.ax.set_yticklabels(['NORMAL', 'ATTAQUE'], fontsize=8, fontweight='bold')

        for tick in self.ax.get_yticklabels():
            if tick.get_text() == 'NORMAL':
                tick.set_color('#44FF44')
            else:
                tick.set_color('#FF4444')

        self.ax.grid(True, axis='y', alpha=0.2, linestyle='--', color='white', linewidth=0.5)

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#335889')
        self.ax.spines['bottom'].set_color('#335889')

        for i, (heure, val) in enumerate(zip(heures, data)):
            if val == 1:
                self.ax.text(heure, val + 0.05, '⚠️',
                           ha='center', va='bottom', fontsize=8)

        self.draw()


# ================= ANIMATED LABEL =================
class AnimatedLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self._scale = 0.35
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
                font-size: {int(32 * self._scale)}px;
                font-weight: bold;
                font-style: italic;
                font-family: 'Segoe UI';
                padding: 15px;
                background-color: none;
                border-radius: 15px;
            }}
        """)

    scale = pyqtProperty(float, getScale, setScale)


# ================= FRAME AVEC EFFET =================
class FocusableFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor("#9b59b6"))
        self.shadow_effect.setOffset(0, 0)
        self.shadow_effect.setEnabled(False)

        self.setGraphicsEffect(self.shadow_effect)

        self.focus_anim = QPropertyAnimation(self.shadow_effect, b"blurRadius")
        self.focus_anim.setDuration(150)
        self.focus_anim.setStartValue(20)
        self.focus_anim.setEndValue(30)
        self.focus_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.focus_timer = QTimer()
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self.remove_focus)

        self.click_anim = QPropertyAnimation(self, b"geometry")
        self.click_anim.setDuration(200)
        self.click_anim.setEasingCurve(QEasingCurve.Type.OutBack)

    def mousePressEvent(self, event):
        rect = self.geometry()
        smaller = rect.adjusted(3, 3, -3, -3)
        normal = rect

        self.click_anim.setStartValue(smaller)
        self.click_anim.setKeyValueAt(0.3, normal)
        self.click_anim.setEndValue(normal)
        self.click_anim.start()

        self.apply_focus()
        event.accept()

    def apply_focus(self):
        self.shadow_effect.setEnabled(True)
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self.focus_anim.start()

        current_style = self.styleSheet()
        self.setStyleSheet(current_style + """
            QFrame {
                border: 2px solid rgba(155, 89, 182, 0.8);
            }
        """)

        self.focus_timer.start(1000)

    def remove_focus(self):
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.focus_anim.start()
        QTimer.singleShot(150, self.restore_style)

    def restore_style(self):
        current_style = self.styleSheet()
        base_style = current_style.replace("border: 2px solid rgba(155, 89, 182, 0.8);", "")
        self.setStyleSheet(base_style)
        self.shadow_effect.setEnabled(False)


# ================= MAIN WINDOW =================
class SimplePage(QWidget):
    def __init__(self):
        super().__init__()

        # Initialisation du gestionnaire de base de données
        self.db_manager = DatabaseManager()

        # Initialisation des variables
        self.attack_stats = {'total_attacks': 0, 'last_hour_attacks': 0, 'severity_counts': {}}
        self.total_packets = 0
        self.risk_level = 0

        # Pas de titre de fenêtre (sera géré par main)
        # Pas de taille fixe - laisser le layout du main gérer
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1E2E4F"))
        self.setPalette(palette)

        # ================= MAIN FRAME =================
        self.cadre = QFrame()
        self.cadre.setStyleSheet("""
            QFrame {
                background-color: #335889;
                border-radius: 20px;
                padding: 20px;
            }
        """)

        main_layout_global = QVBoxLayout(self)
        main_layout_global.setContentsMargins(10, 10, 10, 10)
        main_layout_global.addWidget(self.cadre)

        main_layout = QVBoxLayout(self.cadre)
        main_layout.setSpacing(15)

        # ================= TITLE =================
        self.title = AnimatedLabel("TABLEAU DE BORD - SYSTÈME DE DÉTECTION D'INTRUSION")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.title.setGraphicsEffect(self.opacity_effect)

        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(2000)
        self.opacity_anim.setKeyValueAt(0, 0.5)
        self.opacity_anim.setKeyValueAt(0.5, 1)
        self.opacity_anim.setKeyValueAt(1, 0.5)
        self.opacity_anim.setLoopCount(-1)

        self.scale_anim = QPropertyAnimation(self.title, b"scale")
        self.scale_anim.setDuration(2000)
        self.scale_anim.setKeyValueAt(0, 0.95)
        self.scale_anim.setKeyValueAt(0.5, 1.0)
        self.scale_anim.setKeyValueAt(1, 0.95)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.scale_anim.setLoopCount(-1)

        self.group = QParallelAnimationGroup()
        self.group.addAnimation(self.opacity_anim)
        self.group.addAnimation(self.scale_anim)
        self.group.start()

        # ================= GRID AVEC 4 CADRES =================
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # Mise à jour des données initiales
        self.update_data_from_db()

        # Cadres 1, 2, 3 (identiques)
        self.cadre1 = self.create_inner_frame(
            "📊 NOMBRE TOTAL DE PAQUETS ANALYSÉS",
            self.format_packets_display()
        )

        self.cadre2 = self.create_inner_frame(
            "⚠️ NOMBRE D'ATTAQUES DÉTECTÉES",
            self.format_attacks_display()
        )

        self.cadre3 = self.create_inner_frame(
            "🎯 NIVEAU DE RISQUE GLOBAL",
            self.format_risk_display()
        )

        # ================= CADRE 4 AVEC HISTOGRAMME =================
        self.cadre4 = FocusableFrame()
        self.cadre4.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border-radius: 20px;
                padding: 15px;
                border: 2px solid #335889;
            }
        """)

        layout4 = QVBoxLayout(self.cadre4)
        layout4.setSpacing(10)
        layout4.setContentsMargins(10, 10, 10, 10)

        title4 = QLabel("📈 ÉTAT DU TRAFIC EN TEMPS RÉEL")
        title4.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            border-bottom: 2px solid #335889;
            padding-bottom: 8px;
        """)
        title4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout4.addWidget(title4)

        # Légende intégrée
        legend_widget = QWidget()
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setSpacing(20)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend_layout.setContentsMargins(0, 5, 0, 5)

        normal_label = QLabel("🟢 NORMAL (0)")
        normal_label.setStyleSheet("color: #44FF44; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(normal_label)

        attaque_label = QLabel("🔴 ATTAQUE (1)")
        attaque_label.setStyleSheet("color: #FF4444; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(attaque_label)

        layout4.addWidget(legend_widget)

        # Histogramme
        self.histogram = TrafficHistogram()
        layout4.addWidget(self.histogram)

        # Ajouter les cadres à la grille
        grid_layout.addWidget(self.cadre1, 0, 0)
        grid_layout.addWidget(self.cadre2, 0, 1)
        grid_layout.addWidget(self.cadre3, 1, 0)
        grid_layout.addWidget(self.cadre4, 1, 1)

        # Configuration des proportions
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        main_layout.addLayout(grid_layout)

        # Initialisation de l'histogramme
        hist_data = self.db_manager.get_attacks_last_24h()
        self.histogram.update_histogram(hist_data)

        # Timer pour rafraîchir
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_dashboard)
        self.update_timer.start(5000)

    def format_packets_display(self):
        if self.total_packets == 0:
            return "0 PAQUET\nAucune activité détectée"
        nombre = f"{self.total_packets:,}".replace(",", " ")
        return f"{nombre}\nPAQUETS ANALYSÉS"

    def format_attacks_display(self):
        total = self.attack_stats['total_attacks']
        last_hour = self.attack_stats['last_hour_attacks']

        if total == 0:
            return "0 ATTAQUE\n✅ Système sécurisé"

        severity = self.attack_stats['severity_counts']
        text = f"{total} ATTAQUES"
        if severity:
            text += f"\n🔴 {severity.get('Élevée', 0)}  |  🟡 {severity.get('Moyenne', 0)}  |  🟢 {severity.get('Basse', 0)}"
        text += f"\n+{last_hour} dernière heure"
        return text

    def format_risk_display(self):
        if self.attack_stats['total_attacks'] == 0:
            return "0%\n🟢 AUCUNE MENACE"

        if self.risk_level == 0:
            return "0%\n🟢 RISQUE NUL"
        elif self.risk_level < 30:
            return f"{self.risk_level}%\n🟢 RISQUE FAIBLE"
        elif self.risk_level < 60:
            return f"{self.risk_level}%\n🟡 RISQUE MOYEN"
        else:
            return f"{self.risk_level}%\n🔴 RISQUE ÉLEVÉ"

    def update_data_from_db(self):
        self.attack_stats = self.db_manager.get_attack_stats()
        self.total_packets = self.db_manager.get_total_packets()
        self.risk_level = self.db_manager.calculate_risk_level()

    def refresh_dashboard(self):
        try:
            old_total = self.attack_stats['total_attacks']
            self.update_data_from_db()

            self.update_frame_content(self.cadre1, self.format_packets_display())

            new_attacks = self.attack_stats['total_attacks']
            new_last_hour = self.attack_stats['last_hour_attacks']

            attack_indicator = ""
            if new_attacks > old_total:
                attack_indicator = " ⬆️"
            elif new_attacks < old_total:
                attack_indicator = " ⬇️"

            if new_attacks == 0:
                new_content2 = "0 ATTAQUE\n✅ Système sécurisé"
            else:
                severity = self.attack_stats['severity_counts']
                text = f"{new_attacks} ATTAQUES{attack_indicator}"
                if severity:
                    text += f"\n🔴 {severity.get('Élevée', 0)}  |  🟡 {severity.get('Moyenne', 0)}  |  🟢 {severity.get('Basse', 0)}"
                text += f"\n+{new_last_hour} dernière heure"
                new_content2 = text

            self.update_frame_content(self.cadre2, new_content2)
            self.update_frame_content(self.cadre3, self.format_risk_display())

            hist_data = self.db_manager.get_attacks_last_24h()
            self.histogram.update_histogram(hist_data)

            print(f"✅ Dashboard mis à jour - Attaques: {new_attacks}, Risque: {self.risk_level}%")

        except Exception as e:
            print(f"❌ Erreur mise à jour: {e}")

    def update_frame_content(self, frame, new_content):
        for child in frame.findChildren(QLabel):
            if isinstance(child, QLabel):
                if child.styleSheet() and "font-size: 18px" in child.styleSheet():
                    child.setText(new_content)
                    break

    def create_inner_frame(self, title_text, content_text):
        frame = FocusableFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border-radius: 20px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
            border-bottom: 2px solid #335889;
            padding-bottom: 8px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        content = QLabel(content_text)
        content.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 20px;
        """)
        content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)

        layout.addStretch()
        return frame

    def closeEvent(self, event):
        if hasattr(self, 'db_manager') and self.db_manager.connection:
            self.db_manager.close_connection()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimplePage()
    window.show()
    sys.exit(app.exec())