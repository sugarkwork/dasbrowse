@echo off

call environment.bat

cd %~dp0%system\dazbrowse
call dbupdate.bat
