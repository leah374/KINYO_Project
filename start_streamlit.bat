@echo off
echo ====================================================================
echo KINYO AI Video Generation Platform
echo ====================================================================
echo.

cd /d "%~dp0"

echo Starting Streamlit...
echo.
echo Open your browser and visit: http://127.0.0.1:8501
echo.
echo Press Ctrl+C to stop the server.
echo ====================================================================
echo.

streamlit run streamlit_app/app.py --server.address=127.0.0.1 --server.port=8501

pause
