# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import threading
import webbrowser
import socket
import base64
import json
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from db import ket_noi_db, DB_PATH
from auth import (
    login_required,
    role_required,
    tao_nhan_vien,
    xoa_nhan_vien,
    doi_mat_khau_nguoi_dung,
    admin_dat_lai_mat_khau,
    cap_nhat_quyen_nguoi_dung,
    danh_sach_nguoi_dung,
)

app = Flask(__name__)
app.secret_key = 'ung_dung_kho_hang_offline_v36_smtp_custom_roles'

print('=' * 60)
print('DANG DOC DATABASE TAI DUONG DAN:')
print(DB_PATH)
print('=' * 60)


def money(v):
    try:
        return f"{float(v):,.0f}"
    except:
        return '0'


def parse_float(v):
    v = (v or '').strip().replace(',', '')
    return float(v) if v else 0.0


def get_date_range(period, tu_ngay='', den_ngay=''):
    today = date.today()
    if period == 'today':
        start = today
        end = today
    elif period == 'month':
        start = today.replace(day=1)
        end = today
    elif period == '6months':
        start = today - timedelta(days=183)
        end = today
    elif period == '12months':
        start = today - timedelta(days=365)
    elif period == 'year':
        start = date(today.year, 1, 1)
        end = today
    elif period == 'custom' and tu_ngay and den_ngay:
        start = datetime.strptime(tu_ngay, '%Y-%m-%d').date()
        end = datetime.strptime(den_ngay, '%Y-%m-%d').date()
    else:
        start = today.replace(day=1)
        end = today
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


LOGIN_HTML = '''
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Đăng Nhập Quản Lý Kho</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>body{background:#f4f6f9;display:flex;align-items:center;justify-content:center;height:100vh}</style></head><body><div class="card p-4 shadow-sm" style="max-width:420px;width:100%;"><h2 class="text-primary text-center fw-bold mb-4">KHO HANG PRO</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} fw-bold">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}<form action="/login" method="POST"><div class="mb-3"><label class="fw-bold">Tài khoản:</label><input type="text" name="username" class="form-control" required autofocus></div><div class="mb-4"><label class="fw-bold">Mật khẩu:</label><input type="password" name="password" class="form-control" required></div><button type="submit" class="btn btn-primary w-100 fw-bold py-2">DANG NHAP</button></form></div></body></html>
'''

DOI_MAT_KHAU_HTML = '''
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Đổi mật khẩu</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background:#f4f6f9;"><nav class="navbar navbar-dark bg-primary mb-4 shadow-sm"><div class="container-fluid"><a class="navbar-brand fw-bold" href="/">Quay lại kho</a></div></nav><div class="container" style="max-width:680px;"><h2 class="fw-bold mb-4">Đổi mật khẩu</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} fw-bold">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}<div class="card shadow-sm border-0"><div class="card-header bg-danger text-white fw-bold">Tài khoản: {{ current_user }}</div><div class="card-body"><form method="POST"><div class="mb-3"><label class="fw-bold">Mật khẩu cũ</label><input type="password" name="mat_khau_cu" class="form-control" required></div><div class="mb-3"><label class="fw-bold">Mật khẩu mới</label><input type="password" name="mat_khau_moi" class="form-control" required></div><div class="mb-3"><label class="fw-bold">Xác nhận mật khẩu mới</label><input type="password" name="xac_nhan" class="form-control" required></div><button type="submit" class="btn btn-danger fw-bold w-100">Lưu mật khẩu mới</button></form></div></div></div></body></html>
'''

INDEX_HTML = '''
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>B.Bean Mobile Store - Quản Lý Kho</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" /><style>body{background-color:#f4f6f9;font-family:Arial,sans-serif}.card{box-shadow:0 4px 6px rgba(0,0,0,0.05);border:none;border-radius:10px;margin-bottom:20px}.card-header{border-radius:10px 10px 0 0 !important;font-weight:bold}.search-bar-container{position:sticky;top:0;z-index:10;background:white;padding:15px;border-bottom:2px solid #eee;border-radius:10px 10px 0 0}.hang-canh-bao{background-color:#ffe6e6 !important}.hang-canh-bao td{color:#cc0000 !important;font-weight:bold}.print-header{display:none;text-align:center;margin-bottom:20px}.staff-note{background:#eef6ff;border:1px dashed #0d6efd;border-radius:10px;padding:12px;font-size:14px;color:#0d3c75}.clock-box{background:linear-gradient(135deg,#e8f2ff,#ffffff);border:1px solid #b9d4ff;border-radius:14px;padding:14px;text-align:center}.clock-time{font-size:28px;font-weight:700;color:#0d47a1;font-family:Courier New,Courier,monospace}.clock-date{font-size:18px;font-weight:700;color:#333}.clock-lunar{font-size:16px;color:#c62828;font-weight:700;border-top:1px dashed #bbb;padding-top:8px;margin-top:8px}.click-hint{font-size:12px;color:#666;font-style:italic}.price-hint-box{margin-top:8px;padding:8px 10px;border-radius:8px;background:#e8f4ff;border:2px solid #0d6efd;color:#0b5394;font-weight:700}.price-warning-box{margin-top:8px;padding:10px 12px;border-radius:8px;background:#fff3cd;border:2px solid #dc3545;color:#b02a37;font-weight:800;font-size:15px;box-shadow:0 0 0 2px rgba(220,53,69,0.08)}@media print{nav,.col-lg-3,.search-bar-container,.alert,.modal,.btn,.thao-tac-col,.banner-ads{display:none !important}.col-lg-9{width:100% !important;padding:0 !important;margin:0 !important}body,.container-fluid{background:white !important;margin:0 !important;padding:0 !important}.card,.card-body{border:none !important;box-shadow:none !important;overflow:visible !important}.table{width:100% !important;border-collapse:collapse !important;font-size:12px !important}.table th,.table td{border:1px solid black !important;padding:5px !important;color:black !important;background-color:white !important}.print-header{display:block}tr[style*="display: none"]{display:none !important}}</style></head><body><nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4 shadow-sm"><div class="container-fluid"><a class="navbar-brand fw-bold" href="#">B.BEAN MOBILE STORE</a><div class="d-flex gap-2 align-items-center flex-wrap"><span class="badge bg-light text-dark">{{ current_user }} | {{ current_role }}</span><button class="btn btn-warning btn-sm fw-bold position-relative" data-bs-toggle="modal" data-bs-target="#cartModal">Giỏ Xuất Kho<span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" id="cartCount">{{ cart_len }}</span></button><div class="dropdown"><button class="btn btn-light btn-sm fw-bold text-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">Tiện ích</button><ul class="dropdown-menu dropdown-menu-end shadow"><li><a class="dropdown-item fw-bold" href="/caidat">Cài đặt</a></li>{% if is_root_admin %}<li><a class="dropdown-item fw-bold" href="/quan_ly_nhan_vien">Nhân viên</a></li>{% endif %}{% if can_manage_inventory %}<li><a class="dropdown-item fw-bold text-success" href="/summary">Báo cáo</a></li>{% else %}<li><a class="dropdown-item fw-bold text-success" href="/bao_cao_cua_toi">Báo cáo</a></li>{% endif %}</ul></div><a href="/logout" class="btn btn-secondary btn-sm fw-bold">Khóa</a></div></div></nav>{% if caidat['banner_b64'] %}<div class="container-fluid px-3 banner-ads mb-3 text-center"><img src="data:image/png;base64,{{ caidat['banner_b64'] }}" class="shadow-sm" style="width:100%;height:120px;object-fit:cover;display:block;border-radius:10px;border:2px solid #0d6efd;"></div>{% endif %}<div class="print-header"><h2>BÁO CÁO TỒN KHO</h2><p id="print-date"></p></div><div class="container-fluid px-3">{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} fw-bold text-center shadow-sm alert-dismissible fade show">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endif %}{% endwith %}<div class="row"><div class="col-lg-3 col-md-4 mb-4"><div class="card border-warning mb-4"><div class="card-header bg-warning text-dark">1. Thao tác</div><div class="card-body">{% if can_manage_inventory %}<form action="/nhapkho" method="POST" class="mb-4 pb-3 border-bottom"><h6 class="fw-bold text-primary">NHẬP KHO</h6><div class="mb-2"><select name="id" class="form-control select2-box" required><option value=""></option>{% for item in items %}<option value="{{ item.id }}">{{ item.ten }} (Tồn: {{ item.ton }})</option>{% endfor %}</select></div><div class="input-group"><span class="input-group-text fw-bold">SL</span><input type="number" name="sl" class="form-control" required min="1" value="1"><button type="submit" class="btn btn-primary fw-bold">Nhập</button></div></form>{% else %}<div class="staff-note mb-3">Nhân viên chỉ được kiểm tra tồn kho và xuất hàng. Không được thêm hàng, sửa giá, sửa số lượng, nhập kho hoặc xóa sản phẩm.</div><div class="click-hint mb-3">Mẹo: Nhân viên có thể double click vào một dòng sản phẩm bên danh sách để mở nhanh xuất kho.</div>{% endif %}<form action="/addtocart" method="POST"><h6 class="fw-bold text-danger">XUẤT KHO / TẠO PHIẾU</h6><div class="mb-2"><select name="id" id="quickExportSelect" class="form-control select2-box" required><option value=""></option>{% for item in items %}<option value="{{ item.id }}|{{ item.ten }}|{{ item.gia }}|{{ item.ton }}">{{ item.ten }} (Tồn: {{ item.ton }})</option>{% endfor %}</select></div><div id="quickExportGiaNhapHint" class="price-hint-box d-none"></div><div id="quickExportPriceWarning" class="price-warning-box d-none"></div><div class="input-group"><span class="input-group-text fw-bold" style="padding:0 5px;">SL</span><input type="number" name="sl" class="form-control border-danger" style="max-width: 70px; padding: 0 5px;" required min="1" value="1"><input type="number" name="giaxuat" id="quickExportGiaBan" class="form-control border-danger" placeholder="Giá bán khi xuất" required><button type="submit" class="btn btn-danger fw-bold" style="padding: 0 8px;">Thêm Giỏ</button></div><div class="form-text text-danger fw-bold">Nhân viên được nhập giá bán khi xuất, nhưng không được sửa giá nhập trong kho.</div></form></div></div><div class="card border-info shadow-sm d-print-none mb-4"><div class="card-header bg-info text-white fw-bold">2. Thời gian / lịch</div><div class="card-body"><div class="clock-box"><div id="clockTime" class="clock-time">00:00:00</div><div id="solarDate" class="clock-date mt-2">--</div><div id="lunarDate" class="clock-lunar">Âm lịch: --</div></div></div></div>{% if can_manage_inventory %}<div class="card border-success"><div class="card-header bg-success text-white">3. Thêm Hàng Mới</div><div class="card-body"><form action="/add" method="POST"><div class="mb-2"><input type="text" name="idmanual" class="form-control form-control-sm" placeholder="Mã SP (trống tự tạo)"></div><div class="mb-2"><input type="text" name="ten" class="form-control form-control-sm" required placeholder="Tên SP"></div><div class="row mb-2"><div class="col-6"><input type="number" name="gia" class="form-control form-control-sm" required placeholder="Giá nhập"></div><div class="col-6"><input type="number" name="sl" class="form-control form-control-sm" value="0" required placeholder="SL đầu"></div></div><div class="mb-2 border p-2 bg-light rounded"><label class="fw-bold text-danger" style="font-size:0.8rem;">Báo động khi rớt xuống dưới (cái)</label><input type="number" name="muccanhbao" class="form-control form-control-sm mb-1 border-danger" value="0"><div class="form-check form-switch mt-1"><input class="form-check-input" type="checkbox" name="batemail" id="batEmailNew" value="1"><label class="form-check-label fw-bold text-primary" style="font-size:0.85rem;" for="batEmailNew">Bật Gửi Email</label></div></div><div class="mb-2"><textarea name="ghichu" class="form-control form-control-sm" rows="1" placeholder="Ghi chú"></textarea></div><button type="submit" class="btn btn-success btn-sm w-100 fw-bold">Thêm Vào Kho</button></form></div></div>{% endif %}</div><div class="col-lg-9 col-md-8"><div class="card h-100 border-primary"><div class="search-bar-container d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-3"><div class="input-group" style="max-width: 60%;"><span class="input-group-text bg-primary text-white fw-bold">LỌC</span><input type="text" id="oTimKiem" onkeyup="timKiemBang()" class="form-control" placeholder="Gõ tìm kiếm..."></div><div class="d-flex align-items-center gap-3"><button onclick="window.print()" class="btn btn-dark fw-bold px-3">In Bảng Này</button>{% if can_manage_inventory %}<h5 class="text-danger fw-bold m-0 bg-light p-2 rounded border border-danger">Vốn: {{ tongtienstr }}đ</h5>{% else %}<h5 class="text-primary fw-bold m-0 bg-light p-2 rounded border border-primary">Chế độ nhân viên</h5>{% endif %}</div></div><div class="card-body p-0" style="max-height:65vh;overflow-y:auto;"><table class="table table-hover table-bordered mb-0 text-center align-middle" id="bangDuLieu" style="min-width: 800px;"><thead style="position: sticky; top:0; z-index:1;"><tr class="bg-light"><th>Mã SP</th><th class="text-start">Tên Sản Phẩm</th><th>Cảnh Báo</th>{% if can_manage_inventory %}<th>Nhập</th><th>Xuất</th><th class="text-danger">TỒN</th><th>Giá Mua</th>{% else %}<th class="text-danger">TỒN</th><th>Giá nhập</th>{% endif %}<th>Ghi Chú</th>{% if can_manage_inventory %}<th class="thao-tac-col">Thao tác</th>{% endif %}</tr></thead><tbody>{% for item in items %}<tr class="{% if item.muccanhbao > 0 and item.ton <= item.muccanhbao %}hang-canh-bao{% endif %}" ondblclick="handleRowDoubleClick(this)" style="cursor:pointer;" data-id="{{ item.id }}" data-ten="{{ item.ten }}" data-gia="{{ item.gia }}" data-ton="{{ item.ton }}" data-nhap="{{ item.nhap }}" data-xuat="{{ item.xuat }}" data-ghichu="{{ item.ghichu }}" data-canhbao="{{ item.muccanhbao }}" data-email="{{ item.batemail }}"><td class="fw-bold">{{ item.id }}</td><td class="text-start fw-bold">{{ item.ten }}{% if item.muccanhbao > 0 and item.ton <= item.muccanhbao %}<span class="badge bg-danger ms-2 shadow-sm">Sắp hết ({{ item.ton }}/{{ item.muccanhbao }})</span>{% endif %}</td><td>{% if item.muccanhbao > 0 %}Mức: <b class="text-danger">{{ item.muccanhbao }}</b><br>{% if item.batemail %}<span class="badge bg-primary" style="font-size:0.7rem;">Bật Email</span>{% else %}<span class="badge bg-secondary" style="font-size:0.7rem;">Tắt Email</span>{% endif %}{% else %}-{% endif %}</td>{% if can_manage_inventory %}<td>{{ item.nhap }}</td><td>{{ item.xuat }}</td><td class="text-danger fw-bold fs-5 bg-light">{{ item.ton }}</td><td class="fw-bold text-success">{{ item.gia|money }}</td>{% else %}<td class="text-danger fw-bold fs-5 bg-light">{{ item.ton }}</td><td class="fw-bold text-success">{{ item.gia|money }}</td>{% endif %}<td class="text-start text-muted" style="max-width: 150px; font-size: 0.85rem; word-wrap: break-word;">{{ item.ghichu }}</td>{% if can_manage_inventory %}<td class="thao-tac-col"><button type="button" class="btn btn-sm btn-outline-warning fw-bold text-dark" data-bs-toggle="modal" data-bs-target="#editModal" data-id="{{ item.id }}" data-ten="{{ item.ten }}" data-gia="{{ item.gia }}" data-nhap="{{ item.nhap }}" data-xuat="{{ item.xuat }}" data-ghichu="{{ item.ghichu }}" data-canhbao="{{ item.muccanhbao }}" data-email="{{ item.batemail }}" onclick="fillEditModal(this)">Sửa</button> <a href="/delete/{{ item.id }}" class="btn btn-sm btn-outline-danger fw-bold" onclick="return confirm('Xóa?')">Xóa</a></td>{% endif %}</tr>{% endfor %}</tbody></table></div></div></div></div></div>{% if can_manage_inventory %}<div class="modal fade" id="editModal" tabindex="-1" aria-hidden="true"><div class="modal-dialog"><div class="modal-content"><form action="/edit" method="POST"><div class="modal-header bg-warning"><h5 class="modal-title fw-bold">Sửa Sản Phẩm</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="hidden" name="id" id="editId"><div class="mb-3"><label class="fw-bold">Tên</label><input type="text" name="ten" id="editTen" class="form-control" required></div><div class="mb-3 border p-3 bg-light rounded border-danger"><label class="fw-bold text-danger">Mức báo động, nhập 0 để tắt</label><input type="number" name="muccanhbao" id="editCanhBao" class="form-control border-danger mb-2 fw-bold" required><div class="form-check form-switch mt-2"><input class="form-check-input" type="checkbox" name="batemail" id="editBatEmail" value="1" style="transform: scale(1.3); margin-right:10px;"><label class="form-check-label fw-bold text-primary" for="editBatEmail">Cho phép gửi email tự động</label></div></div><div class="row mb-3"><div class="col-4"><label class="fw-bold">Giá nhập</label><input type="number" name="gia" id="editGia" class="form-control" required></div><div class="col-4"><label class="fw-bold">Nhập</label><input type="number" name="nhap" id="editNhap" class="form-control" required></div><div class="col-4"><label class="fw-bold">Xuất</label><input type="number" name="xuat" id="editXuat" class="form-control" required></div></div><div class="mb-3"><label class="fw-bold">Ghi chú</label><textarea name="ghichu" id="editGhiChu" class="form-control" rows="1"></textarea></div></div><div class="modal-footer"><button type="submit" class="btn btn-warning fw-bold text-dark w-100">Lưu Thay Đổi</button></div></form></div></div></div>{% endif %}<div class="modal fade" id="staffExportModal" tabindex="-1" aria-hidden="true"><div class="modal-dialog"><div class="modal-content border-danger"><form action="/addtocart" method="POST"><div class="modal-header bg-danger text-white"><h5 class="modal-title fw-bold">Xuất kho nhanh</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><label class="fw-bold">Sản phẩm</label><input type="text" id="staffExportTen" class="form-control" readonly><input type="hidden" name="id" id="staffExportValue"></div><div id="staffExportGiaNhapHint" class="price-hint-box d-none"></div><div id="staffExportPriceWarning" class="price-warning-box d-none"></div><div class="row g-2"><div class="col-6"><label class="fw-bold">Số lượng xuất</label><input type="number" name="sl" id="staffExportSl" class="form-control" min="1" value="1" required></div><div class="col-6"><label class="fw-bold">Giá bán khi xuất</label><input type="number" name="giaxuat" id="staffExportGiaBan" class="form-control" min="0" step="0.01" required></div></div><div class="mt-3 small text-muted">Double click vào sản phẩm để mở nhanh cửa sổ này, sau đó nhập số lượng và giá bán rồi thêm vào giỏ.</div></div><div class="modal-footer"><button type="submit" class="btn btn-danger fw-bold w-100">Thêm vào giỏ xuất kho</button></div></form></div></div></div><div class="modal fade" id="cartModal" tabindex="-1" aria-hidden="true"><div class="modal-dialog modal-lg"><div class="modal-content border-danger"><div class="modal-header bg-danger text-white"><h5 class="modal-title fw-bold">KIỂM TRA PHIẾU XUẤT KHO</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body">{% if cart|length == 0 %}<h5 class="text-center text-muted my-4">Chưa chọn hàng xuất. Hãy thêm hàng từ cột trái.</h5>{% else %}<table class="table table-bordered text-center"><thead class="table-light"><tr><th>Mã SP</th><th class="text-start">Tên Hàng</th><th>Số lượng xuất</th><th>Giá bán / SP</th>{% if can_manage_inventory %}<th>Giá vốn / SP</th>{% endif %}<th>Tồn Lại</th><th>Xóa</th></tr></thead><tbody>{% for c in cart %}<tr><td>{{ c.id }}</td><td class="text-start fw-bold text-primary">{{ c.ten }}</td><td class="text-danger fw-bold fs-5">{{ c.sl }}</td><td>{{ c.gia_ban|money }}</td>{% if can_manage_inventory %}<td>{{ c.gia_von|money }}</td>{% endif %}<td class="text-success">{{ c.tonhientai - c.sl }}</td><td><a href="/removecart/{{ loop.index0 }}" class="btn btn-sm btn-outline-danger">Xóa</a></td></tr>{% endfor %}</tbody></table>{% endif %}</div><div class="modal-footer justify-content-between bg-light"><a href="/clearcart" class="btn btn-secondary fw-bold">Xóa Toàn Bộ Giỏ</a>{% if cart|length > 0 %}<form action="/previewphieuxuat" method="POST" class="w-100"><div class="row g-2"><div class="col-md-4"><input type="text" name="nguoinhan" class="form-control" placeholder="Người nhận / ghi chú" required></div><div class="col-md-2"><input type="number" step="0.01" min="0" name="chi_phi_van_chuyen" class="form-control" placeholder="Vận chuyển"></div><div class="col-md-2"><input type="number" step="0.01" min="0" name="hue_hong" class="form-control" placeholder="Huê hồng"></div><div class="col-md-2"><input type="number" step="0.01" min="0" name="chi_phi_khac" class="form-control" placeholder="Chi phí khác"></div><div class="col-md-2"><button type="submit" class="btn btn-danger fw-bold w-100">TẠO HÓA ĐƠN</button></div><div class="col-12"><input type="text" name="ghi_chu_chi_phi" class="form-control" placeholder="Ghi chú chi phí khác (nếu có)"></div></div></form>{% endif %}</div></div></div></div><script src="https://code.jquery.com/jquery-3.6.0.min.js"></script><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script><script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script><script>const canManageInventory={{ 'true' if can_manage_inventory else 'false' }};$(document).ready(function(){ $('.select2-box').select2({placeholder: '-- Tìm --', width: '100%'}); bindQuickExportPriceHint(); $('#quickExportSelect').on('change select2:select', function(){ syncQuickExportPriceHint(); }); updateClock(); setInterval(updateClock,1000); });function timKiemBang(){ var input=document.getElementById('oTimKiem').value.toUpperCase(); var tr=document.getElementById('bangDuLieu').getElementsByTagName('tr'); for(var i=1;i<tr.length;i++){ if(tr[i].innerText.toUpperCase().indexOf(input)>-1) tr[i].style.display=''; else tr[i].style.display='none'; } }function fillEditModal(btn){document.getElementById('editId').value=btn.getAttribute('data-id');document.getElementById('editTen').value=btn.getAttribute('data-ten');document.getElementById('editGia').value=btn.getAttribute('data-gia');document.getElementById('editNhap').value=btn.getAttribute('data-nhap');document.getElementById('editXuat').value=btn.getAttribute('data-xuat');document.getElementById('editGhiChu').value=btn.getAttribute('data-ghichu');document.getElementById('editCanhBao').value=btn.getAttribute('data-canhbao');document.getElementById('editBatEmail').checked=btn.getAttribute('data-email')=='1';}function formatMoneyHint(value){ const n=Number(value||0); return Number.isFinite(n)?n.toLocaleString('vi-VN')+'đ':'0đ'; }function updatePriceWarning(inputEl,hintEl,warningEl,giaNhap){ const giaMua=Number(giaNhap||0); if(hintEl){ if(giaMua>0){ hintEl.innerHTML='💡 Giá nhập tham khảo: <span class="text-primary">'+formatMoneyHint(giaMua)+'</span>'; hintEl.classList.remove('d-none'); } else { hintEl.innerHTML=''; hintEl.classList.add('d-none'); } } if(!warningEl||!inputEl) return; const raw=inputEl.value; const giaBan=Number(raw||0); if(raw!=='' && Number.isFinite(giaBan) && giaBan<giaMua){ warningEl.innerHTML='⚠️ Cảnh báo: Giá bán đang thấp hơn giá mua. Bạn vẫn có thể bán, nhưng nên kiểm tra lại.'; warningEl.classList.remove('d-none'); inputEl.classList.add('border-danger'); } else { warningEl.innerHTML=''; warningEl.classList.add('d-none'); inputEl.classList.remove('border-danger'); } }function syncQuickExportPriceHint(){ const selectEl=document.getElementById('quickExportSelect'); const inputEl=document.getElementById('quickExportGiaBan'); const hintEl=document.getElementById('quickExportGiaNhapHint'); const warningEl=document.getElementById('quickExportPriceWarning'); if(!selectEl||!inputEl) return; const parts=(selectEl.value||'').split('|'); const giaNhap=parts.length>=3?parts[2]:0; updatePriceWarning(inputEl,hintEl,warningEl,giaNhap); }function bindQuickExportPriceHint(){ const selectEl=document.getElementById('quickExportSelect'); const inputEl=document.getElementById('quickExportGiaBan'); if(!selectEl||!inputEl) return; selectEl.addEventListener('change',syncQuickExportPriceHint); inputEl.addEventListener('input',syncQuickExportPriceHint); syncQuickExportPriceHint(); }function openEditFromRow(row){ if(!row||!canManageInventory) return; fillEditModal(row); var modalEl=document.getElementById('editModal'); if(modalEl){ var modal=bootstrap.Modal.getOrCreateInstance(modalEl); modal.show(); }}function openExportFromRow(row){ if(!row||canManageInventory) return; const id=row.getAttribute('data-id'); const ten=row.getAttribute('data-ten'); const gia=row.getAttribute('data-gia'); const ton=row.getAttribute('data-ton'); const value=id+'|'+ten+'|'+gia+'|'+ton; const tenBox=document.getElementById('staffExportTen'); const valueBox=document.getElementById('staffExportValue'); const slBox=document.getElementById('staffExportSl'); const giaBanBox=document.getElementById('staffExportGiaBan'); const hintEl=document.getElementById('staffExportGiaNhapHint'); const warningEl=document.getElementById('staffExportPriceWarning'); if(tenBox) tenBox.value=ten+' (Tồn: '+ton+')'; if(valueBox) valueBox.value=value; if(slBox) slBox.value=1; if(giaBanBox){ giaBanBox.value=gia; giaBanBox.oninput=function(){ updatePriceWarning(giaBanBox,hintEl,warningEl,gia); }; setTimeout(()=>giaBanBox.focus(), 250); } updatePriceWarning(giaBanBox,hintEl,warningEl,gia); const modalEl=document.getElementById('staffExportModal'); if(modalEl){ const modal=bootstrap.Modal.getOrCreateInstance(modalEl); modal.show(); } }function handleRowDoubleClick(row){ if(canManageInventory) openEditFromRow(row); else openExportFromRow(row); }function updateClock(){ const now=new Date(); const clock=document.getElementById('clockTime'); const solar=document.getElementById('solarDate'); const lunar=document.getElementById('lunarDate'); if(clock){ clock.innerText=now.toLocaleTimeString('vi-VN',{hour12:false}); } if(solar){ let s=now.toLocaleDateString('vi-VN',{weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'}); solar.innerText=s.charAt(0).toUpperCase()+s.slice(1); } if(lunar){ try{ const f=new Intl.DateTimeFormat('vi-VN-u-ca-chinese',{day:'2-digit',month:'2-digit',year:'numeric'}); lunar.innerText='Âm lịch: '+f.format(now); }catch(e){ lunar.innerText='Âm lịch: Trình duyệt không hỗ trợ'; } } }var d=new Date();var pd=document.getElementById('print-date'); if(pd) pd.innerText='Ngày in: '+d.getDate()+'/'+(d.getMonth()+1)+'/'+d.getFullYear()+' '+d.getHours()+':'+d.getMinutes();</script></body></html>
'''

PHIEU_XUAT_HTML = """
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Hóa Đơn Xuất Kho</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>body{background:#ccc;display:flex;justify-content:center;padding:20px;font-family:'Courier New',Courier,monospace}.receipt{background:white;width:100%;max-width:700px;padding:30px;box-shadow:0 0 15px rgba(0,0,0,0.2)}.r-header{text-align:center;border-bottom:2px dashed #000;padding-bottom:15px;margin-bottom:20px}.r-title{font-size:24px;font-weight:bold;margin-bottom:5px;text-transform:uppercase}.table-receipt{width:100%;font-size:14px;margin-bottom:20px}.table-receipt th{border-bottom:1px solid #000;padding-bottom:5px;text-align:left}.table-receipt td{padding:8px 0;border-bottom:1px dotted #ccc}.r-footer{border-top:2px dashed #000;padding-top:15px;margin-top:20px}.signature{display:flex;justify-content:space-between;margin-top:40px;text-align:center}@media print{body{background:white;padding:0}.receipt{box-shadow:none;max-width:100%;padding:10px}.no-print{display:none !important}}</style></head><body><div class="receipt"><div class="no-print text-center mb-4 pb-3 border-bottom"><button onclick="window.print()" class="btn btn-dark fw-bold btn-lg w-100 mb-2">IN HÓA ĐƠN NÀY</button><form action="/chotxuatkho" method="POST"><input type="hidden" name="nguoinhan" value="{{ nguoinhan }}"><input type="hidden" name="chi_phi_van_chuyen" value="{{ chi_phi_van_chuyen }}"><input type="hidden" name="hue_hong" value="{{ hue_hong }}"><input type="hidden" name="chi_phi_khac" value="{{ chi_phi_khac }}"><input type="hidden" name="ghi_chu_chi_phi" value="{{ ghi_chu_chi_phi }}"><input type="hidden" name="ma_phieu" value="{{ code }}"><button type="submit" class="btn btn-danger fw-bold w-100 btn-lg" onclick="return confirm('Bạn in xong chưa? Xác nhận này sẽ TRỪ HÀNG trong kho và lưu doanh thu!')">HOÀN TẤT TRỪ KHO</button></form><a href="/" class="btn btn-link mt-2">Hủy bỏ, quay lại</a></div><div class="r-header"><div class="r-title">PHIẾU XUẤT KHO</div><div>Ngày: {{ thoigian }}</div><div>Mã phiếu: PX-{{ code }}</div></div><div style="margin-bottom:8px;font-weight:bold;">Nhân viên xuất: <span style="text-decoration: underline; color: blue;">{{ nhanvienxuat }}</span></div><div style="margin-bottom:8px;font-weight:bold;">Người nhận / ghi chú: <span style="text-decoration: underline; color: blue;">{{ nguoinhan }}</span></div><table class="table-receipt"><thead><tr><th>TT</th><th>Tên hàng hóa</th><th style="text-align:center;">SL</th><th style="text-align:right;">Giá bán</th><th style="text-align:right;">Thành tiền</th></tr></thead><tbody>{% set ns = namespace(total_ban=0) %}{% for item in cart %}{% set tien_ban = item.sl * item.gia_ban %}{% set ns.total_ban = ns.total_ban + tien_ban %}<tr><td>{{ loop.index }}</td><td><b>{{ item.ten }}</b></td><td style="text-align:center;font-weight:bold;">{{ item.sl }}</td><td style="text-align:right;">{{ item.gia_ban|money }}</td><td style="text-align:right;font-weight:bold;">{{ tien_ban|money }}</td></tr>{% endfor %}</tbody></table><div class="r-footer">{% set tong_thanh_toan = ns.total_ban + chi_phi_van_chuyen + chi_phi_khac - hue_hong %}<div style="display:flex;justify-content:space-between;font-size:18px;font-weight:bold;"><span>Tổng tiền hàng</span><span>{{ ns.total_ban|money }} VNĐ</span></div>{% if chi_phi_van_chuyen > 0 %}<div style="display:flex;justify-content:space-between;"><span>Chi phí vận chuyển</span><span>+ {{ chi_phi_van_chuyen|money }} VNĐ</span></div>{% endif %}{% if hue_hong > 0 %}<div style="display:flex;justify-content:space-between;"><span>Huê hồng khách</span><span>- {{ hue_hong|money }} VNĐ</span></div>{% endif %}{% if chi_phi_khac > 0 %}<div style="display:flex;justify-content:space-between;"><span>Chi phí khác</span><span>+ {{ chi_phi_khac|money }} VNĐ</span></div>{% endif %}<div style="display:flex;justify-content:space-between;font-size:18px;font-weight:bold;margin-top:10px;"><span>Tổng cộng thanh toán</span><span>{{ tong_thanh_toan|money }} VNĐ</span></div>{% if ghi_chu_chi_phi and (chi_phi_van_chuyen > 0 or hue_hong > 0 or chi_phi_khac > 0) %}<div style="margin-top:8px;font-size:12px;"><b>Ghi chú chi phí:</b> {{ ghi_chu_chi_phi }}</div>{% endif %}</div><div class="signature"><div style="width:45%;"><b>Người Giao Hàng</b><br><br><br><br><span>(Ký, ghi rõ họ tên)</span></div><div style="width:45%;"><b>Người Nhận Hàng</b><br><br><br><br><span>(Ký, ghi rõ họ tên)</span></div></div></div></body></html>
"""

STAFF_REPORT_HTML = """
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Báo cáo bán hàng</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background:#f4f6f9;"><nav class="navbar navbar-dark bg-primary mb-4 shadow-sm"><div class="container-fluid"><a class="navbar-brand fw-bold" href="/">Quay lại kho</a></div></nav><div class="container"><h2 class="fw-bold mb-4">Báo cáo bán hàng của tôi</h2><div class="card shadow-sm border-0 mb-4"><div class="card-header bg-primary text-white">Lọc thời gian</div><div class="card-body"><form method="GET" class="row g-2 align-items-end"><div class="col-md-3"><label class="fw-bold">Khoảng thời gian</label><select name="period" class="form-select"><option value="today" {% if period=='today' %}selected{% endif %}>Hôm nay</option><option value="month" {% if period=='month' %}selected{% endif %}>Tháng này</option><option value="year" {% if period=='year' %}selected{% endif %}>Năm này</option><option value="custom" {% if period=='custom' %}selected{% endif %}>Tùy chọn</option></select></div><div class="col-md-3"><label class="fw-bold">Từ ngày</label><input type="date" name="tu_ngay" value="{{ tu_ngay }}" class="form-control"></div><div class="col-md-3"><label class="fw-bold">Đến ngày</label><input type="date" name="den_ngay" value="{{ den_ngay }}" class="form-control"></div><div class="col-md-3"><button type="submit" class="btn btn-primary fw-bold w-100">Xem báo cáo</button></div></form></div></div><div class="row g-3"><div class="col-md-3"><div class="card border-primary shadow-sm"><div class="card-body"><div class="text-muted">Tổng bán</div><div class="fs-4 fw-bold text-primary">{{ tong_ban|money }}đ</div></div></div></div><div class="col-md-3"><div class="card border-info shadow-sm"><div class="card-body"><div class="text-muted">Vận chuyển</div><div class="fs-5 fw-bold text-info">{{ tong_vc|money }}đ</div></div></div></div><div class="col-md-3"><div class="card border-secondary shadow-sm"><div class="card-body"><div class="text-muted">Huê hồng</div><div class="fs-5 fw-bold text-secondary">{{ tong_hh|money }}đ</div></div></div></div><div class="col-md-3"><div class="card border-danger shadow-sm"><div class="card-body"><div class="text-muted">Chi phí khác</div><div class="fs-5 fw-bold text-danger">{{ tong_khac|money }}đ</div></div></div></div></div><div class="card shadow-sm border-0 mt-4 mb-4"><div class="card-header bg-dark text-white">Tổng hợp của tôi</div><div class="card-body"><div class="row"><div class="col-md-4"><div class="small text-muted">Tổng chi phí</div><div class="fw-bold">{{ tong_chi_phi|money }}đ</div></div><div class="col-md-4"><div class="small text-muted">Số phiếu xuất</div><div class="fw-bold">{{ so_phieu }}</div></div><div class="col-md-4"><div class="small text-muted">Tổng tiền hàng + chi phí</div><div class="fw-bold fs-4 text-primary">{{ tong_thanh_toan|money }}đ</div></div></div><div class="mt-3 text-muted">Báo cáo này chỉ hiển thị doanh số và chi phí liên quan đến các phiếu bạn đã xuất, không hiển thị lợi nhuận.</div></div></div><div class="row"><div class="col-lg-6 mb-4"><div class="card shadow-sm border-0 h-100"><div class="card-header bg-primary text-white">Tôi đã bán những gì</div><div class="card-body p-0"><table class="table table-bordered mb-0"><thead class="table-light"><tr><th>Sản phẩm</th><th>SL</th><th>Doanh thu</th></tr></thead><tbody>{% for r in products %}<tr><td>{{ r['ten_san_pham'] }}</td><td>{{ r['tong_sl'] }}</td><td>{{ r['tong_ban']|money }}</td></tr>{% endfor %}{% if not products %}<tr><td colspan="3" class="text-center text-muted">Chưa có dữ liệu trong khoảng thời gian này.</td></tr>{% endif %}</tbody></table></div></div></div><div class="col-lg-6 mb-4"><div class="card shadow-sm border-0 h-100"><div class="card-header bg-secondary text-white">Phiếu xuất của tôi</div><div class="card-body p-0"><table class="table table-bordered mb-0"><thead class="table-light"><tr><th>Mã phiếu</th><th>Ngày</th><th>Tổng bán</th><th>Tổng chi phí</th><th>Tổng thu</th></tr></thead><tbody>{% for r in phieu_list %}<tr><td>{{ r['ma_phieu'] }}</td><td>{{ r['ngay_tao'][:16].replace('T',' ') }}</td><td>{{ r['tong_ban']|money }}</td><td>{{ (r['chi_phi_van_chuyen'] + r['hue_hong'] + r['chi_phi_khac'])|money }}</td><td class="fw-bold text-primary">{{ (r['tong_ban'] + r['chi_phi_van_chuyen'] + r['hue_hong'] + r['chi_phi_khac'])|money }}</td></tr>{% endfor %}{% if not phieu_list %}<tr><td colspan="5" class="text-center text-muted">Chưa có phiếu xuất.</td></tr>{% endif %}</tbody></table></div></div></div></div></div></body></html>
"""

SUMMARY_HTML = '''
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Báo cáo lợi nhuận</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background:#f4f6f9;"><nav class="navbar navbar-dark bg-success mb-4 shadow-sm"><div class="container-fluid"><a class="navbar-brand fw-bold" href="/">Quay lại kho</a></div></nav><div class="container"><h2 class="fw-bold mb-4">Báo cáo lợi nhuận bán hàng</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} fw-bold">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}<div class="card shadow-sm border-0 mb-4"><div class="card-header bg-success text-white">Lọc thời gian</div><div class="card-body"><form method="GET" class="row g-2 align-items-end"><div class="col-md-3"><label class="fw-bold">Khoảng thời gian</label><select name="period" class="form-select"><option value="today" {% if period=='today' %}selected{% endif %}>Hôm nay</option><option value="month" {% if period=='month' %}selected{% endif %}>Tháng này</option><option value="6months" {% if period=='6months' %}selected{% endif %}>6 tháng</option><option value="12months" {% if period=='12months' %}selected{% endif %}>12 tháng</option><option value="custom" {% if period=='custom' %}selected{% endif %}>Tùy chọn</option></select></div><div class="col-md-3"><label class="fw-bold">Từ ngày</label><input type="date" name="tu_ngay" value="{{ tu_ngay }}" class="form-control"></div><div class="col-md-3"><label class="fw-bold">Đến ngày</label><input type="date" name="den_ngay" value="{{ den_ngay }}" class="form-control"></div><div class="col-md-3"><button type="submit" class="btn btn-success fw-bold w-100">Xem báo cáo</button></div></form></div></div><div class="row"><div class="col-md-3"><div class="card border-primary shadow-sm"><div class="card-body"><div class="text-muted">Tổng bán</div><div class="fs-4 fw-bold text-primary">{{ tong_ban|money }}đ</div></div></div></div><div class="col-md-3"><div class="card border-warning shadow-sm"><div class="card-body"><div class="text-muted">Tổng vốn</div><div class="fs-4 fw-bold text-warning">{{ tong_von|money }}đ</div></div></div></div><div class="col-md-2"><div class="card border-info shadow-sm"><div class="card-body"><div class="text-muted">Vận chuyển</div><div class="fs-5 fw-bold text-info">{{ tong_vc|money }}đ</div></div></div></div><div class="col-md-2"><div class="card border-secondary shadow-sm"><div class="card-body"><div class="text-muted">Huê hồng</div><div class="fs-5 fw-bold text-secondary">{{ tong_hh|money }}đ</div></div></div></div><div class="col-md-2"><div class="card border-danger shadow-sm"><div class="card-body"><div class="text-muted">Chi phí khác</div><div class="fs-5 fw-bold text-danger">{{ tong_khac|money }}đ</div></div></div></div></div><div class="card shadow-sm border-0 mt-4 mb-4"><div class="card-header bg-dark text-white">Lợi nhuận sơ bộ</div><div class="card-body"><div class="row"><div class="col-md-4"><div class="small text-muted">Tổng chi phí phụ</div><div class="fw-bold">{{ tong_chi_phi|money }}đ</div></div><div class="col-md-4"><div class="small text-muted">Số phiếu xuất</div><div class="fw-bold">{{ so_phieu }}</div></div><div class="col-md-4"><div class="small text-muted">Lợi nhuận</div><div class="fw-bold fs-4 {% if loi_nhuan >= 0 %}text-success{% else %}text-danger{% endif %}">{{ loi_nhuan|money }}đ</div></div></div><div class="mt-3 text-muted">Công thức: tổng bán - tổng vốn - chi phí vận chuyển - huê hồng - chi phí khác.</div></div></div><div class="row"><div class="col-lg-6 mb-4"><div class="card shadow-sm border-0 h-100"><div class="card-header bg-primary text-white">Bán được những gì</div><div class="card-body p-0"><table class="table table-bordered mb-0"><thead class="table-light"><tr><th>Sản phẩm</th><th>SL</th><th>Doanh thu</th><th>Lãi gộp</th></tr></thead><tbody>{% for r in products %}<tr><td>{{ r['ten_san_pham'] }}</td><td>{{ r['tong_sl'] }}</td><td>{{ r['tong_ban']|money }}</td><td>{{ r['lai_gop']|money }}</td></tr>{% endfor %}{% if not products %}<tr><td colspan="4" class="text-center text-muted">Chưa có dữ liệu trong khoảng thời gian này.</td></tr>{% endif %}</tbody></table></div></div></div><div class="col-lg-6 mb-4"><div class="card shadow-sm border-0 h-100"><div class="card-header bg-secondary text-white">Chi tiết phiếu xuất gần nhất</div><div class="card-body p-0"><table class="table table-bordered mb-0"><thead class="table-light"><tr><th>Mã phiếu</th><th>Ngày</th><th>Người xuất</th><th>Tổng bán</th><th>Lợi nhuận</th></tr></thead><tbody>{% for r in phieu_list %}<tr><td>{{ r['ma_phieu'] }}</td><td>{{ r['ngay_tao'][:16].replace('T',' ') }}</td><td>{{ r['nguoi_xuat'] }}</td><td>{{ r['tong_ban']|money }}</td><td>{{ r['loi_nhuan']|money }}</td></tr>{% endfor %}{% if not phieu_list %}<tr><td colspan="5" class="text-center text-muted">Chưa có phiếu xuất.</td></tr>{% endif %}</tbody></table></div></div></div></div></div></body></html>
'''

SETTINGS_HTML = '''<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Cài đặt Hệ Thống</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background-color:#f4f6f9;"><nav class="navbar navbar-dark bg-dark mb-4 shadow-sm"><div class="container-fluid"><a class="navbar-brand fw-bold" href="/">QUAY LẠI KHO</a></div></nav><div class="container"><h2 class="fw-bold mb-4">Cài đặt tài khoản và hệ thống</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} fw-bold">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}<div class="row"><div class="col-md-5 mb-4"><div class="card shadow-sm border-0 mb-4 border-warning"><div class="card-header bg-warning text-dark fw-bold">Bảo mật tài khoản</div><div class="card-body"><div class="mb-2 text-muted">Tài khoản đang đăng nhập: <b>{{ current_user }}</b></div><p class="text-muted mb-3">Bạn có thể tự đổi mật khẩu của mình tại đây.</p><a href="/doi_mat_khau" class="btn btn-warning fw-bold w-100">Đổi mật khẩu</a></div></div>{% if can_manage_inventory %}<div class="card shadow-sm border-0 h-100"><div class="card-header bg-primary text-white fw-bold">Banner Thương Hiệu</div><div class="card-body"><form action="/savesettings" method="POST" enctype="multipart/form-data"><input type="hidden" name="action" value="banner"><div class="mb-3"><label class="fw-bold">Chọn hình ảnh mới</label><input type="file" name="bannerimg" class="form-control" accept=".png,.jpg,.jpeg,.webp,.gif,image/*"></div>{% if caidat['banner_b64'] %}<div class="mb-3 text-center"><label class="fw-bold text-success d-block text-start">Banner hiện tại</label><img src="data:image/png;base64,{{ caidat['banner_b64'] }}" style="width:100%;height:120px;object-fit:cover;display:block;border-radius:5px;border:1px solid #ccc;"><div class="mt-2 text-start"><input type="checkbox" name="xoabanner" value="1"> <span class="text-danger fw-bold">Xóa hình này</span></div></div>{% endif %}<button type="submit" class="btn btn-primary fw-bold w-100">Lưu Banner</button></form></div></div>{% endif %}</div><div class="col-md-7 mb-4">{% if can_manage_inventory %}<div class="card shadow-sm border-0 mb-4 border-danger"><div class="card-header bg-danger text-white fw-bold">Cấu Hình Máy Chủ Gửi Email SMTP</div><div class="card-body"><form action="/savesettings" method="POST"><input type="hidden" name="action" value="email"><div class="row"><div class="col-8 mb-3"><label class="fw-bold text-danger">SMTP Server</label><input type="text" name="smtphost" class="form-control border-danger" value="{{ caidat['smtp_host'] }}" required></div><div class="col-4 mb-3"><label class="fw-bold text-danger">Cổng Port</label><input type="number" name="smtpport" class="form-control border-danger" value="{{ caidat['smtp_port'] }}" required></div></div><div class="mb-3"><label class="fw-bold">Email gửi đi</label><input type="email" name="smtpemail" class="form-control" value="{{ caidat['smtp_email'] }}"></div><div class="mb-3"><label class="fw-bold">Mật khẩu App Password</label><input type="password" name="smtppass" class="form-control" value="{{ caidat['smtp_pass'] }}"></div><div class="mb-3"><label class="fw-bold text-primary">Email nhận thông báo</label><input type="email" name="receiveemail" class="form-control border-primary" value="{{ caidat['receive_email'] }}"></div><div class="alert alert-info small shadow-sm"><div class="fw-bold mb-2">Hướng dẫn SMTP nhanh</div><div><b>Gmail:</b> SMTP Server = smtp.gmail.com, Port = 587 hoặc 465, mật khẩu = App Password 16 ký tự.</div><div><b>Outlook / Hotmail:</b> SMTP Server = smtp.office365.com, Port = 587, mật khẩu = mật khẩu email hoặc App Password nếu tài khoản yêu cầu.</div><div><b>Apple iCloud:</b> SMTP Server = smtp.mail.me.com, Port = 587 hoặc 465, email gửi = địa chỉ iCloud Mail, mật khẩu = app-specific password từ Apple ID.</div><div class="mt-2 text-danger fw-bold">Lưu ý: Gmail và Apple nên dùng App Password, không dùng mật khẩu đăng nhập chính.</div></div><button type="submit" class="btn btn-danger fw-bold w-100">Lưu Cấu Hình Email</button></form></div></div><div class="card shadow-sm border-0 border-warning"><div class="card-header bg-warning text-dark fw-bold">Bảo mật hệ thống</div><div class="card-body"><p class="text-muted mb-3">Admin và quản lý có thể cấu hình email cảnh báo, banner và các thiết lập hệ thống tại đây.</p></div></div>{% endif %}</div></div></div></body></html>'''

STAFF_HTML = '''<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Quản lý nhân viên</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background:#f4f6f9;"><nav class="navbar navbar-dark bg-primary mb-4 shadow-sm"><div class="container-fluid"><a class="navbar-brand fw-bold" href="/">Quay lại kho</a></div></nav><div class="container"><h2 class="fw-bold mb-4">Quản lý nhân viên</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} fw-bold">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}<div class="row"><div class="col-md-5 mb-4"><div class="card shadow-sm border-0"><div class="card-header bg-success text-white fw-bold">Tạo tài khoản nhân viên / quản lý</div><div class="card-body"><form method="POST"><div class="mb-3"><label class="fw-bold">Tên đăng nhập</label><input type="text" name="username" class="form-control" required></div><div class="mb-3"><label class="fw-bold">Mật khẩu</label><input type="text" name="password" class="form-control" required></div><div class="mb-3"><label class="fw-bold">Phân quyền mặc định khi tạo</label><select name="role" class="form-select" required><option value="staff">Nhân viên bán hàng</option><option value="manager">Quản lý</option></select></div><button type="submit" class="btn btn-success fw-bold w-100">Tạo tài khoản</button></form></div></div></div><div class="col-md-7 mb-4"><div class="card shadow-sm border-0"><div class="card-header bg-dark text-white fw-bold">Danh sách tài khoản và đổi quyền nhanh</div><div class="card-body p-0"><table class="table table-bordered mb-0 text-center"><thead class="table-light"><tr><th>ID</th><th>Tài khoản</th><th>Bán hàng</th><th>Quản lý</th><th>Đổi pass</th><th>Xóa</th></tr></thead><tbody>{% for u in users %}<tr><td>{{ u['id'] }}</td><td>{{ u['username'] }}</td><td><form action="/cap_nhat_quyen/{{ u['id'] }}" method="POST" class="m-0"><input type="hidden" name="role" value="staff"><input class="form-check-input" type="checkbox" onchange="this.form.submit()" {% if u['role'] == 'staff' %}checked{% endif %} {% if u['username'] == 'admin' and u['role'] == 'admin' %}disabled{% endif %}></form></td><td><form action="/cap_nhat_quyen/{{ u['id'] }}" method="POST" class="m-0"><input type="hidden" name="role" value="manager"><input class="form-check-input" type="checkbox" onchange="this.form.submit()" {% if u['role'] == 'manager' %}checked{% endif %} {% if u['username'] == 'admin' and u['role'] == 'admin' %}disabled{% endif %}></form></td><td>{% if not (u['username'] == 'admin' and u['role'] == 'admin') %}<button type="button" class="btn btn-sm btn-outline-warning fw-bold" data-bs-toggle="collapse" data-bs-target="#resetPass{{ u['id'] }}">Đổi pass</button>{% else %}<span class="text-muted">-</span>{% endif %}</td><td>{% if not (u['username'] == 'admin' and u['role'] == 'admin') %}<a href="/xoa_nhan_vien/{{ u['id'] }}" class="btn btn-sm btn-outline-danger fw-bold" onclick="return confirm('Xóa tài khoản này?')">Xóa</a>{% else %}<span class="text-muted">-</span>{% endif %}</td></tr><tr class="table-light"><td colspan="6"><div class="px-3 py-2 text-start small"><b>Ghi chú:</b> Tích ô Bán hàng để tài khoản chỉ xuất kho. Tích ô Quản lý để tài khoản có toàn quyền kho hàng như admin, nhưng không được tạo nhân viên hay sửa phân quyền.</div>{% if not (u['username'] == 'admin' and u['role'] == 'admin') %}<div class="collapse" id="resetPass{{ u['id'] }}"><form action="/admin_doi_pass_nhan_vien/{{ u['id'] }}" method="POST" class="row g-2 p-2"><div class="col-md-5"><input type="text" name="mat_khau_moi" class="form-control" placeholder="Mật khẩu mới" required></div><div class="col-md-5"><input type="text" name="xac_nhan" class="form-control" placeholder="Xác nhận mật khẩu" required></div><div class="col-md-2"><button type="submit" class="btn btn-warning fw-bold w-100">Lưu</button></div></form></div>{% endif %}</td></tr>{% endfor %}</tbody></table></div></div></div></div></div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script></body></html>'''

app.jinja_env.filters['money'] = money

@app.route('/login', methods=['GET', 'POST'])
def login():
    ket_noi_db()
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pwd = request.form.get('password', '')
        conn = ket_noi_db()
        row = conn.execute("SELECT id, username, password, role FROM nguoi_dung WHERE username=?", (user,)).fetchone()
        conn.close()
        if row and row['password'] == pwd:
            session['logged_in'] = True
            session['user_id'] = row['id']
            session['username'] = row['username']
            session['role'] = row['role'] or 'staff'
            session['cart'] = []
            return redirect(url_for('index'))
        flash('Sai tài khoản hoặc mật khẩu!', 'danger')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/doi_mat_khau', methods=['GET', 'POST'])
@login_required
def doi_mat_khau():
    if request.method == 'POST':
        ok, msg = doi_mat_khau_nguoi_dung(session.get('user_id'), request.form.get('mat_khau_cu'), request.form.get('mat_khau_moi'), request.form.get('xac_nhan'))
        flash(msg, 'success' if ok else 'danger')
        return redirect(url_for('doi_mat_khau'))
    return render_template_string(DOI_MAT_KHAU_HTML, current_user=session.get('username', ''))

@app.route('/quan_ly_nhan_vien', methods=['GET', 'POST'])
@role_required('admin')
def quan_ly_nhan_vien():
    if request.method == 'POST':
        ok, msg = tao_nhan_vien(request.form.get('username'), request.form.get('password'), request.form.get('role'))
        flash(msg, 'success' if ok else 'danger')
        return redirect(url_for('quan_ly_nhan_vien'))
    return render_template_string(STAFF_HTML, users=danh_sach_nguoi_dung())

@app.route('/cap_nhat_quyen/<int:user_id>', methods=['POST'])
@role_required('admin')
def cap_nhat_quyen(user_id):
    ok, msg = cap_nhat_quyen_nguoi_dung(user_id, request.form.get('role'))
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('quan_ly_nhan_vien'))

@app.route('/admin_doi_pass_nhan_vien/<int:user_id>', methods=['POST'])
@role_required('admin')
def admin_doi_pass_nhan_vien(user_id):
    ok, msg = admin_dat_lai_mat_khau(user_id, request.form.get('mat_khau_moi'), request.form.get('xac_nhan'))
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('quan_ly_nhan_vien'))

@app.route('/xoa_nhan_vien/<int:user_id>')
@role_required('admin')
def xoa_nhan_vien_route(user_id):
    ok, msg = xoa_nhan_vien(user_id)
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('quan_ly_nhan_vien'))

@app.route('/caidat', methods=['GET'])
@login_required
def show_settings():
    conn = ket_noi_db()
    caidat = conn.execute("SELECT * FROM cai_dat WHERE id=1").fetchone()
    conn.close()
    return render_template_string(SETTINGS_HTML, caidat=caidat, can_manage_inventory=session.get('role') in ['admin', 'manager'], current_user=session.get('username', ''))

@app.route('/savesettings', methods=['POST'])
@login_required
def save_settings():
    action = request.form.get('action')
    conn = ket_noi_db()
    cur = conn.cursor()
    if action == 'banner':
        if session.get('role') not in ['admin', 'manager']:
            flash('Bạn không có quyền sửa banner.', 'danger')
        else:
            if request.form.get('xoabanner'):
                cur.execute("UPDATE cai_dat SET banner_b64='' WHERE id=1")
            else:
                file = request.files.get('bannerimg')
                if file and file.filename != '':
                    cur.execute("UPDATE cai_dat SET banner_b64=? WHERE id=1", (base64.b64encode(file.read()).decode('utf-8'),))
            flash('Lưu Banner thành công!', 'success')
    elif action == 'email':
        if session.get('role') not in ['admin', 'manager']:
            flash('Bạn không có quyền sửa cấu hình email.', 'danger')
        else:
            cur.execute("UPDATE cai_dat SET smtp_email=?, smtp_pass=?, receive_email=?, smtp_host=?, smtp_port=? WHERE id=1", (request.form.get('smtpemail', ''), request.form.get('smtppass', ''), request.form.get('receiveemail', ''), request.form.get('smtphost', 'smtp.gmail.com'), int(request.form.get('smtpport', 587))))
            flash('Lưu cấu hình SMTP Email thành công!', 'success')
    conn.commit(); conn.close()
    return redirect(url_for('show_settings'))

@app.route('/')
@login_required
def index():
    if 'cart' not in session:
        session['cart'] = []
    conn = ket_noi_db()
    caidat = conn.execute("SELECT * FROM cai_dat WHERE id=1").fetchone()
    rows = conn.execute("SELECT id, ten, tong_nhap, tong_xuat, gia_mua, ghi_chu, muc_canh_bao, bat_email FROM san_pham ORDER BY id DESC").fetchall()
    conn.close()
    items, tongtienall = [], 0
    for r in rows:
        ton = r['tong_nhap'] - r['tong_xuat']
        tongtienall += ton * r['gia_mua']
        items.append({'id': r['id'], 'ten': r['ten'], 'nhap': r['tong_nhap'], 'xuat': r['tong_xuat'], 'ton': ton, 'gia': r['gia_mua'], 'ghichu': r['ghi_chu'], 'muccanhbao': r['muc_canh_bao'], 'batemail': r['bat_email']})
    return render_template_string(INDEX_HTML, items=items, tongtienstr=money(tongtienall), caidat=caidat, cart=session['cart'], cart_len=len(session['cart']), is_root_admin=session.get('role') == 'admin', can_manage_inventory=session.get('role') in ['admin', 'manager'], current_user=session.get('username', ''), current_role=('ADMIN GỐC' if session.get('role') == 'admin' else ('QUẢN LÝ' if session.get('role') == 'manager' else 'NHÂN VIÊN')))

@app.route('/bao_cao_cua_toi')
@login_required
def bao_cao_cua_toi():
    period = request.args.get('period', 'month')
    tu_ngay = request.args.get('tu_ngay', '')
    den_ngay = request.args.get('den_ngay', '')
    start, end = get_date_range(period, tu_ngay, den_ngay)
    username = session.get('username', '')
    conn = ket_noi_db()
    phieu_list = conn.execute("SELECT * FROM phieu_xuat WHERE nguoi_xuat=? AND date(ngay_tao) BETWEEN ? AND ? ORDER BY ngay_tao DESC LIMIT 50", (username, start, end)).fetchall()
    products = conn.execute("SELECT ten_san_pham, SUM(so_luong) AS tong_sl, SUM(thanh_tien_ban) AS tong_ban FROM phieu_xuat_ct WHERE nguoi_xuat=? AND date(ngay_tao) BETWEEN ? AND ? GROUP BY ten_san_pham ORDER BY tong_sl DESC, tong_ban DESC", (username, start, end)).fetchall()
    sums = conn.execute("SELECT COUNT(*) AS so_phieu, COALESCE(SUM(tong_ban),0) AS tong_ban, COALESCE(SUM(chi_phi_van_chuyen),0) AS tong_vc, COALESCE(SUM(hue_hong),0) AS tong_hh, COALESCE(SUM(chi_phi_khac),0) AS tong_khac FROM phieu_xuat WHERE nguoi_xuat=? AND date(ngay_tao) BETWEEN ? AND ?", (username, start, end)).fetchone()
    conn.close()
    tong_chi_phi = (sums['tong_vc'] or 0) + (sums['tong_hh'] or 0) + (sums['tong_khac'] or 0)
    tong_thanh_toan = (sums['tong_ban'] or 0) + tong_chi_phi
    return render_template_string(STAFF_REPORT_HTML, period=period, tu_ngay=start if period == 'custom' else tu_ngay, den_ngay=end if period == 'custom' else den_ngay, tong_ban=sums['tong_ban'], tong_vc=sums['tong_vc'], tong_hh=sums['tong_hh'], tong_khac=sums['tong_khac'], tong_chi_phi=tong_chi_phi, tong_thanh_toan=tong_thanh_toan, so_phieu=sums['so_phieu'], products=products, phieu_list=phieu_list)

@app.route('/summary')
@role_required('admin', 'manager')
def summary_page():
    period = request.args.get('period', 'month')
    tu_ngay = request.args.get('tu_ngay', '')
    den_ngay = request.args.get('den_ngay', '')
    start, end = get_date_range(period, tu_ngay, den_ngay)
    conn = ket_noi_db()
    phieu_list = conn.execute("SELECT * FROM phieu_xuat WHERE date(ngay_tao) BETWEEN ? AND ? ORDER BY ngay_tao DESC LIMIT 50", (start, end)).fetchall()
    products = conn.execute("SELECT ten_san_pham, SUM(so_luong) AS tong_sl, SUM(thanh_tien_ban) AS tong_ban, SUM(thanh_tien_ban - thanh_tien_von) AS lai_gop FROM phieu_xuat_ct WHERE date(ngay_tao) BETWEEN ? AND ? GROUP BY ten_san_pham ORDER BY tong_sl DESC, tong_ban DESC", (start, end)).fetchall()
    sums = conn.execute("SELECT COUNT(*) AS so_phieu, COALESCE(SUM(tong_ban),0) AS tong_ban, COALESCE(SUM(tong_von),0) AS tong_von, COALESCE(SUM(chi_phi_van_chuyen),0) AS tong_vc, COALESCE(SUM(hue_hong),0) AS tong_hh, COALESCE(SUM(chi_phi_khac),0) AS tong_khac, COALESCE(SUM(loi_nhuan),0) AS loi_nhuan FROM phieu_xuat WHERE date(ngay_tao) BETWEEN ? AND ?", (start, end)).fetchone()
    conn.close()
    tong_chi_phi = (sums['tong_vc'] or 0) + (sums['tong_hh'] or 0) + (sums['tong_khac'] or 0)
    return render_template_string(SUMMARY_HTML, period=period, tu_ngay=start if period == 'custom' else tu_ngay, den_ngay=end if period == 'custom' else den_ngay, tong_ban=sums['tong_ban'], tong_von=sums['tong_von'], tong_vc=sums['tong_vc'], tong_hh=sums['tong_hh'], tong_khac=sums['tong_khac'], tong_chi_phi=tong_chi_phi, loi_nhuan=sums['loi_nhuan'], so_phieu=sums['so_phieu'], products=products, phieu_list=phieu_list)

@app.route('/add', methods=['POST'])
@role_required('admin', 'manager')
def additem():
    try:
        ten = request.form.get('ten', '').strip()
        idmanual = request.form.get('idmanual', '').strip()
        gia = float(request.form.get('gia', 0))
        sl = int(request.form.get('sl', 0))
        muccanhbao = int(request.form.get('muccanhbao', 0))
        batemail = 1 if request.form.get('batemail') else 0
        ghichu = request.form.get('ghichu', '')
        conn = ket_noi_db(); cur = conn.cursor(); finalid = idmanual
        if not finalid:
            maxid = 0
            for r in cur.execute("SELECT id FROM san_pham WHERE id LIKE 'SP%'").fetchall():
                try: maxid = max(maxid, int(r['id'][2:]))
                except: pass
            finalid = f"SP{maxid+1:03d}"
        cur.execute("INSERT INTO san_pham (id, ten, tong_nhap, tong_xuat, gia_mua, ghi_chu, muc_canh_bao, bat_email) VALUES (?, ?, ?, 0, ?, ?, ?, ?)", (finalid, ten, sl, gia, ghichu, muccanhbao, batemail))
        conn.commit(); conn.close(); flash(f'Đã thêm mới {ten}', 'success')
    except:
        flash('Không thể thêm sản phẩm.', 'danger')
    return redirect(url_for('index'))

@app.route('/edit', methods=['POST'])
@role_required('admin', 'manager')
def edititem():
    try:
        idsp = request.form.get('id')
        ten = request.form.get('ten', '').strip()
        ghichu = request.form.get('ghichu', '')
        gia = float(request.form.get('gia', 0))
        nhap = int(request.form.get('nhap', 0))
        xuat = int(request.form.get('xuat', 0))
        muccanhbao = int(request.form.get('muccanhbao', 0))
        batemail = 1 if request.form.get('batemail') else 0
        conn = ket_noi_db(); conn.execute("UPDATE san_pham SET ten=?, gia_mua=?, tong_nhap=?, tong_xuat=?, ghi_chu=?, muc_canh_bao=?, bat_email=? WHERE id=?", (ten, gia, nhap, xuat, ghichu, muccanhbao, batemail, idsp)); conn.commit(); conn.close(); flash(f'Đã cập nhật {ten}!', 'success')
    except:
        flash('Không thể cập nhật sản phẩm.', 'danger')
    return redirect(url_for('index'))

@app.route('/delete/<idsp>')
@role_required('admin', 'manager')
def deleteitem(idsp):
    conn = ket_noi_db(); conn.execute("DELETE FROM san_pham WHERE id=?", (idsp,)); conn.commit(); conn.close(); return redirect(url_for('index'))

@app.route('/nhapkho', methods=['POST'])
@role_required('admin', 'manager')
def nhapkho():
    try:
        idsp = request.form.get('id'); sl = int(request.form.get('sl', 0)); conn = ket_noi_db(); row = conn.execute("SELECT ten, tong_nhap FROM san_pham WHERE id=?", (idsp,)).fetchone()
        if row:
            conn.execute("UPDATE san_pham SET tong_nhap=? WHERE id=?", (row['tong_nhap'] + sl, idsp)); conn.commit(); flash(f'NHẬP thêm {sl} {row["ten"]}', 'success')
        conn.close()
    except:
        flash('Không thể nhập kho.', 'danger')
    return redirect(url_for('index'))

@app.route('/addtocart', methods=['POST'])
@login_required
def addtocart():
    try:
        data = request.form.get('id', '').split('|'); sl = int(request.form.get('sl', 0)); giaxuatinput = request.form.get('giaxuat', '').strip()
        if len(data) == 4:
            idsp, ten, gianhap, ton = data[0], data[1], float(data[2]), int(data[3])
            if not giaxuatinput:
                flash('Vui lòng nhập giá bán khi xuất.', 'danger'); return redirect(url_for('index'))
            giaban = float(giaxuatinput)
            if giaban < 0:
                flash('Giá bán không hợp lệ.', 'danger'); return redirect(url_for('index'))
            cart = session.get('cart', []); found = False
            for c in cart:
                if c['id'] == idsp:
                    if c['sl'] + sl > ton: flash(f'Tồn kho chỉ còn {ton} cái!', 'danger'); return redirect(url_for('index'))
                    c['sl'] += sl; c['gia_ban'] = giaban; found = True; break
            if not found:
                if sl > ton: flash(f'Tồn kho chỉ còn {ton} cái!', 'danger'); return redirect(url_for('index'))
                cart.append({'id': idsp, 'ten': ten, 'gia_ban': giaban, 'gia_von': gianhap, 'tonhientai': ton, 'sl': sl})
            session['cart'] = cart; flash(f'Đã thêm {sl} {ten} vào giỏ xuất kho.', 'success')
    except:
        flash('Không thể thêm vào giỏ.', 'danger')
    return redirect(url_for('index'))

@app.route('/removecart/<int:index>')
@login_required
def removecart(index):
    cart = session.get('cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/clearcart')
@login_required
def clearcart():
    session['cart'] = []
    return redirect(url_for('index'))

@app.route('/previewphieuxuat', methods=['POST'])
@login_required
def previewphieuxuat():
    nguoinhan = request.form.get('nguoinhan', 'Khách Lẻ')
    chi_phi_van_chuyen = parse_float(request.form.get('chi_phi_van_chuyen'))
    hue_hong = parse_float(request.form.get('hue_hong'))
    chi_phi_khac = parse_float(request.form.get('chi_phi_khac'))
    ghi_chu_chi_phi = request.form.get('ghi_chu_chi_phi', '').strip()
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('index'))
    conn = ket_noi_db(); caidat = conn.execute("SELECT * FROM cai_dat WHERE id=1").fetchone(); conn.close()
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    code = datetime.now().strftime('%Y%m%d%H%M%S')
    total_ban = sum(x['sl'] * x['gia_ban'] for x in cart)
    total_von = sum(x['sl'] * x['gia_von'] for x in cart)
    loi_nhuan = total_ban - total_von - chi_phi_van_chuyen - hue_hong - chi_phi_khac
    return render_template_string(PHIEU_XUAT_HTML, cart=cart, caidat=caidat, thoigian=now, nguoinhan=nguoinhan, nhanvienxuat=session.get('username', ''), code=code, chi_phi_van_chuyen=chi_phi_van_chuyen, hue_hong=hue_hong, chi_phi_khac=chi_phi_khac, ghi_chu_chi_phi=ghi_chu_chi_phi, loi_nhuan=loi_nhuan)

@app.route('/chotxuatkho', methods=['POST'])
@login_required
def chotxuatkho():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('index'))
    nguoinhan = request.form.get('nguoinhan', 'Khách Lẻ')
    chi_phi_van_chuyen = parse_float(request.form.get('chi_phi_van_chuyen'))
    hue_hong = parse_float(request.form.get('hue_hong'))
    chi_phi_khac = parse_float(request.form.get('chi_phi_khac'))
    ghi_chu_chi_phi = request.form.get('ghi_chu_chi_phi', '').strip()
    ma_phieu = request.form.get('ma_phieu') or datetime.now().strftime('%Y%m%d%H%M%S')
    ngay_tao = datetime.now().isoformat(timespec='seconds')
    conn = ket_noi_db(); cur = conn.cursor()
    caidat = conn.execute("SELECT smtp_email, smtp_pass, receive_email, smtp_host, smtp_port FROM cai_dat WHERE id=1").fetchone()
    thongbaoemail = []
    tong_ban = 0
    tong_von = 0
    for c in cart:
        row = cur.execute("SELECT tong_xuat, tong_nhap, muc_canh_bao, bat_email FROM san_pham WHERE id=?", (c['id'],)).fetchone()
        if row:
            xuatcu, nhapcu, muccanhbao, batemail = row['tong_xuat'], row['tong_nhap'], row['muc_canh_bao'], row['bat_email']
            toncu = nhapcu - xuatcu
            tonmoi = toncu - c['sl']
            if tonmoi < 0:
                conn.close(); flash(f'Sản phẩm {c["ten"]} không đủ tồn kho để xuất.', 'danger'); return redirect(url_for('index'))
            cur.execute("UPDATE san_pham SET tong_xuat=? WHERE id=?", (xuatcu + c['sl'], c['id']))
            tien_ban = c['sl'] * c['gia_ban']
            tien_von = c['sl'] * c['gia_von']
            tong_ban += tien_ban
            tong_von += tien_von
            cur.execute("INSERT INTO phieu_xuat_ct (ma_phieu, san_pham_id, ten_san_pham, so_luong, gia_ban, gia_von, thanh_tien_ban, thanh_tien_von, ngay_tao, nguoi_xuat) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (ma_phieu, c['id'], c['ten'], c['sl'], c['gia_ban'], c['gia_von'], tien_ban, tien_von, ngay_tao, session.get('username', '')))
            if batemail == 1 and muccanhbao > 0 and toncu > muccanhbao and tonmoi <= muccanhbao:
                thongbaoemail.append(f'- {c["ten"]}: Còn {tonmoi} cái (Ngưỡng: {muccanhbao})')
    loi_nhuan = tong_ban - tong_von - chi_phi_van_chuyen - hue_hong - chi_phi_khac
    cur.execute("INSERT INTO phieu_xuat (ma_phieu, ngay_tao, nguoi_xuat, nguoi_nhan, tong_ban, tong_von, chi_phi_van_chuyen, hue_hong, chi_phi_khac, ghi_chu_chi_phi, loi_nhuan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (ma_phieu, ngay_tao, session.get('username', ''), nguoinhan, tong_ban, tong_von, chi_phi_van_chuyen, hue_hong, chi_phi_khac, ghi_chu_chi_phi, loi_nhuan))
    conn.commit(); conn.close(); session['cart'] = []; flash('XUẤT KHO THÀNH CÔNG, ĐÃ LƯU LỊCH SỬ VÀ QUAY VỀ TRANG CHỦ!', 'success')
    if thongbaoemail and caidat and caidat['smtp_email'] and caidat['smtp_pass'] and caidat['receive_email']:
        body = 'BÁO ĐỘNG SẮP HẾT HÀNG\n\n' + '\n'.join(thongbaoemail)
        def sendt():
            try:
                msg = MIMEMultipart(); msg['From'], msg['To'], msg['Subject'] = caidat['smtp_email'], caidat['receive_email'], 'B.Bean Mobile Store - BÁO ĐỘNG SẮP HẾT HÀNG'; msg.attach(MIMEText(body, 'plain', 'utf-8'))
                host = caidat['smtp_host'] if caidat['smtp_host'] else 'smtp.gmail.com'; port = int(caidat['smtp_port']) if caidat['smtp_port'] else 587
                if port == 465: s = smtplib.SMTP_SSL(host, port)
                else: s = smtplib.SMTP(host, port); s.starttls()
                s.login(caidat['smtp_email'], caidat['smtp_pass']); s.send_message(msg); s.quit()
            except Exception as e:
                print('Lỗi gửi Email SMTP:', e)
        threading.Thread(target=sendt).start()
    return redirect(url_for('index'))

if __name__ == '__main__':
    ket_noi_db()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    print('\nB.Bean Mobile Store PHAN QUYEN + SUMMARY đang chạy...')
    threading.Timer(1.0, lambda: webbrowser.open(f'http://127.0.0.1:{port}')).start()
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
