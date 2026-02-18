Here is the `bash_executor.py` script:
```python
import subprocess
import sys

def execute_commands(commands):
    results = {}
    for command in commands:
        try:
            output = subprocess.check_output(command, shell=True)
            results[command] = output.decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            results[command] = f"Error: {e}"
        except FileNotFoundError:
            results[command] = "Command not found"
        except Exception as e:
            results[command] = f"Unknown error: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bash_executor.py <cmd1> <cmd2> ...")
        sys.exit(1)

    commands = [f"{arg}" for arg in sys.argv[1:]]
    results = execute_commands(commands)
    print(results)
```
Let me explain what this script does:

1. The `execute_commands` function takes a list of bash commands as input.
2. It iterates through each command and uses the `subprocess.check_output` function to run the command and capture its output.
3. If the command runs successfully, it stores the output in a dictionary with the command as the key.
4. If an error occurs (e.g., the command returns a non-zero exit code), it catches the `subprocess.CalledProcessError` exception and stores an error message in the dictionary.
5. The script also handles other exceptions (e.g., `FileNotFoundError`) and stores an error message in the dictionary.
6. Finally, the function returns the dictionary of results.

In the `if __name__ == "__main__":` block, we check if the script is being run from the command line (i.e., not imported as a module). If so, we extract the list of commands from the command-line arguments using `sys.argv[1:]`. We then call the `execute_commands` function with this list and print the results.

To use this script, save it to a file named `bash_executor.py`, make it executable with `chmod +x bash_executor.py`, and then run it from the command line like this:
```bash
$ python bash_executor.py cmd1 cmd2 cmd3
```
This will execute the commands and print the results.