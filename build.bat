@echo off
set BUILD_DIR=build\win
set OUTPUT=%BUILD_DIR%\nifty-reader.exe

:: Check if debug mode is requested
set DEBUG_FLAG=
if "%1"=="debug" (
    set DEBUG_FLAG=-ldflags "-s -w"
    echo Building in DEBUG mode (console will be visible)...
) else (
    set DEBUG_FLAG=-ldflags "-H=windowsgui -s -w"
    echo Building in RELEASE mode (GUI mode)...
)

:: Create build directory
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

:: Build the executable
go build %DEBUG_FLAG% -o "%OUTPUT%" .

:: Copy DLLs from lib/ to build directory
if exist "lib\*.dll" (
    echo Copying DLLs from lib/ to %BUILD_DIR%...
    copy "lib\*.dll" "%BUILD_DIR%\" > nul
)

echo Build complete! Executable and DLLs are in %BUILD_DIR%\
if "%1"=="debug" (
    echo Run '%OUTPUT%' to start with console output
) else (
    echo Run '%OUTPUT%' to start in GUI mode
)
