from functools import wraps
from flask import session, redirect, url_for, flash
from db import ket_noi_db


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('⛔ Bạn không có quyền thực hiện chức năng này!', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def tao_nhan_vien(username, password, role='staff'):
    username = (username or '').strip()
    password = (password or '').strip()
    if not username or not password:
        return False, 'Vui lòng nhập đủ tài khoản và mật khẩu.'
    role = (role or 'staff').strip().lower()
    if role not in ['admin', 'manager', 'staff']:
        role = 'staff'
    conn = ket_noi_db()
    cur = conn.cursor()
    if cur.execute("SELECT id FROM nguoi_dung WHERE username=?", (username,)).fetchone():
        conn.close()
        return False, 'Tài khoản đã tồn tại.'
    cur.execute("INSERT INTO nguoi_dung (username, password, role) VALUES (?, ?, ?)", (username, password, role))
    conn.commit()
    conn.close()
    ten_quyen = 'quản lý full' if role == 'admin' else 'nhân viên xuất kho'
    return True, f'Đã tạo tài khoản: {username} - quyền {ten_quyen}'


def xoa_nhan_vien(user_id):
    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT username, role FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, 'Không tìm thấy tài khoản.'
    if row[1] == 'admin' or row[0] == 'admin':
        conn.close()
        return False, 'Không được xóa tài khoản admin.'
    cur.execute("DELETE FROM nguoi_dung WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return True, f'Đã xóa nhân viên: {row[0]}'


def doi_mat_khau_nguoi_dung(user_id, mat_khau_cu, mat_khau_moi, xac_nhan):
    mat_khau_cu = (mat_khau_cu or '').strip()
    mat_khau_moi = (mat_khau_moi or '').strip()
    xac_nhan = (xac_nhan or '').strip()
    if not mat_khau_cu or not mat_khau_moi or not xac_nhan:
        return False, 'Vui lòng nhập đủ các trường đổi mật khẩu.'
    if mat_khau_moi != xac_nhan:
        return False, 'Mật khẩu mới và xác nhận không khớp.'
    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT password FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, 'Không tìm thấy tài khoản.'
    if row[0] != mat_khau_cu:
        conn.close()
        return False, 'Mật khẩu cũ không đúng.'
    cur.execute("UPDATE nguoi_dung SET password=? WHERE id=?", (mat_khau_moi, user_id))
    conn.commit()
    conn.close()
    return True, 'Đổi mật khẩu thành công.'


def admin_dat_lai_mat_khau(user_id, mat_khau_moi, xac_nhan):
    mat_khau_moi = (mat_khau_moi or '').strip()
    xac_nhan = (xac_nhan or '').strip()
    if not mat_khau_moi or not xac_nhan:
        return False, 'Vui lòng nhập mật khẩu mới và xác nhận.'
    if mat_khau_moi != xac_nhan:
        return False, 'Mật khẩu mới và xác nhận không khớp.'
    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT username, role FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, 'Không tìm thấy tài khoản.'
    cur.execute("UPDATE nguoi_dung SET password=? WHERE id=?", (mat_khau_moi, user_id))
    conn.commit()
    conn.close()
    return True, f'Đã đổi mật khẩu cho tài khoản: {row[0]}'


def danh_sach_nguoi_dung():
    conn = ket_noi_db()
    rows = conn.execute("SELECT id, username, role FROM nguoi_dung ORDER BY CASE WHEN role='admin' THEN 0 ELSE 1 END, username ASC").fetchall()
    conn.close()
    return rows


def cap_nhat_quyen_nguoi_dung(user_id, role):
    role = (role or 'staff').strip().lower()
    if role not in ['admin', 'manager', 'staff']:
        role = 'staff'
    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT username, role FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, 'Không tìm thấy tài khoản.'
    if row[0] == 'admin' and row[1] == 'admin':
        conn.close()
        return False, 'Không được đổi quyền tài khoản admin gốc.'
    cur.execute("UPDATE nguoi_dung SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()
    ten_quyen = 'admin gốc' if role == 'admin' else ('quản lý' if role == 'manager' else 'nhân viên bán hàng')
    return True, f'Đã cập nhật quyền cho {row[0]} thành {ten_quyen}'
