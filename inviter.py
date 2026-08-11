import sys
import os
import csv
import time
import random
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

def load_members(filename):
    if not os.path.exists(filename):
        print(f"[!] Lỗi: Không tìm thấy file '{filename}'. Bạn cần chạy 'python scraper.py' trước!")
        return []
    
    members = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            members.append(row)
    return members

def save_members(filename, members):
    if not members:
        return
    fieldnames = list(members[0].keys())
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(members)

def main():
    print("=" * 60)
    print("      TELEGRAM AUTO MEMBER INVITER TOOL (Telethon)      ")
    print("=" * 60)

    api_id = config.API_ID
    api_hash = config.API_HASH
    phone = config.PHONE_NUMBER

    if not api_id or not api_hash or api_id == "12345678":
        print("[!] CẢNH BÁO: Chưa cấu hình API_ID/API_HASH trong file .env!")
        api_id = input("[?] Nhập API_ID của bạn: ").strip()
        api_hash = input("[?] Nhập API_HASH của bạn: ").strip()
        phone = input("[?] Nhập Số điện thoại Telegram: ").strip()

    client = TelegramClient('telegram_session', int(api_id), api_hash)
    client.connect()

    if not client.is_user_authorized():
        print(f"[*] Đang gửi mã OTP xác thực qua Telegram: {phone}...")
        client.send_code_request(phone)
        try:
            code = input("[?] Nhập mã OTP: ").strip()
            client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("[?] Nhập mật khẩu 2FA: ").strip()
            client.sign_in(password=password)

    dest_group = input("[?] Nhập Link/Username Nhóm CỦA BẠN (VD: https://t.me/nhom_cua_toi hoặc @nhom_cua_toi): ").strip()
    
    try:
        dest_entity = client.get_entity(dest_group)
    except Exception as e:
        print(f"[!] Không thể kết nối tới nhóm của bạn. Lỗi: {e}")
        client.disconnect()
        return

    members = load_members(config.CSV_FILE_PATH)
    if not members:
        client.disconnect()
        return

    pending_members = [m for m in members if m.get('status') == 'pending']
    print(f"[+] Tìm thấy {len(pending_members)} thành viên ở trạng thái 'pending' (chờ mời).")

    added_count = 0
    max_invites = config.MAX_INVITES_PER_SESSION
    delay = config.DELAY_BETWEEN_INVITES

    print(f"[*] Cấu hình an toàn: Thêm tối đa {max_invites} mem/lần chạy, giãn cách {delay}s giữa các lời mời.\n")

    for member in members:
        if added_count >= max_invites:
            print(f"\n[!] Đã đạt hạn mức an toàn {max_invites} người cho phiên này. Dừng lại để bảo vệ account.")
            break

        if member.get('status') != 'pending':
            continue

        username = member.get('username', '')
        user_id = int(member.get('user_id', 0))
        access_hash = int(member.get('access_hash', 0))
        name = member.get('name', username or str(user_id))

        print(f"[*] Đang mời thành viên: {name} (@{username if username else user_id})...", end="")

        try:
            if username:
                user_to_add = client.get_input_entity(username)
            else:
                user_to_add = InputPeerUser(user_id, access_hash)

            if isinstance(dest_entity, (Channel, Chat)) or getattr(dest_entity, 'megagroup', False):
                res = client(InviteToChannelRequest(dest_entity, [user_to_add]))
                res_users = getattr(res, 'users', [])
                if not res_users:
                    print(" -> [CHẶN NGẦM] Telegram bỏ qua (Account chưa đủ uy tín hoặc User chặn người lạ).")
                    member['status'] = 'silently_filtered'
                    continue
            else:
                client(AddChatUserRequest(dest_entity.id, user_to_add, fwd_limit=100))

            added_count += 1
            member['status'] = 'invited'
            print(" -> [THÀNH CÔNG]")

            current_delay = delay + random.randint(1, 6)
            print(f"    [Chờ {current_delay}s để tránh spam filter...]")
            time.sleep(current_delay)

        except PeerFloodError:
            print(" -> [LỖI PEER_FLOOD]")
            print("\n[!] TÀI KHOẢN BỊ TELEGRAM GIỚI HẠN (SPAM LIMIT)!")
            print("[!] Vui lòng tạm dừng sử dụng tài khoản này trong 24-48 giờ.")
            member['status'] = 'peer_flood_error'
            save_members(config.CSV_FILE_PATH, members)
            break

        except UserPrivacyRestrictedError:
            print(" -> [BỎ QUA] Khách bật cài đặt không cho người lạ thêm vào nhóm.")
            member['status'] = 'privacy_restricted'

        except UserAlreadyParticipantError:
            print(" -> [BỎ QUA] Đã là thành viên trong nhóm.")
            member['status'] = 'already_in_group'

        except UserBannedInChannelError:
            print(" -> [BỎ QUA] User bị cấm trong nhóm.")
            member['status'] = 'banned'

        except UserChannelsTooMuchError:
            print(" -> [BỎ QUA] User tham gia quá nhiều nhóm.")
            member['status'] = 'too_many_channels'

        except FloodWaitError as e:
            print(f" -> [THỜI GIAN CHỜ] Telegram bắt chờ {e.seconds} giây.")
            time.sleep(e.seconds)

        except Exception as e:
            err_msg = str(e)
            if "maximum number of users" in err_msg.lower() or "users_too_much" in err_msg.lower():
                print(f" -> [LỖI GIỚI HẠN] Telegram từ chối ép trực tiếp vào nhóm {dest_group}.")
                member['status'] = 'limit_exceeded'
            else:
                print(f" -> [LỖI] {e}")
                member['status'] = f'error_{type(e).__name__}'

        save_members(config.CSV_FILE_PATH, members)

    print("=" * 60)
    print(f"[HOÀN THÀNH] Đã thêm {added_count} thành viên vào nhóm.")
    print(f"[+] Tiến trình được tự động lưu vào '{config.CSV_FILE_PATH}'.")
    client.disconnect()

if __name__ == '__main__':
    main()
