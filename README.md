# 🚀 Telegram Growth Suite v3.0

Tool tự động cào thành viên từ nhóm đối thủ và ép vào nhóm của bạn — hoàn toàn tự động, chống ban.

---

## ⚡ Cài & Chạy Ngay (Windows)

### Bước 1 — Clone project về máy
```bash
git clone https://github.com/phamlong3539-stack/keomenvip.git
cd keomenvip
```

### Bước 2 — Chạy file cài đặt tự động
Double-click vào file **`install.bat`** hoặc chạy trong terminal:
```bash
install.bat
```
Script sẽ tự cài Python dependencies.

### Bước 3 — Khởi động server
Double-click vào file **`run.bat`** hoặc chạy:
```bash
run.bat
```

### Bước 4 — Mở trình duyệt
Truy cập: **http://127.0.0.1:8000**

---

## 🛠️ Yêu Cầu Hệ Thống

- **Python 3.11+** — Tải tại: https://www.python.org/downloads/
- **Windows 10/11** (hoặc Linux/Mac)
- Tài khoản Telegram với API credentials

---

## 🔑 Lấy API Credentials

1. Vào **https://my.telegram.org**
2. Đăng nhập bằng số điện thoại Telegram
3. Vào **"API development tools"**
4. Tạo app → Copy **API ID** và **API Hash**

> ⚠️ **Lưu ý:** API ID là số 7-8 chữ số (VD: `28475912`), KHÔNG phải số điện thoại hay User ID

---

## 📋 Hướng Dẫn Sử Dụng

### 1. Đăng nhập Telegram
- Nhập **API ID**, **API Hash**, **Số điện thoại** (VD: `+84901234567`)
- Bấm **Đăng Nhập** → Nhập mã OTP gửi về Telegram

### 2. Cào thành viên từ nhóm đối thủ
- Nhập link nhóm đối thủ (VD: `https://t.me/tennhom`)
- Bấm **Cào Members**

### 3. Ép thành viên vào nhóm của bạn
- Nhập link nhóm của bạn
- Đặt **Delay** (khuyến nghị >= 35s) và **Max invites** (khuyến nghị <= 30)
- Bấm **Ép Mem Vào Nhóm**

### 4. Chạy tự động 1 click (Pipeline)
- Điền cả nhóm đối thủ và nhóm của bạn
- Bấm **🔥 1-Click Pipeline**

---

## ⚠️ Lưu Ý Quan Trọng

| Vấn đề | Giải thích |
|--------|-----------|
| **FloodWaitError** | Telegram chặn spam, cần chờ theo thời gian hiển thị |
| **Nhóm > 200 mem** | Tài khoản ép mem PHẢI là **Admin** của nhóm đích |
| **Nhóm private** | Tài khoản phải **tham gia nhóm đối thủ trước** mới cào được |
| **Thành công ảo** | Tool kiểm tra thực tế — chỉ đếm mem được thêm thật |

---

## 🔄 Đổi Tài Khoản

Bấm nút **"🔄 Đăng Xuất / Đổi Nick"** → Nhập thông tin tài khoản mới → Đăng nhập lại.  
Mỗi tài khoản lưu session riêng (`session_<sodienthoai>.session`).

---

## 📁 Cấu Trúc Project

```
keomenvip/
├── server.py              # FastAPI backend (chạy cái này)
├── config.py              # Cấu hình chung
├── core/
│   └── telegram_engine.py # Engine Telegram chính
├── static/
│   ├── app.js             # Frontend JavaScript
│   └── style.css          # Giao diện
├── templates/
│   └── index.html         # UI chính
├── install.bat            # Script cài dependencies
├── run.bat                # Script chạy server
├── requirements.txt       # Python packages
└── .env.example           # Mẫu biến môi trường
```

---

## 🔒 Bảo Mật

- File `*.session` chứa thông tin đăng nhập — **KHÔNG chia sẻ**
- File `members.csv` chứa dữ liệu thành viên — không được đưa lên git
- Xem `.gitignore` để biết các file được bảo vệ
