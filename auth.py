from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

from db import ket_noi_db

HASH_METHOD = "pbkdf2:sha256"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("⛔ Bạn không có quyền thực hiện chức năng này!", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


def _is_probably_hash(pw: str) -> bool:
    return isinstance(pw, str) and (pw.startswith("scrypt:") or pw.startswith("pbkdf2:"))


def verify_password_and_migrate_if_needed(user_id: int, stored_password: str, input_password: str) -> bool:
    if stored_password is None:
        return False

    # password đã hash
    if _is_probably_hash(stored_password):
        return check_password_hash(stored_password, input_password or "")

    # legacy plaintext
    if stored_password == (input_password or ""):
        new_hash = generate_password_hash(input_password, method=HASH_METHOD)
        conn = ket_noi_db()
        conn.execute("UPDATE nguoi_dung SET password=? WHERE id=?", (new_hash, user_id))
        conn.commit()
        conn.close()
        return True

    return False


def tao_nhan_vien(username, password, role="staff"):
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return False, "Vui lòng nhập đủ tài khoản và mật khẩu."

    role = (role or "staff").strip().lower()
    if role not in ["admin", "manager", "staff"]:
        role = "staff"

    conn = ket_noi_db()
    cur = conn.cursor()
    if cur.execute("SELECT id FROM nguoi_dung WHERE username=?", (username,)).fetchone():
        conn.close()
        return False, "Tài khoản đã tồn tại."

    pw_hash = generate_password_hash(password, method=HASH_METHOD)
    cur.execute("INSERT INTO nguoi_dung (username, password, role) VALUES (?, ?, ?)", (username, pw_hash, role))
    conn.commit()
    conn.close()

    ten_quyen = "quản lý full" if role == "admin" else ("quản lý" if role == "manager" else "nhân viên xuất kho")
    return True, f"Đã tạo tài khoản: {username} - quyền {ten_quyen}"


def xoa_nhan_vien(user_id):
    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT username, role FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "Không tìm thấy tài khoản."
    if row["role"] == "admin" or row["username"] == "admin":
        conn.close()
        return False, "Không được xóa tài khoản admin."
    cur.execute("DELETE FROM nguoi_dung WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return True, f"Đã xóa nhân viên: {row['username']}"


def doi_mat_khau_nguoi_dung(user_id, mat_khau_cu, mat_khau_moi, xac_nhan):
    mat_khau_cu = (mat_khau_cu or "").strip()
    mat_khau_moi = (mat_khau_moi or "").strip()
    xac_nhan = (xac_nhan or "").strip()
    if not mat_khau_cu or not mat_khau_moi or not xac_nhan:
        return False, "Vui lòng nhập đủ các trường đổi mật khẩu."
    if mat_khau_moi != xac_nhan:
        return False, "Mật khẩu mới và xác nhận không khớp."

    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT password FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "Không tìm thấy tài khoản."

    if not verify_password_and_migrate_if_needed(user_id, row["password"], mat_khau_cu):
        conn.close()
        return False, "Mật khẩu cũ không đúng."

    new_hash = generate_password_hash(mat_khau_moi, method=HASH_METHOD)
    cur.execute("UPDATE nguoi_dung SET password=? WHERE id=?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True, "Đổi mật khẩu thành công."


def admin_dat_lai_mat_khau(user_id, mat_khau_moi, xac_nhan):
    mat_khau_moi = (mat_khau_moi or "").strip()
    xac_nhan = (xac_nhan or "").strip()
    if not mat_khau_moi or not xac_nhan:
        return False, "Vui lòng nhập mật khẩu mới và xác nhận."
    if mat_khau_moi != xac_nhan:
        return False, "Mật khẩu mới và xác nhận không khớp."

    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT username FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "Không tìm thấy tài khoản."

    new_hash = generate_password_hash(mat_khau_moi, method=HASH_METHOD)
    cur.execute("UPDATE nguoi_dung SET password=? WHERE id=?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True, f"Đã đổi mật khẩu cho tài khoản: {row['username']}"


def danh_sach_nguoi_dung():
    conn = ket_noi_db()
    rows = conn.execute(
        "SELECT id, username, role FROM nguoi_dung ORDER BY CASE WHEN role='admin' THEN 0 ELSE 1 END, username ASC"
    ).fetchall()
    conn.close()
    return rows


def cap_nhat_quyen_nguoi_dung(user_id, role):
    role = (role or "staff").strip().lower()
    if role not in ["admin", "manager", "staff"]:
        role = "staff"

    conn = ket_noi_db()
    cur = conn.cursor()
    row = cur.execute("SELECT username, role FROM nguoi_dung WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "Không tìm thấy tài khoản."
    if row["username"] == "admin" and row["role"] == "admin":
        conn.close()
        return False, "Không được đổi quyền tài khoản admin gốc."

    cur.execute("UPDATE nguoi_dung SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()
    ten_quyen = "admin gốc" if role == "admin" else ("quản lý" if role == "manager" else "nhân viên bán hàng")
    return True, f"Đã cập nhật quyền cho {row['username']} thành {ten_quyen}"
