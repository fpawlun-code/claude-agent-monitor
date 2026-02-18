# Quick Restore Guide
## Szybkie przywrócenie stanu po awarii

**Last updated:** 2026-02-17 22:20

---

## 🚨 Jeśli coś nie działa - Sprawdź to:

### 1. Statusline nie widoczny
```powershell
# Restart Claude Code:
exit
claude

# Jeśli dalej nie działa - verify config:
cat C:\Users\fpawl\.claude\settings.json | jq .statusLine

# Should show:
# {
#   "type": "command",
#   "command": "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\fpawl\\.claude\\statusline.ps1",
#   "padding": 2
# }
```

### 2. RTX nie działa
```powershell
# Check status:
cat C:\ClaudeAgent\autonomous\progress.json

# If old timestamp - restart:
cd C:\ClaudeAgent
python -c "import subprocess; subprocess.Popen(['python', 'autonomous/core_autonomy.py'])"

# Stop RTX:
New-Item C:\ClaudeAgent\autonomous\STOP -ItemType File
```

### 3. Oh My Posh errors
```powershell
# Fix PSReadLine:
Install-Module -Name PSReadLine -Force -SkipPublisherCheck

# Restart PowerShell
```

---

## 📂 Kluczowe pliki (do backup/restore)

```
C:\ClaudeAgent\
├── ai_gateway.py           # RTX delegation gateway
├── rtx_agent.py            # RTX agent
├── autonomous\
│   ├── core_autonomy.py    # Main RTX loop (v2 - error detection)
│   ├── progress.json       # RTX status
│   ├── fixes.log           # Error fixes log
│   └── rtx_log.txt         # RTX activity log
├── NEXT_STEPS.md           # Roadmap
└── conversations\          # Backup conversations

C:\Users\fpawl\.claude\
├── statusline.ps1          # Statusline script
├── settings.json           # Claude config
└── MEMORY.md               # Auto-memory (delegation rules)
```

---

## 🔧 Kluczowe komendy

### Terminal:
```powershell
Show-Usage              # RTX stats
claude                  # Start Claude Code
exit                    # Exit Claude
jq                      # JSON formatter
```

### RTX Control:
```powershell
# Status:
cat C:\ClaudeAgent\autonomous\progress.json

# Logs:
tail -20 C:\ClaudeAgent\autonomous\rtx_log.txt

# Fixes:
cat C:\ClaudeAgent\autonomous\fixes.log

# Stop:
New-Item C:\ClaudeAgent\autonomous\STOP -ItemType File

# Start:
cd C:\ClaudeAgent
python -c "import subprocess; subprocess.Popen(['python', 'autonomous/core_autonomy.py'])"
```

---

## 💾 Full Restore (od zera)

Jeśli wszystko się zepsuło:

1. **Restore statusline:**
```powershell
# Copy from backup:
cp C:\ClaudeAgent\conversations\backups\statusline.ps1 C:\Users\fpawl\.claude\

# Update settings.json manually (see backup file)
```

2. **Restore RTX:**
```powershell
cd C:\ClaudeAgent

# Stop old process:
New-Item autonomous\STOP -ItemType File
sleep 5

# Start fresh:
python autonomous\core_autonomy.py
```

3. **Restore PowerShell profile:**
```powershell
# Re-run setup:
cd C:\ClaudeAgent
.\add_to_profile.ps1

# Restart PowerShell
```

---

## 📞 Emergency Contacts

**Conversation backups:**
- `C:\ClaudeAgent\conversations\`

**Full conversation:**
- `C:\ClaudeAgent\conversations\2026-02-17_statusline-rtx-upgrade.md`

**Roadmap:**
- `C:\ClaudeAgent\NEXT_STEPS.md`

**Memory:**
- `C:\Users\fpawl\.claude\projects\C--Users-fpawl\memory\MEMORY.md`

---

## ✅ Verification Checklist

Po restore sprawdź:
- [ ] Statusline widoczny na dole Claude Code
- [ ] `Show-Usage` działa w PowerShell
- [ ] `cat C:\ClaudeAgent\autonomous\progress.json` pokazuje recent timestamp
- [ ] Oh My Posh działa (no red errors)
- [ ] `jq` dostępny (`echo '{"test":1}' | jq`)

---

**Jeśli to nie pomaga:** Przeczytaj pełny backup conversation!
