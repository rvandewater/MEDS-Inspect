# tests/test_integration_mimic_demo.py
import pytest
import subprocess
import sys


@pytest.mark.integration
def test_app_cli_starts():
    # Adjust the command below to match how you normally start your app
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.MEDS_Inspect.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Wait a few seconds to see if it crashes
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        # If still running after timeout, assume it started successfully
        proc.terminate()
        assert True
    else:
        # If it exited early, that's a failure
        assert proc.returncode == 0
