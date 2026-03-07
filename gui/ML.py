import sys
import random
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Configuration matplotlib
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 100
plt.rcParams['figure.figsize'] = [8, 4]

class DetectionConfidenceWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Détection d'Intrusion - Niveau de Confiance")
        
        # Taille de la fenêtre
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height()-80)
        
        # Couleurs pour l'interface
        self.colors = {
            'bg_dark': '#0A1929',
            'bg_medium': '#132F4C',
            'accent': '#1E4976',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'info': '#3498db',
            'text': '#E0E0E0',
            'text_bright': '#FFFFFF'
        }
        
        # Configuration du style
        self.setup_style()
        
        # Initialisation de l'interface
        self.init_ui()
        
        # Timer pour mise à jour
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_confidence)
        self.timer.start(3000)  # Mise à jour toutes les 3 secondes
        
        self.show()
        
    def setup_style(self):
        """Style optimisé pour informaticien"""
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
            QProgressBar {{
                border: 2px solid {self.colors['accent']};
                border-radius: 5px;
                text-align: center;
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: {self.colors['bg_medium']};
                height: 30px;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.colors['success']}, stop:1 {self.colors['info']});
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
            QTextEdit, QPlainTextEdit {{
                background-color: {self.colors['bg_medium']};
                color: #00ff00;
                border: 1px solid {self.colors['info']};
                border-radius: 5px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }}
        """)
        
    def init_ui(self):
        """Interface axée sur la confiance de détection"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # En-tête
        header_layout = QHBoxLayout()
        title_label = QLabel("Machine Learnning")
        title_label.setObjectName("title_label")
        
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #00ff00; font-size: 14px;")
        self.update_timestamp()
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.time_label)
        main_layout.addLayout(header_layout)
        
        # Layout principal
        content_layout = QHBoxLayout()
        
        # Colonne gauche - Métriques de confiance
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(15)
        
        # Groupe Confiance Globale
        confidence_group = QGroupBox(" CONFIANCE GLOBALE DU MODÈLE")
        confidence_layout = QVBoxLayout()
        
        # Barre de progression principale
        self.main_confidence_bar = QProgressBar()
        self.main_confidence_bar.setRange(0, 100)
        self.main_confidence_bar.setValue(98)
        self.main_confidence_bar.setFormat("%p% - Niveau de confiance")
        confidence_layout.addWidget(self.main_confidence_bar)
        
        # Affichage numérique
        confidence_display = QHBoxLayout()
        self.confidence_value = QLabel("98.5%")
        self.confidence_value.setStyleSheet("color: #2ecc71; font-size: 48px; font-weight: bold;")
        confidence_display.addWidget(self.confidence_value)
        confidence_display.addStretch()
        confidence_layout.addLayout(confidence_display)
        
        confidence_group.setLayout(confidence_layout)
        left_layout.addWidget(confidence_group)
        
        # Groupe Détails de Confiance par Type
        details_group = QGroupBox(" CONFIANCE PAR TYPE DE DÉTECTION")
        details_layout = QGridLayout()
        details_layout.setVerticalSpacing(15)
        details_layout.setHorizontalSpacing(20)
        
        # Métriques détaillées
        self.detail_bars = {}
        details = [
            ("Détection normale", 99.2, "success"),
            ("Détection attaque", 97.8, "warning"),
    
        ]
        
        for i, (label, value, color) in enumerate(details):
            row = i // 2
            col = i % 2
            
            detail_widget = QWidget()
            detail_layout = QVBoxLayout(detail_widget)
            
            # Label
            label_widget = QLabel(f"{label}:")
            label_widget.setStyleSheet(f"color: {self.colors['info']}; font-size: 12px;")
            detail_layout.addWidget(label_widget)
            
            # Barre de progression - CORRECTION: conversion en int
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(value))  # Conversion en int ici
            bar.setFormat(f"{value}%")
            
            # Couleur selon le type
            if color == "success":
                bar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
            elif color == "warning":
                bar.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
            elif color == "danger":
                bar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #3498db; }")
            
            detail_layout.addWidget(bar)
            details_layout.addWidget(detail_widget, row, col)
            self.detail_bars[label] = bar
        
        details_group.setLayout(details_layout)
        left_layout.addWidget(details_group)
        
        
        # Boutons de contrôle
        buttons_layout = QHBoxLayout()
        self.analyze_btn = QPushButton(" ANALYSER MAINTENANT")
        self.analyze_btn.clicked.connect(self.force_analysis)
        
        self.reset_btn = QPushButton(" RÉINITIALISER")
        self.reset_btn.clicked.connect(self.reset_confidence)
        
        buttons_layout.addWidget(self.analyze_btn)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addStretch()
        
        left_layout.addLayout(buttons_layout)
        
        # Colonne droite - Graphique d'évolution
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        
        graph_group = QGroupBox(" ÉVOLUTION DE LA CONFIANCE")
        graph_layout = QVBoxLayout()
        
        # Canvas matplotlib pour le graphique
        self.figure = Figure(figsize=(6, 5), facecolor='#0A1929', dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(300)
        
        # Initialisation du graphique
        self.confidence_history = [98.5, 98.2, 98.7, 98.4, 98.9, 98.3, 98.6]
        self.time_points = list(range(len(self.confidence_history)))
        self.update_graph()
        
        graph_layout.addWidget(self.canvas)
        
        # Statistiques en bas
        stats_layout = QHBoxLayout()
        stats_labels = [
            ("Moyenne", "98.5%"),
            ("Min", "97.8%"),
            ("Max", "99.2%"),
            ("Écart-type", "0.4%")
        ]
        
        for label, value in stats_labels:
            stat_widget = QLabel(f"{label}: {value}")
            stat_widget.setStyleSheet(f"color: {self.colors['info']}; font-size: 12px;")
            stats_layout.addWidget(stat_widget)
        
        graph_layout.addLayout(stats_layout)
        graph_group.setLayout(graph_layout)
        right_layout.addWidget(graph_group)
        
        # Assemblage
        content_layout.addWidget(left_column, 60)
        content_layout.addWidget(right_column, 40)
        
        main_layout.addLayout(content_layout)
        
        # Barre d'état
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"background-color: {self.colors['bg_medium']}; color: #00ff00;")
        self.status_bar.showMessage("✓ Système opérationnel - Surveillance active")
    
    def update_graph(self):
        """Met à jour le graphique d'évolution"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Création du graphique
        ax.plot(self.time_points, self.confidence_history, 
                color='#3498db', linewidth=2.5, marker='o', 
                markersize=6, markerfacecolor='#2ecc71')
        
        # Configuration
        ax.set_facecolor('#132F4C')
        ax.set_xlabel('Temps (échantillons)', color='white', fontsize=10)
        ax.set_ylabel('Niveau de confiance (%)', color='white', fontsize=10)
        ax.set_title('Évolution du niveau de confiance', color='white', fontsize=12, pad=15)
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3)
        
        # Limites
        ax.set_ylim(95, 100)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def update_confidence(self):
        """Met à jour les valeurs de confiance"""
        try:
            # Variation aléatoire mais réaliste
            base_confidence = random.uniform(97.0, 99.5)
            
            # Mise à jour de la barre principale - CORRECTION: conversion en int
            self.main_confidence_bar.setValue(int(base_confidence))
            self.confidence_value.setText(f"{base_confidence:.2f}%")
            
            # Changement de couleur selon le niveau
            if base_confidence >= 98:
                color = '#2ecc71'  # Vert
                status = "OPTIMAL"
            elif base_confidence >= 95:
                color = '#f39c12'  # Orange
                status = "ACCEPTABLE"
            else:
                color = '#e74c3c'  # Rouge
                status = "CRITIQUE"
            
            self.confidence_value.setStyleSheet(f"color: {color}; font-size: 48px; font-weight: bold;")
            self.status_bar.showMessage(f"✓ Confiance: {status} - {base_confidence:.2f}%")
            
            # Mise à jour des détails - CORRECTION: conversion en int
            details = {
                "Détection normale": random.uniform(98.5, 99.8),
                "Détection attaque": random.uniform(96.5, 98.5),
             
            }
            
            for label, value in details.items():
                if label in self.detail_bars:
                    bar = self.detail_bars[label]
                    bar.setValue(int(value))  # Conversion en int ici
                    bar.setFormat(f"{value:.1f}%")
            
            # Mise à jour de l'historique
            self.confidence_history.append(base_confidence)
            if len(self.confidence_history) > 20:
                self.confidence_history.pop(0)
            self.time_points = list(range(len(self.confidence_history)))
            
            self.update_graph()
            self.update_timestamp()
            
            # Log
            self.add_log_entry(f"Confiance mise à jour: {base_confidence:.2f}%")
            
        except Exception as e:
            print(f"Erreur: {e}")
    
    
    
    def force_analysis(self):
        """Force une analyse immédiate"""
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("ANALYSE...")
        QApplication.processEvents()
        
        # Simulation d'analyse
        self.add_log_entry("Analyse forcée demandée...")
        QTimer.singleShot(1000, self.complete_analysis)
    
    def complete_analysis(self):
        """Termine l'analyse forcée"""
        self.update_confidence()
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("ANALYSER MAINTENANT")
        self.add_log_entry("Analyse terminée")
    
    def reset_confidence(self):
        """Réinitialise les métriques de confiance"""
        self.add_log_entry("Réinitialisation du système...")
        
        # Réinitialisation
        self.confidence_history = [98.5, 98.2, 98.7, 98.4, 98.9, 98.3, 98.6]
        self.time_points = list(range(len(self.confidence_history)))
        
        self.main_confidence_bar.setValue(98)
        self.confidence_value.setText("98.5%")
        
        self.update_graph()
        self.add_log_entry("Système réinitialisé")
    
    def update_timestamp(self):
        """Met à jour l'horodatage"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(f"{current_time}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Police pour informaticien
    font = QFont("Consolas", 9)
    app.setFont(font)
    
    window = DetectionConfidenceWidget()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()