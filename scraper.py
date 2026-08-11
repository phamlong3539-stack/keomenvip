import sys
import os
import csv
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import config

def main():
    print("=" * 60)
    print("      TELEGRAM MEMBER SCRAPER TOOL (Telethon)      ")
    print("=" * 60)

    api_id = config.API_ID
    api_hash = config.API_HASH
    phone = config.PHONE_NUMBER

    if not api_id or not api_hash or api_id == "12345678":
        print("[!] CẢNH BÁO: Chưa cấu hình API_ID/API_HASH chính xác trong file .env!")
        api_id = input("[?] Nhập API_ID của bạn (từ my.telegram.org): ").strip()
        api_hash = input("[?] Nhập API_HASH của bạn: ").strip()
        phone = input("[?] Nhập Số điện thoại Telegram (Ví dụ +8490...): ").strip()

    client = TelegramClient('telegram_session', int(api_id), api_hash)
    client.connect()

    if not client.is_user_authorized():
        print(f"[*] Đang gửi mã xác thực OTP tới số điện thoại: {phone}...")
        client.send_code_request(phone)
        try:
            code = input("[?] Nhập mã OTP gồm 5 chữ số từ Telegram: ").strip()
            client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("[?] Tài khoản bật 2FA. Nhập mật khẩu 2FA của bạn: ").strip()
            client.sign_in(password=password)

    print("\n[+] Đăng nhập Telegram thành công!")
    target_group = input("[?] Nhập Link/Username nhóm mục tiêu cần quét (VD: https://t.me/nhom_mau hoặc @nhom_mau): ").strip()

    print(f"[*] Đang kết nối tới nhóm {target_group}...")
    try:
        entity = client.get_entity(target_group)
    except Exception as e:
        print(f"[!] Không thể tìm thấy nhóm mục tiêu. Lỗi: {e}")
        client.disconnect()
        return

    print("[*] Đang tiến hành lấy danh sách thành viên (Scraping)...")
    try:
        all_participants = client.get_participants(entity, aggressive=True)
    except Exception as e:
        print(f"[!] Không thể lấy danh sách thành viên. Lỗi (Có thể nhóm ẩn danh sách): {e}")
        client.disconnect()
        return

    print(f"[+] Tìm thấy tổng cộng {len(all_participants)} người dùng trong nhóm.")

    filename = config.CSV_FILE_PATH
    saved_count = 0

    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",", lineterminator="\n")
        writer.writerow(["username", "user_id", "access_hash", "name", "group_title", "status"])
        for user in all_participants:
            if user.bot:
                continue  # Bỏ qua các bot
            
            username = user.username if user.username else ""
            first_name = user.first_name if user.first_name else ""
            last_name = user.last_name if user.last_name else ""
            name = (first_name + " " + last_name).strip()
            
            writer.writerow([username, user.id, user.access_hash, name, getattr(entity, 'title', 'Group'), "pending"])
            saved_count += 1

    print(f"\n[THÀNH CÔNG] Đã lưu thông tin {saved_count} thành viên vào file '{filename}'.")
    client.disconnect()

if __name__ == '__main__':
    main()
