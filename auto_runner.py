import sys
import os
import time
import subprocess

# Auto install missing packages
def install_requirements():
    print("[*] Đang kiểm tra và cài đặt thư viện phụ thuộc...")
    try:
        import telethon
        import dotenv
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[+] Cài đặt thư viện thành công!\n")

install_requirements()

from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.types import InputPeerUser, Channel, Chat
from telethon.errors import (
    PeerFloodError,
    UserPrivacyRestrictedError,
    UserAlreadyParticipantError,
    UserBannedInChannelError,
    FloodWaitError,
    UserChannelsTooMuchError,
    SessionPasswordNeededError
)
import config
import csv

def setup_env():
    env_file = ".env"
    if not os.path.exists(env_file):
        print("=" * 60)
        print("    CẤU HÌNH THÔNG TIN TELEGRAM LẦN ĐẦU (TỰ ĐỘNG)    ")
        print("=" * 60)
        print("Lấy API_ID và API_HASH tại: https://my.telegram.org\n")
        
        api_id = input("[?] Nhập API_ID: ").strip()
        api_hash = input("[?] Nhập API_HASH: ").strip()
        phone = input("[?] Nhập Số điện thoại Telegram (+84...): ").strip()
        target_group = input("[?] Nhập Link/Username Nhóm MỤC TIÊU (để cào mem): ").strip()
        dest_group = input("[?] Nhập Link/Username Nhóm CỦA BẠN (để thêm mem): ").strip()

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"API_ID={api_id}\n")
            f.write(f"API_HASH={api_hash}\n")
            f.write(f"PHONE_NUMBER={phone}\n")
            f.write(f"TARGET_GROUP={target_group}\n")
            f.write(f"DEST_GROUP={dest_group}\n")
        
        print("[+] Đã lưu cấu hình vào file .env!")
        # Reload env vars
        from dotenv import load_dotenv
        load_dotenv(override=True)

def main():
    setup_env()
    
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    api_id = os.getenv("API_ID") or config.API_ID
    api_hash = os.getenv("API_HASH") or config.API_HASH
    phone = os.getenv("PHONE_NUMBER") or config.PHONE_NUMBER
    target_group = os.getenv("TARGET_GROUP")
    dest_group = os.getenv("DEST_GROUP")

    if not target_group:
        target_group = input("[?] Nhập Link/Username Nhóm MỤC TIÊU: ").strip()
    if not dest_group:
        dest_group = input("[?] Nhập Link/Username Nhóm CỦA BẠN: ").strip()

    print("\n" + "=" * 60)
    print("      HỆ THỐNG KÉO MEM TELEGRAM TỰ ĐỘNG (FULL AUTOMATION)      ")
    print("=" * 60)

    client = TelegramClient('telegram_session', int(api_id), api_hash)
    client.connect()

    if not client.is_user_authorized():
        print(f"[*] Gửi mã OTP xác thực tới số: {phone}...")
        client.send_code_request(phone)
        try:
            code = input("[?] Nhập mã OTP từ Telegram: ").strip()
            client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("[?] Nhập mật khẩu 2FA: ").strip()
            client.sign_in(password=password)

    print("[+] Đã kết nối Telegram thành công!")

    # 1. TỰ ĐỘNG SCRAPE NẾU CHƯA CÓ FILE DỮ LIỆU
    csv_file = config.CSV_FILE_PATH
    if not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0:
        print(f"\n[*] BẮT ĐẦU TỰ ĐỘNG QUÉT THÀNH VIÊN TỪ: {target_group}...")
        try:
            target_entity = client.get_entity(target_group)
            participants = client.get_participants(target_entity, aggressive=True)
            
            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["username", "user_id", "access_hash", "name", "group_title", "status"])
                count = 0
                for user in participants:
                    if user.bot:
                        continue
                    uname = user.username or ""
                    fname = (user.first_name or "") + " " + (user.last_name or "")
                    writer.writerow([uname, user.id, user.access_hash, fname.strip(), getattr(target_entity, 'title', 'Group'), "pending"])
                    count += 1
            print(f"[+] Đã quét và lưu tự động {count} thành viên vào '{csv_file}'.")
        except Exception as e:
            print(f"[!] Lỗi khi quét nhóm mục tiêu: {e}")
            client.disconnect()
            return

    # 2. TỰ ĐỘNG INVITE THÀNH VIÊN
    print(f"\n[*] BẮT ĐẦU TỰ ĐỘNG MỜI THÀNH VIÊN VÀO NHÓM: {dest_group}...")
    try:
        dest_entity = client.get_entity(dest_group)
    except Exception as e:
        print(f"[!] Lỗi kết nối nhóm đích: {e}")
        client.disconnect()
        return

    # Đọc danh sách
    members = []
    with open(csv_file, "r", encoding="utf-8") as f:
        members = list(csv.DictReader(f))

    added_count = 0
    max_invites = config.MAX_INVITES_PER_SESSION
    delay = config.DELAY_BETWEEN_INVITES

    for member in members:
        if added_count >= max_invites:
            print(f"\n[!] Tự động dừng tại {max_invites} người để bảo vệ tài khoản khỏi Spam Filter.")
            break

        if member.get('status') != 'pending':
            continue

        username = member.get('username', '')
        user_id = int(member.get('user_id', 0))
        access_hash = int(member.get('access_hash', 0))
        name = member.get('name', username or str(user_id))

        print(f"[*] Auto Invite -> {name} (@{username if username else user_id})...", end="")

        try:
            if username:
                user_to_add = client.get_input_entity(username)
            else:
                user_to_add = InputPeerUser(user_id, access_hash)

            if isinstance(dest_entity, (Channel, Chat)) or getattr(dest_entity, 'megagroup', False):
                client(InviteToChannelRequest(dest_entity, [user_to_add]))
            else:
                client(AddChatUserRequest(dest_entity.id, user_to_add, fwd_limit=100))

            added_count += 1
            member['status'] = 'invited'
            print(" -> [THÀNH CÔNG]")
            time.sleep(delay)

        except PeerFloodError:
            print(" -> [BỊ DỪNG DỌ SPAM LIMIT]")
            member['status'] = 'peer_flood_error'
            break
        except UserPrivacyRestrictedError:
            print(" -> [BỎ QUA] Quyền riêng tư")
            member['status'] = 'privacy_restricted'
        except UserAlreadyParticipantError:
            print(" -> [BỎ QUA] Đã ở trong nhóm")
            member['status'] = 'already_in_group'
        except Exception as e:
            print(f" -> [BỎ QUA] {type(e).__name__}")
            member['status'] = f'error_{type(e).__name__}'

        # Save progress automatically after each invite
        fieldnames = list(members[0].keys())
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(members)

    print("\n" + "=" * 60)
    print(f"[HOÀN THÀNH HOÀN TOÀN] Đã tự động thêm thành công {added_count} mem!")
    print("=" * 60)
    client.disconnect()

if __name__ == '__main__':
    main()
