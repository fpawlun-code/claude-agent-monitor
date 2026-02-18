# Add to PowerShell Profile

$profileAddition = @'

# Oh My Posh
oh-my-posh init pwsh --config 'C:\ClaudeAgent\claude-theme.omp.json' | Invoke-Expression

# Claude Status Function
function Show-Usage {
    Write-Host ""
    Write-Host "🤖 Claude Agent Status:" -ForegroundColor Cyan
    Write-Host "Model: Sonnet 4.5" -ForegroundColor Yellow
    if (Test-Path "C:\ClaudeAgent\autonomous\progress.json") {
        $progress = Get-Content "C:\ClaudeAgent\autonomous\progress.json" | ConvertFrom-Json
        Write-Host "RTX Iterations: $($progress.iterations)" -ForegroundColor Green
        Write-Host "Last Run: $($progress.last_run)" -ForegroundColor White
    }
    Write-Host ""
}

# Auto-show on startup
Show-Usage
'@

Add-Content -Path $PROFILE -Value $profileAddition
Write-Host "✅ Added to PowerShell profile!" -ForegroundColor Green
Write-Host "Restart PowerShell to see new prompt" -ForegroundColor Yellow
