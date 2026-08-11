@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   Telegram Growth Suite v3.0 - KHỞI ĐỘNG
echo ============================================
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Chưa cài Python! Chạy install.bat trước.
    pause
    exit /b 1
)

REM Kiểm tra đã cài thư viện chưa
python -c "import fastapi, telethon, uvicorn" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Chưa cài thư viện. Đang cài tự động...
    pip install -r requirements.txt --quiet
)

echo [OK] Đang khởi động server...
echo [OK] Mở trình duyệt tại: http://127.0.0.1:8000
echo.
echo Nhấn Ctrl+C để dừng server
echo ============================================
echo.

start "" "http://127.0.0.1:8000"
python server.py
pause
