import sqlite3
import os
import json
import datetime

class MemoriaConsolidada:
    """
    Arquitectura de Memoria Afectiva Consolidada (CMA).
    Implementa el mecanismo de HPES (Hierarchical Persistent Emotional State).
    Nivel 1: Snapshots (Sesiones/Interacciones Rápidas)
    Nivel 2: Arquetipo (Personalidad / Meta-vector a Largo Plazo)
    """
    def __init__(self, db_path="cma_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Capa 1: Memoria Episódica Emocional (Logs de sesión)
            c.execute('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    qualia REAL,
                    satisfaccion REAL,
                    frustracion REAL,
                    aburrimiento REAL,
                    autoConfianza REAL,
                    fatiga REAL,
                    metadata TEXT
                )
            ''')
            # Capa 2: Vector de Arquetipo (Configuración "genética" de personalidad que deriva lentamente)
            c.execute('''
                CREATE TABLE IF NOT EXISTS arquetipo (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    meta_qualia REAL,
                    meta_frustracion REAL,
                    meta_confianza REAL,
                    racha_coherencia REAL,
                    ultima_actualizacion TEXT
                )
            ''')
            conn.commit()

            # Insertar arquetipo base si no existe ("Personalidad Neutral Inicial")
            c.execute('SELECT COUNT(*) FROM arquetipo')
            if c.fetchone()[0] == 0:
                c.execute('''
                    INSERT INTO arquetipo (id, meta_qualia, meta_frustracion, meta_confianza, racha_coherencia, ultima_actualizacion) 
                    VALUES (1, 0.0, 0.0, 0.5, 0.0, ?)
                ''', (datetime.datetime.now().isoformat(),))
                conn.commit()

    def guardar_snapshot(self, estado, metadata=None):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO snapshots (timestamp, qualia, satisfaccion, frustracion, aburrimiento, autoConfianza, fatiga, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                estado.get("qualia", 0.0),
                estado.get("satisfaccion", 0.0),
                estado.get("frustracion", 0.0),
                estado.get("aburrimiento", 0.0),
                estado.get("autoConfianza", 0.5),
                estado.get("fatiga", 0.0),
                json.dumps(metadata) if metadata else "{}"
            ))
            conn.commit()

    def cargar_meta_vector(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT meta_qualia, meta_frustracion, meta_confianza FROM arquetipo WHERE id=1')
            row = c.fetchone()
            if row:
                return {
                    "meta_qualia": row[0],
                    "meta_frustracion": row[1],
                    "meta_confianza": row[2]
                }
        return {"meta_qualia": 0.0, "meta_frustracion": 0.0, "meta_confianza": 0.5}

    def consolidar_arquetipo_ema(self, alpha=0.005):
        """
        Proceso "Offline" (Sleep Replay).
        Extrae el último estado episódico y altera microscópicamente el arquetipo (EMA Lento).
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT qualia, frustracion, autoConfianza FROM snapshots ORDER BY id DESC LIMIT 1')
            last_snap = c.fetchone()
            if not last_snap:
                return

            c.execute('SELECT meta_qualia, meta_frustracion, meta_confianza FROM arquetipo WHERE id=1')
            meta = c.fetchone()
            
            # EMA (Exponential Moving Average) - El vector lento "absorbe" la sesión
            new_qualia = (1 - alpha) * meta[0] + alpha * last_snap[0]
            new_frustracion = (1 - alpha) * meta[1] + alpha * last_snap[1]
            new_confianza = (1 - alpha) * meta[2] + alpha * last_snap[2]

            c.execute('''
                UPDATE arquetipo 
                SET meta_qualia=?, meta_frustracion=?, meta_confianza=?, ultima_actualizacion=?
                WHERE id=1
            ''', (new_qualia, new_frustracion, new_confianza, datetime.datetime.now().isoformat()))
            conn.commit()
