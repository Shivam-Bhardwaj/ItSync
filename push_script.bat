@echo off
REM Basic Windows batch script to add all changes, commit with message from a file, and push.

SET COMMIT_MSG_FILE=COMMIT_MSG.txt
SET REMOTE_NAME=origin
REM Getting current branch name in batch is tricky, often just use main/master or specify manually
REM For simplicity, this script assumes you want to push the current checked-out branch.
REM A more robust solution might involve 'git branch --show-current' if using a recent Git version.
REM Or parse output of 'git status -bs --porcelain' or 'git symbolic-ref --short HEAD'

REM Check if commit message file exists
IF NOT EXIST "%COMMIT_MSG_FILE%" (
    echo Error: Commit message file '%COMMIT_MSG_FILE%' not found!
    goto :eof
)

echo --- Adding all changes ---
git add .

echo --- Checking for staged changes ---
REM Check if there are changes staged for commit. Exit code 0 means no changes.
git diff --staged --quiet
IF %ERRORLEVEL% EQU 0 (
  echo No changes staged for commit.
  goto :eof
)

echo --- Committing changes ---
REM Use the content of the file as the commit message
git commit -F "%COMMIT_MSG_FILE%"

REM Check if commit was successful
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Git commit failed.
    goto :eof
)

echo --- Pushing to %REMOTE_NAME% (current branch) ---
REM Pushing the current branch without explicitly naming it
git push "%REMOTE_NAME%"

REM Check if push was successful
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Git push failed.
    goto :eof
)

echo --- Push successful! ---

:eof

