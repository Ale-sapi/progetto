@echo on

REM Define the target directory
set "TARGET_DIR=C:\ESD\MCT"
echo Target directory: %TARGET_DIR%

REM Create the target directory if it doesn't exist
echo Checking target directory...
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
    if errorlevel 1 (
        echo Error: Failed to create target directory.
        exit /b 1
    )
    echo Created directory: %TARGET_DIR%
) else (
    echo Target directory already exists: %TARGET_DIR%
)

REM Clone the repository if it doesn't exist
if not exist "%TARGET_DIR%\.git" (
    echo Cloning the repository...
    git clone https://github.com/Ale-sapi/progetto.git "%TARGET_DIR%"
    if errorlevel 1 (
        echo Error: Failed to clone the repository.
        exit /b 1
    )
) else (
    echo Repository already exists. Pulling the latest changes...
    cd "%TARGET_DIR%"
    git pull
    if errorlevel 1 (
        echo Error: Failed to pull the latest changes.
        exit /b 1
    )
)

REM Check if the script exists
set "TARGET_FILE=%TARGET_DIR%\a1.py"
echo Checking for script: %TARGET_FILE%
if not exist "%TARGET_FILE%" (
    echo Error: Script a1.py not found. Please check the repository.
    exit /b 1
)

REM Install necessary Python libraries
echo Installing required Python libraries...
pip install pyperclip keyboard google-generativeai pillow tk
if errorlevel 1 (
    echo Error: Failed to install Python libraries.
    exit /b 1
)

REM Confirm completion and run the script
echo Setup complete. Running the script in hidden mode...
start python c:\ESD\MCT\a1.py
if errorlevel 1 (
    echo Error: Failed to run the script.
    exit /b 1
)
echo Script is running. You can close this window.
echo Press any key to exit...
pause