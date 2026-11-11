@echo off
rem Buoc 1: kiem tra core/ dung lai canh nap cong giong het ban goc.
rem Dung canh 2 lan (ban goc trong Videos\claude_test va ban dung tu core), xuat dau van tay, render 5 khung 25%%, so sanh.
setlocal
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ROOT=%~dp0..
set OUT=%ROOT%\_verify
set FRAMES=200,360,640,900,1300
%BLENDER% -b -P "%ROOT%\tools\fingerprint.py" -- "%USERPROFILE%\Videos\claude_test\manhole_scene_v2.py" "%OUT%\orig" --render %FRAMES%
%BLENDER% -b -P "%ROOT%\tools\fingerprint.py" -- "%ROOT%\projects\manhole-round\scene_v2_core.py" "%OUT%\core" --render %FRAMES%
%BLENDER% -b --python "%ROOT%\tools\compare.py" -- "%OUT%\orig" "%OUT%\core"
echo Anh cac khung nam trong %OUT%\orig va %OUT%\core
pause
