"""Generate deployment guide for Token Guard via RTX"""
from ai_gateway import delegate_to_rtx

task = """Create a comprehensive DEPLOYMENT GUIDE for Token Guard wrapper.

INCLUDE:
1. System requirements
2. Installation steps (detailed)
3. PowerShell alias setup (step-by-step)
4. Bash alias setup (for Git Bash users)
5. Verification steps
6. Usage examples
7. Configuration customization
8. Troubleshooting section
9. Uninstall instructions

TARGET AUDIENCE: Windows 11 users with PowerShell

Make it PRODUCTION-READY with:
- Clear step-by-step instructions
- Code blocks for copy-paste
- Screenshots descriptions where helpful
- Common pitfalls and solutions
- Quick start for impatient users

Format: Professional README.md with proper sections and formatting."""

result = delegate_to_rtx(
    task_description=task,
    role="expert technical writer",
    temperature=0.4
)

with open('DEPLOYMENT_GUIDE.md', 'w', encoding='utf-8') as f:
    f.write(result)

print("[OK] Deployment guide generated!")
