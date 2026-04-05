import sys
import os
from datetime import datetime, timedelta

# Ajouter le dossier parent pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import depuis le même dossier (data)
from data.db_connection import connect_db


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect_db()

    def connect_db(self):
        """Établit la connexion à la base de données"""
        try:
            self.connection = connect_db()
            if self.connection:
                print("✅ DatabaseManager connecté avec succès")
            else:
                print("⚠️ Échec de connexion pour DatabaseManager")
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            self.connection = None

    def get_attack_stats(self):
        """Récupère les statistiques d'attaques"""
        try:
            if not self.connection:
                self.connect_db()

            cursor = self.connection.cursor()

            # Nombre total d'attaques
            cursor.execute("SELECT COUNT(*) FROM security_alerts")
            total_attacks = cursor.fetchone()[0]

            # Attaques de la dernière heure
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute("""
                SELECT COUNT(*) FROM security_alerts 
                WHERE timestamp >= %s
            """, (one_hour_ago,))
            last_hour_attacks = cursor.fetchone()[0]

            # Distribution par sévérité
            cursor.execute("""
                SELECT severity, COUNT(*) 
                FROM security_alerts 
                GROUP BY severity
            """)
            severity_counts = dict(cursor.fetchall())

            cursor.close()
            return {
                'total_attacks': total_attacks,
                'last_hour_attacks': last_hour_attacks,
                'severity_counts': severity_counts
            }
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des statistiques: {e}")
            return {
                'total_attacks': 0,
                'last_hour_attacks': 0,
                'severity_counts': {'Élevée': 0, 'Moyenne': 0, 'Basse': 0}
            }

    def get_total_packets(self):
        """Simule ou récupère le nombre total de paquets analysés"""
        try:
            if not self.connection:
                self.connect_db()

            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM security_alerts")
            total = cursor.fetchone()[0]
            cursor.close()
            if total == 0:
                return 0
            return total * 100
        except Exception as e:
            print(f"❌ Erreur get_total_packets: {e}")
            return 0

    def calculate_risk_level(self):
        """Calcule le niveau de risque global"""
        try:
            if not self.connection:
                self.connect_db()

            cursor = self.connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM security_alerts")
            total_alerts = cursor.fetchone()[0]

            if total_alerts == 0:
                cursor.close()
                return 0

            last_24h = datetime.now() - timedelta(hours=24)
            cursor.execute("""
                SELECT severity, COUNT(*) 
                FROM security_alerts 
                WHERE timestamp >= %s
                GROUP BY severity
            """, (last_24h,))

            severity_data = dict(cursor.fetchall())

            if not severity_data:
                cursor.close()
                return 0

            risk_score = 0
            total_alerts_recent = sum(severity_data.values())

            if total_alerts_recent > 0:
                risk_score = (
                                     severity_data.get('Élevée', 0) * 3 +
                                     severity_data.get('Moyenne', 0) * 2 +
                                     severity_data.get('Basse', 0) * 1
                             ) / (total_alerts_recent * 3) * 100

            cursor.close()
            return min(100, int(risk_score))
        except Exception as e:
            print(f"❌ Erreur calcul risque: {e}")
            return 0

    def get_attacks_last_24h(self):
        """Retourne un tableau 0/1 pour les 24 dernières heures"""
        try:
            if not self.connection:
                self.connect_db()

            cursor = self.connection.cursor()

            last_24h = datetime.now() - timedelta(hours=24)

            cursor.execute("""
                SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*)
                FROM security_alerts
                WHERE timestamp >= %s
                GROUP BY EXTRACT(HOUR FROM timestamp)
                ORDER BY hour
            """, (last_24h,))

            rows = cursor.fetchall()

            hours = [0] * 24

            for r in rows:
                h = int(r[0])
                if r[1] > 0:
                    hours[h] = 1

            cursor.close()
            return hours

        except Exception as e:
            print(f"❌ Erreur histogramme: {e}")
            return [0] * 24

    def close_connection(self):
        """Ferme la connexion à la base de données"""
        if self.connection:
            self.connection.close()
            print("🔒 Connexion à la base de données fermée")