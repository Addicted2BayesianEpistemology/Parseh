@echo off
rem Install Parseh on Windows -- double-click this file.
rem
rem It makes the environment Parseh rebuilds books and divides words in:
rem everything goes into this folder, under .runtime\, and nothing anywhere
rem else -- unless the computer already has conda with an ilya-frank
rem environment, which is used instead.  Then the packages that environment
rem lacks, the guide (html-guide\markdown compiled into the pages the hub's
rem guide button opens), the models the word analyzers download, and the
rem readers.  After it, double-click serve.bat to start Parseh.
rem
rem   install.bat              everything
rem   install.bat --recreate   throw .runtime\env away and make it again
rem
rem The same steps as ./install.sh on Linux and macOS, done by lib\runtime.py;
rem this file only finds a Python to run it with -- or, on a computer with
rem none, makes the environment first with micromamba, which is one program.
rem (Line endings must stay CRLF: cmd.exe misreads labels otherwise.)
setlocal
chcp 65001 >nul
title Parseh -- install
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "ENVNAME=ilya-frank"
set "PY="

rem ---- 1. an environment that already exists ------------------------------
if exist ".runtime\env\python.exe" set "PY="%CD%\.runtime\env\python.exe""
if not defined PY for %%r in ("%USERPROFILE%\miniconda3" "%USERPROFILE%\anaconda3" "%USERPROFILE%\miniforge3" "%USERPROFILE%\mambaforge" "%USERPROFILE%\micromamba" "%USERPROFILE%\.conda" "%LOCALAPPDATA%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%LOCALAPPDATA%\miniforge3" "%LOCALAPPDATA%\mambaforge" "%LOCALAPPDATA%\Programs\miniconda3" "%LOCALAPPDATA%\Programs\anaconda3" "%ProgramData%\miniconda3" "%ProgramData%\anaconda3" "%ProgramData%\miniforge3") do call :try_env "%%~r"
if defined PY goto run

rem ---- 2. none: micromamba, then the environment, into .runtime\ -----------
echo.
echo   Parseh needs its environment, and this computer does not have it yet.
echo   It goes into this folder (.runtime\) and takes a few hundred megabytes.
echo.
if not exist ".runtime\bin" mkdir ".runtime\bin"
if exist ".runtime\bin\micromamba.exe" goto haveMamba
echo   Downloading micromamba ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-win-64' -OutFile '.runtime\bin\micromamba.exe.part'"
if errorlevel 1 goto fail
move /y ".runtime\bin\micromamba.exe.part" ".runtime\bin\micromamba.exe" >nul
:haveMamba
echo   Making the environment (this takes a while, once) ...
set "MAMBA_ROOT_PREFIX=%CD%\.runtime\mamba"
".runtime\bin\micromamba.exe" create -y -r "%CD%\.runtime\mamba" -p "%CD%\.runtime\env" -f environment.yml
if errorlevel 1 goto fail
set "PY="%CD%\.runtime\env\python.exe""

:run
%PY% lib\runtime.py install %*
if errorlevel 1 goto fail
echo.
echo   Parseh is installed.  Double-click serve.bat to start it.
echo.
pause
exit /b 0

:fail
echo.
echo   The installation did not finish -- the messages above say why.
echo.
pause
exit /b 1

rem ---- subroutines -----------------------------------------------------------
:try_env
rem try_env <conda root>: its ilya-frank environment, if it has one
if defined PY goto :eof
if not exist "%~1\envs\%ENVNAME%\python.exe" goto :eof
set "PY="%~1\envs\%ENVNAME%\python.exe""
goto :eof
