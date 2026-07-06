@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "SPEC_FILE=mtdp_enrichment.spec"
set "REACT_DIR=%ROOT_DIR%prototyping\compression_gui_react_seed_validated\compression_gui_react_seed_validated"
set "CONDA_ROOT=C:\Users\giaco\anaconda3"
set "CONDA_ENV=pyinstaller"
set "APP_ICON=src\mtdp_enrichment\assets\icons\nextcomp_app_icon.ico"
set "DIST_DIR=%ROOT_DIR%dist\NextCOMP_data_reduction_suite"
set "DIST_EXE=%ROOT_DIR%dist\NextCOMP_data_reduction_suite.exe"
set "FINAL_EXE=%DIST_DIR%\NextCOMP_data_reduction_suite.exe"
set "OLD_DIST_DIR=%ROOT_DIR%dist\mtdp_enrichment"
set "OLD_DIST_DIR_LEGACY=%ROOT_DIR%dist\NextCOMP_Data_Reduction_Suite"
set "OLD_DIST_EXE=%ROOT_DIR%dist\mtdp_enrichment.exe"
set "PYTHONNOUSERSITE=1"

cd /d "%ROOT_DIR%"
if errorlevel 1 exit /b 1

if not exist "%CONDA_ROOT%\Scripts\activate.bat" (
  echo Conda activation script not found:
  echo   %CONDA_ROOT%\Scripts\activate.bat
  exit /b 1
)

if not exist "%CONDA_ROOT%\envs\%CONDA_ENV%\python.exe" (
  echo Conda environment not found:
  echo   %CONDA_ROOT%\envs\%CONDA_ENV%
  exit /b 1
)

if not exist "%SPEC_FILE%" (
  echo PyInstaller spec file not found:
  echo   %ROOT_DIR%%SPEC_FILE%
  exit /b 1
)

if not exist "%APP_ICON%" (
  echo NextCOMP executable icon not found:
  echo   %ROOT_DIR%%APP_ICON%
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found on PATH. Install Node.js or use an environment with npm available.
  exit /b 1
)

if not exist "%REACT_DIR%\package.json" (
  echo React frontend folder was not found: %REACT_DIR%
  exit /b 1
)

pushd "%REACT_DIR%"
if errorlevel 1 exit /b 1

if exist package-lock.json (
  call npm ci
) else (
  call npm install
)
if errorlevel 1 exit /b 1

call npm run build
if errorlevel 1 exit /b 1

if not exist "%REACT_DIR%\dist\index.html" (
  echo React frontend build did not produce dist\index.html.
  exit /b 1
)

popd

echo Activating conda environment: %CONDA_ENV%
call "%CONDA_ROOT%\Scripts\activate.bat" "%CONDA_ROOT%\envs\%CONDA_ENV%"
if errorlevel 1 exit /b %errorlevel%

python -m pip install -r requirements-pyinstaller.txt
if errorlevel 1 (
  echo.
  echo PyInstaller environment dependency installation failed.
  exit /b %errorlevel%
)

echo.
echo Building dist\NextCOMP_data_reduction_suite with PyInstaller...
echo Spec: %SPEC_FILE%
echo Icon: %APP_ICON%
echo.

if exist "%DIST_DIR%" (
  rmdir /s /q "%DIST_DIR%"
  if exist "%DIST_DIR%" (
    echo Existing dist folder could not be removed. Close any running copy of NextCOMP_data_reduction_suite.exe or Explorer preview:
    echo   %DIST_DIR%
    exit /b 1
  )
)
if exist "%DIST_EXE%" (
  del /f /q "%DIST_EXE%"
  if exist "%DIST_EXE%" (
    echo Existing one-file executable could not be removed:
    echo   %DIST_EXE%
    exit /b 1
  )
)
if exist "%OLD_DIST_DIR%" (
  rmdir /s /q "%OLD_DIST_DIR%"
)
if exist "%OLD_DIST_DIR_LEGACY%" (
  rmdir /s /q "%OLD_DIST_DIR_LEGACY%"
)
if exist "%OLD_DIST_EXE%" (
  del /f /q "%OLD_DIST_EXE%"
)

python -m PyInstaller "%SPEC_FILE%" --clean --noconfirm
if errorlevel 1 (
  echo.
  echo PyInstaller build failed.
  exit /b %errorlevel%
)

if not exist "%DIST_EXE%" (
  echo.
  echo Expected one-file executable was not produced:
  echo   %DIST_EXE%
  exit /b 1
)

mkdir "%DIST_DIR%" || exit /b 1
move /y "%DIST_EXE%" "%FINAL_EXE%" >nul
if errorlevel 1 exit /b %errorlevel%

echo Editable resource defaults are embedded in the exe.
echo On first run they are materialized under the OS user app-data folder:
echo   %%APPDATA%%\NextCOMP\mtdp_enrichment

echo.
echo Build complete:
echo   %DIST_DIR%
echo   %FINAL_EXE%
echo.
endlocal
exit /b 0
