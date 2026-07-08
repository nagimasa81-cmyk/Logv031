@echo off
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'manifest.json','masters','templates','profiles' -DestinationPath 'master_update_current.zip' -Force"
echo Created master_update_current.zip
pause
