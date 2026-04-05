from auth import (
    login_required,
    role_required,
    tao_nhan_vien,
    xoa_nhan_vien,
    doi_mat_khau_nguoi_dung,
    admin_dat_lai_mat_khau,
    cap_nhat_quyen_nguoi_dung,
    danh_sach_nguoi_dung,
    verify_password_and_migrate_if_needed,
)
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
        end = today
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
    @app.route('/login', methods=['GET', 'POST'])
def login():
    ket_noi_db()
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pwd = request.form.get('password', '')

        conn = ket_noi_db()
        row = conn.execute(
            "SELECT id, username, password, role FROM nguoi_dung WHERE username=?",
            (user,)
        ).fetchone()
        conn.close()

        if row and verify_password_and_migrate_if_needed(row['id'], row['password'], pwd):
            session['logged_in'] = True
            session['user_id'] = row['id']
            session['username'] = row['username']
            session['role'] = row['role'] or 'staff'
            session['cart'] = []
            return redirect(url_for('index'))

        flash('Sai tài khoản hoặc mật khẩu!', 'danger')

    return render_template_string(LOGIN_HTML)
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

    ma_phieu = request.form.get('ma_phieu') or datetime.now().strftime('%Y%m%d%H%M%S%f')
    ngay_tao = datetime.now().isoformat(timespec='seconds')

    conn = ket_noi_db()
    cur = conn.cursor()

    try:
        conn.execute("BEGIN IMMEDIATE")

        caidat = conn.execute(
            "SELECT smtp_email, smtp_pass, receive_email, smtp_host, smtp_port FROM cai_dat WHERE id=1"
        ).fetchone()

        thongbaoemail = []
        tong_ban = 0
        tong_von = 0

        for c in cart:
            row = cur.execute(
                "SELECT tong_xuat, tong_nhap, muc_canh_bao, bat_email FROM san_pham WHERE id=?",
                (c['id'],)
            ).fetchone()

            if not row:
                raise Exception(f"Không tìm thấy sản phẩm ID={c['id']}")

            xuatcu, nhapcu, muccanhbao, batemail = row['tong_xuat'], row['tong_nhap'], row['muc_canh_bao'], row['bat_email']
            toncu = nhapcu - xuatcu
            tonmoi = toncu - c['sl']

            if tonmoi < 0:
                raise Exception(f'Sản phẩm {c["ten"]} không đủ tồn kho để xuất.')

            cur.execute("UPDATE san_pham SET tong_xuat=? WHERE id=?", (xuatcu + c['sl'], c['id']))

            tien_ban = c['sl'] * c['gia_ban']
            tien_von = c['sl'] * c['gia_von']
            tong_ban += tien_ban
            tong_von += tien_von

            cur.execute(
                "INSERT INTO phieu_xuat_ct (ma_phieu, san_pham_id, ten_san_pham, so_luong, gia_ban, gia_von, thanh_tien_ban, thanh_tien_von, ngay_tao, nguoi_xuat) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ma_phieu, c['id'], c['ten'], c['sl'], c['gia_ban'], c['gia_von'], tien_ban, tien_von, ngay_tao, session.get('username', ''))
            )

            if batemail == 1 and muccanhbao > 0 and toncu > muccanhbao and tonmoi <= muccanhbao:
                thongbaoemail.append(f'- {c["ten"]}: Còn {tonmoi} cái (Ngưỡng: {muccanhbao})')

        loi_nhuan = tong_ban - tong_von - chi_phi_van_chuyen - hue_hong - chi_phi_khac

        cur.execute(
            "INSERT INTO phieu_xuat (ma_phieu, ngay_tao, nguoi_xuat, nguoi_nhan, tong_ban, tong_von, chi_phi_van_chuyen, hue_hong, chi_phi_khac, ghi_chu_chi_phi, loi_nhuan) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ma_phieu, ngay_tao, session.get('username', ''), nguoinhan, tong_ban, tong_von, chi_phi_van_chuyen, hue_hong, chi_phi_khac, ghi_chu_chi_phi, loi_nhuan)
        )

        conn.commit()
        conn.close()

        session['cart'] = []
        flash('XUẤT KHO THÀNH CÔNG, ĐÃ LƯU LỊCH SỬ VÀ QUAY VỀ TRANG CHỦ!', 'success')

        if thongbaoemail and caidat and caidat['smtp_email'] and caidat['smtp_pass'] and caidat['receive_email']:
            body = 'BÁO ĐỘNG SẮP HẾT HÀNG\n\n' + '\n'.join(thongbaoemail)

            def sendt():
                try:
                    msg = MIMEMultipart()
                    msg['From'], msg['To'], msg['Subject'] = caidat['smtp_email'], caidat['receive_email'], 'B.Bean Mobile Store - BÁO ĐỘNG SẮP HẾT HÀNG'
                    msg.attach(MIMEText(body, 'plain', 'utf-8'))
                    host = caidat['smtp_host'] if caidat['smtp_host'] else 'smtp.gmail.com'
                    port = int(caidat['smtp_port']) if caidat['smtp_port'] else 587
                    if port == 465:
                        s = smtplib.SMTP_SSL(host, port)
                    else:
                        s = smtplib.SMTP(host, port)
                        s.starttls()
                    s.login(caidat['smtp_email'], caidat['smtp_pass'])
                    s.send_message(msg)
                    s.quit()
                except Exception as e:
                    print('Lỗi gửi Email SMTP:', e)

            threading.Thread(target=sendt).start()

        return redirect(url_for('index'))

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        flash(f'Lỗi xuất kho: {e}', 'danger')
        return redirect(url_for('index'))
