import sys
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                            QTableWidgetItem, QComboBox, QHeaderView, QMessageBox,
                            QFileDialog, QGroupBox, QGridLayout, QFrame, QStatusBar)
from PyQt6.QtCore import Qt, QDate, QTimer, QRect  # Ajout de QRect ici
from PyQt6.QtGui import QFont, QPalette, QColor, QBrush
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

class RapportInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Générateur de Rapports de Sécurité - Console SOC")
        
        # Taille de la fenêtre
        screen = QApplication.primaryScreen()
        size = screen.size()
        # Correction ici - on utilise la largeur et hauteur directement sans QRect
        self.setGeometry(0, 0, size.width(), size.height())
        self.setFixedSize(size.width(), size.height()-80)
        
        # Couleurs pour l'interface (compatibles avec le style informaticien)
        self.colors = {
            'bg_dark': '#0A1929',
            'bg_medium': '#132F4C',
            'accent': '#1E4976',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'info': '#3498db',
            'text': '#E0E0E0',
            'text_bright': '#FFFFFF',
            'terminal_green': '#00ff00'
        }
        
        # Configuration du style
        self.setup_style()
        
        # Données d'exemple pour tous les mois
        self.donnees_rapports = {
            'janvier': {
                'attaques': 120,
                'dos': 40,
                'scans': 50,
                'brute_force': 30,
                'details': [
                    {'date': '2024-01-01', 'type': 'DoS', 'source': '192.168.1.100', 'severite': 'Haute'},
                    {'date': '2024-01-02', 'type': 'Scan', 'source': '10.0.0.50', 'severite': 'Moyenne'},
                    {'date': '2024-01-03', 'type': 'Brute Force', 'source': '172.16.0.25', 'severite': 'Haute'},
                ]
            },
            'février': {
                'attaques': 145,
                'dos': 55,
                'scans': 45,
                'brute_force': 45,
                'details': [
                    {'date': '2024-02-01', 'type': 'DoS', 'source': '192.168.1.200', 'severite': 'Haute'},
                    {'date': '2024-02-02', 'type': 'Scan', 'source': '10.0.0.75', 'severite': 'Basse'},
                ]
            },
            'mars': {
                'attaques': 98,
                'dos': 30,
                'scans': 40,
                'brute_force': 28,
                'details': [
                    {'date': '2024-03-01', 'type': 'Brute Force', 'source': '172.16.0.100', 'severite': 'Moyenne'},
                ]
            },
            'avril': {
                'attaques': 135,
                'dos': 45,
                'scans': 55,
                'brute_force': 35,
                'details': [
                    {'date': '2024-04-01', 'type': 'DoS', 'source': '192.168.1.150', 'severite': 'Haute'},
                    {'date': '2024-04-05', 'type': 'Scan', 'source': '10.0.0.90', 'severite': 'Basse'},
                ]
            },
            'mai': {
                'attaques': 160,
                'dos': 60,
                'scans': 50,
                'brute_force': 50,
                'details': [
                    {'date': '2024-05-02', 'type': 'Brute Force', 'source': '172.16.0.200', 'severite': 'Haute'},
                    {'date': '2024-05-10', 'type': 'Scan', 'source': '10.0.0.110', 'severite': 'Moyenne'},
                ]
            },
            'juin': {
                'attaques': 110,
                'dos': 35,
                'scans': 45,
                'brute_force': 30,
                'details': [
                    {'date': '2024-06-03', 'type': 'DoS', 'source': '192.168.1.180', 'severite': 'Moyenne'},
                ]
            },
            'juillet': {
                'attaques': 90,
                'dos': 25,
                'scans': 35,
                'brute_force': 30,
                'details': [
                    {'date': '2024-07-01', 'type': 'Scan', 'source': '10.0.0.130', 'severite': 'Basse'},
                ]
            },
            'août': {
                'attaques': 85,
                'dos': 20,
                'scans': 40,
                'brute_force': 25,
                'details': [
                    {'date': '2024-08-05', 'type': 'Brute Force', 'source': '172.16.0.150', 'severite': 'Haute'},
                ]
            },
            'septembre': {
                'attaques': 140,
                'dos': 50,
                'scans': 45,
                'brute_force': 45,
                'details': [
                    {'date': '2024-09-02', 'type': 'DoS', 'source': '192.168.1.220', 'severite': 'Haute'},
                    {'date': '2024-09-08', 'type': 'Scan', 'source': '10.0.0.140', 'severite': 'Moyenne'},
                ]
            },
            'octobre': {
                'attaques': 155,
                'dos': 55,
                'scans': 50,
                'brute_force': 50,
                'details': [
                    {'date': '2024-10-01', 'type': 'Brute Force', 'source': '172.16.0.250', 'severite': 'Haute'},
                    {'date': '2024-10-10', 'type': 'DoS', 'source': '192.168.1.250', 'severite': 'Haute'},
                ]
            },
            'novembre': {
                'attaques': 130,
                'dos': 40,
                'scans': 50,
                'brute_force': 40,
                'details': [
                    {'date': '2024-11-03', 'type': 'Scan', 'source': '10.0.0.160', 'severite': 'Basse'},
                ]
            },
            'décembre': {
                'attaques': 175,
                'dos': 65,
                'scans': 55,
                'brute_force': 55,
                'details': [
                    {'date': '2024-12-01', 'type': 'DoS', 'source': '192.168.1.300', 'severite': 'Haute'},
                    {'date': '2024-12-05', 'type': 'Brute Force', 'source': '172.16.0.300', 'severite': 'Haute'},
                    {'date': '2024-12-15', 'type': 'Scan', 'source': '10.0.0.180', 'severite': 'Moyenne'},
                ]
            }
        }
        
        self.init_ui()
        
        
    def setup_style(self):
        """Style optimisé pour informaticien (compatible avec le second code)"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['bg_dark']};
            }}
            QLabel {{
                color: {self.colors['text']};
                font-family: 'Consolas', 'Courier New', monospace;
            }}
            QLabel#title_label {{
                font-size: 20px;
                font-weight: bold;
                color: {self.colors['text_bright']};
                padding: 10px;
                background-color: {self.colors['accent']};
                border-radius: 5px;
                letter-spacing: 1px;
            }}
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {self.colors['info']};
                border: 2px solid {self.colors['accent']};
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: rgba(10, 25, 41, 0.95);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: {self.colors['info']};
            }}
            QComboBox {{
                background-color: {self.colors['bg_medium']};
                color: {self.colors['text_bright']};
                border: 1px solid {self.colors['info']};
                border-radius: 3px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                min-width: 200px;
            }}
            QComboBox:hover {{
                border: 1px solid {self.colors['success']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.colors['info']};
                width: 0;
                height: 0;
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Consolas', monospace;
            }}
            QPushButton:hover {{
                background-color: {self.colors['info']};
            }}
            QPushButton#pdf_button {{
                background-color: {self.colors['danger']};
            }}
            QPushButton#pdf_button:hover {{
                background-color: #c0392b;
            }}
            QTableWidget {{
                background-color: {self.colors['bg_medium']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['info']};
                gridline-color: {self.colors['accent']};
                font-family: 'Consolas', monospace;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.colors['accent']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.colors['info']};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.colors['accent']};
                color: {self.colors['text_bright']};
                padding: 10px;
                border: 1px solid {self.colors['bg_dark']};
                font-weight: bold;
                font-size: 13px;
            }}
            QFrame#header_frame {{
                background-color: {self.colors['accent']};
                border-radius: 5px;
                padding: 10px;
            }}
            QFrame#toolbar_frame {{
                background-color: {self.colors['bg_medium']};
                border-radius: 5px;
                padding: 8px;
            }}
            QStatusBar {{
                background-color: {self.colors['bg_medium']};
                color: {self.colors['terminal_green']};
                font-family: 'Consolas', monospace;
            }}
        """)
        
    def init_ui(self):
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # En-tête
        self.creer_en_tete(main_layout)
        
        # Zone de contrôle
        self.creer_zone_controle(main_layout)
        
        # Tableau des détails
        self.creer_tableau_details(main_layout)
        
        # Barre d'outils inférieure
        self.creer_barre_outils(main_layout)
        
        # Barre d'état
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✓ Système opérationnel - Prêt à générer des rapports")
        
    def creer_en_tete(self, layout):
        # Frame d'en-tête
        header_frame = QFrame()
        header_frame.setObjectName("header_frame")
        
        header_layout = QHBoxLayout(header_frame)
        
        # Titre
        title_label = QLabel("GÉNÉRATEUR DE RAPPORTS DE SÉCURITÉ")
        title_label.setObjectName("title_label")
        header_layout.addWidget(title_label)
        
        # Horodatage
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {self.colors['terminal_green']}; font-size: 14px;")
        
        header_layout.addStretch()
        header_layout.addWidget(self.time_label)
        
        layout.addWidget(header_frame)
        
    def creer_zone_controle(self, layout):
        # Groupe de contrôle
        control_group = QGroupBox(" PÉRIODE DU RAPPORT")
        
        control_layout = QHBoxLayout(control_group)
        
        # Sélecteur de mois
        control_layout.addWidget(QLabel("⌂ Sélectionner le mois:"))
        
        self.mois_combo = QComboBox()
        self.mois_combo.addItems([
            "Tous les mois",
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ])
        self.mois_combo.currentTextChanged.connect(self.mettre_a_jour_rapport)
        control_layout.addWidget(self.mois_combo)
        
        # Bouton PDF
        self.pdf_btn = QPushButton("⬇ EXPORTER EN PDF")
        self.pdf_btn.setObjectName("pdf_button")
        self.pdf_btn.clicked.connect(self.exporter_pdf)
        control_layout.addWidget(self.pdf_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
    def creer_tableau_details(self, layout):
        # Groupe du tableau
        table_group = QGroupBox(" DÉTAILS DES ÉVÉNEMENTS DE SÉCURITÉ")
        table_layout = QVBoxLayout(table_group)
        
        # Tableau des détails
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(4)
        self.details_table.setHorizontalHeaderLabels(["Date", "Type d'attaque", "Source", "Sévérité"])
        
        # Ajustement des colonnes
        header = self.details_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        table_layout.addWidget(self.details_table)
        layout.addWidget(table_group)
        
    def creer_barre_outils(self, layout):
        # Barre d'outils inférieure
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbar_frame")
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # Statistiques supplémentaires
        self.stats_label = QLabel("⚡ Rapport prêt à être généré")
        self.stats_label.setStyleSheet(f"color: {self.colors['info']}; font-size: 12px;")
        toolbar_layout.addWidget(self.stats_label)
        
        toolbar_layout.addStretch()
        
        layout.addWidget(toolbar_frame)
        
    def mettre_a_jour_rapport(self):
        mois = self.mois_combo.currentText()
        
        if mois == "Tous les mois":
            # Rassembler tous les détails de tous les mois
            tous_les_details = []
            for mois_data in self.donnees_rapports.values():
                tous_les_details.extend(mois_data.get('details', []))
            
            # Trier par date
            tous_les_details.sort(key=lambda x: x['date'])
            
            # Mettre à jour le tableau
            self.details_table.setRowCount(len(tous_les_details))
            
            for i, detail in enumerate(tous_les_details):
                self.details_table.setItem(i, 0, QTableWidgetItem(detail['date']))
                self.details_table.setItem(i, 1, QTableWidgetItem(detail['type']))
                self.details_table.setItem(i, 2, QTableWidgetItem(detail['source']))
                
                # Coloration selon la sévérité
                severite_item = QTableWidgetItem(detail['severite'])
                if detail['severite'] == 'Haute':
                    severite_item.setBackground(QBrush(QColor(231, 76, 60, 100)))  # Danger avec transparence
                elif detail['severite'] == 'Moyenne':
                    severite_item.setBackground(QBrush(QColor(243, 156, 18, 100)))  # Warning avec transparence
                else:
                    severite_item.setBackground(QBrush(QColor(46, 204, 113, 100)))  # Success avec transparence
                    
                self.details_table.setItem(i, 3, severite_item)
            
            # Mise à jour du label
            self.stats_label.setText(f"Rapport annuel chargé - {len(tous_les_details)} événements détaillés")
            self.status_bar.showMessage(f"✓ Rapport annuel chargé - {len(tous_les_details)} événements")
            
        elif mois in self.donnees_rapports:
            donnees = self.donnees_rapports[mois]
            
            # Mise à jour du tableau
            details = donnees.get('details', [])
            self.details_table.setRowCount(len(details))
            
            for i, detail in enumerate(details):
                self.details_table.setItem(i, 0, QTableWidgetItem(detail['date']))
                self.details_table.setItem(i, 1, QTableWidgetItem(detail['type']))
                self.details_table.setItem(i, 2, QTableWidgetItem(detail['source']))
                
                # Coloration selon la sévérité
                severite_item = QTableWidgetItem(detail['severite'])
                if detail['severite'] == 'Haute':
                    severite_item.setBackground(QBrush(QColor(231, 76, 60, 100)))
                elif detail['severite'] == 'Moyenne':
                    severite_item.setBackground(QBrush(QColor(243, 156, 18, 100)))
                else:
                    severite_item.setBackground(QBrush(QColor(46, 204, 113, 100)))
                    
                self.details_table.setItem(i, 3, severite_item)
            
            # Mise à jour du label
            self.stats_label.setText(f" Rapport {mois.capitalize()} chargé - {len(details)} événements détaillés")
            self.status_bar.showMessage(f"✓ Rapport {mois} chargé - {len(details)} événements")
    
    
        
    def exporter_pdf(self):
        mois = self.mois_combo.currentText()
        
        # Gestion du cas "Tous les mois"
        if mois == "Tous les mois":
            # Boîte de dialogue pour choisir l'emplacement du fichier
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                "Enregistrer le rapport PDF", 
                f"rapport_securite_annuel_{datetime.now().strftime('%Y%m%d')}.pdf", 
                "Fichiers PDF (*.pdf)"
            )
            
            if filename:
                try:
                    self.generer_pdf_annuel(filename)
                    QMessageBox.information(self, "✅ Succès", f"Rapport annuel PDF généré avec succès:\n{filename}")
                    self.status_bar.showMessage(f"✓ PDF généré: {filename}")
                except Exception as e:
                    QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de la génération du PDF:\n{str(e)}")
        
        elif mois in self.donnees_rapports:
            # Boîte de dialogue pour choisir l'emplacement du fichier
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                "Enregistrer le rapport PDF", 
                f"rapport_securite_{mois}_{datetime.now().strftime('%Y%m%d')}.pdf", 
                "Fichiers PDF (*.pdf)"
            )
            
            if filename:
                try:
                    self.generer_pdf(filename, mois)
                    QMessageBox.information(self, "✅ Succès", f"Rapport PDF généré avec succès:\n{filename}")
                    self.status_bar.showMessage(f"✓ PDF généré: {filename}")
                except Exception as e:
                    QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de la génération du PDF:\n{str(e)}")
        else:
            QMessageBox.warning(self, "⚠ Attention", "Aucune donnée disponible pour cette période")
    
    def generer_pdf(self, filename, mois):
        donnees = self.donnees_rapports[mois]
        
        # Création du document PDF
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0A1929'),
            spaceAfter=30,
            alignment=1  # Centre
        )
        title = Paragraph(f"Rapport de Sécurité - {mois.capitalize()} 2024", title_style)
        story.append(title)
        
        # Date de génération
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1E4976'),
            alignment=2  # Droite
        )
        date_text = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        story.append(Paragraph(date_text, date_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Détails des événements
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#132F4C'),
            spaceAfter=10
        )
        story.append(Paragraph("Détail des événements", summary_style))
        
        if donnees['details']:
            # En-têtes du tableau détaillé
            details_data = [['Date', 'Type', 'Source', 'Sévérité']]
            
            # Ajout des données
            for detail in donnees['details']:
                details_data.append([
                    detail['date'],
                    detail['type'],
                    detail['source'],
                    detail['severite']
                ])
            
            # Création du tableau détaillé
            details_table = Table(details_data, colWidths=[1*inch, 1.5*inch, 2*inch, 1*inch])
            
            # Style du tableau détaillé
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#132F4C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1E4976'))
            ]
            
            # Coloration selon la sévérité
            for i, detail in enumerate(donnees['details'], start=1):
                if detail['severite'] == 'Haute':
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#ffcccc')))
                elif detail['severite'] == 'Moyenne':
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#ffffcc')))
                else:
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#ccffcc')))
            
            details_table.setStyle(TableStyle(table_style))
            story.append(details_table)
        else:
            story.append(Paragraph("Aucun détail d'événement disponible", styles['Normal']))
        
        # Pied de page
        story.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#1E4976'),
            alignment=1
        )
        footer_text = "Rapport généré automatiquement - Console SOC"
        story.append(Paragraph(footer_text, footer_style))
        
        # Génération du PDF
        doc.build(story)
    
    def generer_pdf_annuel(self, filename):
        # Rassembler tous les détails de tous les mois
        tous_les_details = []
        for mois, donnees in self.donnees_rapports.items():
            for detail in donnees.get('details', []):
                # Ajouter le mois pour référence
                detail_avec_mois = detail.copy()
                detail_avec_mois['mois'] = mois
                tous_les_details.append(detail_avec_mois)
        
        # Trier par date
        tous_les_details.sort(key=lambda x: x['date'])
        
        # Création du document PDF
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0A1929'),
            spaceAfter=30,
            alignment=1  # Centre
        )
        title = Paragraph("Rapport de Sécurité Annuel 2024", title_style)
        story.append(title)
        
        # Date de génération
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1E4976'),
            alignment=2  # Droite
        )
        date_text = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        story.append(Paragraph(date_text, date_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Statistiques annuelles
        total_attaques = sum(d['attaques'] for d in self.donnees_rapports.values())
        total_dos = sum(d['dos'] for d in self.donnees_rapports.values())
        total_scans = sum(d['scans'] for d in self.donnees_rapports.values())
        total_brute_force = sum(d['brute_force'] for d in self.donnees_rapports.values())
        
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#132F4C'),
            spaceAfter=10
        )
        story.append(Paragraph("Résumé annuel", summary_style))
        
        # Tableau des statistiques annuelles
        stats_data = [
            ['Type', 'Nombre'],
            ['Total attaques', str(total_attaques)],
            ['Attaques DoS', str(total_dos)],
            ['Scans réseau', str(total_scans)],
            ['Brute force', str(total_brute_force)]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E4976')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#132F4C'))
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.5*inch))
        
        # Détails des événements
        story.append(Paragraph("Détail des événements annuels", summary_style))
        
        if tous_les_details:
            # En-têtes du tableau détaillé (avec mois en plus)
            details_data = [['Date', 'Mois', 'Type', 'Source', 'Sévérité']]
            
            # Ajout des données
            for detail in tous_les_details:
                details_data.append([
                    detail['date'],
                    detail['mois'].capitalize(),
                    detail['type'],
                    detail['source'],
                    detail['severite']
                ])
            
            # Création du tableau détaillé
            details_table = Table(details_data, colWidths=[0.8*inch, 0.8*inch, 1.2*inch, 1.8*inch, 0.8*inch])
            
            # Style du tableau détaillé
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#132F4C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1E4976'))
            ]
            
            # Coloration selon la sévérité
            for i, detail in enumerate(tous_les_details, start=1):
                if detail['severite'] == 'Haute':
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#ffcccc')))
                elif detail['severite'] == 'Moyenne':
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#ffffcc')))
                else:
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#ccffcc')))
            
            details_table.setStyle(TableStyle(table_style))
            story.append(details_table)
        else:
            story.append(Paragraph("Aucun détail d'événement disponible", styles['Normal']))
        
        # Pied de page
        story.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#1E4976'),
            alignment=1
        )
        footer_text = "Rapport annuel généré automatiquement - Console SOC"
        story.append(Paragraph(footer_text, footer_style))
        
        # Génération du PDF
        doc.build(story)

def main():
    app = QApplication(sys.argv)
    
    # Application du style global
    app.setStyle('Fusion')
    
    # Police pour informaticien
    font = QFont("Consolas", 9)
    app.setFont(font)
    
    # Palette de couleurs adaptée
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(10, 25, 41))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Base, QColor(19, 47, 76))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 73, 118))
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Button, QColor(30, 73, 118))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(52, 152, 219))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    app.setPalette(palette)
    
    # Création et affichage de la fenêtre principale
    window = RapportInterface()
    window.show()
    
    # Chargement initial du rapport
    window.mettre_a_jour_rapport()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()