@echo off
cd /d d:\Coding\Nongor_TEST\Bot\nongor_bot_v3

echo Renaming README...
if exist README_V3.md ren README_V3.md README.md

echo Initializing Git...
if not exist .git (
    git init
) 

echo Configuring remote...
git remote remove origin 2>nul
git remote add origin https://github.com/kazisalman21/nongor-bot

echo Checking out main branch...
git checkout -b main 2>nul || git checkout main

echo Adding files...
git add .

echo Committing...
git commit -m "Nongor Bot V3 Premium Release"

echo Pushing to GitHub...
git push -u origin main --force

echo Done!
pause
