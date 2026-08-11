# Telegram Growth Suite

Hệ thống kéo thành viên Telegram tự động — Enterprise v3.0

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy server

```bash
python server.py
```

Truy cập: `http://localhost:8000`

## Lấy API ID & Hash

1. Vào https://my.telegram.org
2. Chọn **API development tools**
3. Copy `api_id` và `api_hash`

## Tính năng

- Cào thành viên nhóm đối thủ (2 chế độ: danh sách + lịch sử tin nhắn)
- Tự động ép mem vào nhóm của bạn
- Realtime log qua WebSocket
- Chống ban: Jitter delay, giới hạn phiên
- Giao diện Web responsive (PC & điện thoại)
