@echo off
setlocal
cd /d "%~dp0"
title 인권센터 자료 수집기

echo.
echo ================================================================
echo   한세대학교 인권센터 - 공개자료 수집기
echo ================================================================
echo.

if not exist "수집기.py" goto NOFILE

set PYEXE=
where python >nul 2>nul
if not errorlevel 1 set PYEXE=python
if not "%PYEXE%"=="" goto RUN
where py >nul 2>nul
if not errorlevel 1 set PYEXE=py
if not "%PYEXE%"=="" goto RUN
goto NOPY

:RUN
%PYEXE% -u "수집기.py"
goto END

:NOFILE
echo  [!] 이 폴더에 「수집기.py」 가 없습니다.
echo      압축을 완전히 푼 폴더 안에서 실행해 주세요.
goto END

:NOPY
echo  [!] 파이썬(Python)이 설치되어 있지 않습니다.
echo.
echo      1. https://www.python.org/downloads  접속
echo      2. [Download Python] 으로 설치
echo      3. 설치 첫 화면에서 [Add python.exe to PATH] 체크 필수
echo      4. 설치 후 이 파일을 다시 더블클릭
echo.
echo      * 파이썬 없이도 「검색.html」 은 그대로 사용할 수 있습니다.
goto END

:END
echo.
pause
