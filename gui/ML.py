import sys
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

import warnings
warnings.filterwarnings('ignore')

try:
    from config import COLORS, INPUT_STYLE, BTN_PRIMARY_STYLE, BTN_SECONDARY_STYLE
except ImportError:
    COLORS = {
        'bg_dark':    '#0f172a',
        'bg_medium':  '#1e293b',
        'text_bright':'#f8fafc',
        'info':       '#0EA5E9',
        'accent':     '#06b6d4',
        'success':    '#10b981',
        'danger':     '#ef4444',
        'warning':    '#f59e0b',
    }
    INPUT_STYLE = ""
    BTN_PRIMARY_STYLE = ""
    BTN_SECONDARY_STYLE = ""

REQUIRED_FILES = {
    'model':    'lightgbm_final.pkl',
    'scaler':   'scaler.pkl',
    'encoder':  'label_encoder.pkl',
    'features': 'feature_cols.pkl',
}


# ============================================================
# WORKER
# ============================================================
class PredictionWorker(QThread):
    progress    = pyqtSignal(int)
    status_msg  = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error       = pyqtSignal(str)

    def __init__(self, csv_path, model, scaler, encoder, features):
        super().__init__()
        self.csv_path = csv_path
        self.model    = model
        self.scaler   = scaler
        self.encoder  = encoder
        self.features = features

    def run(self):
        try:
            self.status_msg.emit("Lecture CSV…")
            self.progress.emit(10)
            df_raw = pd.read_csv(self.csv_path)
            n_rows = len(df_raw)

            label_col = self._detect_label(df_raw)
            y_true = None
            if label_col:
                y_true = df_raw[label_col].copy()
                df_raw = df_raw.drop(columns=[label_col])

            self.status_msg.emit("Alignement features…")
            self.progress.emit(30)
            missing = [f for f in self.features if f not in df_raw.columns]
            if missing:
                raise ValueError(f"Colonnes manquantes : {missing[:5]}")
            df = df_raw[self.features].copy()
            for col in df.select_dtypes(include='object').columns:
                from sklearn.preprocessing import LabelEncoder as _LE
                df[col] = _LE().fit_transform(df[col].astype(str))
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(df.median(numeric_only=True)).fillna(0)

            self.status_msg.emit("Prédiction LightGBM…")
            self.progress.emit(55)
            X = self.scaler.transform(df.values.astype(np.float64))
            y_pred_enc = self.model.predict(X)

            if hasattr(self.model, 'predict_proba'):
                probas = self.model.predict_proba(X)
                conf_per_row = probas.max(axis=1)
                global_conf  = float(conf_per_row.mean()) * 100
            else:
                conf_per_row = np.ones(len(y_pred_enc)) * 0.95
                global_conf  = 95.0

            self.status_msg.emit("Décodage classes…")
            self.progress.emit(80)
            try:
                y_pred_labels = self.encoder.inverse_transform(y_pred_enc.astype(int))
            except Exception:
                y_pred_labels = y_pred_enc.astype(str)

            is_attack = np.array([
                str(l).lower() not in ('normal', '0', 'benign', 'legitimate')
                for l in y_pred_labels
            ])
            n_attacks = int(is_attack.sum())
            n_normal  = n_rows - n_attacks

            accuracy = None
            if y_true is not None:
                try:
                    from sklearn.metrics import accuracy_score
                    y_t = self.encoder.transform(y_true.astype(str)) \
                        if hasattr(self.encoder, 'transform') else y_true.values
                    accuracy = accuracy_score(y_t[:len(y_pred_enc)], y_pred_enc) * 100
                except Exception:
                    pass

            attack_dist = {}
            for lbl, att in zip(y_pred_labels, is_attack):
                if att:
                    attack_dist[str(lbl)] = attack_dist.get(str(lbl), 0) + 1

            preview = df_raw[self.features].head(500).copy()
            preview.insert(0, 'Statut',    ['ATTAQUE' if a else 'NORMAL'     for a in is_attack[:500]])
            preview.insert(1, 'Prédiction', y_pred_labels[:500])
            preview.insert(2, 'Confiance',  [f"{c*100:.1f}%" for c in conf_per_row[:500]])

            self.progress.emit(100)
            self.result_ready.emit({
                'n_rows':      n_rows,
                'n_attacks':   n_attacks,
                'n_normal':    n_normal,
                'global_conf': global_conf,
                'accuracy':    accuracy,
                'attack_dist': attack_dist,
                'preview':     preview,
            })

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

    @staticmethod
    def _detect_label(df):
        for c in ['label','Label','class','Class','attack','Attack','target','Target']:
            if c in df.columns:
                return c
        last = df.columns[-1]
        return last if df[last].dtype == object else None


# ============================================================
# CARTE MÉTRIQUE
# ============================================================
class MetricCard(QWidget):
    def __init__(self, icon, title, value="—", accent=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.accent = accent or COLORS['info']
        self.setMinimumHeight(88)
        self.setMaximumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self._icon  = QLabel(icon)
        self._icon.setObjectName("card_icon")
        self._title = QLabel(title.upper())
        self._title.setObjectName("card_title")
        top.addWidget(self._icon)
        top.addWidget(self._title)
        top.addStretch()

        self._val = QLabel(value)
        self._val.setObjectName("card_value")
        self._val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addLayout(top)
        lay.addWidget(self._val)

    def set_value(self, v, color=None):
        self._val.setText(str(v))
        c = color or COLORS['text_bright']
        self._val.setStyleSheet(f"color: {c}; font-size: 22px; font-weight: bold;")


class Panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


class CyberButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("cyber_button")


def section_label(text):
    l = QLabel(text)
    l.setObjectName("section_label")
    return l


# ============================================================
# FENETRE PRINCIPALE
# ============================================================
class IDSWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDS · Network Intrusion Detection System")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setup_style()

        self._model = self._scaler = self._encoder = self._features = None
        self._csv_path = None
        self._raw_df   = None   # DataFrame complet après analyse (500 lignes preview)
        self._worker   = None

        self._build_ui()

    # ------------------------------------------------------------------
    def setup_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_bright']};
                font-family: 'Segoe UI';
            }}
            QLabel {{ font-size: 12px; }}

            QLabel#section_label {{
                color: {COLORS['info']};
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 3px;
                padding: 4px;
            }}
            QWidget#panel {{
                background-color: {COLORS['bg_medium']};
                border-radius: 10px;
                border: 1px solid {COLORS['accent']};
            }}
            QWidget#card {{
                background-color: {COLORS['bg_medium']};
                border-radius: 12px;
                border: 2px solid {COLORS['accent']};
            }}
            QWidget#card:hover {{
                border: 2px solid {COLORS['info']};
            }}
            QLabel#card_icon  {{ font-size: 16px; color: {COLORS['info']}; }}
            QLabel#card_title {{
                font-size: 9px; font-weight: bold;
                letter-spacing: 2px; color: {COLORS['accent']};
            }}
            QLabel#card_value {{
                font-size: 22px; font-weight: bold;
                color: {COLORS['text_bright']};
            }}

            QGroupBox {{
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
                background-color: {COLORS['bg_medium']};
                margin-top: 12px; padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 12px;
                padding: 0 8px; color: {COLORS['info']};
            }}

            QTableWidget {{
                background-color: {COLORS['bg_medium']};
                alternate-background-color: {COLORS['bg_dark']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
                gridline-color: {COLORS['accent']};
            }}
            QTableWidget::item {{ padding: 6px 8px; }}
            QTableWidget::item:selected {{ background-color: {COLORS['info']}40; }}
            QHeaderView::section {{
                background-color: #0B1120;
                color: {COLORS['text_bright']};
                padding: 8px; border: none;
                border-bottom: 2px solid {COLORS['info']};
                font-weight: bold;
            }}

            QProgressBar {{
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                background-color: {COLORS['bg_dark']};
                text-align: center; color: {COLORS['text_bright']};
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['info']}, stop:1 {COLORS['success']});
                border-radius: 5px;
            }}

            QComboBox {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 6px; padding: 6px 10px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text_bright']};
                selection-background-color: {COLORS['info']};
            }}

            QLineEdit {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 6px; padding: 6px 10px;
            }}
            QLineEdit:focus {{ border: 2px solid {COLORS['info']}; }}

            QStatusBar {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['info']};
                border-top: 1px solid {COLORS['accent']};
            }}

            QScrollBar:vertical {{
                background: {COLORS['bg_dark']}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['accent']}; border-radius: 4px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

            QPushButton#cyber_button {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['info']};
                border: 1px solid {COLORS['info']};
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }}
            QPushButton#cyber_button:hover  {{ background-color: {COLORS['info']}20; }}
            QPushButton#cyber_button:disabled {{
                color: {COLORS['accent']}80; border-color: {COLORS['accent']}80;
            }}
        """)

    # ------------------------------------------------------------------
    def _build_ui(self):
        root_w = QWidget(self)
        root_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(root_w)

        root = QVBoxLayout(root_w)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        header = self._make_header()
        header.setFixedHeight(62)
        root.addWidget(header)

        toolbar = self._make_toolbar()
        toolbar.setFixedHeight(54)
        root.addWidget(toolbar)

        body_w = QWidget()
        body = QHBoxLayout(body_w)
        body.setSpacing(12)
        body.setContentsMargins(14, 10, 14, 10)
        body.addWidget(self._make_left_panel(),  30)
        body.addWidget(self._make_right_panel(), 70)
        root.addWidget(body_w, 1)

        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._sb.showMessage("◉  SYSTÈME PRÊT  ·  Chargez le dossier modèle puis un fichier CSV")

        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

    # ── Header ────────────────────────────────────────────────────────
    def _make_header(self):
        w = Panel()
        w.setFixedHeight(62)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(12)

        logo = QLabel("🛡")
        logo.setStyleSheet(f"font-size: 26px; color: {COLORS['info']};")

        col = QVBoxLayout()
        col.setSpacing(1)
        t1 = QLabel("NETWORK IDS")
        t1.setStyleSheet("font-size: 17px; font-weight: bold; letter-spacing: 3px;")
        t2 = QLabel("LightGBM · Intrusion Detection System")
        t2.setStyleSheet(f"color: {COLORS['info']}; font-size: 9px; letter-spacing: 2px;")
        col.addWidget(t1)
        col.addWidget(t2)

        lay.addWidget(logo)
        lay.addLayout(col)
        lay.addStretch()

        self._inds = {}
        ind_panel = Panel()
        ind_panel.setFixedHeight(42)
        ind_lay = QHBoxLayout(ind_panel)
        ind_lay.setContentsMargins(14, 4, 14, 4)
        ind_lay.setSpacing(16)

        for key, fname in REQUIRED_FILES.items():
            short = (fname.replace('lightgbm_final', 'lgbm')
                         .replace('feature_cols',    'features')
                         .replace('label_encoder',   'encoder')
                         .replace('.pkl', ''))
            vc  = QVBoxLayout()
            vc.setSpacing(0)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(short)
            lbl.setStyleSheet("font-size: 8px; letter-spacing: 1px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vc.addWidget(dot)
            vc.addWidget(lbl)
            self._inds[key] = dot
            ind_lay.addLayout(vc)

        lay.addWidget(ind_panel)
        lay.addSpacing(14)

        self._time_lbl = QLabel()
        self._time_lbl.setStyleSheet(f"color: {COLORS['info']}; font-size: 11px;")
        lay.addWidget(self._time_lbl)
        return w

    # ── Toolbar ───────────────────────────────────────────────────────
    def _make_toolbar(self):
        w = Panel()
        w.setFixedHeight(54)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        self._btn_dir = CyberButton("📁  MODÈLE")
        self._btn_dir.clicked.connect(self._load_model_dir)

        self._dir_lbl = QLabel("Aucun dossier")
        self._dir_lbl.setStyleSheet("font-size: 10px;")
        self._dir_lbl.setMaximumWidth(240)

        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setFixedWidth(1)
        div1.setStyleSheet(f"background: {COLORS['accent']};")

        self._btn_csv = CyberButton("📂  CSV")
        self._btn_csv.clicked.connect(self._browse_csv)

        self._csv_lbl = QLabel("Aucun fichier")
        self._csv_lbl.setStyleSheet("font-size: 10px;")
        self._csv_lbl.setMaximumWidth(240)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setFixedWidth(1)
        div2.setStyleSheet(f"background: {COLORS['accent']};")

        self._run_btn = CyberButton("▶  ANALYSER")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._run)

        self._prog_lbl = QLabel("—")
        self._prog_lbl.setStyleSheet(f"color: {COLORS['info']}; font-size: 9px;")
        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setFixedWidth(140)
        self._prog.setFixedHeight(5)
        self._prog.setTextVisible(False)

        pc = QVBoxLayout()
        pc.setSpacing(2)
        pc.addWidget(self._prog_lbl)
        pc.addWidget(self._prog)

        lay.addWidget(self._btn_dir)
        lay.addWidget(self._dir_lbl)
        lay.addWidget(div1)
        lay.addWidget(self._btn_csv)
        lay.addWidget(self._csv_lbl)
        lay.addWidget(div2)
        lay.addStretch()
        lay.addLayout(pc)
        lay.addWidget(self._run_btn)
        return w

    # ── Panneau gauche ────────────────────────────────────────────────
    def _make_left_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        # Confidence
        conf_panel = Panel()
        cl = QVBoxLayout(conf_panel)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(6)
        cl.addWidget(section_label("◈  CONFIANCE GLOBALE"))

        self._conf_val = QLabel("—")
        self._conf_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._conf_val.setStyleSheet(f"font-size: 52px; font-weight: bold; color: {COLORS['accent']}88;")

        self._conf_bar = QProgressBar()
        self._conf_bar.setRange(0, 100)
        self._conf_bar.setValue(0)
        self._conf_bar.setFixedHeight(7)
        self._conf_bar.setTextVisible(False)

        self._badge = QLabel("◉  EN ATTENTE")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(f"font-size: 10px; letter-spacing: 2px; color: {COLORS['accent']}88;")

        cl.addWidget(self._conf_val)
        cl.addWidget(self._conf_bar)
        cl.addWidget(self._badge)
        lay.addWidget(conf_panel)

        # Metric cards
        self._cards = {}
        grid = QGridLayout()
        grid.setSpacing(8)
        metrics = [
            ("total",    "", "PAQUETS",   COLORS['info']),
            ("attacks",  "⚠️",  "ATTAQUES",  COLORS['danger']),
            ("normal",   "✓",  "NORMAL",    COLORS['success']),
            ("accuracy", "", "PRÉCISION", COLORS['warning']),
        ]
        for i, (key, icon, title, color) in enumerate(metrics):
            c = MetricCard(icon, title, "—", color)
            self._cards[key] = c
            grid.addWidget(c, i // 2, i % 2)
        lay.addLayout(grid)

        # Distribution
        dist_panel = Panel()
        dl = QVBoxLayout(dist_panel)
        dl.setContentsMargins(14, 10, 14, 6)
        dl.setSpacing(6)
        dl.addWidget(section_label("◈  DISTRIBUTION"))

        # Stacked widget: placeholder  ↔  chart
        self._dist_stack = QStackedWidget()

        # — placeholder —
        ph = QWidget()
        ph_lay = QVBoxLayout(ph)
        ph_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lay.setSpacing(10)
        ph_circle = QLabel("○")
        ph_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_circle.setStyleSheet(f"""
            font-size: 64px;
            color: {COLORS['accent']}33;
            border: 3px dashed {COLORS['accent']}33;
            border-radius: 50px;
            min-width: 100px; min-height: 100px;
            max-width: 100px; max-height: 100px;
        """)
        ph_txt = QLabel("Aucune donnée\nLancez une analyse")
        ph_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_txt.setStyleSheet(f"color: {COLORS['accent']}66; font-size: 10px; letter-spacing: 1px;")
        ph_lay.addWidget(ph_circle, alignment=Qt.AlignmentFlag.AlignCenter)
        ph_lay.addWidget(ph_txt)

        # — chart —
        self._dist_fig    = Figure(figsize=(3, 2.2), dpi=90)
        self._dist_fig.patch.set_facecolor(COLORS['bg_medium'])
        self._dist_canvas = FigureCanvas(self._dist_fig)

        self._dist_stack.addWidget(ph)              # index 0
        self._dist_stack.addWidget(self._dist_canvas)  # index 1
        self._dist_stack.setCurrentIndex(0)

        dl.addWidget(self._dist_stack)
        lay.addWidget(dist_panel, 1)

        # Buttons
        br = QHBoxLayout()
        br.setSpacing(8)
        rst = CyberButton("↺  RESET")
        rst.clicked.connect(self._reset)
        self._exp_btn = CyberButton("↓  EXPORTER")
        self._exp_btn.clicked.connect(self._export)
        self._exp_btn.setEnabled(False)
        br.addWidget(rst)
        br.addWidget(self._exp_btn)
        lay.addLayout(br)
        return w

    # ── Panneau droit ─────────────────────────────────────────────────
    def _make_right_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        lay.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        hdr.addWidget(section_label("◈  JOURNAL DES CONNEXIONS"))
        hdr.addStretch()

        self._filter = QComboBox()
        self._filter.addItems(["TOUS", "ATTAQUES", "NORMAL"])
        self._filter.setFixedWidth(110)
        self._filter.currentIndexChanged.connect(self._apply_filter)

        self._search = QLineEdit()
        self._search.setPlaceholderText("  Rechercher…")
        self._search.setFixedWidth(190)
        self._search.textChanged.connect(self._apply_filter)

        hdr.addWidget(self._filter)
        hdr.addWidget(self._search)
        lay.addLayout(hdr)

        # ── Stacked widget: empty-state  ↔  table ──
        self._right_stack = QStackedWidget()

        # index 0 — état vide avec guide 3 étapes
        self._right_stack.addWidget(self._make_empty_state_widget())

        # index 1 — tableau réel
        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(26)
        self._right_stack.addWidget(self._table)

        self._right_stack.setCurrentIndex(0)
        lay.addWidget(self._right_stack, 1)
        return w

    # ── Widget état vide avec guide 3 étapes ──────────────────────────
    def _make_empty_state_widget(self):
        w = QWidget()
        w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(24)
        lay.setContentsMargins(40, 40, 40, 40)

        # — guide étapes —
        steps_w  = QWidget()
        steps_lay = QHBoxLayout(steps_w)
        steps_lay.setSpacing(0)
        steps_lay.setContentsMargins(0, 0, 0, 0)

        self._step_circles = []
        self._step_labels  = []
        step_defs = [("1", "CHARGER MODÈLE"), ("2", "CHARGER CSV"), ("▶", "ANALYSER")]

        for i, (num, label) in enumerate(step_defs):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.setSpacing(6)

            circle = QLabel(num)
            circle.setFixedSize(40, 40)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setStyleSheet(self._step_style("pending"))

            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"font-size: 8px; letter-spacing: 1.5px; color: {COLORS['accent']}66; background: transparent;")

            col.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl,    alignment=Qt.AlignmentFlag.AlignCenter)
            self._step_circles.append(circle)
            self._step_labels.append(lbl)
            steps_lay.addLayout(col)

            if i < 2:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(2)
                line.setFixedWidth(60)
                line.setStyleSheet(f"background: {COLORS['accent']}33;")
                steps_lay.addWidget(line, alignment=Qt.AlignmentFlag.AlignVCenter)

        lay.addWidget(steps_w, alignment=Qt.AlignmentFlag.AlignCenter)

        # — icône centrale —
        icon_lbl = QLabel("🛡")
        icon_lbl.setStyleSheet("font-size: 48px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        # — titre & sous-titre —
        self._empty_title = QLabel("SYSTÈME EN ATTENTE")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLORS['accent']}; letter-spacing: 2px; background: transparent;")

        self._empty_sub = QLabel(
            "Chargez le dossier contenant les fichiers .pkl du modèle,\n"
            "puis sélectionnez un fichier CSV de captures réseau.")
        self._empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_sub.setStyleSheet(
            f"font-size: 10px; color: {COLORS['accent']}77; line-height: 1.8; background: transparent;")
        self._empty_sub.setWordWrap(True)

        lay.addWidget(self._empty_title)
        lay.addWidget(self._empty_sub)

        # — set étape 0 active —
        self._set_step(0)
        return w

    def _step_style(self, state):
        if state == "pending":
            return (f"border-radius: 20px; border: 2px solid {COLORS['accent']}44;"
                    f" color: {COLORS['accent']}55; font-weight: bold; font-size: 13px;"
                    f" background: {COLORS['bg_dark']};")
        if state == "active":
            return (f"border-radius: 20px; border: 2px solid {COLORS['info']};"
                    f" color: {COLORS['info']}; font-weight: bold; font-size: 13px;"
                    f" background: {COLORS['info']}22;")
        if state == "done":
            return (f"border-radius: 20px; border: 2px solid {COLORS['success']};"
                    f" color: {COLORS['success']}; font-weight: bold; font-size: 13px;"
                    f" background: {COLORS['success']}22;")
        return ""

    def _set_step(self, active_step):
        """Met à jour visuellement les cercles des étapes (0=model, 1=csv, 2=run)."""
        for i, (circle, lbl) in enumerate(zip(self._step_circles, self._step_labels)):
            if i < active_step:
                circle.setStyleSheet(self._step_style("done"))
                circle.setText("✓")
                lbl.setStyleSheet(f"font-size: 8px; letter-spacing: 1.5px; color: {COLORS['success']}99; background: transparent;")
            elif i == active_step:
                circle.setStyleSheet(self._step_style("active"))
                circle.setText(["1","2","▶"][i])
                lbl.setStyleSheet(f"font-size: 8px; letter-spacing: 1.5px; color: {COLORS['info']}; background: transparent;")
            else:
                circle.setStyleSheet(self._step_style("pending"))
                circle.setText(["1","2","▶"][i])
                lbl.setStyleSheet(f"font-size: 8px; letter-spacing: 1.5px; color: {COLORS['accent']}66; background: transparent;")

    # ══════════════════════════════════════════════════════════════════
    # LOGIQUE
    # ══════════════════════════════════════════════════════════════════
    def _load_model_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier du modèle")
        if not d:
            return
        path   = Path(d)
        loaded = {}
        all_ok = True

        for key, fname in REQUIRED_FILES.items():
            fp  = path / fname
            dot = self._inds[key]
            if fp.exists():
                try:
                    with open(fp, 'rb') as f:
                        loaded[key] = pickle.load(f)
                    dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
                except Exception as e:
                    print(f"❌ {fname} : {e}")
                    dot.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
                    all_ok = False
            else:
                dot.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
                all_ok = False

        if not all_ok:
            QMessageBox.warning(self, "Erreur de chargement",
                "Un ou plusieurs fichiers .pkl sont introuvables ou impossibles à charger.")
            return

        self._model    = loaded.get('model')
        self._scaler   = loaded.get('scaler')
        self._encoder  = loaded.get('encoder')
        self._features = loaded.get('features')

        s = str(path)
        self._dir_lbl.setText(("…" + s[-32:]) if len(s) > 32 else s)
        self._dir_lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px;")

        num_feat = len(self._features) if self._features is not None else 0
        self._sb.showMessage(f"◉  MODÈLE CHARGÉ  ·  {num_feat} features")

        # Mise à jour guide étapes
        self._set_step(1)
        self._empty_title.setText("MODÈLE CHARGÉ — CHOISISSEZ UN CSV")
        self._empty_sub.setText("Le modèle LightGBM est prêt.\nSélectionnez maintenant un fichier CSV de captures réseau.")

        self._check_ready()

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Fichier CSV", "", "CSV (*.csv);;Tous (*)")
        if not path:
            return
        self._csv_path = path
        s = path
        self._csv_lbl.setText(("…" + s[-32:]) if len(s) > 32 else s)
        self._csv_lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px;")

        # Mise à jour guide étapes
        self._set_step(2)
        self._empty_title.setText("PRÊT — CLIQUEZ  ▶  ANALYSER")
        self._empty_sub.setText("Tout est en place.\nCliquez sur ANALYSER pour lancer la détection d'intrusions.")

        self._sb.showMessage("◉  CSV PRÊT  ·  Cliquez ANALYSER pour démarrer")
        self._check_ready()

    def _check_ready(self):
        self._run_btn.setEnabled(self._model is not None and self._csv_path is not None)

    def _run(self):
        self._run_btn.setEnabled(False)
        self._prog.setValue(0)
        self._worker = PredictionWorker(
            self._csv_path, self._model, self._scaler, self._encoder, self._features)
        self._worker.progress.connect(self._prog.setValue)
        self._worker.status_msg.connect(lambda m: (
            self._prog_lbl.setText(m),
            self._sb.showMessage(f"◉  {m}")))
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # ── Résultats ─────────────────────────────────────────────────────
    def _on_result(self, res):
        self._run_btn.setEnabled(True)
        self._exp_btn.setEnabled(True)
        self._prog_lbl.setText("TERMINÉ ✓")
        self._raw_df = res['preview']   # DataFrame complet avec Statut/Prédiction/Confiance

        n   = res['n_rows']
        att = res['n_attacks']
        nor = res['n_normal']
        gc  = res['global_conf']
        pct = att / n * 100 if n else 0
        acc = res['accuracy']

        # Confiance
        self._conf_bar.setValue(int(gc))
        self._conf_val.setText(f"{gc:.1f}%")
        clr = COLORS['success'] if gc >= 90 else (COLORS['warning'] if gc >= 70 else COLORS['danger'])
        self._conf_val.setStyleSheet(f"color: {clr}; font-size: 52px; font-weight: bold;")

        if pct > 30:
            badge, bclr = "⚠  CRITIQUE — MENACES DÉTECTÉES", COLORS['danger']
        elif pct > 5:
            badge, bclr = "◉  SUSPECT — SURVEILLER",          COLORS['warning']
        else:
            badge, bclr = "✓  RÉSEAU SÉCURISÉ",               COLORS['success']

        self._badge.setText(badge)
        self._badge.setStyleSheet(f"color: {bclr}; font-size: 10px; letter-spacing: 2px;")

        self._cards["total"   ].set_value(f"{n:,}",                         COLORS['info'])
        self._cards["attacks" ].set_value(f"{att:,} ({pct:.1f}%)",          COLORS['danger'] if att > 0 else COLORS['success'])
        self._cards["normal"  ].set_value(f"{nor:,} ({100-pct:.1f}%)",      COLORS['success'])
        self._cards["accuracy"].set_value(f"{acc:.1f}%" if acc else "N/A",  COLORS['warning'])

        # Afficher le tableau (masque l'état vide)
        self._right_stack.setCurrentIndex(1)
        self._populate_table(self._raw_df)

        # Afficher le graphique distribution
        self._dist_stack.setCurrentIndex(1)
        self._draw_dist(res['attack_dist'], nor, att)

        self._sb.showMessage(
            f"◉  ANALYSE COMPLÈTE  ·  {n:,} paquets  ·  {att:,} attaques ({pct:.1f}%)  ·  {badge}")

    def _on_error(self, msg):
        self._run_btn.setEnabled(True)
        self._prog_lbl.setText("ERREUR ✗")
        QMessageBox.critical(self, "Erreur d'analyse", msg[:800])

    # ── Tableau ───────────────────────────────────────────────────────
    def _populate_table(self, df):
        """Peuple le tableau avec le DataFrame fourni (déjà filtré)."""
        if df is None or df.empty:
            self._table.clear()
            self._table.setRowCount(0)
            return

        fixed = ['Statut', 'Prédiction', 'Confiance']
        feat  = [c for c in df.columns if c not in fixed][:14]
        cols  = fixed + feat

        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels([c.upper() for c in cols])
        self._table.setRowCount(len(df))

        for ri, (_, row) in enumerate(df.iterrows()):
            is_att = str(row.get('Statut', '')) == 'ATTAQUE'
            for ci, col in enumerate(cols):
                val  = str(row.get(col, ''))[:32]
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                if col == 'Statut':
                    item.setText("⚠ ATTAQUE" if is_att else "✓ NORMAL")
                    item.setForeground(QColor(COLORS['danger'] if is_att else COLORS['success']))
                    font = QFont(); font.setBold(True); item.setFont(font)
                elif col == 'Prédiction':
                    item.setForeground(QColor(COLORS['danger'] if is_att else COLORS['success']))
                elif col == 'Confiance':
                    item.setForeground(QColor(COLORS['warning']))
                else:
                    item.setForeground(QColor(COLORS['text_bright']))

                if is_att:
                    item.setBackground(QColor(COLORS['danger'] + '20'))

                self._table.setItem(ri, ci, item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)

    # ── Filtre  ──────────────────────────────────────────────────────
    def _apply_filter(self):
        """Filtre le DataFrame _raw_df selon le combo + la recherche texte,
           puis repeuple le tableau. Fonctionne uniquement si des données existent."""
        if self._raw_df is None or self._raw_df.empty:
            return

        df = self._raw_df.copy()

        # 1) Filtre combo TOUS / ATTAQUES / NORMAL
        mode = self._filter.currentText()
        if mode == "ATTAQUES":
            df = df[df['Statut'] == 'ATTAQUE']
        elif mode == "NORMAL":
            df = df[df['Statut'] == 'NORMAL']

        # 2) Filtre texte (recherche dans toutes les colonnes)
        query = self._search.text().strip().lower()
        if query:
            mask = df.apply(
                lambda row: any(query in str(v).lower() for v in row),
                axis=1
            )
            df = df[mask]

        # 3) Mise à jour du label section avec le compte
        total = len(self._raw_df)
        shown = len(df)
        label_txt = f"◈  JOURNAL DES CONNEXIONS  ({shown:,} / {total:,})"
        # Cherche le section_label dans le layout parent
        for i in range(self.centralWidget().layout().count()):
            pass  # le label est dans right panel, on le met à jour via le widget dédié

        self._populate_table(df)

    # ── Distribution ──────────────────────────────────────────────────
    def _draw_dist(self, attack_dist, n_normal, n_attacks):
        self._dist_fig.clear()
        self._dist_fig.patch.set_facecolor(COLORS['bg_medium'])
        ax = self._dist_fig.add_subplot(111)
        ax.set_facecolor(COLORS['bg_medium'])

        labels, values, colors = [], [], []
        if n_normal:
            labels.append("Normal"); values.append(n_normal); colors.append(COLORS['success'])

        palette = [COLORS['danger'], COLORS['warning'], '#8b5cf6', '#ec4899', '#14b8a6']
        for i, (k, v) in enumerate(sorted(attack_dist.items(), key=lambda x: -x[1])):
            labels.append(k[:15]); values.append(v); colors.append(palette[i % len(palette)])

        if values:
            wedges, texts, autos = ax.pie(
                values, colors=colors, autopct='%1.0f%%',
                startangle=90, pctdistance=0.72,
                wedgeprops=dict(edgecolor=COLORS['bg_dark'], linewidth=2, width=0.55),
                textprops=dict(color=COLORS['text_bright'], fontsize=8))
            for a in autos:
                a.set_fontweight('bold')

            patches = [mpatches.Patch(color=c, label=l) for c, l in zip(colors, labels)]
            ax.legend(handles=patches, loc='lower center',
                      bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False,
                      prop={'size': 7}, labelcolor=COLORS['text_bright'])

        self._dist_fig.tight_layout(pad=0.2)
        self._dist_canvas.draw()

    # ── Export ────────────────────────────────────────────────────────
    def _export(self):
        if self._raw_df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer", "resultats_ids.csv", "CSV (*.csv)")
        if path:
            self._raw_df.to_csv(path, index=False)
            QMessageBox.information(self, "Export", f"Enregistré :\n{path}")

    # ── Reset ─────────────────────────────────────────────────────────
    def _reset(self):
        self._csv_path = None
        self._raw_df   = None

        # Tableau → état vide
        self._right_stack.setCurrentIndex(0)
        self._set_step(0 if self._model is None else 1)
        self._empty_title.setText(
            "SYSTÈME EN ATTENTE" if self._model is None else "MODÈLE CHARGÉ — CHOISISSEZ UN CSV")
        self._empty_sub.setText(
            "Chargez le dossier contenant les fichiers .pkl du modèle,\n"
            "puis sélectionnez un fichier CSV de captures réseau."
            if self._model is None else
            "Le modèle LightGBM est prêt.\nSélectionnez maintenant un fichier CSV de captures réseau.")

        # Distribution → placeholder
        self._dist_stack.setCurrentIndex(0)
        self._dist_fig.clear()

        # Confidence
        self._conf_val.setText("—")
        self._conf_val.setStyleSheet(f"color: {COLORS['accent']}88; font-size: 52px; font-weight: bold;")
        self._conf_bar.setValue(0)
        self._badge.setText("◉  EN ATTENTE")
        self._badge.setStyleSheet(f"font-size: 10px; letter-spacing: 2px; color: {COLORS['accent']}88;")

        # Cartes
        for c in self._cards.values():
            c.set_value("—", COLORS['accent'] + '88')

        # Barre / boutons
        self._prog.setValue(0)
        self._prog_lbl.setText("—")
        self._csv_lbl.setText("Aucun fichier")
        self._csv_lbl.setStyleSheet("font-size: 10px;")
        self._run_btn.setEnabled(False)
        self._exp_btn.setEnabled(False)
        self._sb.showMessage("◉  RÉINITIALISÉ")

        # Vider le filtre et la recherche sans déclencher apply_filter
        self._filter.blockSignals(True)
        self._search.blockSignals(True)
        self._filter.setCurrentIndex(0)
        self._search.clear()
        self._filter.blockSignals(False)
        self._search.blockSignals(False)

    def _tick(self):
        self._time_lbl.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))


# ══════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = IDSWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()