#!/usr/bin/env python3
"""
Example usage of rebase_and_test.py script
This file shows different scenarios for rebasing and testing.
"""

import subprocess
import sys
from pathlib import Path

def run_example(description: str, command: list):
    """Run an example command with description."""
    print(f"\n{'='*60}")
    print(f"EXAMPLE: {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(command)}")
    print("\nPress Enter to run this example or Ctrl+C to skip...")
    
    try:
        input()
        result = subprocess.run(command, check=False)
        if result.returncode == 0:
            print("✅ Example completed successfully!")
        else:
            print("❌ Example failed!")
    except KeyboardInterrupt:
        print("\nSkipped this example.")

def main():
    """Run example scenarios."""
    script_path = Path("rebase_and_test.py")
    
    if not script_path.exists():
        print("Error: rebase_and_test.py not found!")
        sys.exit(1)
    
    print("Git Rebase and Docker Compose Test Examples")
    print("=" * 50)
    
    # Example 1: Basic rebase onto a commit
    run_example(
        "Rebase current branch onto specific commit",
        ["python3", "rebase_and_test.py", "abc123", "--mode", "onto"]
    )
    
    # Example 2: Rebase with specific branch
    run_example(
        "Rebase feature branch onto main",
        ["python3", "rebase_and_test.py", "main", "--branch", "feature-branch"]
    )
    
    # Example 3: Interactive rebase
    run_example(
        "Interactive rebase from specific commit",
        ["python3", "rebase_and_test.py", "abc123", "--mode", "interactive"]
    )
    
    # Example 4: Run tests on specific service
    run_example(
        "Rebase and run tests on specific service",
        ["python3", "rebase_and_test.py", "abc123", "--test-service", "web", "--test-command", "pytest tests/"]
    )
    
    # Example 5: Custom compose file
    run_example(
        "Use custom docker-compose file",
        ["python3", "rebase_and_test.py", "abc123", "--compose-file", "docker-compose.test.yml"]
    )
    
    # Example 6: Skip build and cleanup
    run_example(
        "Skip build and cleanup after tests",
        ["python3", "rebase_and_test.py", "abc123", "--skip-build", "--cleanup"]
    )

if __name__ == "__main__":
    main()