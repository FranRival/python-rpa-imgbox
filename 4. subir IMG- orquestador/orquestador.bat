@echo off
setlocal enabledelayedexpansion

REM ===== CONFIGURACION =====
set PYTHON=python
set UPLOADER=C:\Users\dell\Desktop\uploader\uploader.py
set RUTAS=C:\Users\dell\Desktop\batch-ruta.txt
set EXCEL_DIR=C:\Users\dell\Desktop

echo ==========================================
echo  ORQUESTADOR DE BATCHES - INICIADO
echo ==========================================

for /f "usebackq delims=" %%R in ("%RUTAS%") do (

    echo.
    echo ======================================
    echo Procesando ruta:
    echo %%R
    echo ======================================

    REM Entrar a la ruta
    pushd "%%R" || (
        echo ❌ No se pudo entrar a %%R
        goto :siguiente
    )

    REM Ejecutar uploader
    echo ▶ Ejecutando uploader...
    "%PYTHON%" "%UPLOADER%"

    REM Esperar que aparezca resultado_embeds
    echo ⏳ Esperando resultado_embeds...
    :esperar_excel
    if not exist "%EXCEL_DIR%\resultado_embeds*" (
        timeout /t 5 >nul
        goto esperar_excel
    )

    echo ✔ Archivo detectado.

    REM Obtener nombre del batch (carpeta padre)
    for %%A in ("%%R\..") do set NOMBRE=%%~nxA

    REM Buscar nombre disponible
    set COUNT=1
    :buscar_nombre
    if exist "%EXCEL_DIR%\!NOMBRE!_!COUNT!.*" (
        set /a COUNT+=1
        goto buscar_nombre
    )

    REM Intentar renombrar hasta que Windows libere el archivo
    echo 🔄 Esperando liberacion del archivo para renombrar...
    :intentar_renombrar
    for %%F in ("%EXCEL_DIR%\resultado_embeds*") do (
        ren "%%F" "!NOMBRE!_!COUNT!%%~xF" >nul 2>&1
    )

    REM Verificar si ya fue renombrado
    if exist "%EXCEL_DIR%\resultado_embeds*" (
        timeout /t 5 >nul
        goto intentar_renombrar
    )

    echo ✅ Archivo renombrado correctamente como !NOMBRE!_!COUNT!

    popd

    :siguiente
    timeout /t 2 >nul
)

echo.
echo ==========================================
echo ✅ TODOS LOS BATCHES FINALIZADOS
echo ==========================================
pause
