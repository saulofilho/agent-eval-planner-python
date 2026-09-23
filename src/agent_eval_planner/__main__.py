"""Main entry point when invoked as python -m agent_eval_planner."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
