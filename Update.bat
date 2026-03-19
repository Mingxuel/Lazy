@echo off

cd /d "%~dp0"

git add .
echo git add .

git commit -m "Updated."
echo git commit

git push
echo git push


