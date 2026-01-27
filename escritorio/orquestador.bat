@echo off
setlocal enabledelayedexpansion

echo =========================================
echo 🚀 ORQUESTADOR INICIADO
echo =========================================
echo.

set PYTHON="C:\Users\dell\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set UPLOADER="C:\Users\dell\Desktop\uploader\uploader.py"
set BATCH_FILE="C:\Users\dell\Desktop\batch-ruta.txt"

if not exist %BATCH_FILE% (
    echo ❌ No existe batch-ruta.txt
    pause
    exit /b
)

:LOOP
for /f "usebackq delims=" %%A in (%BATCH_FILE%) do (
    set CURRENT=%%A
    goto PROCESS
)

echo.
echo ✅ No quedan batches pendientes.
goto END


:PROCESS
echo.
echo =========================================
echo 📁 Procesando batch:
echo %CURRENT%
echo =========================================
echo.

%PYTHON% %UPLOADER% "%CURRENT%"

if errorlevel 1 (
    echo.
    echo ❌ Error detectado en uploader. Proceso detenido.
    pause
    exit /b
)

echo.
echo ✅ Batch terminado correctamente.
echo Eliminando ruta del batch-ruta.txt ...

findstr /v /c:"%CURRENT%" %BATCH_FILE% > "%BATCH_FILE%.tmp"
move /y "%BATCH_FILE%.tmp" %BATCH_FILE% >nul

timeout /t 2 >nul
goto LOOP


:END
echo.
echo =========================================
echo 🎉 PROCESO COMPLETADO
echo =========================================
pause
