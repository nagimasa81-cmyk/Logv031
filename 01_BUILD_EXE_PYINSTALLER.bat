@echo off
cd /d %~dp0
where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo PyInstaller is not installed.
  echo Run: pip install pyinstaller
  pause
  exit /b 1
)
pyinstaller --noconfirm --windowed --onedir --name Complaint_Service_Hub main.py
xcopy /E /I /Y config dist\Complaint_Service_Hub\config
xcopy /E /I /Y masters dist\Complaint_Service_Hub\masters
xcopy /E /I /Y templates dist\Complaint_Service_Hub\templates
xcopy /E /I /Y profiles dist\Complaint_Service_Hub\profiles
if not exist dist\Complaint_Service_Hub\logs mkdir dist\Complaint_Service_Hub\logs
copy README_StartHere.txt dist\Complaint_Service_Hub\README_StartHere.txt
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\Complaint_Service_Hub\*' -DestinationPath 'Complaint_Service_Hub_Distribution.zip' -Force"
echo Build complete: Complaint_Service_Hub_Distribution.zip
pause
