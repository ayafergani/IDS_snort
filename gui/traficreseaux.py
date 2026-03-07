import sys
import random
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pyqtgraph as pg
from collections import defaultdict

class TrafficAnalyzerInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analyseur de Trafic Réseau - Interface 3")
        screen = QApplication.primaryScreen()
        size = screen.size()

        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height()-80)
        
        # Données simulées
        self.traffic_data = self.generate_traffic_data()
        
        # Configuration du style moderne avec couleurs harmonisées
        self.setup_style()
        self.init_ui()
        
        # Timer pour mise à jour en temps réel
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(3000)  # Mise à jour toutes les 3 secondes
        
    def setup_style(self):
        """Configuration du style moderne et professionnel avec couleurs harmonisées"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E2E4F;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QLabel#title_label {
                font-size: 20px;
                font-weight: bold;
                color: white;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #335889, stop:1 #1E2E4F);
                border-radius: 8px;
            }
            QLabel#stat_label {
                font-size: 13px;
                font-weight: bold;
                color: #bbdefb;
            }
            QLabel#value_label {
                font-size: 22px;
                font-weight: bold;
                color: white;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: white;
                border: 2px solid #335889;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: rgba(30, 46, 79, 0.7);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #90caf9;
            }
            QTableWidget {
                background-color: rgba(47, 65, 102, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                gridline-color: #335889;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #335889;
            }
            QTableWidget::item:selected {
                background-color: #9b59b6;
            }
            QHeaderView::section {
                background-color: #335889;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar {
                border: 2px solid #335889;
                border-radius: 6px;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 22px;
                background-color: rgba(0, 0, 0, 0.3);
                font-size: 11px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9b59b6, stop:1 #8e44ad);
            }
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #6c3483;
            }
            QTabWidget::pane {
                border: 2px solid #335889;
                border-radius: 8px;
                background-color: rgba(30, 46, 79, 0.5);
            }
            QTabBar::tab {
                background-color: #335889;
                color: white;
                padding: 8px 18px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #9b59b6;
            }
            QTabBar::tab:hover {
                background-color: #8e44ad;
            }
            QLineEdit {
                padding: 8px;
                background-color: rgba(47, 65, 102, 0.8);
                border: 2px solid #335889;
                border-radius: 6px;
                color: white;
                font-size: 12px;
            }
        """)
        
    def init_ui(self):
        """Initialisation de l'interface utilisateur"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # En-tête
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # Contenu principal avec onglets
        tab_widget = QTabWidget()
        
        # Onglet 1 : Vue d'ensemble
        overview_tab = self.create_overview_tab()
        tab_widget.addTab(overview_tab, " Vue d'ensemble")
        
        # Onglet 2 : Détails des IP
        ip_tab = self.create_ip_tab()
        tab_widget.addTab(ip_tab, " Adresses IP")
        
        # Onglet 3 : Analyse des ports
        ports_tab = self.create_ports_tab()
        tab_widget.addTab(ports_tab, " Ports")
        
        main_layout.addWidget(tab_widget)
        
    def create_header(self):
        """Crée l'en-tête avec titre et informations générales"""
        header_layout = QHBoxLayout()
        
        # Titre principal
        title_label = QLabel(" ANALYSE DU TRAFIC RÉSEAU")
        title_label.setObjectName("title_label")
        
        # Horodatage
        self.time_label = QLabel()
        self.time_label.setObjectName("stat_label")
        self.update_timestamp()
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.time_label)
        
        return header_layout
    
    def create_overview_tab(self):
        """Crée l'onglet de vue d'ensemble avec Top 5 IP amélioré"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Statistiques globales
        stats_widget = self.create_stats_widget()
        layout.addWidget(stats_widget)
        
        # Graphique de répartition des protocoles
        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(15)
        
        # Graphique répartition des protocoles
        protocol_group = QGroupBox("Répartition des protocoles")
        protocol_layout = QVBoxLayout()
        protocol_layout.setSpacing(8)
        
        # TCP
        tcp_layout = QHBoxLayout()
        tcp_label = QLabel("TCP")
        tcp_label.setObjectName("stat_label")
        tcp_label.setMinimumWidth(50)
        self.tcp_bar = QProgressBar()
        self.tcp_bar.setRange(0, 100)
        self.tcp_bar.setValue(60)
        self.tcp_bar.setFormat("%p%")
        self.tcp_percent = QLabel("60%")
        self.tcp_percent.setObjectName("value_label")
        self.tcp_percent.setStyleSheet("color: #9b59b6; font-size: 18px;")
        tcp_layout.addWidget(tcp_label)
        tcp_layout.addWidget(self.tcp_bar)
        tcp_layout.addWidget(self.tcp_percent)
        protocol_layout.addLayout(tcp_layout)
        
        # UDP
        udp_layout = QHBoxLayout()
        udp_label = QLabel("UDP")
        udp_label.setObjectName("stat_label")
        udp_label.setMinimumWidth(50)
        self.udp_bar = QProgressBar()
        self.udp_bar.setRange(0, 100)
        self.udp_bar.setValue(30)
        self.udp_bar.setFormat("%p%")
        self.udp_percent = QLabel("30%")
        self.udp_percent.setObjectName("value_label")
        self.udp_percent.setStyleSheet("color: #66bb6a; font-size: 18px;")
        udp_layout.addWidget(udp_label)
        udp_layout.addWidget(self.udp_bar)
        udp_layout.addWidget(self.udp_percent)
        protocol_layout.addLayout(udp_layout)
        
        # ICMP
        icmp_layout = QHBoxLayout()
        icmp_label = QLabel("ICMP")
        icmp_label.setObjectName("stat_label")
        icmp_label.setMinimumWidth(50)
        self.icmp_bar = QProgressBar()
        self.icmp_bar.setRange(0, 100)
        self.icmp_bar.setValue(10)
        self.icmp_bar.setFormat("%p%")
        self.icmp_percent = QLabel("10%")
        self.icmp_percent.setObjectName("value_label")
        self.icmp_percent.setStyleSheet("color: #ffa726; font-size: 18px;")
        icmp_layout.addWidget(icmp_label)
        icmp_layout.addWidget(self.icmp_bar)
        icmp_layout.addWidget(self.icmp_percent)
        protocol_layout.addLayout(icmp_layout)
        
        protocol_group.setLayout(protocol_layout)
        chart_layout.addWidget(protocol_group)
        
        # Volume de données
        volume_group = QGroupBox("Volume de données")
        volume_layout = QVBoxLayout()
        
        self.volume_label = QLabel("2.4 GB")
        self.volume_label.setObjectName("value_label")
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_label.setStyleSheet("font-size: 19px;")
        volume_layout.addWidget(self.volume_label)
        
        volume_detail = QLabel("↑ 1.2 GB · ↓ 1.2 GB")
        volume_detail.setObjectName("stat_label")
        volume_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        volume_layout.addWidget(volume_detail)
        
        volume_group.setLayout(volume_layout)
        chart_layout.addWidget(volume_group)
        
        # Paquets par seconde
        pps_group = QGroupBox(" Paquets/s")
        pps_layout = QVBoxLayout()
        
        self.pps_label = QLabel("1,450")
        self.pps_label.setObjectName("value_label")
        self.pps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pps_label.setStyleSheet("font-size: 19px;")
        pps_layout.addWidget(self.pps_label)
        
        pps_trend = QLabel("+12% vs moyenne")
        pps_trend.setObjectName("stat_label")
        pps_trend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pps_trend.setStyleSheet("color: #4caf50;")
        pps_layout.addWidget(pps_trend)
        
        pps_group.setLayout(pps_layout)
        chart_layout.addWidget(pps_group)
        
        layout.addLayout(chart_layout)
        
        # Tableau Top 5 IP avec volume et paquets amélioré
        ip_group = QGroupBox("Top 5 IP - Volume de données et Paquets")
        ip_layout = QVBoxLayout()
        
        self.ip_table = QTableWidget()
        self.ip_table.setColumnCount(5)
        self.ip_table.setHorizontalHeaderLabels([
            "Adresse IP", 
            " Volume (MB)", 
            " Paquets", 
            "TCP/UDP/ICMP",
            "% Trafic"
        ])
        
        # Configuration des largeurs de colonnes
        header = self.ip_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.update_ip_table()
        ip_layout.addWidget(self.ip_table)
        
        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)
        
        return tab
    
    def create_ip_tab(self):
        """Crée l'onglet des détails IP"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        
        # Filtres
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtrer par IP:")
        filter_label.setObjectName("stat_label")
        filter_label.setStyleSheet("font-size: 12px;")
        
        self.ip_filter = QLineEdit()
        self.ip_filter.setPlaceholderText("Entrez une adresse IP...")
        
        filter_btn = QPushButton("🔍 Rechercher")
        filter_btn.setStyleSheet("font-size: 12px; padding: 8px 15px;")
        filter_btn.clicked.connect(self.filter_ips)
        
        reset_btn = QPushButton("🔄 Réinitialiser")
        reset_btn.setStyleSheet("font-size: 12px; padding: 8px 15px;")
        reset_btn.clicked.connect(self.reset_filter)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.ip_filter)
        filter_layout.addWidget(filter_btn)
        filter_layout.addWidget(reset_btn)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Tableau détaillé des IP
        self.detailed_ip_table = QTableWidget()
        self.detailed_ip_table.setColumnCount(6)
        self.detailed_ip_table.setHorizontalHeaderLabels([
            "Adresse IP", "Paquets TCP", "Paquets UDP", "Paquets ICMP", 
            "Volume Total", "Dernière activité"
        ])
        self.detailed_ip_table.horizontalHeader().setStretchLastSection(True)
        self.update_detailed_ip_table()
        
        layout.addWidget(self.detailed_ip_table)
        
        return tab
    
    def create_ports_tab(self):
        """Crée l'onglet d'analyse des ports"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        
        # Statistiques des ports
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        # Top ports TCP
        tcp_ports_group = QGroupBox(" Top ports TCP")
        tcp_ports_layout = QVBoxLayout()
        
        self.tcp_ports_table = QTableWidget()
        self.tcp_ports_table.setColumnCount(3)
        self.tcp_ports_table.setHorizontalHeaderLabels(["Port", "Service", "Connexions"])
        self.tcp_ports_table.horizontalHeader().setStretchLastSection(True)
        self.update_tcp_ports_table()
        tcp_ports_layout.addWidget(self.tcp_ports_table)
        
        tcp_ports_group.setLayout(tcp_ports_layout)
        stats_layout.addWidget(tcp_ports_group)
        
        # Top ports UDP
        udp_ports_group = QGroupBox("Top ports UDP")
        udp_ports_layout = QVBoxLayout()
        
        self.udp_ports_table = QTableWidget()
        self.udp_ports_table.setColumnCount(3)
        self.udp_ports_table.setHorizontalHeaderLabels(["Port", "Service", "Datagrammes"])
        self.udp_ports_table.horizontalHeader().setStretchLastSection(True)
        self.update_udp_ports_table()
        udp_ports_layout.addWidget(self.udp_ports_table)
        
        udp_ports_group.setLayout(udp_ports_layout)
        stats_layout.addWidget(udp_ports_group)
        
        layout.addLayout(stats_layout)
        
        # Graphique d'activité des ports
        ports_activity_group = QGroupBox("Activité des ports")
        ports_activity_layout = QVBoxLayout()
        ports_activity_layout.setSpacing(8)
        
        # Simulation d'un graphique avec des barres de progression
        ports_list = [80, 443, 22, 53, 3389, 8080, 3306, 5432]
        for port in ports_list[:5]:  # Top 5
            port_layout = QHBoxLayout()
            port_label = QLabel(f"Port {port}")
            port_label.setObjectName("stat_label")
            port_label.setMinimumWidth(80)
            port_label.setStyleSheet("font-size: 12px;")
            
            port_bar = QProgressBar()
            port_bar.setRange(0, 100)
            port_bar.setValue(random.randint(30, 95))
            port_bar.setFormat(f"{port_bar.value()} conn/s")
            port_bar.setStyleSheet("font-size: 11px;")
            
            port_layout.addWidget(port_label)
            port_layout.addWidget(port_bar)
            ports_activity_layout.addLayout(port_layout)
        
        ports_activity_group.setLayout(ports_activity_layout)
        layout.addWidget(ports_activity_group)
        
        return tab
    
    def create_stats_widget(self):
        """Crée le widget des statistiques rapides"""
        group = QGroupBox(" Statistiques en temps réel")
        group.setStyleSheet("font-size: 13px;")
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        stats = [
            (" Connexions actives", "1,234", "#9b59b6"),
            (" Taux de perte", "0.2%", "#4caf50"),
            (" Latence moyenne", "24ms", "#ff9800"),
            (" Sessions TCP", "892", "#f44336")
        ]
        
        for title, value, color in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setSpacing(5)
            
            title_label = QLabel(title)
            title_label.setObjectName("stat_label")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setStyleSheet("font-size: 12px;")
            
            value_label = QLabel(value)
            value_label.setObjectName("value_label")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet(f"color: {color}; font-size: 20px;")
            
            stat_layout.addWidget(title_label)
            stat_layout.addWidget(value_label)
            
            layout.addWidget(stat_widget)
        
        group.setLayout(layout)
        return group
    
    def generate_traffic_data(self):
        """Génère des données de trafic simulées"""
        data = {
            'ips': {},
            'ports_tcp': defaultdict(int),
            'ports_udp': defaultdict(int)
        }
        
        # Génération d'adresses IP simulées avec des volumes réalistes
        base_ips = [
            "192.168.1.50", "192.168.1.100", "192.168.1.150", 
            "192.168.1.200", "10.0.0.25", "10.0.0.50",
            "172.16.0.10", "172.16.0.20", "192.168.1.75",
            "192.168.1.125"
        ]
        
        for ip in base_ips:
            tcp = random.randint(500, 8000)
            udp = random.randint(200, 3000)
            icmp = random.randint(20, 800)
            data['ips'][ip] = {
                'tcp': tcp,
                'udp': udp,
                'icmp': icmp,
                'last_seen': datetime.now()
            }
        
        # Génération de ports populaires
        popular_ports = {
            80: 'HTTP', 443: 'HTTPS', 22: 'SSH', 53: 'DNS',
            3389: 'RDP', 8080: 'HTTP-Alt', 3306: 'MySQL',
            5432: 'PostgreSQL', 25: 'SMTP', 110: 'POP3'
        }
        
        for port, service in popular_ports.items():
            data['ports_tcp'][port] = random.randint(50, 1000)
            data['ports_udp'][port] = random.randint(20, 500)
        
        return data
    
    def update_data(self):
        """Met à jour les données en temps réel"""
        # Mise à jour des pourcentages
        tcp = random.randint(55, 65)
        udp = random.randint(25, 35)
        icmp = 100 - tcp - udp
        
        self.tcp_bar.setValue(tcp)
        self.udp_bar.setValue(udp)
        self.icmp_bar.setValue(icmp)
        
        self.tcp_percent.setText(f"{tcp}%")
        self.udp_percent.setText(f"{udp}%")
        self.icmp_percent.setText(f"{icmp}%")
        
        # Mise à jour du volume
        volume = random.uniform(1.8, 3.2)
        self.volume_label.setText(f"{volume:.1f} GB")
        
        # Mise à jour des paquets/s
        pps = random.randint(1200, 1800)
        self.pps_label.setText(f"{pps:,}")
        
        # Mise à jour des tableaux
        self.update_ip_table()
        self.update_detailed_ip_table()
        self.update_tcp_ports_table()
        self.update_udp_ports_table()
        
        # Mise à jour de l'horodatage
        self.update_timestamp()
    
    def update_timestamp(self):
        """Met à jour l'horodatage"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.setText(f"Dernière mise à jour : {current_time}")
    
    def update_ip_table(self):
        """Met à jour le tableau des IP les plus actives avec volume et paquets"""
        # Tri des IP par volume de données (simulé par le nombre total de paquets)
        sorted_ips = sorted(
            self.traffic_data['ips'].items(),
            key=lambda x: (x[1]['tcp'] + x[1]['udp'] + x[1]['icmp']) * random.uniform(0.8, 1.5),
            reverse=True
        )[:5]
        
        self.ip_table.setRowCount(len(sorted_ips))
        total_volume = sum((data['tcp'] + data['udp'] + data['icmp']) * 0.001 
                          for _, data in sorted_ips)
        
        for row, (ip, data) in enumerate(sorted_ips):
            packets = data['tcp'] + data['udp'] + data['icmp']
            volume = packets * random.uniform(0.0008, 0.0012)  # Simulation du volume en MB
            
            # Adresse IP
            ip_item = QTableWidgetItem(ip)
            ip_item.setForeground(QColor("#90caf9"))
            ip_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            
            # Volume
            volume_item = QTableWidgetItem(f"{volume:.1f} MB")
            volume_item.setForeground(QColor("#ffb74d"))
            volume_item.setFont(QFont("Segoe UI", 11))
            
            # Paquets
            packets_item = QTableWidgetItem(f"{packets:,}")
            packets_item.setForeground(QColor("#9b59b6"))
            packets_item.setFont(QFont("Segoe UI", 11))
            
            # Détail TCP/UDP/ICMP
            detail = f"TCP:{data['tcp']:,} | UDP:{data['udp']:,} | ICMP:{data['icmp']}"
            detail_item = QTableWidgetItem(detail)
            detail_item.setForeground(QColor("#bbdefb"))
            detail_item.setFont(QFont("Segoe UI", 10))
            
            # Pourcentage du trafic
            percent = (volume / total_volume * 100) if total_volume > 0 else 0
            percent_item = QTableWidgetItem(f"{percent:.1f}%")
            percent_item.setForeground(QColor("#a5d6a7"))
            percent_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            
            self.ip_table.setItem(row, 0, ip_item)
            self.ip_table.setItem(row, 1, volume_item)
            self.ip_table.setItem(row, 2, packets_item)
            self.ip_table.setItem(row, 3, detail_item)
            self.ip_table.setItem(row, 4, percent_item)
        
        self.ip_table.resizeColumnsToContents()
    
    def update_detailed_ip_table(self):
        """Met à jour le tableau détaillé des IP"""
        ips = list(self.traffic_data['ips'].items())
        self.detailed_ip_table.setRowCount(len(ips))
        
        for row, (ip, data) in enumerate(ips):
            items = [
                (ip, "#90caf9", 11),
                (f"{data['tcp']:,}", "#9b59b6", 11),
                (f"{data['udp']:,}", "#66bb6a", 11),
                (f"{data['icmp']:,}", "#ffa726", 11),
                (f"{(data['tcp']+data['udp']+data['icmp'])*0.001:.1f} MB", "#bbdefb", 11),
                (data['last_seen'].strftime("%H:%M:%S"), "#bbdefb", 10)
            ]
            
            for col, (value, color, size) in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setForeground(QColor(color))
                font = QFont("Segoe UI", size)
                item.setFont(font)
                self.detailed_ip_table.setItem(row, col, item)
        
        self.detailed_ip_table.resizeColumnsToContents()
    
    def update_tcp_ports_table(self):
        """Met à jour le tableau des ports TCP"""
        sorted_ports = sorted(
            self.traffic_data['ports_tcp'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        self.tcp_ports_table.setRowCount(len(sorted_ports))
        
        services = {
            80: 'HTTP', 443: 'HTTPS', 22: 'SSH', 3389: 'RDP',
            8080: 'HTTP-Alt', 3306: 'MySQL', 5432: 'PostgreSQL',
            25: 'SMTP', 110: 'POP3', 143: 'IMAP', 993: 'IMAPS',
            995: 'POP3S', 21: 'FTP', 23: 'Telnet'
        }
        
        for row, (port, count) in enumerate(sorted_ports):
            service = services.get(port, 'Inconnu')
            
            port_item = QTableWidgetItem(str(port))
            port_item.setForeground(QColor("#90caf9"))
            
            service_item = QTableWidgetItem(service)
            service_item.setForeground(QColor("#bbdefb"))
            
            count_item = QTableWidgetItem(f"{count:,}")
            count_item.setForeground(QColor("#9b59b6"))
            
            self.tcp_ports_table.setItem(row, 0, port_item)
            self.tcp_ports_table.setItem(row, 1, service_item)
            self.tcp_ports_table.setItem(row, 2, count_item)
    
    def update_udp_ports_table(self):
        """Met à jour le tableau des ports UDP"""
        sorted_ports = sorted(
            self.traffic_data['ports_udp'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        self.udp_ports_table.setRowCount(len(sorted_ports))
        
        services = {
            53: 'DNS', 67: 'DHCP', 68: 'DHCP', 69: 'TFTP',
            123: 'NTP', 161: 'SNMP', 162: 'SNMP-Trap',
            500: 'IPsec', 1194: 'OpenVPN'
        }
        
        for row, (port, count) in enumerate(sorted_ports):
            service = services.get(port, 'Inconnu')
            
            port_item = QTableWidgetItem(str(port))
            port_item.setForeground(QColor("#90caf9"))
            
            service_item = QTableWidgetItem(service)
            service_item.setForeground(QColor("#bbdefb"))
            
            count_item = QTableWidgetItem(f"{count:,}")
            count_item.setForeground(QColor("#66bb6a"))
            
            self.udp_ports_table.setItem(row, 0, port_item)
            self.udp_ports_table.setItem(row, 1, service_item)
            self.udp_ports_table.setItem(row, 2, count_item)
    
    def filter_ips(self):
        """Filtre les IP selon la recherche"""
        filter_text = self.ip_filter.text().lower()
        
        for row in range(self.detailed_ip_table.rowCount()):
            ip_item = self.detailed_ip_table.item(row, 0)
            if ip_item:
                match = filter_text in ip_item.text().lower()
                self.detailed_ip_table.setRowHidden(row, not match)
    
    def reset_filter(self):
        """Réinitialise le filtre IP"""
        self.ip_filter.clear()
        for row in range(self.detailed_ip_table.rowCount()):
            self.detailed_ip_table.setRowHidden(row, False)

def main():
    app = QApplication(sys.argv)
    
    # Configuration de la police globale réduite
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Création et affichage de la fenêtre
    window = TrafficAnalyzerInterface()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()