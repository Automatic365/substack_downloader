import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Download and compile Substack posts" in result.stdout
