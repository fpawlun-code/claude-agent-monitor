# Claude Terminal Setup - Oh My Posh + Status Bar

Write-Host "Installing Oh My Posh + jq..." -ForegroundColor Cyan

# Install Oh My Posh
winget install JanDeDobbeleer.OhMyPosh -e --accept-source-agreements --accept-package-agreements

# Install jq
winget install jqlang.jq -e --accept-source-agreements --accept-package-agreements

# Create custom theme
$themePath = "$env:POSH_THEMES_PATH\claude.omp.json"
$theme = @'
{
  "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",
  "version": 2,
  "final_space": true,
  "console_title_template": "{{ .Shell }} - {{ .Folder }}",
  "blocks": [
    {
      "type": "prompt",
      "alignment": "left",
      "segments": [
        {
          "type": "text",
          "style": "plain",
          "foreground": "magenta",
          "template": "🤖 Claude "
        },
        {
          "type": "path",
          "style": "powerline",
          "powerline_symbol": "\uE0B0",
          "foreground": "cyan",
          "background": "blue",
          "template": " {{ .Path }} "
        },
        {
          "type": "git",
          "style": "powerline",
          "powerline_symbol": "\uE0B0",
          "foreground": "black",
          "background": "green",
          "template": " {{ .HEAD }} "
        }
      ]
    },
    {
      "type": "prompt",
      "alignment": "right",
      "segments": [
        {
          "type": "text",
          "style": "plain",
          "foreground": "yellow",
          "template": "⚡ Sonnet 4.5 "
        },
        {
          "type": "time",
          "style": "plain",
          "foreground": "white",
          "template": "{{ .CurrentDate | date \"15:04\" }}"
        }
      ]
    },
    {
      "type": "prompt",
      "alignment": "left",
      "newline": true,
      "segments": [
        {
          "type": "text",
          "style": "plain",
          "foreground": "lightGreen",
          "template": "❯ "
        }
      ]
    }
  ]
}
'@

$theme | Out-File -FilePath $themePath -Encoding UTF8

# Add to PowerShell profile
$profileContent = @"

# Oh My Posh
oh-my-posh init pwsh --config '$themePath' | Invoke-Expression

# Aliases
Set-Alias -Name jq -Value 'jq.exe' -Force

# Claude Status Function
function Show-Usage {
    Write-Host ""
    Write-Host "🤖 Claude Agent Status:" -ForegroundColor Cyan
    Write-Host "Model: Sonnet 4.5" -ForegroundColor Yellow
    if (Test-Path "C:\ClaudeAgent\autonomous\progress.json") {
        `$progress = Get-Content "C:\ClaudeAgent\autonomous\progress.json" | ConvertFrom-Json
        Write-Host "RTX Iterations: `$(`$progress.iterations)" -ForegroundColor Green
        Write-Host "Last Run: `$(`$progress.last_run)" -ForegroundColor White
    }
    Write-Host ""
}

# Auto-show on startup
Show-Usage
"@

Add-Content -Path $PROFILE -Value $profileContent

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart PowerShell" -ForegroundColor White
Write-Host "2. Type 'Show-Usage' to see Claude status" -ForegroundColor White
Write-Host "3. Use 'jq' for JSON formatting" -ForegroundColor White
