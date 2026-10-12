@echo off
rem Kanpan launcher - double-click to start
chcp 65001 >nul
set PYTHONPATH=C:\Users\Administrator\.goldminer3\projects\0309bee2-b4c4-11f1-9511-80fa5b6f62b4\pylibs
"C:\Program Files\Python313\python.exe" "%~dp0kanpan.py" %*
pause
