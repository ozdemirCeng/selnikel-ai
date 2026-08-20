"""
Selnikel AI Benchmark Runner CLI Entrypoint.
Thin wrapper forwarding arguments directly to app.cli.benchmark_runner.
"""
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.cli.benchmark_runner import main

if __name__ == "__main__":
    main()