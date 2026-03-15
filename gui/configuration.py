import sys
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QPushButton, QLabel, QTextEdit, QMessageBox, QFrame,
    QTabWidget, QListWidget, QLineEdit,
    QTableWidget, QTableWidgetItem,
    QSplitter, QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QColor, QPalette
#from data.queries import fetch_rules_from_db

class InterfaceParametresIDS(QMainWindow):
    def __init__(self):
        super().__init__()
        # Définir le nom du fichier de configuration AVANT d'appeler initUI
        self.fichier_config = "configuration_ids.json"
        
        # Configuration du fond d'écran
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1E2E4F"))
        self.setPalette(palette)
        
        self.initUI()
        self.load_rules()
        
    def initUI(self):
        # Configuration de la fenêtre principale
        screen = QApplication.primaryScreen()
        size = screen.size()

        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height()-80)
        self.setWindowTitle("🔐 Interface Complète de Configuration IDS")
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # En-tête
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🛡️ SYSTÈME DE DÉTECTION D'INTRUSION (IDS) - CONFIGURATION AVANCÉE")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; padding: 10px;")
        
        self.status_label = QLabel("● STATUT: ACTIF")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #27ae60; background-color: #2F4166; padding: 8px; border-radius: 5px; border: 1px solid #335889;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # Création des onglets
        tabs = QTabWidget()
        tabs.setFont(QFont("Arial", 11))
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #335889;
                border-radius: 5px;
                padding: 10px;
                background-color: #1E2E4F;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 5px;
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #9b59b6;
                border-bottom: 2px solid #9b59b6;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #335889;
            }
        """)
        
        # Onglet 1: Réglage Général
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, " Réglage Général")
        
        # Onglet 2: Seuils de Détection
        seuils_tab = self.create_seuils_tab()
        tabs.addTab(seuils_tab, " Seuils de Détection")
        
        # Onglet 3: Gestion des Règles
        regles_tab = self.create_regles_tab()
        tabs.addTab(regles_tab, " Gestion des Règles")
        
        # Onglet 4: Sécurité Réseau
        securite_tab = self.create_securite_tab()
        tabs.addTab(securite_tab, "Sécurité Réseau")
        
        main_layout.addWidget(tabs)
        
        # Barre d'outils inférieure
        toolbar_layout = QHBoxLayout()
        
        # Bouton Appliquer
        self.btn_appliquer = QPushButton(" APPLIQUER LA CONFIGURATION")
        self.btn_appliquer.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_appliquer.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        self.btn_appliquer.clicked.connect(self.appliquer_configuration)
        
        # Bouton Réinitialiser
        self.btn_reset = QPushButton(" RÉINITIALISER")
        self.btn_reset.setFont(QFont("Arial", 12))
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #f39c12;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_configuration)
        
        # Bouton Sauvegarder
        self.btn_save = QPushButton(" SAUVEGARDER")
        self.btn_save.setFont(QFont("Arial", 12))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #7d3c98;
            }
        """)
        self.btn_save.clicked.connect(self.sauvegarder_configuration)
        
        toolbar_layout.addWidget(self.btn_appliquer)
        toolbar_layout.addWidget(self.btn_reset)
        toolbar_layout.addWidget(self.btn_save)
        toolbar_layout.addStretch()
        
        # Label de statut
        self.status_bar = QLabel("Prêt | Configuration par défaut chargée")
        self.status_bar.setFont(QFont("Arial", 10))
        self.status_bar.setStyleSheet("color: white; background-color: #2F4166; padding: 8px; border-radius: 5px; border: 1px solid #335889;")
        toolbar_layout.addWidget(self.status_bar)
        
        main_layout.addLayout(toolbar_layout)
        
        # Charger la configuration automatiquement au démarrage
        self.charger_configuration_auto()
        
    def create_general_tab(self):
        """Crée l'onglet Réglage Général"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        widget.setStyleSheet("background-color: #1E2E4F;")
        
        # Groupe Activation IDS
        group_activation = QGroupBox(" Activation du Système")
        group_activation.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_activation.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        activation_layout = QVBoxLayout()
        
        self.cb_activer_ids = QCheckBox("Activer le système IDS")
        self.cb_activer_ids.setFont(QFont("Arial", 11))
        self.cb_activer_ids.setStyleSheet("color: white;")
        self.cb_activer_ids.setChecked(True)
        self.cb_activer_ids.toggled.connect(self.toggle_ids)
        
        activation_layout.addWidget(self.cb_activer_ids)
        group_activation.setLayout(activation_layout)
        layout.addWidget(group_activation)
        
        # Groupe Options de Démarrage
        group_demarrage = QGroupBox(" Options de Démarrage")
        group_demarrage.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_demarrage.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        demarrage_layout = QVBoxLayout()
        
        self.cb_demarrage_auto = QCheckBox("Démarrer la surveillance automatiquement au démarrage")
        self.cb_demarrage_auto.setFont(QFont("Arial", 11))
        self.cb_demarrage_auto.setStyleSheet("color: white;")
        self.cb_demarrage_auto.setChecked(True)
        
        self.cb_redemarrage_auto = QCheckBox(" Redémarrer automatiquement en cas d'erreur")
        self.cb_redemarrage_auto.setFont(QFont("Arial", 11))
        self.cb_redemarrage_auto.setStyleSheet("color: white;")
        self.cb_redemarrage_auto.setChecked(True)
        
        demarrage_layout.addWidget(self.cb_demarrage_auto)
        demarrage_layout.addWidget(self.cb_redemarrage_auto)
        
        group_demarrage.setLayout(demarrage_layout)
        layout.addWidget(group_demarrage)
        
        # Groupe Intervalle de Scan
        group_intervalle = QGroupBox("Intervalle de Scan")
        group_intervalle.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_intervalle.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        intervalle_layout = QHBoxLayout()
        
        intervalle_layout.addWidget(QLabel("Scanner toutes les:"))
        intervalle_layout.itemAt(0).widget().setStyleSheet("color: white;")
        
        self.spin_intervalle = QSpinBox()
        self.spin_intervalle.setFont(QFont("Arial", 11))
        self.spin_intervalle.setRange(1, 3600)
        self.spin_intervalle.setValue(5)
        self.spin_intervalle.setSuffix(" secondes")
        self.spin_intervalle.setFixedWidth(150)
        self.spin_intervalle.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #335889;
                border: none;
                border-radius: 2px;
            }
        """)
        
        intervalle_layout.addWidget(self.spin_intervalle)
        intervalle_layout.addStretch()
        
        group_intervalle.setLayout(intervalle_layout)
        layout.addWidget(group_intervalle)
        
        return widget
    
    def create_seuils_tab(self):
        """Crée l'onglet Seuils de Détection"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        widget.setStyleSheet("background-color: #1E2E4F;")
        
        # Groupe Trafic Réseau
        group_trafic = QGroupBox(" Trafic Réseau")
        group_trafic.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_trafic.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        trafic_layout = QGridLayout()
        
        # Ligne 1
        label1 = QLabel("Nombre max de paquets/seconde:")
        label1.setStyleSheet("color: white;")
        trafic_layout.addWidget(label1, 0, 0)
        self.spin_max_paquets = QSpinBox()
        self.spin_max_paquets.setRange(100, 100000)
        self.spin_max_paquets.setValue(5000)
        self.spin_max_paquets.setSuffix(" paquets/s")
        self.spin_max_paquets.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        trafic_layout.addWidget(self.spin_max_paquets, 0, 1)
        
        # Ligne 2
        label2 = QLabel("Volume max de données:")
        label2.setStyleSheet("color: white;")
        trafic_layout.addWidget(label2, 1, 0)
        self.spin_volume_max = QSpinBox()
        self.spin_volume_max.setRange(1, 10000)
        self.spin_volume_max.setValue(100)
        self.spin_volume_max.setSuffix(" MB/s")
        self.spin_volume_max.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        trafic_layout.addWidget(self.spin_volume_max, 1, 1)
        
        # Ligne 3
        label3 = QLabel("Nombre max connexions simultanées:")
        label3.setStyleSheet("color: white;")
        trafic_layout.addWidget(label3, 2, 0)
        self.spin_max_connexions = QSpinBox()
        self.spin_max_connexions.setRange(10, 10000)
        self.spin_max_connexions.setValue(1000)
        self.spin_max_connexions.setSuffix(" connexions")
        self.spin_max_connexions.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        trafic_layout.addWidget(self.spin_max_connexions, 2, 1)
        
        group_trafic.setLayout(trafic_layout)
        layout.addWidget(group_trafic)
        
        # Groupe SSH / Authentification
        group_ssh = QGroupBox("🔐 SSH / Authentification")
        group_ssh.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_ssh.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        ssh_layout = QGridLayout()
        
        label4 = QLabel("Nombre max de tentatives de login:")
        label4.setStyleSheet("color: white;")
        ssh_layout.addWidget(label4, 0, 0)
        self.spin_max_tentatives = QSpinBox()
        self.spin_max_tentatives.setRange(1, 50)
        self.spin_max_tentatives.setValue(5)
        self.spin_max_tentatives.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        ssh_layout.addWidget(self.spin_max_tentatives, 0, 1)
        
        label5 = QLabel("Temps de blocage IP:")
        label5.setStyleSheet("color: white;")
        ssh_layout.addWidget(label5, 1, 0)
        self.spin_temps_blocage_auth = QSpinBox()
        self.spin_temps_blocage_auth.setRange(1, 1440)
        self.spin_temps_blocage_auth.setValue(10)
        self.spin_temps_blocage_auth.setSuffix(" minutes")
        self.spin_temps_blocage_auth.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        ssh_layout.addWidget(self.spin_temps_blocage_auth, 1, 1)
        
        group_ssh.setLayout(ssh_layout)
        layout.addWidget(group_ssh)
        
        # Groupe Scan de Ports
        group_scan = QGroupBox("🔍 Scan de Ports")
        group_scan.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_scan.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        scan_layout = QHBoxLayout()
        
        label6 = QLabel("Alerte si plus de")
        label6.setStyleSheet("color: white;")
        scan_layout.addWidget(label6)
        
        self.spin_ports_scan = QSpinBox()
        self.spin_ports_scan.setRange(1, 1000)
        self.spin_ports_scan.setValue(50)
        self.spin_ports_scan.setSuffix(" ports")
        self.spin_ports_scan.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        scan_layout.addWidget(self.spin_ports_scan)
        
        label7 = QLabel("scannés en")
        label7.setStyleSheet("color: white;")
        scan_layout.addWidget(label7)
        
        self.spin_temps_scan = QSpinBox()
        self.spin_temps_scan.setRange(1, 60)
        self.spin_temps_scan.setValue(10)
        self.spin_temps_scan.setSuffix(" secondes")
        self.spin_temps_scan.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        scan_layout.addWidget(self.spin_temps_scan)
        
        scan_layout.addStretch()
        group_scan.setLayout(scan_layout)
        layout.addWidget(group_scan)
        
        layout.addStretch()
        return widget
    
    def create_regles_tab(self):
        """Crée l'onglet Gestion des Règles"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        widget.setStyleSheet("background-color: #1E2E4F;")
        
        # Panneau gauche - Liste des règles
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #1E2E4F;")
        left_layout = QVBoxLayout(left_panel)
        
        group_liste = QGroupBox(" Règles existantes")
        group_liste.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_liste.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        liste_layout = QVBoxLayout()
        
        self.table_regles = QTableWidget()
        self.table_regles.setColumnCount(2)
        self.table_regles.setHorizontalHeaderLabels(["SID", "Règle"])
        self.table_regles.horizontalHeader().setStretchLastSection(True)
        self.table_regles.setAlternatingRowColors(True)
        self.table_regles.setStyleSheet("""
            QTableWidget {
                background-color: #2F4166;
                alternate-background-color: #335889;
                color: white;
                gridline-color: #9b59b6;
                selection-background-color: #9b59b6;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1E2E4F;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                font-weight: bold;
            }
        """)

        self.table_regles.resizeColumnsToContents()
        liste_layout.addWidget(self.table_regles)
        group_liste.setLayout(liste_layout)
        left_layout.addWidget(group_liste)
        
        # Panneau droit - Gestion des règles
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #1E2E4F;")
        right_layout = QVBoxLayout(right_panel)
        
        # Groupe Ajout/Modification
        group_edit = QGroupBox("✏️ Éditeur de règle")
        group_edit.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_edit.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        edit_layout = QVBoxLayout()
        
        edit_layout.addWidget(QLabel("Nouvelle règle:"))
        edit_layout.itemAt(0).widget().setStyleSheet("color: white;")
        
        self.edit_regle = QTextEdit()
        self.edit_regle.setMaximumHeight(100)
        self.edit_regle.setPlaceholderText("Ex: bloquer port 23\nEx: alerter si ICMP > 500")
        self.edit_regle.setStyleSheet("""
            QTextEdit {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 5px;
            }
            QTextEdit::placeholder {
                color: #888;
            }
        """)
        edit_layout.addWidget(self.edit_regle)
        
        btn_layout = QHBoxLayout()
        self.btn_ajouter = QPushButton("Ajouter")
        self.btn_modifier = QPushButton(" Modifier")
        self.btn_supprimer = QPushButton("Supprimer")
        
        for btn in [self.btn_ajouter, self.btn_modifier, self.btn_supprimer]:
            btn.setFont(QFont("Arial", 10))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #335889;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #9b59b6;
                }
            """)
            btn_layout.addWidget(btn)
        
        edit_layout.addLayout(btn_layout)
        group_edit.setLayout(edit_layout)
        right_layout.addWidget(group_edit)
        
        # Connexions
        self.btn_ajouter.clicked.connect(self.ajouter_regle)
        self.btn_supprimer.clicked.connect(self.supprimer_regle)
        
        # Layout principal avec splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #335889;
            }
        """)
        
        layout.addWidget(splitter)
        return widget

    def load_rules(self):

        rules = fetch_rules_from_db(self)

        self.table_regles.setRowCount(0)

        for sid, rule in rules:
            row = self.table_regles.rowCount()
            self.table_regles.insertRow(row)

            self.table_regles.setItem(row, 0, QTableWidgetItem(str(sid)))
            self.table_regles.setItem(row, 1, QTableWidgetItem(rule))

    def add_rule_to_table(self, rule,sid):
        row_count = self.table_regles.rowCount()
        self.table_regles.insertRow(row_count)

        item_etat = QTableWidgetItem(str(sid))
        item_regle = QTableWidgetItem(rule)

        self.table_regles.setItem(row_count, 0, item_etat)
        self.table_regles.setItem(row_count, 1, item_regle)
    
    def create_securite_tab(self):
        """Crée l'onglet Sécurité Réseau (sans liste blanche)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        widget.setStyleSheet("background-color: #1E2E4F;")
        
        # Groupe Liste Noire uniquement
        group_blacklist = QGroupBox("Liste Noire (Blacklist)")
        group_blacklist.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_blacklist.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        blacklist_layout = QVBoxLayout()
        
        self.blacklist = QListWidget()
        self.blacklist.addItems(["1.2.3.4", "5.6.7.8", "10.0.0.50"])
        self.blacklist.setStyleSheet("""
            QListWidget {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #9b59b6;
            }
            QListWidget::item:hover {
                background-color: #335889;
            }
        """)
        blacklist_layout.addWidget(self.blacklist)
        
        blacklist_btn_layout = QHBoxLayout()
        self.btn_blacklist_ajouter = QPushButton(" Ajouter IP")
        self.btn_blacklist_supprimer = QPushButton(" Supprimer")
        
        for btn in [self.btn_blacklist_ajouter, self.btn_blacklist_supprimer]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #335889;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #9b59b6;
                }
            """)
        
        blacklist_btn_layout.addWidget(self.btn_blacklist_ajouter)
        blacklist_btn_layout.addWidget(self.btn_blacklist_supprimer)
        blacklist_layout.addLayout(blacklist_btn_layout)
        
        group_blacklist.setLayout(blacklist_layout)
        layout.addWidget(group_blacklist)
        
        # Groupe Blocage Automatique
        group_blocage = QGroupBox("🛡️ Blocage Automatique")
        group_blocage.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_blocage.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        blocage_layout = QVBoxLayout()
        
        self.cb_blocage_auto = QCheckBox("Bloquer automatiquement les IPs en cas d'attaque")
        self.cb_blocage_auto.setStyleSheet("color: white;")
        self.cb_blocage_auto.setChecked(True)
        blocage_layout.addWidget(self.cb_blocage_auto)
        
        temps_layout = QHBoxLayout()
        label_temps = QLabel("Temps de blocage:")
        label_temps.setStyleSheet("color: white;")
        temps_layout.addWidget(label_temps)
        
        self.spin_temps_blocage_auto = QSpinBox()
        self.spin_temps_blocage_auto.setRange(1, 1440)
        self.spin_temps_blocage_auto.setValue(30)
        self.spin_temps_blocage_auto.setSuffix(" minutes")
        self.spin_temps_blocage_auto.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        temps_layout.addWidget(self.spin_temps_blocage_auto)
        temps_layout.addStretch()
        blocage_layout.addLayout(temps_layout)
        
        group_blocage.setLayout(blocage_layout)
        layout.addWidget(group_blocage)
        
        # Groupe Restrictions
        group_restrictions = QGroupBox(" Restrictions d'accès")
        group_restrictions.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        group_restrictions.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
        """)
        restrictions_layout = QVBoxLayout()
        
        self.cb_ip_internes = QCheckBox("Autoriser uniquement les IPs internes")
        self.cb_ip_internes.setStyleSheet("color: white;")
        self.cb_ip_internes.setChecked(False)
        restrictions_layout.addWidget(self.cb_ip_internes)
        
        self.cb_rejeter_externes = QCheckBox("Rejeter automatiquement le trafic externe non autorisé")
        self.cb_rejeter_externes.setStyleSheet("color: white;")
        self.cb_rejeter_externes.setChecked(True)
        restrictions_layout.addWidget(self.cb_rejeter_externes)
        
        group_restrictions.setLayout(restrictions_layout)
        layout.addWidget(group_restrictions)
        
        # Input pour nouvelle IP
        input_layout = QHBoxLayout()
        label_ip = QLabel("Nouvelle IP/CIDR:")
        label_ip.setStyleSheet("color: white;")
        input_layout.addWidget(label_ip)
        
        self.edit_nouvelle_ip = QLineEdit()
        self.edit_nouvelle_ip.setPlaceholderText("Ex: 192.168.1.100 ou 10.0.0.0/24")
        self.edit_nouvelle_ip.setStyleSheet("""
            QLineEdit {
                background-color: #2F4166;
                color: white;
                border: 1px solid #335889;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        input_layout.addWidget(self.edit_nouvelle_ip)
        layout.addLayout(input_layout)
        
        # Connexions
        self.btn_blacklist_ajouter.clicked.connect(lambda: self.ajouter_ip("blacklist"))
        self.btn_blacklist_supprimer.clicked.connect(lambda: self.supprimer_ip("blacklist"))
        
        return widget
    
    def toggle_ids(self, etat):
        """Active/désactive l'IDS"""
        status = "ACTIF" if etat else "INACTIF"
        self.status_label.setText(f"● STATUT: {status}")
        self.status_bar.setText(f"⚡ IDS {status}")
        
    def ajouter_regle(self,rule,sid):
        """Ajoute une nouvelle règle"""
        nouvelle_regle = rule
        if nouvelle_regle:
            row = self.table_regles.rowCount()
            self.table_regles.insertRow(row)
            
            item_etat = QTableWidgetItem(str(sid))
            item_etat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_regles.setItem(row, 0, item_etat)
            
            item_regle = QTableWidgetItem(nouvelle_regle)
            item_regle.setForeground(QColor("white"))
            self.table_regles.setItem(row, 1, item_regle)
            
            self.edit_regle.clear()
            self.status_bar.setText(f" Règle ajoutée: {nouvelle_regle[:30]}...")
    
    def supprimer_regle(self):
        """Supprime la règle sélectionnée"""
        current_row = self.table_regles.currentRow()
        if current_row >= 0:
            self.table_regles.removeRow(current_row)
            self.status_bar.setText(" Règle supprimée")
    
    def ajouter_ip(self, liste_type):
        """Ajoute une IP à la blacklist"""
        ip = self.edit_nouvelle_ip.text().strip()
        if ip:
            self.blacklist.addItem(ip)
            self.edit_nouvelle_ip.clear()
            self.status_bar.setText(f"IP ajoutée à la blacklist")
    
    def supprimer_ip(self, liste_type):
        """Supprime l'IP sélectionnée"""
        current = self.blacklist.currentItem()
        if current:
            self.blacklist.takeItem(self.blacklist.row(current))
            self.status_bar.setText(" IP supprimée")
    
    def get_configuration(self):
        """Récupère toute la configuration sous forme de dictionnaire"""
        config = {
            "date_sauvegarde": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "general": {
                "activer_ids": self.cb_activer_ids.isChecked(),
                "demarrage_auto": self.cb_demarrage_auto.isChecked(),
                "redemarrage_auto": self.cb_redemarrage_auto.isChecked(),
                "intervalle_scan": self.spin_intervalle.value()
            },
            "seuils": {
                "max_paquets": self.spin_max_paquets.value(),
                "volume_max": self.spin_volume_max.value(),
                "max_connexions": self.spin_max_connexions.value(),
                "max_tentatives": self.spin_max_tentatives.value(),
                "temps_blocage_auth": self.spin_temps_blocage_auth.value(),
                "ports_scan": self.spin_ports_scan.value(),
                "temps_scan": self.spin_temps_scan.value()
            },
            "regles": [],
            "securite": {
                "blacklist": [],
                "blocage_auto": self.cb_blocage_auto.isChecked(),
                "temps_blocage_auto": self.spin_temps_blocage_auto.value(),
                "ip_internes_only": self.cb_ip_internes.isChecked(),
                "rejeter_externes": self.cb_rejeter_externes.isChecked()
            }
        }
        
        # Récupérer les règles
        for row in range(self.table_regles.rowCount()):
            etat = self.table_regles.item(row, 0).text()
            regle = self.table_regles.item(row, 1).text()
            config["regles"].append({"etat": etat, "regle": regle})
        
        # Récupérer la blacklist
        for i in range(self.blacklist.count()):
            config["securite"]["blacklist"].append(self.blacklist.item(i).text())
        
        return config
    
    def set_configuration(self, config):
        """Applique une configuration depuis un dictionnaire"""
        try:
            # Général
            self.cb_activer_ids.setChecked(config["general"]["activer_ids"])
            self.cb_demarrage_auto.setChecked(config["general"]["demarrage_auto"])
            self.cb_redemarrage_auto.setChecked(config["general"]["redemarrage_auto"])
            self.spin_intervalle.setValue(config["general"]["intervalle_scan"])
            
            # Seuils
            self.spin_max_paquets.setValue(config["seuils"]["max_paquets"])
            self.spin_volume_max.setValue(config["seuils"]["volume_max"])
            self.spin_max_connexions.setValue(config["seuils"]["max_connexions"])
            self.spin_max_tentatives.setValue(config["seuils"]["max_tentatives"])
            self.spin_temps_blocage_auth.setValue(config["seuils"]["temps_blocage_auth"])
            self.spin_ports_scan.setValue(config["seuils"]["ports_scan"])
            self.spin_temps_scan.setValue(config["seuils"]["temps_scan"])
            
            # Règles
            self.table_regles.setRowCount(0)
            for regle in config["regles"]:
                row = self.table_regles.rowCount()
                self.table_regles.insertRow(row)
                
                item_etat = QTableWidgetItem(regle["etat"])
                item_etat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_etat.setForeground(QColor("#9b59b6"))
                self.table_regles.setItem(row, 0, item_etat)
                
                item_regle = QTableWidgetItem(regle["regle"])
                item_regle.setForeground(QColor("white"))
                self.table_regles.setItem(row, 1, item_regle)
            
            # Sécurité
            self.blacklist.clear()
            for ip in config["securite"]["blacklist"]:
                self.blacklist.addItem(ip)
            
            self.cb_blocage_auto.setChecked(config["securite"]["blocage_auto"])
            self.spin_temps_blocage_auto.setValue(config["securite"]["temps_blocage_auto"])
            self.cb_ip_internes.setChecked(config["securite"]["ip_internes_only"])
            self.cb_rejeter_externes.setChecked(config["securite"]["rejeter_externes"])
            
            self.status_bar.setText("✅ Configuration chargée avec succès")
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")
    
    def appliquer_configuration(self):
        """Applique la configuration"""
        QMessageBox.information(self, "Configuration", "✅ Configuration appliquée avec succès!")
        self.status_bar.setText("✅ Configuration appliquée")
    
    def reset_configuration(self):
        """Réinitialise la configuration"""
        reply = QMessageBox.question(self, "Confirmation", 
                                    "Voulez-vous vraiment réinitialiser toute la configuration?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Recharger la configuration par défaut
            self.cb_activer_ids.setChecked(True)
            self.cb_demarrage_auto.setChecked(True)
            self.cb_redemarrage_auto.setChecked(True)
            self.spin_intervalle.setValue(5)
            
            self.spin_max_paquets.setValue(5000)
            self.spin_volume_max.setValue(100)
            self.spin_max_connexions.setValue(1000)
            self.spin_max_tentatives.setValue(5)
            self.spin_temps_blocage_auth.setValue(10)
            self.spin_ports_scan.setValue(50)
            self.spin_temps_scan.setValue(10)
            
            # Règles par défaut
            self.table_regles.setRowCount(0)
            regles_defaut = [
                ("✓", "Alerte si trafic ICMP > 500/sec"),
                ("✓", "Bloquer port 23 (Telnet)"),
                ("✓", "Surveiller port 22 (SSH)"),
                ("✓", "Alerte si SYN > 1000/sec"),
            ]
            for etat, regle in regles_defaut:
                row = self.table_regles.rowCount()
                self.table_regles.insertRow(row)
                
                item_etat = QTableWidgetItem(etat)
                item_etat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_etat.setForeground(QColor("#9b59b6"))
                self.table_regles.setItem(row, 0, item_etat)
                
                item_regle = QTableWidgetItem(regle)
                item_regle.setForeground(QColor("white"))
                self.table_regles.setItem(row, 1, item_regle)
            
            # Blacklist par défaut
            self.blacklist.clear()
            self.blacklist.addItems(["1.2.3.4", "5.6.7.8", "10.0.0.50"])
            
            self.cb_blocage_auto.setChecked(True)
            self.spin_temps_blocage_auto.setValue(30)
            self.cb_ip_internes.setChecked(False)
            self.cb_rejeter_externes.setChecked(True)
            
            self.status_bar.setText("🔄 Configuration réinitialisée")
    
    def sauvegarder_configuration(self):
        """Sauvegarde la configuration dans un fichier"""
        config = self.get_configuration()
        
        # Demander l'emplacement de sauvegarde
        fichier, _ = QFileDialog.getSaveFileName(
            self, 
            "Sauvegarder la configuration", 
            self.fichier_config,
            "Fichiers JSON (*.json);;Tous les fichiers (*)"
        )
        
        if fichier:
            try:
                with open(fichier, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                
                self.fichier_config = fichier
                QMessageBox.information(self, "Sauvegarde", f" Configuration sauvegardée dans:\n{fichier}")
                self.status_bar.setText(f" Configuration sauvegardée: {os.path.basename(fichier)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f" Erreur lors de la sauvegarde:\n{str(e)}")
    
    def charger_configuration_auto(self):
        """Charge automatiquement la configuration si le fichier existe"""
        if os.path.exists(self.fichier_config):
            try:
                with open(self.fichier_config, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.set_configuration(config)
                self.status_bar.setText(f" Configuration chargée depuis {self.fichier_config}")
            except Exception as e:
                print(f"Erreur lors du chargement automatique: {e}")
                self.status_bar.setText("Erreur lors du chargement, configuration par défaut utilisée")

def main():
    app = QApplication(sys.argv)
    # Style global
    app.setStyleSheet("""
        QMessageBox {
            background-color: #1E2E4F;
            color: white;
        }
        QMessageBox QLabel {
            color: white;
        }
        QMessageBox QPushButton {
            background-color: #335889;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
            min-width: 80px;
        }
        QMessageBox QPushButton:hover {
            background-color: #9b59b6;
        }
    """)
    
    window = InterfaceParametresIDS()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()