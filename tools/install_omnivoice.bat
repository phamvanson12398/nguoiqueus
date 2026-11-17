@echo off
rem Cai OmniVoice (k2-fsa) cho WhyShorts Studio: tao moi truong Python rieng o %USERPROFILE%\WhyShortsVoice\venv
rem (torch CUDA 12.8 + omnivoice, khoang 3 GB). Chay MOT lan. Can Python 3.10-3.12 (python.org) va card NVIDIA.
rem Lan dau tao giong, OmniVoice tai them model tu Hugging Face (~2-3 GB).
setlocal
set DIR=%USERPROFILE%\WhyShortsVoice
set VPY=%DIR%\venv\Scripts\python.exe
if exist "%VPY%" goto have_venv
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" (where python >nul 2>nul && set PY=python)
if "%PY%"=="" goto nopy
echo Tao moi truong Python o %DIR%\venv ...
%PY% -m venv "%DIR%\venv"
if not exist "%VPY%" goto nopy
:have_venv
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 goto fail
"%VPY%" -m pip install --upgrade omnivoice soundfile numpy
if errorlevel 1 goto fail
"%VPY%" -c "import torch, omnivoice; print('OmniVoice OK. CUDA (card NVIDIA):', torch.cuda.is_available())"
if errorlevel 1 goto fail
echo.
echo Xong. Mo lai WhyShorts Studio (start_studio.bat): tab Giong doc se tu tim thay OmniVoice.
pause
exit /b 0
:nopy
echo Khong tim thay Python. Cai Python 3.11 tu https://www.python.org/downloads/ (tick "Add python.exe to PATH") roi chay lai file nay.
pause
exit /b 1
:fail
echo Cai dat loi (xem dong bao loi phia tren). Thu chay lai; neu loi mang thi doi mot luc.
pause
exit /b 1
