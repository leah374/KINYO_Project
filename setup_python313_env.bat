@echo off
REM ============================================================
REM KINYO AI - Python 3.13 Environment Setup Script
REM ============================================================

echo.
echo ========================================
echo   KINYO AI Environment Setup
echo   Python Version: 3.13
echo ========================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Conda not found! Please install Anaconda or Miniconda first.
    pause
    exit /b 1
)

REM Remove old environment if exists
echo [1/5] Checking for existing environment...
conda env list | findstr "kinuyo" >nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Removing old kinuyo environment...
    conda env remove -n kinuyo -y
)

REM Create new environment with Python 3.13
echo.
echo [2/5] Creating new conda environment with Python 3.13...
conda create -n kinuyo python=3.13 -y
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create conda environment!
    pause
    exit /b 1
)

REM Activate environment
echo.
echo [3/5] Activating kinuyo environment...
call conda activate kinuyo
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate environment!
    pause
    exit /b 1
)

REM Install dependencies
echo.
echo [4/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements_python313.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

REM Verify installation
echo.
echo [5/5] Verifying installation...
python -c "import sys; print(f'Python: {sys.version}')"
python -c "import langgraph; print(f'LangGraph: {langgraph.__version__}')"
python -c "import streamlit; print(f'Streamlit: {streamlit.__version__}')"
python -c "from langgraph.graph import StateGraph, END; print('LangGraph imports: OK')"

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To activate the environment, run:
echo   conda activate kinuyo
echo.
echo To start the Streamlit app, run:
echo   streamlit run streamlit_app/app.py
echo.
pause
