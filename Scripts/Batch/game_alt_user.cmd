ECHO OFF

SET main=Roxedus
SET alt=Smurf
SET is_running=None

echo Checks if Steam is running
tasklist /FI "IMAGENAME eq Steam.exe" | find /i "Steam.exe" > nul
if %ERRORLEVEL% == 0 GOTO :find_user
echo Steam is not running, cleaning up
GOTO :kill

:find_user
tasklist /FI "USERNAME eq %alt%" /FI "IMAGENAME eq Steam.exe" | find /i "Steam.exe" > nul
if %ERRORLEVEL% == 0 SET is_running=%alt%
tasklist /FI "USERNAME eq %main%" /FI "IMAGENAME eq Steam.exe" | find /i "Steam.exe" > nul
if %ERRORLEVEL% == 0 SET is_running=%main%
ECHO Running user is %is_running%
GOTO kill

:clean_up
echo Starts Steam, and exiting
start "" "C:\Program Files (x86)\Steam\Steam.exe"
GOTO:eof

:kill
echo Kill Steam if it is running
tasklist /FI "IMAGENAME eq Steam.exe" | find /i "Steam.exe" > nul
if %ERRORLEVEL% == 0 taskkill /IM "Steam.exe" /F

echo Kill uplay if it is running
tasklist /FI "IMAGENAME eq upc.exe" | find /i "upc.exe" > nul
if %ERRORLEVEL% == 0 taskkill /IM "upc.exe" /F

if %is_running% == %alt% GOTO :alt_running
if %is_running% == %main% GOTO :main_running
if %is_running% == "None" GOTO :clean_up

:switched
echo Magic Done, enjoy your game
GOTO:eof

:main_running
echo Main running, switching to alt
runas /user:%alt% /savecred "C:\Program Files (x86)\Steam\Steam.exe"
runas /user:%alt% /savecred "C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\Uplay.exe"
GOTO :switched

:alt_running
echo Alt running, switching to Main
start "" "C:\Program Files (x86)\Steam\Steam.exe"
start "" "C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\Uplay.exe"
GOTO :switched
