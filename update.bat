@echo off

call environment.bat

git -C "%~dp0%system\dazbrowse" pull 2>NUL
if %ERRORLEVEL% == 0 goto :done

git -C "%~dp0%system\dazbrowse" reset --hard
git -C "%~dp0%system\dazbrowse" pull

:done
pause
