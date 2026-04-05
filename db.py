import sqlite3
import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, 'datav37.db')


def ket_noi_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS san_pham (
            id TEXT PRIMARY KEY,
            ten TEXT NOT NULL,
            tong_nhap INTEGER DEFAULT 0,
            tong_xuat INTEGER DEFAULT 0,
            gia_mua REAL NOT NULL,
            ghi_chu TEXT DEFAULT ''
        )
    ''')
    cur.execute("PRAGMA table_info(san_pham)")
    cols = [col[1] for col in cur.fetchall()]
    if 'muc_canh_bao' not in cols:
        cur.execute("ALTER TABLE san_pham ADD COLUMN muc_canh_bao INTEGER DEFAULT 0")
    if 'bat_email' not in cols:
        cur.execute("ALTER TABLE san_pham ADD COLUMN bat_email INTEGER DEFAULT 0")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS nguoi_dung (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cur.execute("PRAGMA table_info(nguoi_dung)")
    user_cols = [col[1] for col in cur.fetchall()]
    if 'role' not in user_cols:
        cur.execute("ALTER TABLE nguoi_dung ADD COLUMN role TEXT DEFAULT 'staff'")

    if not cur.execute("SELECT * FROM nguoi_dung WHERE username='admin'").fetchone():
        cur.execute("INSERT INTO nguoi_dung (username, password, role) VALUES ('admin', '123456', 'admin')")
    else:
        cur.execute("UPDATE nguoi_dung SET role='admin' WHERE username='admin'")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS cai_dat (
            id INTEGER PRIMARY KEY,
            banner_b64 TEXT DEFAULT '',
            smtp_email TEXT DEFAULT '',
            smtp_pass TEXT DEFAULT '',
            receive_email TEXT DEFAULT ''
        )
    ''')
    cur.execute("PRAGMA table_info(cai_dat)")
    cd_cols = [col[1] for col in cur.fetchall()]
    if 'smtp_host' not in cd_cols:
        cur.execute("ALTER TABLE cai_dat ADD COLUMN smtp_host TEXT DEFAULT 'smtp.gmail.com'")
    if 'smtp_port' not in cd_cols:
        cur.execute("ALTER TABLE cai_dat ADD COLUMN smtp_port INTEGER DEFAULT 587")
    if not cur.execute("SELECT * FROM cai_dat WHERE id=1").fetchone():
        cur.execute("INSERT INTO cai_dat (id, banner_b64, smtp_email, smtp_pass, receive_email, smtp_host, smtp_port) VALUES (1, '', '', '', '', 'smtp.gmail.com', 587)")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS phieu_xuat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_phieu TEXT,
            ngay_tao TEXT,
            nguoi_xuat TEXT,
            nguoi_nhan TEXT,
            tong_ban REAL DEFAULT 0,
            tong_von REAL DEFAULT 0,
            chi_phi_van_chuyen REAL DEFAULT 0,
            hue_hong REAL DEFAULT 0,
            chi_phi_khac REAL DEFAULT 0,
            ghi_chu_chi_phi TEXT DEFAULT '',
            loi_nhuan REAL DEFAULT 0
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS phieu_xuat_ct (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_phieu TEXT,
            san_pham_id TEXT,
            ten_san_pham TEXT,
            so_luong INTEGER DEFAULT 0,
            gia_ban REAL DEFAULT 0,
            gia_von REAL DEFAULT 0,
            thanh_tien_ban REAL DEFAULT 0,
            thanh_tien_von REAL DEFAULT 0,
            ngay_tao TEXT,
            nguoi_xuat TEXT
        )
    ''')

    conn.commit()
    return conn
