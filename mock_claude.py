"""Mock Claude Code for testing Token Guard"""
import time
import sys

print("Claude Code v1.0 (MOCK)")
print("Session started...")
time.sleep(0.5)

# Simulate normal operation
print("\nUser: Read the file test.txt")
time.sleep(0.3)

# Simulate violation - using Read() directly
print("Assistant: Let me read that file.")
print("Tool: Read(file_path='test.txt')")  # This should trigger violation
time.sleep(0.5)

# Simulate token usage
print("tokens=250")
time.sleep(0.3)

# Simulate another operation
print("\nUser: Run bash command")
time.sleep(0.3)

# Simulate Bash violation
print("Assistant: Let me run that command.")
print("Tool: Bash(command='ls -la')")  # This should trigger violation
time.sleep(0.5)

# Simulate more token usage
print("tokens=350")
time.sleep(0.3)

# Simulate correct usage
print("\nUser: Delegate read operation")
print("Assistant: Using delegate_read() instead.")
print("Tool: delegate_read(file='test.txt', goal='extract content')")
time.sleep(0.5)

print("tokens=100")
print("\nSession completed. Total tokens: 700")
