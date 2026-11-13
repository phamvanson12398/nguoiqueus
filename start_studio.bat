@echo off
rem Mo WhyShorts Studio (http://127.0.0.1:1111) bang Python di kem Blender, khong can cai Python rieng.
cd /d %~dp0
set PY="C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"
if not exist %PY% set PY=python
%PY% server.py
pause
