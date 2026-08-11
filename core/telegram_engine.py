import asyncio
import csv
import os
import random
import logging
from datetime import datetime
from typing import Callable, Optional

from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.types import (
    InputUser, Channel, Chat,
    UserStatusOnline, UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth
)
from telethon.errors import (
    PeerFloodError, UserPrivacyRestrictedError, UserAlreadyParticipantError,
    UserBannedInChannelError, FloodWaitError, UserChannelsTooMuchError,
    SessionPasswordNeededError, ChatAdminRequiredError, ChatWriteForbiddenError,
    ChannelPrivateError, ChatForbiddenError
)

logger = logging.getLogger("TelegramEngine")

class TelegramGrowthEngine:
    """Enterprise Telegram Member Growth Engine v3.0"""

    def __init__(self, session_name: str = "telegram_session"):
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        self.is_running = False

    # ─── Auth ───────────────────────────────────────────────

    async def connect(self, api_id: int, api_hash: str, phone: str) -> dict:
        if api_id > 2147483647 or api_id < 10000:
            raise Exception(
                "❌ API_ID không hợp lệ!\n"
                "API_ID phải lấy từ https://my.telegram.org → 'API development tools'\n"
                "Không được nhập User ID, Bot ID hay số điện thoại vào ô này."
            )

        clean_phone = "".join(filter(str.isdigit, phone))
        session_name = f"session_{clean_phone}" if clean_phone else "telegram_session"

        if self.client and self.client.is_connected():
            try:
                me = await self.client.get_me()
                # Nếu đã đăng nhập đúng số điện thoại này
                if me and clean_phone in getattr(me, 'phone', ''):
                    return {
                        "status": "authorized",
                        "message": f"Đã kết nối tài khoản: {me.first_name} (+{me.phone})"
                    }
            except Exception:
                pass
            await self.client.disconnect()

        self.session_name = session_name
        self.client = TelegramClient(self.session_name, api_id, api_hash)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            sent = await self.client.send_code_request(phone)
            return {
                "status": "otp_required",
                "phone_code_hash": sent.phone_code_hash,
                "message": f"Đã gửi mã OTP tới {phone}"
            }

        me = await self.client.get_me()
        # Nếu session sẵn có là của số điện thoại khác, tiến hành hủy và gửi OTP cho số mới
        if clean_phone and clean_phone not in getattr(me, 'phone', ''):
            await self.client.disconnect()
            # Xóa session cũ của số khác nếu cần
            session_file = f"{session_name}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
            self.client = TelegramClient(session_name, api_id, api_hash)
            await self.client.connect()
            sent = await self.client.send_code_request(phone)
            return {
                "status": "otp_required",
                "phone_code_hash": sent.phone_code_hash,
                "message": f"Đã gửi mã OTP tới {phone}"
            }

        return {
            "status": "authorized",
            "message": f"Đăng nhập thành công: {me.first_name} (+{me.phone})"
        }

    async def logout(self) -> dict:
        if self.client:
            try:
                if self.client.is_connected():
                    await self.client.disconnect()
            except Exception:
                pass
            self.client = None
        return {"status": "logged_out", "message": "Đã đăng xuất tài khoản thành công."}

    async def verify_otp(self, phone: str, code: str, phone_code_hash: str, password: Optional[str] = None) -> dict:
        if not self.client:
            raise Exception("Chưa khởi tạo client. Gọi connect() trước.")
        try:
            await self.client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            if not password:
                return {"status": "2fa_required", "message": "Tài khoản bật 2FA, nhập mật khẩu."}
            await self.client.sign_in(password=password)

        me = await self.client.get_me()
        return {"status": "authorized", "message": f"Đăng nhập thành công: {me.first_name}"}

    # ─── Scraper ─────────────────────────────────────────────

    async def scrape(
        self,
        target_link: str,
        csv_file: str,
        only_active: bool = True,
        only_photo: bool = False,
        cb: Optional[Callable] = None
    ) -> int:
        if not self.client or not await self.client.is_user_authorized():
            raise Exception("Chưa đăng nhập Telegram.")

        await self._log(cb, f"🔍 Đang kết nối nhóm đối thủ: {target_link}")

        # Lấy entity — nếu nhóm private, sẽ báo lỗi rõ ràng
        try:
            target = await self.client.get_entity(target_link)
        except (ChannelPrivateError, ChatForbiddenError, ValueError) as e:
            await self._log(cb, f"❌ Không thể truy cập nhóm đối thủ: Nhóm này là PRIVATE hoặc tài khoản bị BAN. Hãy dùng link mời hoặc đảm bảo tài khoản đã được tham gia vào nhóm trước.")
            raise Exception(f"Nhóm đối thủ '{target_link}' là private hoặc bạn bị ban: {str(e)}")
        except Exception as e:
            await self._log(cb, f"❌ Không tìm thấy nhóm: {target_link} — {str(e)[:100]}")
            raise

        # Tự gia nhập nhóm đối thủ để cào được thành viên
        try:
            await self.client(JoinChannelRequest(target))
            await self._log(cb, "✅ Đã tham gia nhóm đối thủ.")
        except ChannelPrivateError:
            await self._log(cb, "⚠️ Nhóm đối thủ là PRIVATE — cần link mời để tham gia. Hãy dùng link dạng t.me/+xxxx.")
        except Exception:
            await self._log(cb, "ℹ️ Đã là thành viên hoặc là kênh công khai.")

        users = []
        # Thử Chế độ 1: get_participants (nhanh, đủ dữ liệu)
        try:
            await self._log(cb, "⚡ Chế độ 1: Đang cào danh sách thành viên trực tiếp...")
            users = await self.client.get_participants(target, aggressive=True)
            await self._log(cb, f"📊 Cào được {len(users)} thành viên từ danh sách nhóm.")
        except (ChatAdminRequiredError, ChatWriteForbiddenError) as e:
            await self._log(cb, "⚠️ Không cào được danh sách (Nhóm ẩn). Chuyển Chế độ 2: Cào qua lịch sử tin nhắn...")
            try:
                seen = set()
                async for msg in self.client.iter_messages(target, limit=3000):
                    if msg.sender_id and msg.sender_id not in seen:
                        seen.add(msg.sender_id)
                        if msg.sender:
                            users.append(msg.sender)
                await self._log(cb, f"📊 Chế độ 2: Cào được {len(users)} thành viên active từ lịch sử tin nhắn.")
            except (ChannelPrivateError, ChatForbiddenError) as e2:
                await self._log(cb, f"❌ Nhóm đối thủ là PRIVATE — tài khoản chưa tham gia hoặc bị ban. Không thể cào lịch sử tin nhắn.")
                raise Exception(f"Không thể cào lịch sử nhóm private '{target_link}': {str(e2)}")
            except Exception as e2:
                await self._log(cb, f"⚠️ Lỗi cào lịch sử tin nhắn: {str(e2)[:100]}")
        except (ChannelPrivateError, ChatForbiddenError) as e:
            await self._log(cb, f"❌ Nhóm đối thủ là PRIVATE hoặc tài khoản bị BAN khỏi nhóm. Không thể cào thành viên.")
            raise Exception(f"Không thể cào nhóm private '{target_link}': {str(e)}")
        except Exception as e:
            await self._log(cb, f"⚠️ Không cào được danh sách ({str(e)[:80]}). Chuyển Chế độ 2: Cào qua lịch sử tin nhắn...")
            try:
                seen = set()
                async for msg in self.client.iter_messages(target, limit=3000):
                    if msg.sender_id and msg.sender_id not in seen:
                        seen.add(msg.sender_id)
                        if msg.sender:
                            users.append(msg.sender)
                await self._log(cb, f"📊 Chế độ 2: Cào được {len(users)} thành viên active từ lịch sử tin nhắn.")
            except (ChannelPrivateError, ChatForbiddenError) as e2:
                await self._log(cb, f"❌ Nhóm đối thủ là PRIVATE — tài khoản chưa tham gia hoặc bị ban. Không thể cào lịch sử tin nhắn.")
                raise Exception(f"Không thể cào lịch sử nhóm private '{target_link}': {str(e2)}")
            except Exception as e2:
                await self._log(cb, f"⚠️ Lỗi cào lịch sử tin nhắn: {str(e2)[:100]}")

        if not users:
            await self._log(cb, "⚠️ Không tìm được thành viên nào.")
            return 0

        # Lọc và ghi CSV
        saved = 0
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["username", "user_id", "access_hash", "name", "activity", "status"])
            for user in users:
                if getattr(user, "bot", False) or getattr(user, "deleted", False):
                    continue
                if only_photo and not getattr(user, "photo", None):
                    continue

                activity = "unknown"
                st = getattr(user, "status", None)
                if isinstance(st, (UserStatusOnline, UserStatusRecently)):
                    activity = "recently_active"
                elif isinstance(st, UserStatusLastWeek):
                    activity = "last_week"
                elif isinstance(st, UserStatusLastMonth):
                    activity = "last_month"
                else:
                    if only_active:
                        continue

                uname = getattr(user, "username", "") or ""
                fname = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
                ahash = getattr(user, "access_hash", 0) or 0

                w.writerow([uname, user.id, ahash, fname, activity, "pending"])
                saved += 1

        await self._log(cb, f"✅ Đã lọc & lưu {saved} thành viên chất lượng vào danh sách.")
        return saved

    # ─── Inviter ─────────────────────────────────────────────

    async def invite(
        self,
        dest_link: str,
        csv_file: str,
        delay: int = 35,
        max_per_session: int = 30,
        cb: Optional[Callable] = None
    ) -> int:
        if not self.client or not await self.client.is_user_authorized():
            raise Exception("Chưa đăng nhập Telegram.")
        if not os.path.exists(csv_file):
            raise Exception("Không có file danh sách. Chạy Scraper trước!")

        self.is_running = True
        dest = await self.client.get_entity(dest_link)
        is_channel = isinstance(dest, (Channel, Chat)) or getattr(dest, "megagroup", False)

        try:
            me = await self.client.get_me()
            perms = await self.client.get_permissions(dest, me)
            if not getattr(perms, "is_admin", False):
                await self._log(cb, "⚠️ LƯU Ý: Tài khoản đăng nhập KHÔNG PHẢI LÀ ADMIN của nhóm đích. Với nhóm >200 mem, Telegram bắt buộc nick ép mem phải là Admin có quyền Add Members!")
        except Exception:
            pass

        members = list(csv.DictReader(open(csv_file, encoding="utf-8")))
        pending = [m for m in members if m.get("status") == "pending"]
        total = min(len(pending), max_per_session)

        await self._log(cb, f"🚀 Bắt đầu chiến dịch: {len(pending)} mem chờ | Mục tiêu phiên này: {total} mem")
        await self._broadcast(cb, {"type": "progress", "added": 0, "total": total, "current": ""})

        added = 0
        for m in members:
            if not self.is_running or added >= max_per_session:
                break
            if m.get("status") != "pending":
                continue

            uname = m.get("username", "")
            uid   = int(m.get("user_id", 0))
            ahash = int(m.get("access_hash", 0))
            name  = m.get("name") or uname or str(uid)

            # Xác định đối tượng Telegram user
            user_entity = None
            if uname:
                try:
                    user_entity = await self.client.get_input_entity(uname)
                except Exception:
                    pass
            if not user_entity and uid and ahash:
                user_entity = InputUser(uid, ahash)
            if not user_entity and uid:
                try:
                    user_entity = await self.client.get_input_entity(uid)
                except Exception:
                    m["status"] = "error_cannot_resolve"
                    await self._log(cb, f"⚠️ Bỏ qua {name}: không thể định danh tài khoản.")
                    continue

            try:
                if is_channel:
                    res = await self.client(InviteToChannelRequest(dest, [user_entity]))
                    # Kiểm tra xem Telegram có thực sự thêm user vào không (tránh thành công ảo)
                    res_users = getattr(res, "users", [])
                    if not res_users:
                        m["status"] = "silently_filtered"
                        await self._log(cb, f"⚠️ Telegram chặn ngầm {name} (@{uname}): Account chưa đủ uy tín hoặc User chặn người lạ.")
                        continue
                else:
                    await self.client(AddChatUserRequest(dest.id, user_entity, fwd_limit=100))

                added += 1
                m["status"] = "invited"
                await self._log(cb, f"✅ Đã ép THẬT vào nhóm: {name} (@{uname}) [{added}/{total}]")
                await self._broadcast(cb, {"type": "progress", "added": added, "total": total, "current": name})

                # Jitter delay chống spam filter
                real_delay = delay + random.randint(0, 8)
                await self._log(cb, f"⏳ Chờ {real_delay}s trước khi mời tiếp...")
                await asyncio.sleep(real_delay)

            except PeerFloodError:
                m["status"] = "flood_error"
                await self._log(cb, "❌ PEER_FLOOD: Tài khoản bị Telegram chặn spam. Dừng ngay!")
                self.is_running = False
                break
            except UserPrivacyRestrictedError:
                m["status"] = "privacy_restricted"
                await self._log(cb, f"🔒 Bỏ qua {name}: Đã tắt tính năng cho phép thêm vào nhóm.")
            except UserAlreadyParticipantError:
                m["status"] = "already_in"
                await self._log(cb, f"ℹ️ Bỏ qua {name}: Đã có trong nhóm rồi.")
            except UserBannedInChannelError:
                m["status"] = "banned"
                await self._log(cb, f"🚫 Bỏ qua {name}: Bị ban khỏi nhóm.")
            except UserChannelsTooMuchError:
                m["status"] = "too_many_groups"
                await self._log(cb, f"⚠️ Bỏ qua {name}: Tham gia quá nhiều nhóm rồi.")
            except FloodWaitError as e:
                await self._log(cb, f"⏱️ Telegram yêu cầu chờ {e.seconds}s...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                err_msg = str(e)
                if "maximum number of users" in err_msg.lower() or "users_too_much" in err_msg.lower():
                    m["status"] = "limit_exceeded"
                    await self._log(cb, f"❌ TELEGRAM TỪ CHỐI ÉP MEM TRỰC TIẾP: Nhóm '{dest_link}' đã vượt giới hạn ép mem trực tiếp của Telegram hoặc tài khoản ép chưa đủ quyền Admin!")
                else:
                    m["status"] = "error"
                    await self._log(cb, f"⚠️ Lỗi ép {name} vào nhóm: {err_msg[:120]}")

            # Lưu tiến trình liên tục
            self._save_csv(csv_file, members)

        self.is_running = False
        self._save_csv(csv_file, members)
        await self._log(cb, f"🎉 Hoàn tất! Đã ép {added} thành viên thật vào nhóm của bạn!")
        await self._broadcast(cb, {"type": "done", "added": added, "total": total})
        return added

    # ─── Full Pipeline ─────────────────────────────────────────

    async def run_pipeline(
        self,
        target_link: str,
        dest_link: str,
        csv_file: str,
        delay: int = 35,
        max_per_session: int = 30,
        only_active: bool = True,
        only_photo: bool = False,
        cb: Optional[Callable] = None
    ) -> int:
        await self._log(cb, "═" * 50)
        await self._log(cb, "  🔥 TELEGRAM GROWTH ENGINE v3.0 — BẮT ĐẦU")
        await self._log(cb, "═" * 50)
        await self._log(cb, f"📍 Nhóm đối thủ (nguồn): {target_link}")
        await self._log(cb, f"🎯 Nhóm của bạn (đích):  {dest_link}")
        await self._log(cb, f"⚙️  Delay: {delay}s | Giới hạn phiên: {max_per_session} mem")
        await self._log(cb, "")

        scraped = await self.scrape(
            target_link=target_link,
            csv_file=csv_file,
            only_active=only_active,
            only_photo=only_photo,
            cb=cb
        )
        if scraped == 0:
            await self._log(cb, "⚠️ Không có thành viên nào để mời. Dừng pipeline.")
            return 0

        await self._log(cb, "")
        await self._log(cb, f"📋 Bước 2/2: Bắt đầu ép {min(scraped, max_per_session)} mem vào nhóm...")

        added = await self.invite(
            dest_link=dest_link,
            csv_file=csv_file,
            delay=delay,
            max_per_session=max_per_session,
            cb=cb
        )

        await self._log(cb, "")
        await self._log(cb, "═" * 50)
        await self._log(cb, f"  ✅ HOÀN THÀNH: Đã cào {scraped} mem, ép thành công {added} mem thật!")
        await self._log(cb, "═" * 50)
        return added

    def stop(self):
        self.is_running = False

    # ─── Helpers ──────────────────────────────────────────────

    async def _log(self, cb: Optional[Callable], msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(msg)
        if cb:
            await cb({"type": "log", "message": f"[{ts}] {msg}"})

    async def _broadcast(self, cb: Optional[Callable], data: dict):
        if cb:
            await cb(data)

    def _save_csv(self, csv_file: str, members: list):
        if not members:
            return
        fieldnames = list(members[0].keys())
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(members)
