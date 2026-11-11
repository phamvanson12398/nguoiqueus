@echo off
rem Buoc 2: dung canh nap cong tu story.json + thu vien, so voi ban goc, roi xuat 3 anh xem truoc.
setlocal
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ROOT=%~dp0..
set OUT=%ROOT%\_verify
set FRAMES=200,360,640,900,1300
if not exist "%OUT%\orig\fingerprint.json" %BLENDER% -b -P "%ROOT%\tools\fingerprint.py" -- "%USERPROFILE%\Videos\claude_test\manhole_scene_v2.py" "%OUT%\orig" --render %FRAMES%
%BLENDER% -b -P "%ROOT%\tools\fingerprint.py" -- "%ROOT%\projects\manhole-round\story.json" "%OUT%\story" --render %FRAMES%
%BLENDER% -b --python "%ROOT%\tools\compare.py" -- "%OUT%\orig" "%OUT%\story"
%BLENDER% -b -P "%ROOT%\builder.py" -- "%ROOT%\projects\manhole-round\story.json" --preview 200,640,1300
%BLENDER% -b -P "%ROOT%\builder.py" -- "%ROOT%\projects\demo-v3\story.json" --preview 60,130,165
%BLENDER% -b -P "%ROOT%\tools\thumbs.py"
echo Xem anh: projects\manhole-round\preview, projects\demo-v3\preview, library\*\*\thumb.png
pause
