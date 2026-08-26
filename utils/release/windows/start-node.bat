@echo off
setlocal
cd /d "%~dp0"
echo Starting the Monzero node. Keep this window open.
monzerod.exe --disable-rpc-ban --add-priority-node node.monzero.org:6174 --add-priority-node node2.monzero.org:6174 --no-igd
if errorlevel 1 (
  echo.
  echo The node stopped with an error. Check %%APPDATA%%\monzero\monzero.log
  pause
)
