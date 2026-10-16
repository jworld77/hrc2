@echo off
cd /d "%~dp0"
echo ==== 1. PYTHON CHECK ====
where python
where py
python -V 2>&1
py -V 2>&1
echo.
echo ==== 2. FILES IN THIS FOLDER ====
dir /b
echo.
echo ==== 3. DATA FOLDER ====
dir /b data
echo.
echo Copy this whole screen and send it if something is wrong.
echo.
pause
