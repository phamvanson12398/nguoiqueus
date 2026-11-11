@echo off
rem Video dai buoc 1: kiem tra Shorts van giong het (verify_story.bat), roi xem truoc video dai 16:9 va do toc do render.
setlocal
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ROOT=%~dp0..
%BLENDER% -b -P "%ROOT%\builder.py" -- "%ROOT%\projects\demo-long\story.json" --preview 15,60,120,175,230,300,345 --pct 50
%BLENDER% -b -P "%ROOT%\builder.py" -- "%ROOT%\projects\demo-long\story.json" --render --frames 100-160
echo Xem anh: projects\demo-long\preview  ^|  doan render thu: projects\demo-long\parts  (dong RENDER FRAME cho biet giay/khung)
pause
