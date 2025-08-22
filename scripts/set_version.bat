@echo off
REM Quick script to set version information for Maintenance Dashboard
REM Usage: set_version.bat <commit_count> <commit_hash> <branch> <commit_date>
REM Example: set_version.bat 123 abc1234 main 2024-01-15

if "%4"=="" (
    echo Usage: set_version.bat ^<commit_count^> ^<commit_hash^> ^<branch^> ^<commit_date^>
    echo Example: set_version.bat 123 abc1234 main 2024-01-15
    pause
    exit /b 1
)

echo Setting version information...
echo Commit Count: %1
echo Commit Hash: %2
echo Branch: %3
echo Commit Date: %4
echo.

REM Create version.json
echo {> version.json
echo   "commit_count": %1,>> version.json
echo   "commit_hash": "%2",>> version.json
echo   "branch": "%3",>> version.json
echo   "commit_date": "%4",>> version.json
echo   "version": "v%1.%2",>> version.json
echo   "full_version": "v%1.%2 (%3) - %4">> version.json
echo }>> version.json

REM Create .env file
echo # Version Information (Auto-generated)> .env
echo GIT_COMMIT_COUNT=%1>> .env
echo GIT_COMMIT_HASH=%2>> .env
echo GIT_BRANCH=%3>> .env
echo GIT_COMMIT_DATE=%4>> .env
echo.>> .env
echo # Other environment variables can be added below>> .env

echo ✅ Version set successfully!
echo 📝 Version: v%1.%2
echo 📝 Commit: %2
echo 📝 Branch: %3
echo 📝 Date: %4
echo 📝 Full: v%1.%2 (%3) - %4
echo.
echo 🌐 For Portainer deployment, use these environment variables:
echo    GIT_COMMIT_COUNT=%1
echo    GIT_COMMIT_HASH=%2
echo    GIT_BRANCH=%3
echo    GIT_COMMIT_DATE=%4
echo.
echo 💡 Copy these values into your Portainer stack environment variables!
echo 🔄 The web application will now show the updated version information.
echo.
pause
