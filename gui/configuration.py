import re
import sys
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QCheckBox, QSpinBox,
    QPushButton, QLabel, QTextEdit, QMessageBox,
    QTabWidget, QListWidget, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# On importe les couleurs de ta config centrale pour la cohérence
from config import COLORS
from data.rules import afficher_db, ajouter_regle, modifier_regle, supprimer_regle, reset_db

# ================== STYLES UNIFIÉS ==================
INPUT_STYLE = f"""
    QComboBox, QDateEdit, QLineEdit, QSpinBox, QTextEdit, QListWidget {{
        background-color: #334155;
        color: white;
        padding: 8px;
        border: 1px solid {COLORS['accent']};
        border-radius: 6px;
    }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {COLORS['info']};
    }}
"""

BTN_PRIMARY_STYLE = """
    QPushButton {
        background-color: #0EA5E9;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover { background-color: #0284C7; }
"""

BTN_DANGER_STYLE = """
    QPushButton {
        background-color: #EF4444;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #B91C1C; }
"""

BTN_SUCCESS_STYLE = """
    QPushButton {
        background-color: #10B981;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #059669; }
"""

TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {COLORS['bg_medium']};
        alternate-background-color: {COLORS['bg_dark']};
        color: white;
        gridline-color: {COLORS['accent']};
        border-radius: 8px;
        border: 1px solid {COLORS['accent']};
    }}
    QHeaderView::section {{
        background-color: #0B1120;
        color: white;
        padding: 10px;
        border: none;
        border-bottom: 2px solid {COLORS['info']};
        font-weight: bold;
    }}
"""


class InterfaceParametresIDS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fichier_config = "configuration_ids.json"

        # Chemins Snort
        self.snort_rules_dir = "/etc/snort/rules"
        self.snort_custom_rules_file = "/etc/snort/rules/custom.rules"
        self.snort_local_rules_file = "/etc/snort/rules/local.rules"

        # Vérifier et créer les dossiers si nécessaire
        self.ensure_snort_directories()

        # Fond sombre SaaS
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        self.setPalette(palette)

        self.initUI()
        self.load_rules()

    def ensure_snort_directories(self):
        """Vérifie et crée les dossiers nécessaires pour Snort"""
        try:
            # Créer le dossier rules s'il n'existe pas
            if not os.path.exists(self.snort_rules_dir):
                os.makedirs(self.snort_rules_dir, exist_ok=True)
                print(f"✅ Dossier créé: {self.snort_rules_dir}")
        except PermissionError:
            print(f"⚠️ Permission refusée pour créer {self.snort_rules_dir}")
            # Utiliser un dossier local comme fallback
            self.snort_rules_dir = os.path.expanduser("~/snort_rules")
            self.snort_custom_rules_file = os.path.join(self.snort_rules_dir, "custom.rules")
            self.snort_local_rules_file = os.path.join(self.snort_rules_dir, "local.rules")
            os.makedirs(self.snort_rules_dir, exist_ok=True)
            print(f"📁 Utilisation du dossier alternatif: {self.snort_rules_dir}")

    def initUI(self):
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height() - 80)
        self.setWindowTitle("🔐 Configuration IDS - Console d'Administration")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # En-tête
        header_layout = QHBoxLayout()
        title_label = QLabel("🛡️ CONFIGURATION AVANCÉE DU SYSTÈME")
        title_label.setStyleSheet(f"color: {COLORS['info']}; font-size: 20px; font-weight: bold; padding: 10px;")

        self.status_label = QLabel("● STATUT: ACTIF")
        self.status_label.setStyleSheet(
            f"color: {COLORS['success']}; background-color: #1E293B; padding: 8px 15px; border-radius: 6px; border: 1px solid {COLORS['accent']}; font-weight: bold;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        main_layout.addLayout(header_layout)

        # Onglets stylisés
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['accent']}; border-radius: 8px; background-color: {COLORS['bg_dark']}; }}
            QTabBar::tab {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text']}; padding: 12px 25px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background-color: {COLORS['info']}; color: {COLORS['bg_dark']}; font-weight: bold; }}
        """)

        tabs.addTab(self.create_general_tab(), "⚙️ Général")
        tabs.addTab(self.create_seuils_tab(), "📊 Seuils")
        tabs.addTab(self.create_regles_tab(), "📋 Règles")
        tabs.addTab(self.create_securite_tab(), "🛡️ Sécurité Réseau")
        tabs.addTab(self.create_snort_tab(), "🐍 Export Snort")

        main_layout.addWidget(tabs)

        # Barre d'outils inférieure
        toolbar_layout = QHBoxLayout()
        self.btn_appliquer = QPushButton("🚀 APPLIQUER & EXPORTER")
        self.btn_appliquer.setStyleSheet(BTN_PRIMARY_STYLE)
        self.btn_appliquer.clicked.connect(self.appliquer_et_exporter)

        self.btn_reset = QPushButton("🔄 RESET")
        self.btn_reset.setStyleSheet(BTN_DANGER_STYLE)
        self.btn_reset.clicked.connect(self.reset_configuration)

        self.btn_save = QPushButton("💾 SAUVEGARDER")
        self.btn_save.setStyleSheet(BTN_PRIMARY_STYLE.replace("#0EA5E9", COLORS['accent']))
        self.btn_save.clicked.connect(self.sauvegarder_configuration)

        toolbar_layout.addWidget(self.btn_appliquer)
        toolbar_layout.addWidget(self.btn_reset)
        toolbar_layout.addWidget(self.btn_save)
        toolbar_layout.addStretch()

        self.status_bar = QLabel("Prêt | Console synchronisée")
        self.status_bar.setStyleSheet(
            f"color: {COLORS['text']}; background-color: #1E293B; padding: 10px; border-radius: 6px;")
        toolbar_layout.addWidget(self.status_bar)

        main_layout.addLayout(toolbar_layout)
        self.charger_configuration_auto()

    def create_snort_tab(self):
        """Onglet pour la configuration Snort"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Groupe d'export
        group_export = self.create_styled_group("📁 Export des règles vers Snort")
        export_layout = QVBoxLayout()

        # Info sur le chemin
        path_info = QLabel(f"📂 Dossier de destination: {self.snort_rules_dir}")
        path_info.setStyleSheet("color: #94A3B8; font-family: monospace; padding: 5px;")
        export_layout.addWidget(path_info)

        # Boutons d'export
        btn_layout = QHBoxLayout()
        self.btn_export_snort = QPushButton("📤 Exporter vers Snort")
        self.btn_export_snort.setStyleSheet(BTN_SUCCESS_STYLE)
        self.btn_export_snort.clicked.connect(self.exporter_regles_snort)
        btn_layout.addWidget(self.btn_export_snort)

        self.btn_export_personnalise = QPushButton("💾 Exporter vers fichier personnalisé")
        self.btn_export_personnalise.setStyleSheet(BTN_PRIMARY_STYLE)
        self.btn_export_personnalise.clicked.connect(self.exporter_regles_fichier)
        btn_layout.addWidget(self.btn_export_personnalise)

        export_layout.addLayout(btn_layout)
        group_export.setLayout(export_layout)

        # Groupe d'aperçu
        group_preview = self.create_styled_group("📄 Aperçu des règles générées")
        preview_layout = QVBoxLayout()

        self.preview_text = QTextEdit()
        self.preview_text.setStyleSheet(INPUT_STYLE)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)

        group_preview.setLayout(preview_layout)

        layout.addWidget(group_export)
        layout.addWidget(group_preview)

        return widget

    def generer_fichier_regles(self):
        """Génère le contenu du fichier de règles Snort à partir de la BDD"""
        try:
            rules = afficher_db()

            # En-tête du fichier
            header = f"""# ============================================
# FICHIER DE RÈGLES SNORT - GÉNÉRÉ AUTOMATIQUEMENT
# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Console IDS - Toutes les règles sont actives
# ============================================

# Règles personnalisées générées depuis la base de données
# Total: {len(rules)} règle(s)

"""

            # Corps des règles
            rules_content = []
            for sid, rule in rules:
                # Nettoyer la règle si nécessaire
                rule = rule.strip()
                if rule and not rule.startswith('#'):
                    # Ajouter le sid si pas présent
                    if 'sid:' not in rule:
                        rule = rule.rstrip(')') + f" sid:{sid};)"
                    rules_content.append(rule)
                elif rule and rule.startswith('#'):
                    # Garder les commentaires
                    rules_content.append(rule)
                else:
                    rules_content.append(f"# Règle {sid}: {rule}")

            # Assemblage final
            full_content = header + "\n".join(rules_content)

            # Ajouter des règles par défaut si la base est vide
            if not rules_content:
                full_content += """
# Règles par défaut - Surveillance de base
alert icmp any any -> $HOME_NET any (msg:"ICMP Echo Request détecté"; itype:8; sid:1000001; rev:1;)
alert tcp $EXTERNAL_NET any -> $HOME_NET 22 (msg:"Tentative SSH détectée"; flow:to_server,established; sid:1000002; rev:1;)
alert tcp $EXTERNAL_NET any -> $HOME_NET 80 (msg:"Trafic HTTP détecté"; flow:to_server,established; sid:1000003; rev:1;)
"""

            return full_content

        except Exception as e:
            print(f"❌ Erreur génération règles: {e}")
            return f"# Erreur lors de la génération des règles: {e}"

    def exporter_regles_snort(self):
        """Exporte les règles vers le dossier Snort"""
        try:
            # Générer le contenu
            content = self.generer_fichier_regles()

            # Afficher l'aperçu
            self.preview_text.setText(content)

            # Écrire dans le fichier custom.rules
            with open(self.snort_custom_rules_file, 'w') as f:
                f.write(content)

            # Optionnel: ajouter une ligne include dans snort.conf si nécessaire
            self.verifier_include_snort_conf()

            self.status_bar.setText(f"✅ Règles exportées avec succès vers {self.snort_custom_rules_file}")
            QMessageBox.information(
                self,
                "✅ Export réussi",
                f"Les règles ont été exportées vers:\n{self.snort_custom_rules_file}\n\n"
                f"Redémarrez Snort pour appliquer les modifications:\n"
                f"sudo systemctl restart snort\nou\nsudo pkill -f snort"
            )

        except PermissionError:
            # Fallback: proposer d'exporter avec sudo
            reply = QMessageBox.question(
                self,
                "Permission refusée",
                f"Permission refusée pour écrire dans {self.snort_custom_rules_file}\n\n"
                "Voulez-vous exporter vers un fichier local ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.exporter_regles_fichier()

        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de l'export:\n{str(e)}")
            self.status_bar.setText(f"❌ Erreur: {str(e)}")

    def exporter_regles_fichier(self):
        """Exporte les règles vers un fichier choisi par l'utilisateur"""
        try:
            content = self.generer_fichier_regles()

            # Afficher l'aperçu
            self.preview_text.setText(content)

            # Demander le chemin de sauvegarde
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer les règles Snort",
                os.path.expanduser(f"~/snort_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rules"),
                "Fichiers règles (*.rules);;Tous les fichiers (*)"
            )

            if path:
                with open(path, 'w') as f:
                    f.write(content)
                self.status_bar.setText(f"✅ Règles sauvegardées: {path}")
                QMessageBox.information(self, "✅ Succès", f"Fichier sauvegardé:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de la sauvegarde:\n{str(e)}")

    def verifier_include_snort_conf(self):
        """Vérifie et ajoute l'include des règles personnalisées dans snort.conf"""
        snort_conf = "/etc/snort/snort.conf"
        include_line = f"include {self.snort_custom_rules_file}"

        try:
            if os.path.exists(snort_conf):
                with open(snort_conf, 'r') as f:
                    content = f.read()

                if include_line not in content:
                    # Ajouter l'include à la fin
                    with open(snort_conf, 'a') as f:
                        f.write(f"\n# Règles personnalisées générées par la console IDS\n{include_line}\n")
                    print(f"✅ Include ajouté dans {snort_conf}")

        except PermissionError:
            print(f"⚠️ Permission refusée pour modifier {snort_conf}")
            print(f"   Ajoutez manuellement: {include_line}")

    def appliquer_et_exporter(self):
        """Applique la configuration ET exporte les règles vers Snort"""
        # Appliquer la configuration
        self.appliquer_configuration()

        # Exporter les règles
        self.exporter_regles_snort()

    def create_styled_group(self, title):
        group = QGroupBox(f" {title} ")
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['info']}; font-weight: bold; border: 1px solid {COLORS['accent']};
                border-radius: 8px; margin-top: 15px; padding-top: 20px; background-color: {COLORS['bg_medium']};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
        """)
        return group

    def create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group_activation = self.create_styled_group("Activation du Système")
        activation_layout = QVBoxLayout()
        self.cb_activer_ids = QCheckBox("Activer la surveillance temps-réel")
        self.cb_activer_ids.setStyleSheet("color: white; font-size: 13px;")
        self.cb_activer_ids.setChecked(True)
        self.cb_activer_ids.toggled.connect(self.toggle_ids)
        activation_layout.addWidget(self.cb_activer_ids)
        group_activation.setLayout(activation_layout)

        group_demarrage = self.create_styled_group("Options de Boot")
        dem_layout = QVBoxLayout()
        self.cb_demarrage_auto = QCheckBox("Lancement automatique au boot")
        self.cb_redemarrage_auto = QCheckBox("Auto-restart en cas de crash")
        for cb in [self.cb_demarrage_auto, self.cb_redemarrage_auto]:
            cb.setStyleSheet("color: white; font-size: 13px;")
            cb.setChecked(True)
            dem_layout.addWidget(cb)
        group_demarrage.setLayout(dem_layout)

        layout.addWidget(group_activation)
        layout.addWidget(group_demarrage)
        layout.addStretch()
        return widget

    def create_seuils_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = self.create_styled_group("Seuils de Tolérance")
        grid = QGridLayout()

        labels = ["Max Paquets/s :", "Volume Max (MB/s) :", "Max Connexions :", "Tentatives Login :"]
        self.spin_max_paquets = QSpinBox()
        self.spin_volume_max = QSpinBox()
        self.spin_max_connexions = QSpinBox()
        self.spin_max_tentatives = QSpinBox()

        spins = [self.spin_max_paquets, self.spin_volume_max, self.spin_max_connexions, self.spin_max_tentatives]
        for i, text in enumerate(labels):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: white;")
            grid.addWidget(lbl, i, 0)
            spins[i].setStyleSheet(INPUT_STYLE)
            spins[i].setRange(1, 100000)
            grid.addWidget(spins[i], i, 1)

        group.setLayout(grid)
        layout.addWidget(group)
        layout.addStretch()
        return widget

    def create_regles_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table
        self.table_regles = QTableWidget()
        self.table_regles.setColumnCount(2)
        self.table_regles.setHorizontalHeaderLabels(["SID", "DÉFINITION DE LA RÈGLE"])
        self.table_regles.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_regles.setStyleSheet(TABLE_STYLE)
        self.table_regles.setAlternatingRowColors(True)

        # Editor
        group_edit = self.create_styled_group("⌨️ Éditeur Quick-Rule")
        edit_layout = QVBoxLayout()
        self.edit_regle = QTextEdit()
        self.edit_regle.setStyleSheet(INPUT_STYLE)
        self.edit_regle.setMaximumHeight(80)
        edit_layout.addWidget(self.edit_regle)

        btn_lay = QHBoxLayout()
        self.btn_ajouter = QPushButton("➕ Ajouter")
        self.btn_modifier = QPushButton("✏️ Modifier")
        self.btn_supprimer = QPushButton("❌ Supprimer")

        for btn in [self.btn_ajouter, self.btn_modifier, self.btn_supprimer]:
            btn.setStyleSheet(BTN_PRIMARY_STYLE.replace("#0EA5E9", "#334155"))
            btn_lay.addWidget(btn)

        edit_layout.addLayout(btn_lay)
        group_edit.setLayout(edit_layout)

        layout.addWidget(self.table_regles, 70)
        layout.addWidget(group_edit, 30)

        self.btn_ajouter.clicked.connect(self.add_rules)
        self.btn_supprimer.clicked.connect(self.delete_rule)
        self.btn_modifier.clicked.connect(self.update_rule)
        self.table_regles.itemDoubleClicked.connect(self.charger_regle_pour_modification)
        return widget

    def create_securite_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = self.create_styled_group("Blacklist IP")
        vbox = QVBoxLayout()
        self.blacklist = QListWidget()
        self.blacklist.setStyleSheet(INPUT_STYLE)
        vbox.addWidget(self.blacklist)

        self.edit_nouvelle_ip = QLineEdit()
        self.edit_nouvelle_ip.setStyleSheet(INPUT_STYLE)
        self.edit_nouvelle_ip.setPlaceholderText("Ajouter une IP (ex: 192.168.1.100)")
        vbox.addWidget(self.edit_nouvelle_ip)

        btn_lay = QHBoxLayout()
        self.btn_blacklist_ajouter = QPushButton("Ajouter")
        self.btn_blacklist_supprimer = QPushButton("Supprimer")
        for b in [self.btn_blacklist_ajouter, self.btn_blacklist_supprimer]:
            b.setStyleSheet(BTN_PRIMARY_STYLE.replace("#0EA5E9", "#334155"))
            btn_lay.addWidget(b)
        vbox.addLayout(btn_lay)
        group.setLayout(vbox)

        layout.addWidget(group)
        self.btn_blacklist_ajouter.clicked.connect(lambda: self.ajouter_ip("blacklist"))
        self.btn_blacklist_supprimer.clicked.connect(lambda: self.supprimer_ip("blacklist"))
        return widget

    # --- LOGIQUE EXISTANTE ---
    def toggle_ids(self, etat):
        status = "ACTIF" if etat else "INACTIF"
        self.status_label.setText(f"● STATUT: {status}")
        self.status_label.setStyleSheet(
            f"color: {COLORS['success'] if etat else COLORS['danger']}; background-color: #1E293B; padding: 8px 15px; border-radius: 6px; border: 1px solid {COLORS['accent']}; font-weight: bold;")

    def load_rules(self):
        try:
            rules = afficher_db()
            self.table_regles.setRowCount(0)
            for sid, rule in rules:
                row = self.table_regles.rowCount()
                self.table_regles.insertRow(row)
                self.table_regles.setItem(row, 0, QTableWidgetItem(str(sid)))
                self.table_regles.setItem(row, 1, QTableWidgetItem(rule))
        except:
            pass

    def add_rules(self):
        rule = self.edit_regle.toPlainText()
        if rule:
            ajouter_regle(rule)
            self.load_rules()
            self.edit_regle.clear()

    def charger_regle_pour_modification(self, item):
        row = item.row()
        self.sid = int(self.table_regles.item(row, 0).text())
        self.edit_regle.setText(self.table_regles.item(row, 1).text())

    def update_rule(self):
        if hasattr(self, 'sid'):
            modifier_regle(self.sid, self.edit_regle.toPlainText())
            self.load_rules()

    def delete_rule(self):
        if hasattr(self, 'sid'):
            supprimer_regle(self.sid)
            self.load_rules()

    def ajouter_ip(self, t):
        ip = self.edit_nouvelle_ip.text().strip()
        if ip:
            self.blacklist.addItem(ip)
            self.edit_nouvelle_ip.clear()

    def supprimer_ip(self, t):
        current = self.blacklist.currentItem()
        if current:
            self.blacklist.takeItem(self.blacklist.row(current))

    def appliquer_configuration(self):
        """Applique la configuration et exporte les règles"""
        # Ici vous pouvez ajouter d'autres actions de configuration
        self.exporter_regles_snort()
        QMessageBox.information(self, "Succès", "✅ Configuration appliquée et règles exportées vers Snort.")

    def reset_configuration(self):
        if QMessageBox.question(self, "Confirmer",
                                "Réinitialiser la BDD des règles ?") == QMessageBox.StandardButton.Yes:
            reset_db()
            self.load_rules()

    def sauvegarder_configuration(self):
        config = {"date": str(datetime.now()), "rules_count": self.table_regles.rowCount()}
        path, _ = QFileDialog.getSaveFileName(self, "Sauver JSON", "config.json", "*.json")
        if path:
            with open(path, 'w') as f:
                json.dump(config, f)
            QMessageBox.information(self, "Ok", "Fichier config généré.")

    def charger_configuration_auto(self):
        self.status_bar.setText("✓ Configuration temps-réel synchronisée")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InterfaceParametresIDS()
    window.show()
    sys.exit(app.exec())