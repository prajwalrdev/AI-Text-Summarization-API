@echo off
echo ==============================================================
echo       BUILDING AI TEXT SUMMARIZER C BACKEND (WINDOWS)
echo ==============================================================

where gcc >nul 2>nul
if %errorlevel% equ 0 (
    echo Compiling with GCC (MinGW)...
    gcc -O2 -Wall server.c gemini.c db.c -o server.exe -lws2_32 -lwinhttp
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] server.exe created successfully!
        echo Run it with: server.exe
    ) else (
        echo [ERROR] Compilation failed.
    )
    goto end
)

where cl >nul 2>nul
if %errorlevel% equ 0 (
    echo Compiling with Microsoft Visual C++ (cl.exe)...
    cl /O2 /Fe:server.exe server.c gemini.c db.c ws2_32.lib winhttp.lib
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] server.exe created successfully!
        echo Run it with: server.exe
    ) else (
        echo [ERROR] Compilation failed.
    )
    goto end
)

echo.
echo [NOTICE] No C compiler (GCC / MinGW or MSVC cl.exe) was found in your PATH.
echo.
echo How to install a C compiler on Windows 11:
echo Option 1: Install MinGW via MSYS2 (https://www.msys2.org/) or winlibs (https://winlibs.com/)
echo Option 2: Install Visual Studio Community with C++ Build Tools
echo.

:end
echo ==============================================================
