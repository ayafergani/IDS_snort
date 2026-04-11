import sys
import os
from datetime import datetime, timedelta

# Permet d'importer depuis le dossier parent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QFrame, QGridLayout, QGraphicsOpacityEffect,
    QHBoxLayout, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer
from PyQt6.QtGui import QPalette, QColor

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# === IMPORTATION DE NOTRE NOUVELLE ARCHITECTURE ===
from config import COLORS
from gui.components import AnimatedLabel, FocusableFrame
from data.dashboard import DatabaseManager
from snort_module.lancement import SnortManager  # ✅ Import du SnortManager


class TrafficHistogram(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(5.5, 3.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.ax.set_facecolor(COLORS['bg_dark'])
        self.fig.patch.set_facecolor(COLORS['bg_dark'])
        self.fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.18)

        self.setMinimumHeight(250)
        self.setMaximumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.update_histogram([0] * 24)

    def update_histogram(self, data):
        self.ax.clear()
        self.ax.set_facecolor(COLORS['bg_dark'])

        heures = list(range(24))
        couleurs = [COLORS['success'] if val == 0 else COLORS['danger'] for val in data]

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
                tick.set_color(COLORS['success'])
            else:
                tick.set_color(COLORS['danger'])

        self.ax.grid(True, axis='y', alpha=0.2, linestyle='--', color='white', linewidth=0.5)

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color(COLORS['accent'])
        self.ax.spines['bottom'].set_color(COLORS['accent'])

        for i, (heure, val) in enumerate(zip(heures, data)):
            if val == 1:
                self.ax.text(heure, val + 0.05, '⚠️', ha='center', va='bottom', fontsize=8)

        self.draw()


class SimplePage(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.snort = SnortManager()  # ✅ Initialisation de SnortManager
        self.attack_stats = {'total_attacks': 0, 'last_hour_attacks': 0, 'severity_counts': {}}
        self.total_packets = 0
        self.risk_level = 0
        self.is_running = False  # ✅ Ajout de is_running (état du système)
        self.snort_running = False  # ✅ État de Snort

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        self.setPalette(palette)

        # Cadre principal - BLEU FONCÉ
        self.cadre = QFrame()
        self.cadre.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 20px;
                padding: 20px;
            }}
        """)

        main_layout_global = QVBoxLayout(self)
        main_layout_global.setContentsMargins(0, 0, 0, 0)
        main_layout_global.setSpacing(0)
        main_layout_global.addWidget(self.cadre)
        main_layout_global.addStretch()

        main_layout = QVBoxLayout(self.cadre)
        main_layout.setSpacing(15)

        # === HEADER AVEC TITRE ET BOUTON START ===
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        self.title = AnimatedLabel("TABLEAU DE BORD ")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title, 1)

        # Bouton START/STOP
        self.start_stop_btn = QPushButton("▶️ START")
        self.start_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_stop_btn.setFixedSize(100, 40)
        self.start_stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']}cc;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['info']}99;
            }}
        """)
        self.start_stop_btn.clicked.connect(self.toggle_system)  # ✅ Connexion du signal
        header_layout.addWidget(self.start_stop_btn)

        main_layout.addLayout(header_layout)

        # Animation du titre
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

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # Premier chargement des données (affichage initial)
        self.update_data_from_db()

        self.cadre1 = self.create_inner_frame("📊 NOMBRE TOTAL DE PAQUETS ANALYSÉS", self.format_packets_display())
        self.cadre2 = self.create_inner_frame("⚠️ NOMBRE D'ATTAQUES DÉTECTÉES", self.format_attacks_display())
        self.cadre3 = self.create_inner_frame("🎯 NIVEAU DE RISQUE GLOBAL", self.format_risk_display())

        # Cadre pour l'histogramme
        self.cadre4 = FocusableFrame()
        self.cadre4.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 20px;
                padding: 15px;
                border: 2px solid {COLORS['accent']};
            }}
        """)

        layout4 = QVBoxLayout(self.cadre4)
        layout4.setSpacing(10)
        layout4.setContentsMargins(10, 10, 10, 10)

        title4 = QLabel("📈 ÉTAT DU TRAFIC EN TEMPS RÉEL")
        title4.setStyleSheet(f"""
            color: white;
            font-size: 16px;
            font-weight: bold;
            border-bottom: 2px solid {COLORS['accent']};
            padding-bottom: 8px;
        """)
        title4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout4.addWidget(title4)

        legend_widget = QWidget()
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setSpacing(20)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend_layout.setContentsMargins(0, 5, 0, 5)

        normal_label = QLabel("🟢 NORMAL (0)")
        normal_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(normal_label)

        attaque_label = QLabel("🔴 ATTAQUE (1)")
        attaque_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(attaque_label)

        layout4.addWidget(legend_widget)

        self.histogram = TrafficHistogram()
        layout4.addWidget(self.histogram)

        grid_layout.addWidget(self.cadre1, 0, 0)
        grid_layout.addWidget(self.cadre2, 0, 1)
        grid_layout.addWidget(self.cadre3, 1, 0)
        grid_layout.addWidget(self.cadre4, 1, 1)

        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        main_layout.addLayout(grid_layout)

        # Chargement initial de l'histogramme
        hist_data = self.db_manager.get_attacks_last_24h()
        self.histogram.update_histogram(hist_data)

        # Timer de mise à jour
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_dashboard)
        # ⚡ NE PAS démarrer le timer automatiquement

    # ✅ MÉTHODE TOGGLE CORRIGÉE
    def toggle_system(self):
        """Active ou désactive Snort et la mise à jour en temps réel"""
        if self.is_running:
            # === ARRÊTER LE SYSTÈME ===
            print("🛑 Arrêt du système...")
            self.snort.stop_snort()
            self.update_timer.stop()
            self.is_running = False
            self.snort_running = False

            self.start_stop_btn.setText("▶️ START")
            self.start_stop_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['info']};
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['info']}cc;
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['info']}99;
                }}
            """)
            print("✅ Système arrêté")

        else:
            # === DÉMARRER LE SYSTÈME ===
            print("🚀 Démarrage du système...")

            # Démarrer Snort
            success = self.snort.start()

            # Vérifier si Snort tourne vraiment
            if success or self.snort.is_running():
                # Démarrer le timer de mise à jour
                self.update_timer.start(5000)
                self.is_running = True
                self.snort_running = True

                self.start_stop_btn.setText("⏹️ STOP")
                self.start_stop_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['danger']};
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 8px 16px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['danger']}cc;
                    }}
                    QPushButton:pressed {{
                        background-color: {COLORS['danger']}99;
                    }}
                """)

                # Rafraîchir immédiatement
                self.refresh_dashboard()
                print("✅ Système démarré avec succès")
            else:
                self.start_stop_btn.setText("❌ ERREUR")
                print("❌ Échec du démarrage de Snort")
                QTimer.singleShot(3000, self.reset_button_text)

    def reset_button_text(self):
        """Réinitialise le texte du bouton après une erreur"""
        self.start_stop_btn.setText("▶️ START")
        self.start_stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']}cc;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['info']}99;
            }}
        """)

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
            text += f"\n🔴 {severity.get('élevée', 0)}  |  🟡 {severity.get('Moyenne', 0)}  |  🟢 {severity.get('Basse', 0)}"
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
        # Ne mettre à jour que si Snort est en cours d'exécution
        if not hasattr(self, "snort_running") or not self.snort_running:
            return

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
                    text += f"\n🔴 {severity.get('élevée', 0)}  |  🟡 {severity.get('Moyenne', 0)}  |  🟢 {severity.get('Basse', 0)}"
                text += f"\n+{new_last_hour} dernière heure"
                new_content2 = text

            self.update_frame_content(self.cadre2, new_content2)
            self.update_frame_content(self.cadre3, self.format_risk_display())

            hist_data = self.db_manager.get_attacks_last_24h()
            self.histogram.update_histogram(hist_data)

            print("📊 Dashboard updated:", new_attacks)

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
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 20px;
                padding: 15px;
                border: 1px solid {COLORS['accent']};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setStyleSheet(f"""
            color: white;
            font-size: 14px;
            font-weight: bold;
            border-bottom: 2px solid {COLORS['accent']};
            padding-bottom: 8px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        content = QLabel(content_text)
        content.setStyleSheet(f"""
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 20px;
            background-color: {COLORS['bg_dark']};
        """)
        content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)

        layout.addStretch()
        return frame

    def closeEvent(self, event):
        """Fermeture propre de l'application"""
        # Arrêter Snort si encore en cours d'exécution
        if self.is_running:
            self.snort.stop()

        # Fermer la connexion à la base de données
        if hasattr(self, 'db_manager') and self.db_manager.connection:
            self.db_manager.close_connection()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimplePage()
    window.show()
    sys.exit(app.exec())