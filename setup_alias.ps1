# Token Guard PowerShell Alias Setup

Write-Host "Setting up Token Guard alias..." -ForegroundColor Green

# Get profile path
$profilePath = $PROFILE

# Create profile if it doesn't exist
if (!(Test-Path $profilePath)) {
    Write-Host "Creating PowerShell profile at: $profilePath" -ForegroundColor Yellow
    New-Item -Path $profilePath -Type File -Force | Out-Null
}

# Alias function to add
$aliasFunction = @'

# Token Guard Wrapper for Claude Code
function claude-guarded {
    python C:\ClaudeAgent\token_guard.py $args
}

Set-Alias cg claude-guarded
Write-Host "Token Guard active! Use: claude-guarded or cg" -ForegroundColor Green
'@

# Check if alias already exists
$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

if ($null -eq $profileContent -or $profileContent -notmatch "claude-guarded") {
    Add-Content -Path $profilePath -Value $aliasFunction
    Write-Host "Alias added to profile: $profilePath" -ForegroundColor Green
} else {
    Write-Host "Alias already exists in profile" -ForegroundColor Yellow
}

# Reload profile
Write-Host "Reloading profile..." -ForegroundColor Cyan
. $profilePath

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Usage: claude-guarded or cg" -ForegroundColor Cyan
