@echo off

cd /d "%~dp0"

git add .
echo git add .：%~dp0

git commit -m "Updated."
echo git commit：%~dp0

git push
echo git push：%~dp0


