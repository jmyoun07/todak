@echo off
rem Todak Supabase backup - double-click: a dated zip appears in the "backup" folder next to this file.
rem To include the verification photos too, run from a command window:  this.bat --photos
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
for /d %%D in ("%~dp0..\8_*") do python "%%D\_backup_db.py" %*
echo.
pause
