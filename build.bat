@echo off
setlocal enabledelayedexpansion
echo ==============================================================
echo       BUILDING AI TEXT SUMMARIZER C BACKEND (WINDOWS)
echo ==============================================================

set PG_INC=
set PG_LIB=
set PG_FLAG=

if exist "C:\Program Files\PostgreSQL\19\include\libpq-fe.h" (
    set PG_INC=-I"C:\Program Files\PostgreSQL\19\include"
    set PG_LIB=-L"C:\Program Files\PostgreSQL\19\lib" -llibpq
    set PG_FLAG=-DUSE_LIBPQ
    echo [INFO] Detected PostgreSQL 19 at C:\Program Files\PostgreSQL\19 (Native libpq enabled)
) else if exist "C:\Program Files\PostgreSQL\18\include\libpq-fe.h" (
    set PG_INC=-I"C:\Program Files\PostgreSQL\18\include"
    set PG_LIB=-L"C:\Program Files\PostgreSQL\18\lib" -llibpq
    set PG_FLAG=-DUSE_LIBPQ
    echo [INFO] Detected PostgreSQL 18 at C:\Program Files\PostgreSQL\18 (Native libpq enabled)
) else if exist "C:\Program Files\PostgreSQL\17\include\libpq-fe.h" (
    set PG_INC=-I"C:\Program Files\PostgreSQL\17\include"
    set PG_LIB=-L"C:\Program Files\PostgreSQL\17\lib" -llibpq
    set PG_FLAG=-DUSE_LIBPQ
    echo [INFO] Detected PostgreSQL 17 at C:\Program Files\PostgreSQL\17 (Native libpq enabled)
) else (
    echo [INFO] PostgreSQL libpq headers not found in default path. Building in standalone logging mode.
)

where gcc >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Compiling with GCC (MinGW)...
    gcc -O2 -Wall %PG_FLAG% %PG_INC% server.c gemini.c db.c -o server.exe -lws2_32 -lwinhttp %PG_LIB%
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] server.exe created successfully!
        echo Run it with: .\server.exe
    ) else (
        echo [ERROR] GCC compilation failed.
    )
    goto end
)

where clang >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Compiling with Clang...
    clang -O2 -Wall %PG_FLAG% %PG_INC% server.c gemini.c db.c -o server.exe -lws2_32 -lwinhttp %PG_LIB%
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] server.exe created successfully!
        echo Run it with: .\server.exe
    ) else (
        echo [ERROR] Clang compilation failed.
    )
    goto end
)

where cl >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Compiling with Microsoft Visual C++ (cl.exe)...
    if defined PG_FLAG (
        cl /O2 /DUSE_LIBPQ /I"C:\Program Files\PostgreSQL\19\include" /Fe:server.exe server.c gemini.c db.c ws2_32.lib winhttp.lib /link /LIBPATH:"C:\Program Files\PostgreSQL\19\lib" libpq.lib
    ) else (
        cl /O2 /Fe:server.exe server.c gemini.c db.c ws2_32.lib winhttp.lib
    )
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] server.exe created successfully!
        echo Run it with: .\server.exe
    ) else (
        echo [ERROR] MSVC compilation failed.
    )
    goto end
)

echo.
echo [NOTICE] No C compiler (GCC, Clang, or MSVC) was found in your PATH.
echo.
echo Follow the quick guide below to install GCC or Clang on Windows 11.
echo.

:end
echo ==============================================================
