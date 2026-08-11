@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   Telegram Growth Suite v3.0 - CÀI ĐẶT
echo ============================================
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Chưa cài Python!
    echo Tải Python tại: https://www.python.org/downloads/
    echo Nhớ tick vào "Add Python to PATH" khi cài!
    pause
    exit /b 1
)

echo [OK] Đã tìm thấy Python:
python --version
echo.

REM Nâng cấp pip
echo [1/2] Đang nâng cấp pip...
python -m pip install --upgrade pip --quiet

REM Cài dependencies
echo [2/2] Đang cài thư viện cần thiết...
pip install -r requirements.txt

echo.
echo ============================================
echo   CÀI ĐẶT HOÀN TẤT!
echo   Bây giờ chạy file run.bat để khởi động
echo ============================================
echo.
pause
