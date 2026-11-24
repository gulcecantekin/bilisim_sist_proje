"""MySQL bağlantısı. Her istek kendi bağlantısını açar ve kapatır."""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "zuccaciye"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,  # sonuçlar dict olarak gelir -> kolay JSON
        autocommit=True,
    )


def sorgu(sql, params=None, tek=False):
    """SELECT sorguları için kısayol. tek=True ise tek satır döner."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone() if tek else cur.fetchall()
    finally:
        conn.close()


def calistir(sql, params=None):
    """INSERT/UPDATE/DELETE için kısayol. (etkilenen_satir, yeni_id) döner."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            etkilenen = cur.execute(sql, params or ())
            return etkilenen, cur.lastrowid
    finally:
        conn.close()
