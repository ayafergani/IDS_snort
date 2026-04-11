import sys
import re
import logging
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import psycopg2
from psycopg2.extras import RealDictCursor
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DÉFINITION DES COULEURS (du deuxième code) ===
COLORS = {
    'bg_dark': '#0F172A',  # Fond principal très sombre
    'bg_medium': '#1E293B',  # Fond secondaire
    'accent': '#334155',  # Bordures/accent
    'text': '#94A3B8',  # Texte secondaire
    'text_bright': '#F1F5F9',  # Texte principal clair
    'info': '#0EA5E9',  # Bleu info (TCP, liens)
    'success': '#10B981',  # Vert succès (UDP, positif)
    'warning': '#F59E0B',  # Orange warning (ICMP, attention)
    'danger': '#EF4444'  # Rouge danger (erreurs)
}


class DatabaseManager:
    def __init__(self):
        self.db_config = {
            'host': '192.168.1.2',
            'database': 'ids_db',
            'user': 'marwa',
            'password': 'marwa',
            'port': 5432,
            'connect_timeout': 5
        }
        self.connection = None
        self.cache = {}
        self.last_cache_update = {}
        self.cache_ttl = 3
        self.reconnect_attempts = 0
        self.connect()

    def connect(self):
        """Établit la connexion avec gestion des erreurs"""
        try:
            if self.connection and not self.connection.closed:
                return True

            self.connection = psycopg2.connect(**self.db_config)
            self.connection.autocommit = True
            self.reconnect_attempts = 0
            logger.info("Connexion DB établie")
            return True
        except Exception as e:
            logger.error(f"Erreur DB: {e}")
            self.connection = None
            self.reconnect_attempts += 1

            if self.reconnect_attempts > 3:
                logger.warning("Trop de tentatives, pause de 5 secondes...")
                time.sleep(5)
                self.reconnect_attempts = 0
            return False

    def ensure_connection(self):
        """Vérifie et rétablit la connexion si nécessaire"""
        if not self.connection or self.connection.closed:
            return self.connect()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except:
            return self.connect()

    def parse_rx_tx(self, volume_str):
        """Parse le volume et retourne (rx, tx) en MB"""
        if not volume_str:
            return 0, 0
        try:
            rx_match = re.search(r'RX:\s*([\d.]+)MB', volume_str, re.IGNORECASE)
            tx_match = re.search(r'TX:\s*([\d.]+)MB', volume_str, re.IGNORECASE)
            rx = float(rx_match.group(1)) if rx_match else 0
            tx = float(tx_match.group(1)) if tx_match else 0
            return rx, tx
        except Exception as e:
            logger.error(f"Erreur parsing volume '{volume_str}': {e}")
            return 0, 0

    def parse_volume(self, volume_str):
        if not volume_str:
            return 0
        try:
            rx_match = re.search(r'RX:\s*([\d.]+)MB', volume_str, re.IGNORECASE)
            tx_match = re.search(r'TX:\s*([\d.]+)MB', volume_str, re.IGNORECASE)
            rx = float(rx_match.group(1)) if rx_match else 0
            tx = float(tx_match.group(1)) if tx_match else 0
            return rx + tx
        except:
            return 0

    def parse_loss(self, loss_str):
        if not loss_str:
            return 0
        try:
            if '%' in loss_str:
                return float(loss_str.replace('%', ''))
            return float(loss_str)
        except:
            return 0

    def _is_cache_valid(self, key):
        if key not in self.last_cache_update:
            return False
        return (datetime.now() - self.last_cache_update[key]).total_seconds() < self.cache_ttl

    def get_alerts(self, limit=100):
        if not self.ensure_connection():
            return []
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM alertes ORDER BY timestamp DESC LIMIT %s", (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur alerts: {e}")
            self.connection = None
            return []

    def get_statistics(self):
        cache_key = 'statistics'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        if not self.ensure_connection():
            return self._get_default_stats()

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT COUNT(*) as total_alerts FROM alertes")
                total_alerts = cursor.fetchone()['total_alerts']

                cursor.execute("""
                    SELECT COUNT(*) as recent_alerts 
                    FROM alertes 
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                """)
                recent_alerts = cursor.fetchone()['recent_alerts']

                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT source_ip) as unique_sources,
                        COUNT(DISTINCT CASE WHEN protocol = 'TCP' AND source_port IS NOT NULL THEN source_port END) as tcp_sessions,
                        COUNT(CASE WHEN protocol = 'TCP' THEN 1 END) as tcp_count,
                        COUNT(CASE WHEN protocol = 'UDP' THEN 1 END) as udp_count,
                        COUNT(CASE WHEN protocol = 'ICMP' THEN 1 END) as icmp_count
                    FROM alertes
                """)
                result = cursor.fetchone()

                cursor.execute("SELECT volume FROM alertes WHERE volume IS NOT NULL AND volume != ''")
                volumes = cursor.fetchall()

                total_rx_mb = 0
                total_tx_mb = 0

                for v in volumes:
                    rx, tx = self.parse_rx_tx(v['volume'])
                    total_rx_mb += rx
                    total_tx_mb += tx

                logger.info(f"SOMME TOTALE - RX: {total_rx_mb} MB, TX: {total_tx_mb} MB")

                cursor.execute("SELECT loss FROM alertes WHERE loss IS NOT NULL AND loss != ''")
                loss_records = cursor.fetchall()

                total_loss_sum = sum(self.parse_loss(r['loss']) for r in loss_records)
                total_loss_count = len(loss_records)

                avg_loss = (total_loss_sum / total_loss_count) if total_loss_count > 0 else 0

                LATENCY_FACTOR = 10
                avg_latency_ms = avg_loss * LATENCY_FACTOR

                cursor.execute("""
                    SELECT COUNT(*) as total_packets,
                           GREATEST(EXTRACT(EPOCH FROM (COALESCE(MAX(timestamp), NOW()) - COALESCE(MIN(timestamp), NOW()))), 1) as time_span
                    FROM alertes WHERE timestamp > NOW() - INTERVAL '1 hour'
                """)
                packet_stats = cursor.fetchone()
                packets_per_second = packet_stats['total_packets'] / packet_stats['time_span'] if packet_stats and \
                                                                                                  packet_stats[
                                                                                                      'time_span'] > 0 else 0

                stats = {
                    'total_alerts': total_alerts,
                    'recent_alerts': recent_alerts,
                    'unique_sources': result['unique_sources'] or 0,
                    'avg_loss': avg_loss,
                    'avg_latency_ms': avg_latency_ms,
                    'tcp_sessions': result['tcp_sessions'] or 0,
                    'protocol_stats': [
                        {'protocol': 'TCP', 'count': result['tcp_count'] or 0},
                        {'protocol': 'UDP', 'count': result['udp_count'] or 0},
                        {'protocol': 'ICMP', 'count': result['icmp_count'] or 0}
                    ],
                    'total_rx_mb': total_rx_mb,
                    'total_tx_mb': total_tx_mb,
                    'packets_per_second': packets_per_second
                }

                self.cache[cache_key] = stats
                self.last_cache_update[cache_key] = datetime.now()
                return stats
        except Exception as e:
            logger.error(f"Erreur stats: {e}")
            self.connection = None
            return self._get_default_stats()

    def _get_default_stats(self):
        return {
            'total_alerts': 0,
            'recent_alerts': 0,
            'unique_sources': 0,
            'avg_loss': 0,
            'avg_latency_ms': 0,
            'tcp_sessions': 0,
            'protocol_stats': [],
            'total_rx_mb': 0,
            'total_tx_mb': 0,
            'packets_per_second': 0
        }

    def get_top_ips(self, limit=5):
        cache_key = f'top_ips_{limit}'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        if not self.ensure_connection():
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT source_ip, COUNT(*) as packet_count,
                           COUNT(CASE WHEN protocol = 'TCP' THEN 1 END) as tcp_count,
                           COUNT(CASE WHEN protocol = 'UDP' THEN 1 END) as udp_count,
                           COUNT(CASE WHEN protocol = 'ICMP' THEN 1 END) as icmp_count
                    FROM alertes 
                    WHERE source_ip IS NOT NULL
                    GROUP BY source_ip 
                    ORDER BY packet_count DESC 
                    LIMIT %s
                """, (limit * 2,))
                ip_data = cursor.fetchall()

                result = []
                for ip in ip_data:
                    cursor.execute(
                        "SELECT volume FROM alertes WHERE source_ip = %s AND volume IS NOT NULL AND volume != ''",
                        (ip['source_ip'],))
                    total_volume_mb = sum(self.parse_volume(v['volume']) for v in cursor.fetchall())
                    result.append({
                        'source_ip': ip['source_ip'],
                        'packet_count': ip['packet_count'],
                        'total_volume': total_volume_mb,
                        'tcp_count': ip['tcp_count'],
                        'udp_count': ip['udp_count'],
                        'icmp_count': ip['icmp_count']
                    })

                result.sort(key=lambda x: x['total_volume'], reverse=True)
                result = result[:limit]

                self.cache[cache_key] = result
                self.last_cache_update[cache_key] = datetime.now()
                return result
        except Exception as e:
            logger.error(f"Erreur top IPs: {e}")
            self.connection = None
            return []

    def get_all_ips(self):
        cache_key = 'all_ips'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        if not self.ensure_connection():
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT source_ip, COUNT(*) as packet_count,
                           COUNT(CASE WHEN protocol = 'TCP' THEN 1 END) as tcp_count,
                           COUNT(CASE WHEN protocol = 'UDP' THEN 1 END) as udp_count,
                           COUNT(CASE WHEN protocol = 'ICMP' THEN 1 END) as icmp_count,
                           MAX(timestamp) as last_seen
                    FROM alertes 
                    WHERE source_ip IS NOT NULL
                    GROUP BY source_ip 
                    ORDER BY packet_count DESC 
                    LIMIT 50
                """)
                ip_data = cursor.fetchall()

                result = []
                for ip in ip_data:
                    cursor.execute(
                        "SELECT volume FROM alertes WHERE source_ip = %s AND volume IS NOT NULL AND volume != ''",
                        (ip['source_ip'],))
                    total_volume_mb = sum(self.parse_volume(v['volume']) for v in cursor.fetchall())
                    result.append({
                        'source_ip': ip['source_ip'],
                        'packet_count': ip['packet_count'],
                        'total_volume': total_volume_mb,
                        'tcp_count': ip['tcp_count'],
                        'udp_count': ip['udp_count'],
                        'icmp_count': ip['icmp_count'],
                        'last_seen': ip['last_seen']
                    })

                self.cache[cache_key] = result
                self.last_cache_update[cache_key] = datetime.now()
                return result
        except Exception as e:
            logger.error(f"Erreur all IPs: {e}")
            self.connection = None
            return []

    def get_port_stats(self):
        cache_key = 'port_stats'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        if not self.ensure_connection():
            return {'tcp_ports': [], 'udp_ports': []}

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                WITH all_ports AS (
                    SELECT source_port AS port, protocol, service
                    FROM alertes
                    WHERE source_port IS NOT NULL AND source_port > 0

                    UNION ALL

                    SELECT destination_port AS port, protocol, service
                    FROM alertes
                    WHERE destination_port IS NOT NULL AND destination_port > 0
                ),
                ranked_services AS (
                    SELECT port, service, COUNT(*) as service_count,
                           ROW_NUMBER() OVER (PARTITION BY port ORDER BY COUNT(*) DESC) as rn
                    FROM all_ports
                    WHERE service IS NOT NULL AND service != ''
                    GROUP BY port, service
                ),
                port_stats AS (
                    SELECT port, COUNT(*) as connection_count
                    FROM all_ports
                    WHERE protocol = 'TCP'
                    GROUP BY port
                )
                SELECT ps.port, ps.connection_count,
                       COALESCE(rs.service, 'Inconnu') as service_name
                FROM port_stats ps
                LEFT JOIN ranked_services rs 
                    ON ps.port = rs.port AND rs.rn = 1
                ORDER BY ps.connection_count DESC
                LIMIT 20
            """)
                tcp_ports = cursor.fetchall()

                cursor.execute("""
                WITH all_ports AS (
                    SELECT source_port AS port, protocol, service
                    FROM alertes
                    WHERE source_port IS NOT NULL AND source_port > 0

                    UNION ALL

                    SELECT destination_port AS port, protocol, service
                    FROM alertes
                    WHERE destination_port IS NOT NULL AND destination_port > 0
                )
                SELECT port, COUNT(*) as datagram_count,
                       COALESCE(
                           (SELECT service FROM all_ports ap2 
                            WHERE ap2.port = all_ports.port AND service IS NOT NULL AND service != ''
                            GROUP BY service ORDER BY COUNT(*) DESC LIMIT 1),
                           'Inconnu'
                       ) as service_name
                FROM all_ports
                WHERE protocol = 'UDP'
                GROUP BY port
                ORDER BY datagram_count DESC
                LIMIT 20
            """)
                udp_ports = cursor.fetchall()

                result = {'tcp_ports': tcp_ports, 'udp_ports': udp_ports}

                self.cache[cache_key] = result
                self.last_cache_update[cache_key] = datetime.now()
                return result

        except Exception as e:
            logger.error(f"Erreur ports: {e}")
            self.connection = None
            return {'tcp_ports': [], 'udp_ports': []}

    def close(self):
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Connexion DB fermée")


class TrafficAnalyzerInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analyseur de Trafic Réseau")
        screen = QApplication.primaryScreen().size()
        self.setGeometry(0, 0, screen.width(), screen.height() - 80)
        self.setFixedSize(screen.width(), screen.height() - 80)

        # Application du fond sombre
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        self.setPalette(palette)

        self.db_manager = DatabaseManager()
        self.setup_style()
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)

        self.last_ui_state = {}
        self.is_closing = False

    def show_service_details(self, item):
        if item is None:
            return
        if item.column() == 1:
            service_text = item.text()
            msg = QMessageBox(self)
            msg.setWindowTitle("Détail du service")
            msg.setText(f"Service sélectionné:\n\n{service_text}")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {COLORS['bg_dark']};
                }}
                QLabel {{
                    color: {COLORS['text_bright']};
                    font-size: 13px;
                }}
                QPushButton {{
                    background-color: {COLORS['info']};
                    color: white;
                    border-radius: 5px;
                    padding: 6px 15px;
                }}
                QPushButton:hover {{
                    background-color: #0284C7;
                }}
            """)
            msg.exec()

    def setup_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {COLORS['bg_dark']}; }}
            QLabel {{ 
                color: {COLORS['text_bright']}; 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 12px; 
            }}
            QLabel#title_label {{ 
                font-size: 20px; 
                font-weight: bold; 
                color: {COLORS['text_bright']}; 
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {COLORS['bg_medium']}, stop:1 {COLORS['bg_dark']}); 
                border-radius: 8px; 
            }}
            QLabel#stat_label {{ 
                font-size: 13px; 
                font-weight: bold; 
                color: {COLORS['text']}; 
            }}
            QLabel#value_label {{ 
                font-size: 22px; 
                font-weight: bold; 
                color: {COLORS['text_bright']}; 
            }}
            QGroupBox {{ 
                font-size: 14px; 
                font-weight: bold; 
                color: {COLORS['text_bright']}; 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 8px; 
                margin-top: 12px; 
                padding-top: 12px; 
                background-color: {COLORS['bg_medium']}; 
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                left: 15px; 
                padding: 0 8px; 
                color: {COLORS['info']}; 
            }}
            QTableWidget {{ 
                background-color: {COLORS['bg_medium']}; 
                color: {COLORS['text_bright']}; 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 6px; 
                gridline-color: {COLORS['accent']}; 
                font-size: 12px; 
            }}
            QTableWidget::item {{ 
                padding: 6px; 
                border-bottom: 1px solid {COLORS['accent']}; 
                background-color: {COLORS['bg_medium']};
            }}
            QTableWidget::item:selected {{ 
                background-color: {COLORS['info']}; 
                color: {COLORS['bg_dark']}; 
            }}
            QTableWidget::item:!selected {{
                background-color: {COLORS['bg_medium']};
            }}
            QHeaderView::section {{ 
                background-color: {COLORS['bg_dark']}; 
                color: {COLORS['text_bright']}; 
                padding: 8px; 
                border: none; 
                border-right: 1px solid {COLORS['accent']};
                border-bottom: 2px solid {COLORS['info']};
                font-weight: bold; 
                font-size: 12px; 
            }}
            QProgressBar {{ 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 6px; 
                text-align: center; 
                color: white; 
                font-weight: bold; 
                height: 22px; 
                background-color: {COLORS['bg_dark']}; 
                font-size: 11px; 
            }}
            QProgressBar::chunk {{ 
                border-radius: 4px; 
            }}
            QPushButton {{ 
                background-color: {COLORS['info']}; 
                color: white; 
                border: none; 
                border-radius: 6px; 
                padding: 8px 18px; 
                font-size: 12px; 
                font-weight: bold; 
            }}
            QPushButton:hover {{ background-color: #0284C7; }}
            QPushButton:pressed {{ background-color: #0369A1; }}
            QTabWidget::pane {{ 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 8px; 
                background-color: {COLORS['bg_dark']}; 
            }}
            QTabBar::tab {{ 
                background-color: {COLORS['bg_medium']}; 
                color: {COLORS['text']}; 
                padding: 8px 18px; 
                margin-right: 2px; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                font-size: 12px; 
                font-weight: bold; 
            }}
            QTabBar::tab:selected {{ 
                background-color: {COLORS['info']}; 
                color: {COLORS['bg_dark']}; 
            }}
            QTabBar::tab:hover {{ 
                background-color: #0284C7; 
                color: white;
            }}
            QLineEdit {{ 
                padding: 8px; 
                background-color: {COLORS['bg_medium']}; 
                border: 1px solid {COLORS['accent']}; 
                border-radius: 6px; 
                color: {COLORS['text_bright']}; 
                font-size: 12px; 
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['info']};
            }}
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        header_layout = QHBoxLayout()
        title_label = QLabel("🌐 ANALYSE DU TRAFIC RÉSEAU")
        title_label.setObjectName("title_label")
        self.db_status_label = QLabel()
        self.db_status_label.setObjectName("stat_label")
        self.time_label = QLabel()
        self.time_label.setObjectName("stat_label")
        self.update_db_status()
        self.update_timestamp()

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.db_status_label)
        header_layout.addWidget(self.time_label)
        main_layout.addLayout(header_layout)

        tab_widget = QTabWidget()
        tab_widget.addTab(self.create_overview_tab(), "📊 Vue d'ensemble")
        tab_widget.addTab(self.create_ip_tab(), "🌐 Adresses IP")
        tab_widget.addTab(self.create_ports_tab(), "🔌 Ports")
        main_layout.addWidget(tab_widget)

    def create_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        group = QGroupBox(" Statistiques en temps réel")
        group.setStyleSheet("font-size: 13px;")
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self.total_alerts_label = QLabel()
        self.loss_rate_label = QLabel()
        self.tcp_sessions_label = QLabel()
        self.latency_label = QLabel()

        stats_data = [
            (" Total des alertes", self.total_alerts_label, COLORS['warning']),
            (" Taux de perte", self.loss_rate_label, COLORS['success']),
            (" Sessions TCP", self.tcp_sessions_label, COLORS['info']),
            (" Latence moyenne", self.latency_label, COLORS['warning'])
        ]

        for title, label, color in stats_data:
            widget = QWidget()
            vlayout = QVBoxLayout(widget)
            vlayout.setSpacing(5)
            t = QLabel(title)
            t.setObjectName("stat_label")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setStyleSheet("font-size: 12px;")
            label.setObjectName("value_label")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {color}; font-size: 20px;")
            vlayout.addWidget(t)
            vlayout.addWidget(label)
            stats_layout.addWidget(widget)
        group.setLayout(stats_layout)
        layout.addWidget(group)

        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(15)

        protocol_group = QGroupBox("Répartition des protocoles")
        protocol_layout = QVBoxLayout()
        protocol_layout.setSpacing(8)

        self.tcp_bar = QProgressBar()
        self.udp_bar = QProgressBar()
        self.icmp_bar = QProgressBar()
        self.tcp_percent = QLabel()
        self.udp_percent = QLabel()
        self.icmp_percent = QLabel()

        for name, bar, pct, color in [("TCP", self.tcp_bar, self.tcp_percent, COLORS['info']),
                                      ("UDP", self.udp_bar, self.udp_percent, COLORS['success']),
                                      ("ICMP", self.icmp_bar, self.icmp_percent, COLORS['warning'])]:
            hlayout = QHBoxLayout()
            label = QLabel(name)
            label.setObjectName("stat_label")
            label.setMinimumWidth(50)
            bar.setRange(0, 100)
            bar.setFormat("%p%")
            bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}")
            pct.setObjectName("value_label")
            pct.setStyleSheet(f"color: {color}; font-size: 18px;")
            hlayout.addWidget(label)
            hlayout.addWidget(bar)
            hlayout.addWidget(pct)
            protocol_layout.addLayout(hlayout)
        protocol_group.setLayout(protocol_layout)
        chart_layout.addWidget(protocol_group)

        volume_group = QGroupBox("Volume de données (Total)")
        volume_layout = QVBoxLayout()

        self.total_rx_label = QLabel("📥 RX Total: 0 MB")
        self.total_rx_label.setObjectName("value_label")
        self.total_rx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_rx_label.setStyleSheet(f"font-size: 15px; color: {COLORS['info']};")
        volume_layout.addWidget(self.total_rx_label)

        self.total_tx_label = QLabel("📤 TX Total: 0 MB")
        self.total_tx_label.setObjectName("value_label")
        self.total_tx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_tx_label.setStyleSheet(f"font-size: 15px; color: {COLORS['success']};")
        volume_layout.addWidget(self.total_tx_label)

        self.total_volume_label = QLabel("📊 Volume Total: 0 MB")
        self.total_volume_label.setObjectName("value_label")
        self.total_volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_volume_label.setStyleSheet(f"font-size: 14px; color: {COLORS['warning']};")
        volume_layout.addWidget(self.total_volume_label)

        volume_detail = QLabel("Somme de tous les volumes (Réception + Émission)")
        volume_detail.setObjectName("stat_label")
        volume_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        volume_layout.addWidget(volume_detail)

        volume_group.setLayout(volume_layout)
        chart_layout.addWidget(volume_group)

        pps_group = QGroupBox(" Paquets/s")
        pps_layout = QVBoxLayout()
        self.pps_label = QLabel("0")
        self.pps_label.setObjectName("value_label")
        self.pps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pps_label.setStyleSheet(f"font-size: 24px; color: {COLORS['info']};")
        pps_layout.addWidget(self.pps_label)
        pps_trend = QLabel("Données en temps réel")
        pps_trend.setObjectName("stat_label")
        pps_trend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pps_trend.setStyleSheet(f"color: {COLORS['success']};")
        pps_layout.addWidget(pps_trend)
        pps_group.setLayout(pps_layout)
        chart_layout.addWidget(pps_group)
        layout.addLayout(chart_layout)

        ip_group = QGroupBox("Top 5 IP - Volume de données et Paquets")
        ip_layout = QVBoxLayout()
        self.ip_table = QTableWidget()
        self.ip_table.setColumnCount(5)
        self.ip_table.setHorizontalHeaderLabels(["Adresse IP", " Volume (MB)", " Paquets", "TCP/UDP/ICMP", "% Trafic"])
        self.ip_table.setAlternatingRowColors(True)
        header = self.ip_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        ip_layout.addWidget(self.ip_table)
        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)

        return tab

    def create_ip_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

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

        self.detailed_ip_table = QTableWidget()
        self.detailed_ip_table.setColumnCount(6)
        self.detailed_ip_table.setHorizontalHeaderLabels(
            ["Adresse IP", "Paquets TCP", "Paquets UDP", "Paquets ICMP", "Volume Total", "Dernière activité"])
        self.detailed_ip_table.setAlternatingRowColors(True)
        self.detailed_ip_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.detailed_ip_table)

        return tab

    def create_ports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        tcp_ports_group = QGroupBox(" Top ports TCP")
        tcp_ports_group.setMinimumHeight(300)
        tcp_ports_group.setMaximumHeight(400)
        tcp_ports_layout = QVBoxLayout()
        self.tcp_ports_table = QTableWidget()
        self.tcp_ports_table.setColumnCount(3)
        self.tcp_ports_table.setHorizontalHeaderLabels(["Port", "Service", "Connexions"])
        self.tcp_ports_table.horizontalHeader().setStretchLastSection(True)
        self.tcp_ports_table.setAlternatingRowColors(True)
        self.tcp_ports_table.itemClicked.connect(self.show_service_details)

        tcp_ports_layout.addWidget(self.tcp_ports_table)
        tcp_ports_group.setLayout(tcp_ports_layout)
        stats_layout.addWidget(tcp_ports_group)

        udp_ports_group = QGroupBox(" Top ports UDP")
        udp_ports_group.setMinimumHeight(300)
        udp_ports_group.setMaximumHeight(400)
        udp_ports_layout = QVBoxLayout()
        self.udp_ports_table = QTableWidget()
        self.udp_ports_table.setColumnCount(3)
        self.udp_ports_table.setHorizontalHeaderLabels(["Port", "Service", "Datagrammes"])
        self.udp_ports_table.horizontalHeader().setStretchLastSection(True)
        self.udp_ports_table.setAlternatingRowColors(True)
        self.udp_ports_table.itemClicked.connect(self.show_service_details)
        udp_ports_layout.addWidget(self.udp_ports_table)
        udp_ports_group.setLayout(udp_ports_layout)
        stats_layout.addWidget(udp_ports_group)

        ports_activity_group = QGroupBox(" Activité des ports (22-SSH, 53-DNS, 80-HTTP)")
        ports_activity_group.setMinimumHeight(300)
        ports_activity_group.setMaximumHeight(400)
        self.ports_activity_layout = QVBoxLayout()
        ports_activity_group.setLayout(self.ports_activity_layout)
        stats_layout.addWidget(ports_activity_group)

        layout.addLayout(stats_layout)

        return tab

    def update_db_status(self):
        if self.db_manager.connection and not self.db_manager.connection.closed:
            self.db_status_label.setText("✅ Base de données connectée")
            self.db_status_label.setStyleSheet(f"color: {COLORS['success']};")
        else:
            self.db_status_label.setText("❌ Base de données déconnectée")
            self.db_status_label.setStyleSheet(f"color: {COLORS['danger']};")

    def update_timestamp(self):
        self.time_label.setText(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    def _should_update_ui(self, key, new_value):
        if key not in self.last_ui_state or self.last_ui_state[key] != new_value:
            self.last_ui_state[key] = new_value
            return True
        return False

    def update_data(self):
        if self.is_closing:
            return

        try:
            stats = self.db_manager.get_statistics()

            total_alerts_str = f"{stats['total_alerts']:,}"
            if self._should_update_ui('total_alerts', total_alerts_str):
                self.total_alerts_label.setText(total_alerts_str)

            loss_str = f"{stats['avg_loss']:.2f}%"
            if self._should_update_ui('loss_rate', loss_str):
                self.loss_rate_label.setText(loss_str)

            tcp_sessions_str = f"{stats['tcp_sessions']:,}"
            if self._should_update_ui('tcp_sessions', tcp_sessions_str):
                self.tcp_sessions_label.setText(tcp_sessions_str)

            latency_str = f"{stats['avg_latency_ms']:.0f}ms"
            if self._should_update_ui('latency', latency_str):
                self.latency_label.setText(latency_str)

            protocol_counts = {p['protocol']: p['count'] for p in stats['protocol_stats']}
            total = sum(protocol_counts.values())
            if total > 0:
                tcp_percent = (protocol_counts.get('TCP', 0) / total) * 100
                udp_percent = (protocol_counts.get('UDP', 0) / total) * 100
                icmp_percent = (protocol_counts.get('ICMP', 0) / total) * 100

                if self._should_update_ui('tcp_bar', int(tcp_percent)):
                    self.tcp_bar.setValue(int(tcp_percent))
                    self.tcp_percent.setText(f"{tcp_percent:.0f}%")
                if self._should_update_ui('udp_bar', int(udp_percent)):
                    self.udp_bar.setValue(int(udp_percent))
                    self.udp_percent.setText(f"{udp_percent:.0f}%")
                if self._should_update_ui('icmp_bar', int(icmp_percent)):
                    self.icmp_bar.setValue(int(icmp_percent))
                    self.icmp_percent.setText(f"{icmp_percent:.0f}%")

            total_rx_mb = stats['total_rx_mb']
            total_tx_mb = stats['total_tx_mb']
            total_volume_mb = total_rx_mb + total_tx_mb

            if total_rx_mb >= 1024:
                total_rx_str = f"📥 RX Total: {total_rx_mb / 1024:.2f} GB"
            else:
                total_rx_str = f"📥 RX Total: {total_rx_mb:.2f} MB"

            if total_tx_mb >= 1024:
                total_tx_str = f"📤 TX Total: {total_tx_mb / 1024:.2f} GB"
            else:
                total_tx_str = f"📤 TX Total: {total_tx_mb:.2f} MB"

            if total_volume_mb >= 1024:
                total_vol_str = f"📊 Volume Total: {total_volume_mb / 1024:.2f} GB"
            else:
                total_vol_str = f"📊 Volume Total: {total_volume_mb:.2f} MB"

            if self._should_update_ui('total_rx', total_rx_str):
                self.total_rx_label.setText(total_rx_str)
            if self._should_update_ui('total_tx', total_tx_str):
                self.total_tx_label.setText(total_tx_str)
            if self._should_update_ui('total_volume', total_vol_str):
                self.total_volume_label.setText(total_vol_str)

            pps_str = f"{stats['packets_per_second']:.0f}"
            if self._should_update_ui('pps', pps_str):
                self.pps_label.setText(pps_str)

            self.update_ip_table()
            self.update_detailed_ip_table()
            self.update_tcp_ports_table()
            self.update_udp_ports_table()
            self.update_port_activity()
            self.update_timestamp()
            self.update_db_status()
        except Exception as e:
            logger.error(f"Erreur update: {e}")

    def update_ip_table(self):
        try:
            top_ips = self.db_manager.get_top_ips(5)
            if top_ips:
                self.ip_table.setRowCount(len(top_ips))
                total_volume = sum(ip['total_volume'] for ip in top_ips)
                for row, ip in enumerate(top_ips):
                    for col, (value, color, size) in enumerate([
                        (ip['source_ip'], COLORS['text_bright'], 11),
                        (f"{ip['total_volume']:.1f} MB", COLORS['warning'], 11),
                        (f"{ip['packet_count']:,}", COLORS['info'], 11),
                        (f"TCP:{ip['tcp_count']:,} | UDP:{ip['udp_count']:,} | ICMP:{ip['icmp_count']}", COLORS['text'],
                         10),
                        (f"{(ip['total_volume'] / total_volume * 100) if total_volume > 0 else 0:.1f}%",
                         COLORS['success'], 11)
                    ]):
                        item = QTableWidgetItem(str(value))
                        item.setForeground(QColor(color))
                        if col in [0, 4]:
                            item.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
                        else:
                            item.setFont(QFont("Segoe UI", size))
                        self.ip_table.setItem(row, col, item)
                self.ip_table.resizeColumnsToContents()
        except Exception as e:
            logger.error(f"Erreur IP table: {e}")

    def update_detailed_ip_table(self):
        try:
            all_ips = self.db_manager.get_all_ips()
            if all_ips:
                self.detailed_ip_table.setRowCount(len(all_ips))
                for row, ip in enumerate(all_ips):
                    last_seen = ip['last_seen'].strftime("%H:%M:%S") if ip['last_seen'] else "N/A"
                    for col, (value, color, size) in enumerate([
                        (ip['source_ip'], COLORS['text_bright'], 11),
                        (f"{ip['tcp_count']:,}", COLORS['info'], 11),
                        (f"{ip['udp_count']:,}", COLORS['success'], 11),
                        (f"{ip['icmp_count']:,}", COLORS['warning'], 11),
                        (f"{ip['total_volume']:.1f} MB", COLORS['text_bright'], 11),
                        (last_seen, COLORS['text'], 10)
                    ]):
                        item = QTableWidgetItem(str(value))
                        item.setForeground(QColor(color))
                        item.setFont(QFont("Segoe UI", size))
                        self.detailed_ip_table.setItem(row, col, item)
                self.detailed_ip_table.resizeColumnsToContents()
        except Exception as e:
            logger.error(f"Erreur detailed IP: {e}")

    def update_tcp_ports_table(self):
        try:
            ports = self.db_manager.get_port_stats()['tcp_ports']
            if ports:
                self.tcp_ports_table.setRowCount(len(ports))
                for row, p in enumerate(ports):
                    service = p['service_name'] if p['service_name'] else 'Inconnu'
                    # Pas de setBackground - le style CSS gère le fond sombre
                    self.tcp_ports_table.setItem(row, 0, QTableWidgetItem(str(p['port'])))
                    self.tcp_ports_table.setItem(row, 1, QTableWidgetItem(service))
                    self.tcp_ports_table.setItem(row, 2, QTableWidgetItem(f"{p['connection_count']:,}"))
            else:
                self.tcp_ports_table.setRowCount(1)
                self.tcp_ports_table.setItem(0, 0, QTableWidgetItem("Aucun port TCP"))
                self.tcp_ports_table.setItem(0, 1, QTableWidgetItem("-"))
                self.tcp_ports_table.setItem(0, 2, QTableWidgetItem("0"))
        except Exception as e:
            logger.error(f"Erreur TCP ports: {e}")
            self.tcp_ports_table.setRowCount(1)
            self.tcp_ports_table.setItem(0, 0, QTableWidgetItem("Erreur de chargement"))
            self.tcp_ports_table.setItem(0, 1, QTableWidgetItem("-"))
            self.tcp_ports_table.setItem(0, 2, QTableWidgetItem("0"))

    def update_udp_ports_table(self):
        try:
            ports = self.db_manager.get_port_stats()['udp_ports']
            if ports:
                self.udp_ports_table.setRowCount(len(ports))
                for row, p in enumerate(ports):
                    service = p['service_name'] if p['service_name'] else 'Inconnu'
                    # Pas de setBackground - le style CSS gère le fond sombre
                    self.udp_ports_table.setItem(row, 0, QTableWidgetItem(str(p['port'])))
                    self.udp_ports_table.setItem(row, 1, QTableWidgetItem(service))
                    self.udp_ports_table.setItem(row, 2, QTableWidgetItem(f"{p['datagram_count']:,}"))
            else:
                self.udp_ports_table.setRowCount(1)
                self.udp_ports_table.setItem(0, 0, QTableWidgetItem("Aucun port UDP"))
                self.udp_ports_table.setItem(0, 1, QTableWidgetItem("-"))
                self.udp_ports_table.setItem(0, 2, QTableWidgetItem("0"))
        except Exception as e:
            logger.error(f"Erreur UDP ports: {e}")
            self.udp_ports_table.setRowCount(1)
            self.udp_ports_table.setItem(0, 0, QTableWidgetItem("Erreur de chargement"))
            self.udp_ports_table.setItem(0, 1, QTableWidgetItem("-"))
            self.udp_ports_table.setItem(0, 2, QTableWidgetItem("0"))

    def _create_item(self, text, color):
        item = QTableWidgetItem(text)
        item.setForeground(QColor(color))
        return item

    def update_port_activity(self):
        for i in reversed(range(self.ports_activity_layout.count())):
            w = self.ports_activity_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        try:
            port_stats = self.db_manager.get_port_stats()
            ports_a_surveiller = [22, 53, 80]

            port_data_map = {}
            for port in ports_a_surveiller:
                port_data_map[port] = {
                    'tcp_count': 0,
                    'udp_count': 0,
                    'service': 'Inconnu'
                }

                for p in port_stats['tcp_ports']:
                    if p['port'] == port:
                        port_data_map[port]['service'] = p['service_name']
                        break

            for p in port_stats['tcp_ports']:
                if p['port'] in ports_a_surveiller:
                    port_data_map[p['port']]['tcp_count'] = p['connection_count']

            for p in port_stats['udp_ports']:
                if p['port'] in ports_a_surveiller:
                    port_data_map[p['port']]['udp_count'] = p['datagram_count']

            max_activite = 0
            for port in ports_a_surveiller:
                max_activite = max(max_activite, port_data_map[port]['tcp_count'], port_data_map[port]['udp_count'])

            for port in ports_a_surveiller:
                data = port_data_map[port]

                port_widget = QWidget()
                port_layout = QHBoxLayout(port_widget)
                port_layout.setSpacing(10)
                port_layout.setContentsMargins(5, 5, 5, 5)

                port_label = QLabel(f"Port {port} ")
                port_label.setObjectName("stat_label")
                port_label.setMinimumWidth(120)
                port_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['text_bright']};")
                port_layout.addWidget(port_label)

                activite_total = data['tcp_count'] + data['udp_count']

                bar_container = QWidget()
                bar_layout = QVBoxLayout(bar_container)
                bar_layout.setSpacing(3)
                bar_layout.setContentsMargins(0, 0, 0, 0)

                if activite_total > 0:
                    tcp_bar = QProgressBar()
                    if max_activite > 0:
                        tcp_percent = int((data['tcp_count'] / max_activite) * 100)
                        tcp_bar.setValue(tcp_percent)
                    else:
                        tcp_bar.setValue(0)
                    tcp_bar.setFormat(f"TCP: {data['tcp_count']:,} connexions")
                    tcp_bar.setStyleSheet(f"""
                        QProgressBar {{
                            border: 1px solid {COLORS['accent']};
                            border-radius: 6px;
                            text-align: center;
                            color: white;
                            font-weight: bold;
                            height: 24px;
                            background-color: {COLORS['bg_dark']};
                            font-size: 11px;
                        }}
                        QProgressBar::chunk {{
                            border-radius: 4px;
                            background-color: {COLORS['info']};
                        }}
                    """)
                    bar_layout.addWidget(tcp_bar)

                    udp_bar = QProgressBar()
                    if max_activite > 0:
                        udp_percent = int((data['udp_count'] / max_activite) * 100)
                        udp_bar.setValue(udp_percent)
                    else:
                        udp_bar.setValue(0)
                    udp_bar.setFormat(f"UDP: {data['udp_count']:,} datagrammes")
                    udp_bar.setStyleSheet(f"""
                        QProgressBar {{
                            border: 1px solid {COLORS['accent']};
                            border-radius: 6px;
                            text-align: center;
                            color: white;
                            font-weight: bold;
                            height: 24px;
                            background-color: {COLORS['bg_dark']};
                            font-size: 11px;
                        }}
                        QProgressBar::chunk {{
                            border-radius: 4px;
                            background-color: {COLORS['success']};
                        }}
                    """)
                    bar_layout.addWidget(udp_bar)
                else:
                    no_activity_bar = QProgressBar()
                    no_activity_bar.setValue(0)
                    no_activity_bar.setFormat("Aucune activité détectée")
                    no_activity_bar.setStyleSheet(f"""
                        QProgressBar {{
                            border: 1px solid {COLORS['accent']};
                            border-radius: 6px;
                            text-align: center;
                            color: {COLORS['text']};
                            font-weight: bold;
                            height: 48px;
                            background-color: {COLORS['bg_dark']};
                            font-size: 11px;
                        }}
                    """)
                    bar_layout.addWidget(no_activity_bar)

                port_layout.addWidget(bar_container, 1)

                total_label = QLabel(f"Total: {activite_total:,}")
                total_label.setObjectName("stat_label")
                total_label.setMinimumWidth(80)
                total_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['warning']};")
                total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                port_layout.addWidget(total_label)

                self.ports_activity_layout.addWidget(port_widget)

                if port != ports_a_surveiller[-1]:
                    separator = QFrame()
                    separator.setFrameShape(QFrame.Shape.HLine)
                    separator.setStyleSheet(f"background-color: {COLORS['accent']}; max-height: 1px;")
                    self.ports_activity_layout.addWidget(separator)

            total_tcp = sum(port_data_map[p]['tcp_count'] for p in ports_a_surveiller)
            total_udp = sum(port_data_map[p]['udp_count'] for p in ports_a_surveiller)

            summary_widget = QWidget()
            summary_widget.setStyleSheet(
                f"background-color: {COLORS['bg_medium']}; border-radius: 6px; margin-top: 10px;")
            summary_layout = QHBoxLayout(summary_widget)
            summary_layout.setContentsMargins(10, 8, 10, 8)

            total_tcp_label = QLabel(f"📊 Total TCP: {total_tcp:,} connexions")
            total_tcp_label.setObjectName("stat_label")
            total_tcp_label.setStyleSheet(f"font-size: 11px; color: {COLORS['info']}; font-weight: bold;")

            total_udp_label = QLabel(f"📊 Total UDP: {total_udp:,} datagrammes")
            total_udp_label.setObjectName("stat_label")
            total_udp_label.setStyleSheet(f"font-size: 11px; color: {COLORS['success']}; font-weight: bold;")

            summary_layout.addWidget(total_tcp_label)
            summary_layout.addStretch()
            summary_layout.addWidget(total_udp_label)

            self.ports_activity_layout.addWidget(summary_widget)

        except Exception as e:
            logger.error(f"Erreur port activity: {e}")
            error_label = QLabel(f"Erreur lors du chargement des données: {str(e)}")
            error_label.setObjectName("stat_label")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet(f"color: {COLORS['danger']}; padding: 20px;")
            self.ports_activity_layout.addWidget(error_label)

    def filter_ips(self):
        filter_text = self.ip_filter.text().lower()
        for row in range(self.detailed_ip_table.rowCount()):
            ip_item = self.detailed_ip_table.item(row, 0)
            if ip_item:
                self.detailed_ip_table.setRowHidden(row, not (filter_text in ip_item.text().lower()))

    def reset_filter(self):
        self.ip_filter.clear()
        for row in range(self.detailed_ip_table.rowCount()):
            self.detailed_ip_table.setRowHidden(row, False)

    def closeEvent(self, event):
        self.is_closing = True
        self.timer.stop()
        self.db_manager.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont("Segoe UI", 9))
    window = TrafficAnalyzerInterface()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()