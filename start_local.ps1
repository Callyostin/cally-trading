$pwd = Get-Location

# Set up Backend
Write-Host "Setting up Backend Services..."
cd backend
if (-Not (Test-Path venv)) { python -m venv venv }
.\venv\Scripts\pip.exe install -r requirements.txt
cd ..

# Start Backend
Write-Host "Starting Backend in a new window..."
Start-Process powershell -WorkingDirectory "$pwd\backend" -ArgumentList "-NoExit -Command `".\venv\Scripts\python.exe main.py`""

# Set up Frontend
Write-Host "Setting up Frontend Services..."
cd frontend
npm install
cd ..

# Start Frontend
Write-Host "Starting Frontend in a new window..."
Start-Process powershell -WorkingDirectory "$pwd\frontend" -ArgumentList "-NoExit -Command `"npm run dev`""

Write-Host "Both services have been started in new windows!"
