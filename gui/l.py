import sys
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTableWidget, QTableWidgetItem, 
                            QHeaderView, QLabel, QPushButton, QComboBox,
                            QTabWidget, QGroupBox, QGridLayout, QMessageBox,
                            QLineEdit, QDateEdit, QCheckBox, QFrame)
from PyQt6.QtCore import Qt, QTimer, QDate, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QIcon, QPalette, QPixmap
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QGraphicsDropShadowEffect


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


class AlertInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Système de Détection d'Intrusions - Interface Alertes")
        
        # Configuration plein écran
        screen = QApplication.primaryScreen()
        size = screen.size()

        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height()-80)
        
        # Background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1E2E4F"))
        self.setPalette(palette)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal avec marges
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Titre animé
        self.title = AnimatedLabel("🔔 ALERTES DE SÉCURITÉ")
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
        
        # Horodatage
        self.timestamp_label = QLabel()
        timestamp_font = QFont("Arial", 12)
        self.timestamp_label.setFont(timestamp_font)
        self.timestamp_label.setStyleSheet("color: white; padding: 10px;")
        self.update_timestamp()
        main_layout.addWidget(self.timestamp_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Barre de filtres
        self.setup_filter_bar(main_layout)
        
        # Zone d'onglets pour ML et Snort
        self.setup_tabs(main_layout)
        
        # Barre de statistiques
        self.setup_stats_bar(main_layout)
        
        # Timer pour mise à jour automatique
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_alerts)
        self.timer.start(5000)  # Rafraîchir toutes les 5 secondes
        
        # Charger les données initiales
        self.load_sample_data()
    
    def setup_filter_bar(self, parent_layout):
        """Configuration de la barre de filtres"""
        filter_widget = QGroupBox("Filtres")
        filter_widget.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        filter_layout = QGridLayout()
        
        # Filtre par gravité - Label en blanc
        gravite_label = QLabel("Gravité:")
        gravite_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(gravite_label, 0, 0)
        
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["Toutes", "Élevée", "Moyenne", "Basse"])
        self.severity_combo.currentTextChanged.connect(self.apply_filters)
        self.severity_combo.setStyleSheet("""
            QComboBox {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
            }
        """)
        filter_layout.addWidget(self.severity_combo, 0, 1)
        
        # Filtre par type d'attaque - Label en blanc
        attack_label = QLabel("Type d'attaque:")
        attack_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(attack_label, 0, 2)
        
        self.attack_type_combo = QComboBox()
        self.attack_type_combo.addItems(["Tous", "DoS", "Scan Port", "Brute Force", "Malware"])
        self.attack_type_combo.currentTextChanged.connect(self.apply_filters)
        self.attack_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
            }
        """)
        filter_layout.addWidget(self.attack_type_combo, 0, 3)
        
        # Filtre par date - Label en blanc et champ plus large
        date_label = QLabel("Date:")
        date_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(date_label, 0, 4)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.apply_filters)
        # Augmentation de la taille du champ date (minimale et préférée)
        self.date_edit.setMinimumWidth(150)  # Largeur minimale augmentée
        self.date_edit.setFixedWidth(200)     # Largeur fixe augmentée
        self.date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
                min-width: 150px;
                max-width: 200px;
            }
            QDateEdit::drop-down {
                border: none;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
            }
        """)
        filter_layout.addWidget(self.date_edit, 0, 5)
        
        # Recherche IP - Label en blanc
        ip_label = QLabel("Recherche IP:")
        ip_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(ip_label, 0, 6)
        
        self.search_ip = QLineEdit()
        self.search_ip.setPlaceholderText("Entrez une IP...")
        self.search_ip.textChanged.connect(self.apply_filters)
        self.search_ip.setMinimumWidth(150)
        self.search_ip.setStyleSheet("""
            QLineEdit {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        filter_layout.addWidget(self.search_ip, 0, 7)
        
        # Bouton réinitialiser
        reset_btn = QPushButton("Réinitialiser les filtres")
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        filter_layout.addWidget(reset_btn, 0, 8)
        
        filter_widget.setLayout(filter_layout)
        parent_layout.addWidget(filter_widget)
    
    def setup_tabs(self, parent_layout):
        """Configuration des onglets pour ML et Snort"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #335889;
                border-radius: 10px;
                background-color: #1E2E4F;
            }
            QTabBar::tab {
                background-color: #2F4166;
                color: white;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #9b59b6;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #335889;
            }
        """)
        
        # Onglet Machine Learning
        self.ml_tab = QWidget()
        self.ml_tab.setStyleSheet("background-color: #1E2E4F;")
        self.setup_ml_tab()
        self.tab_widget.addTab(self.ml_tab, "🤖 Détection ML")
        
        # Onglet Snort
        self.snort_tab = QWidget()
        self.snort_tab.setStyleSheet("background-color: #1E2E4F;")
        self.setup_snort_tab()
        self.tab_widget.addTab(self.snort_tab, "🛡️ Détection Snort")
        
        parent_layout.addWidget(self.tab_widget)
    
    def setup_ml_tab(self):
        """Configuration de l'onglet Machine Learning"""
        layout = QVBoxLayout(self.ml_tab)
        
        # Tableau des alertes ML
        self.ml_table = QTableWidget()
        self.ml_table.setColumnCount(5)
        self.ml_table.setHorizontalHeaderLabels([
            "Date", "IP Source", "IP Destination", 
            "Type Attaque", "Gravité"
        ])
        
        # Configuration du tableau
        self.ml_table.setStyleSheet("""
            QTableWidget {
                background-color: #2F4166;
                alternate-background-color: #335889;
                color: white;
                gridline-color: #9b59b6;
                selection-background-color: #9b59b6;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1E2E4F;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)
        
        header = self.ml_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ml_table.setAlternatingRowColors(True)
        self.ml_table.setSortingEnabled(True)
        
        layout.addWidget(self.ml_table)
    
    def setup_snort_tab(self):
        """Configuration de l'onglet Snort"""
        layout = QVBoxLayout(self.snort_tab)
        
        # Tableau des alertes Snort
        self.snort_table = QTableWidget()
        self.snort_table.setColumnCount(5)
        self.snort_table.setHorizontalHeaderLabels([
            "Date", "IP Source", "IP Destination", 
            "Type Attaque", "Gravité"
        ])
        
        # Configuration du tableau
        self.snort_table.setStyleSheet("""
            QTableWidget {
                background-color: #2F4166;
                alternate-background-color: #335889;
                color: white;
                gridline-color: #9b59b6;
                selection-background-color: #9b59b6;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1E2E4F;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)
        
        header = self.snort_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.snort_table.setAlternatingRowColors(True)
        self.snort_table.setSortingEnabled(True)
        
        layout.addWidget(self.snort_table)
    
    def setup_stats_bar(self, parent_layout):
        """Configuration de la barre de statistiques"""
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        
        # Statistiques ML
        self.ml_stats = QLabel("🤖 ML: 0 alertes")
        self.ml_stats.setStyleSheet("""
            QLabel {
                background-color: #2F4166;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)
        
        # Statistiques Snort
        self.snort_stats = QLabel("🛡️ Snort: 0 alertes")
        self.snort_stats.setStyleSheet("""
            QLabel {
                background-color: #2F4166;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)
        
        # Statistiques globales
        self.total_stats = QLabel("📊 Total: 0 alertes")
        self.total_stats.setStyleSheet("""
            QLabel {
                background-color: #9b59b6;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #8e44ad;
            }
        """)
        
        stats_layout.addWidget(self.ml_stats)
        stats_layout.addWidget(self.snort_stats)
        stats_layout.addStretch()
        stats_layout.addWidget(self.total_stats)
        
        parent_layout.addWidget(stats_widget)
    
    def load_sample_data(self):
        """Charger des données d'exemple"""
        # Données ML
        ml_data = [
            ["14:22", "192.168.1.50", "192.168.1.10", "DoS", "Élevée"],
            ["14:25", "10.0.0.15", "192.168.1.20", "Brute Force", "Élevée"],
            ["14:30", "10.0.0.5", "192.168.1.15", "Scan Port", "Moyenne"],
            ["14:35", "172.16.0.8", "192.168.1.25", "Malware", "Élevée"],
            ["14:40", "192.168.1.100", "192.168.1.1", "DoS", "Basse"],
        ]
        
        # Données Snort
        snort_data = [
            ["14:23", "192.168.1.45", "192.168.1.12", "Scan Port", "Moyenne"],
            ["14:28", "10.0.0.10", "192.168.1.18", "DoS", "Élevée"],
            ["14:32", "172.16.0.3", "192.168.1.22", "Malware", "Élevée"],
            ["14:38", "192.168.1.55", "192.168.1.5", "Brute Force", "Moyenne"],
            ["14:42", "10.0.0.7", "192.168.1.30", "Scan Port", "Basse"],
        ]
        
        self.populate_table(self.ml_table, ml_data)
        self.populate_table(self.snort_table, snort_data)
        self.update_statistics()
    
    def populate_table(self, table, data):
        """Remplir un tableau avec des données"""
        table.setRowCount(len(data))
        
        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                
                # Colorer selon la gravité
                if col == 4:  # Colonne Gravité
                    if value == "Élevée":
                        item.setBackground(QColor("#920004"))
                        item.setForeground(QColor("white"))
                    elif value == "Moyenne":
                        item.setBackground(QColor("#d24e01"))
                        item.setForeground(QColor("black"))
                    elif value == "Basse":
                        item.setBackground(QColor("#2B7337"))
                        item.setForeground(QColor("black"))
                
                # Centrer le texte
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, item)
    
    def update_timestamp(self):
        """Mettre à jour l'horodatage"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.timestamp_label.setText(f"Dernière mise à jour: {current_time}")
    
    def update_statistics(self):
        """Mettre à jour les statistiques"""
        # Compter uniquement les lignes visibles
        ml_visible = 0
        for row in range(self.ml_table.rowCount()):
            if not self.ml_table.isRowHidden(row):
                ml_visible += 1
                
        snort_visible = 0
        for row in range(self.snort_table.rowCount()):
            if not self.snort_table.isRowHidden(row):
                snort_visible += 1
        
        total = ml_visible + snort_visible
        
        self.ml_stats.setText(f"🤖 ML: {ml_visible} alertes")
        self.snort_stats.setText(f"🛡️ Snort: {snort_visible} alertes")
        self.total_stats.setText(f"📊 Total: {total} alertes")
    
    def refresh_alerts(self):
        """Rafraîchir les alertes"""
        self.update_timestamp()
        # Ici, vous ajouteriez la logique pour récupérer les vraies données
        # Pour l'exemple, on recharge juste les données
        self.load_sample_data()
        self.apply_filters()
    
    def apply_filters(self):
        """Appliquer les filtres"""
        severity_filter = self.severity_combo.currentText()
        attack_filter = self.attack_type_combo.currentText()
        ip_search = self.search_ip.text().lower()
        
        # Filtrer les deux tableaux
        self.filter_table(self.ml_table, severity_filter, attack_filter, ip_search)
        self.filter_table(self.snort_table, severity_filter, attack_filter, ip_search)
        
        self.update_statistics()
    
    def filter_table(self, table, severity, attack, ip_search):
        """Filtrer un tableau spécifique"""
        for row in range(table.rowCount()):
            show_row = True
            
            # Filtre par gravité
            if severity != "Toutes":
                severity_item = table.item(row, 4)
                if severity_item and severity_item.text() != severity:
                    show_row = False
            
            # Filtre par type d'attaque
            if show_row and attack != "Tous":
                attack_item = table.item(row, 3)
                if attack_item and attack_item.text() != attack:
                    show_row = False
            
            # Recherche par IP
            if show_row and ip_search:
                src_ip = table.item(row, 1).text().lower()
                dst_ip = table.item(row, 2).text().lower()
                if ip_search not in src_ip and ip_search not in dst_ip:
                    show_row = False
            
            table.setRowHidden(row, not show_row)
    
    def reset_filters(self):
        """Réinitialiser tous les filtres"""
        self.severity_combo.setCurrentText("Toutes")
        self.attack_type_combo.setCurrentText("Tous")
        self.date_edit.setDate(QDate.currentDate())
        self.search_ip.clear()
        
        # Afficher toutes les lignes
        for table in [self.ml_table, self.snort_table]:
            for row in range(table.rowCount()):
                table.setRowHidden(row, False)
        
        self.update_statistics()


def main():
    app = QApplication(sys.argv)
    
    # Créer et afficher l'interface
    window = AlertInterface()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()