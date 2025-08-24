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

echo Setting version information using unified version.py...
echo Commit Count: %1
echo Commit Hash: %2
echo Branch: %3
echo Commit Date: %4
echo.

REM Use the unified version.py script
python version.py %1 %2 %3 %4
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Version set successfully using unified system!
) else (
    echo.
    echo ❌ Failed to set version using unified system
    pause
    exit /b 1
)

pause
