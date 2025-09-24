# AI Guidance

Always remember the following points as you are working on this code base:

1. Use the virtual env in the project root (`source .venv/bin/activate && <your_command>`)

2. Prefer explicit errors over fallbacks. The goal is to fix issues, not mask errors.

3. Follow good software development practices like SOLID.

4. Simpler is better.

5. Remember the purpose of this package is to provide its functionality in a clear and maintainable manner. Avoid adding special-cases or hack fixes simply to get around issues.

6. Do NOT make bandaid fixes that break clean architecture guidelines. Always respect the architectural boundaries.

7. After all code changes, run `source .venv/bin/activate && ruff format src/ tests/ && ruff check src/ tests/ --fix && mypy src/ && bandit -r src/` to ensure code quality is retained in an iterative manner.

8. Avoid making lines longer than 88 characters (E501 ruff check).

9. Thread safety is critical - all public APIs must be thread-safe and work correctly in concurrent environments.

10. Do not perform any git operations as the developer will handle those.

## Testing Strategy

See [TESTING.md](TESTING.md) for full details.

## Cross-Platform Compatibility

11. **Always use `pathlib.Path` for file and directory operations** - Never use string concatenation or os.path.join() for paths. Use `Path("/base") / "subdir" / "file.txt"` instead of `"/base/subdir/file.txt"`.

12. **Handle file operations with proper resource management** - Always use context managers (`with` statements) for file operations. Close file handles explicitly on Windows by exiting the context before any file operations like deletion.

13. **Use proper encoding for file operations** - Always specify `encoding="utf-8"` when reading/writing text files to ensure consistent behavior across platforms.

14. **Handle Windows file locking gracefully** - When using temporary files, ensure file handles are closed before deletion. Use try/except blocks around file deletion operations to handle Windows-specific permission errors.

15. **Test file operations with tempfile properly** - Use `tempfile.NamedTemporaryFile` with `delete=False`, capture the path outside the context manager, then handle cleanup with proper error handling for Windows compatibility.

16. **Use os-independent path operations** - Never hardcode path separators (`/` or `\`). Let `pathlib.Path` handle platform differences automatically.

Example of correct cross-platform file handling:

```python
from pathlib import Path
import tempfile

# Correct way to handle temporary files cross-platform
with tempfile.NamedTemporaryFile(
    mode="w", suffix=".yaml", delete=False, encoding="utf-8"
) as temp_file:
    temp_file.write(content)
    temp_file.flush()
    temp_file_path = Path(temp_file.name)

try:
    # Use the file
    process_file(temp_file_path)
finally:
    try:
        temp_file_path.unlink()
    except (OSError, PermissionError):
        # On Windows, sometimes the file is still locked
        pass
```
