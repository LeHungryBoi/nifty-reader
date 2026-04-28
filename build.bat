@echo off
setlocal

set BUILD_DIR=build\win
set OUTPUT=%BUILD_DIR%\nifty-reader.exe

if "%~1"=="debug" goto debug
if "%~1"=="run" goto run
goto release

:debug
set LDFLAGS=-s -w
echo Building in DEBUG mode (console will be visible)...
goto build

:run
set LDFLAGS=-s -w
echo Building in RUN mode (console will be visible)...
goto build

:release
set LDFLAGS=-H=windowsgui -s -w
echo Building in RELEASE mode (GUI mode)...
goto build

:build
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

go build -ldflags "%LDFLAGS%" -o "%OUTPUT%" .

if exist "lib\*.dll" (
    echo Copying DLLs from lib/ to %BUILD_DIR%...
    copy "lib\*.dll" "%BUILD_DIR%\" > nul
)

echo Build complete! Executable and DLLs are in %BUILD_DIR%\

if "%~1"=="run" (
    echo Running %OUTPUT%...
    "%OUTPUT%"
)

endlocal
