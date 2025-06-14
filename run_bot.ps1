# Check if Python is installed
try {
    $pythonVersion = (python --version 2>&1)
    Write-Host "Found Python: $pythonVersion"
} catch {
    Write-Host "Python is not installed or not in PATH. Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    if (-not $?) {
        Write-Host "Failed to create virtual environment. Make sure '.venv' module is available." -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"
if (-not $?) {
    Write-Host "Failed to activate virtual environment." -ForegroundColor Red
    exit 1
}
Write-Host "Virtual environment activated." -ForegroundColor Green

# Check if .env file exists, create it if not
$envFile = ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    $discordToken = Read-Host -Prompt "Enter your Discord bot token"
    "DISCORD_BOT_TOKEN=$discordToken" | Out-File -FilePath $envFile -Encoding utf8
    Write-Host ".env file created." -ForegroundColor Green
} else {
    Write-Host ".env file already exists." -ForegroundColor Green
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if (-not $?) {
    Write-Host "Failed to install dependencies." -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies installed successfully." -ForegroundColor Green

# Run the bot
Write-Host "Starting Discord bot..." -ForegroundColor Green
python -m app.bot
