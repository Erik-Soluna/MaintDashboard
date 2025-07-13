#!/usr/bin/env python3
"""
Git Rebase and Docker Compose Test Runner
This script helps you rebase specific commits and run tests using Docker Compose.
"""

import subprocess
import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rebase_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GitRebaseManager:
    """Handles git operations for rebasing specific commits."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.original_branch = None
        
    def run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Execute a command and return the result."""
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check
            )
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            logger.error(f"Error output: {e.stderr}")
            raise
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self.run_command(["git", "branch", "--show-current"])
        return result.stdout.strip()
    
    def backup_current_state(self) -> str:
        """Create a backup branch of current state."""
        self.original_branch = self.get_current_branch()
        timestamp = int(time.time())
        backup_branch = f"backup-{self.original_branch}-{timestamp}"
        
        self.run_command(["git", "branch", backup_branch])
        logger.info(f"Created backup branch: {backup_branch}")
        return backup_branch
    
    def fetch_latest(self, remote: str = "origin") -> None:
        """Fetch latest changes from remote."""
        logger.info("Fetching latest changes...")
        self.run_command(["git", "fetch", remote])
    
    def pull_latest(self, branch: Optional[str] = None) -> None:
        """Pull latest changes for specified branch."""
        if branch:
            current_branch = self.get_current_branch()
            if current_branch != branch:
                self.run_command(["git", "checkout", branch])
        
        logger.info("Pulling latest changes...")
        self.run_command(["git", "pull"])
    
    def rebase_onto_commit(self, target_commit: str) -> None:
        """Rebase current branch onto a specific commit."""
        logger.info(f"Rebasing onto commit: {target_commit}")
        try:
            self.run_command(["git", "rebase", target_commit])
            logger.info("Rebase completed successfully!")
        except subprocess.CalledProcessError:
            logger.error("Rebase failed - you may need to resolve conflicts")
            self.show_rebase_status()
            raise
    
    def interactive_rebase_from_commit(self, from_commit: str) -> None:
        """Start interactive rebase from a specific commit."""
        logger.info(f"Starting interactive rebase from commit: {from_commit}")
        try:
            # For interactive rebase, we need to use the parent of the commit
            parent_commit = self.get_parent_commit(from_commit)
            self.run_command(["git", "rebase", "-i", parent_commit])
            logger.info("Interactive rebase started!")
        except subprocess.CalledProcessError:
            logger.error("Interactive rebase failed")
            raise
    
    def get_parent_commit(self, commit: str) -> str:
        """Get the parent commit of a given commit."""
        result = self.run_command(["git", "rev-parse", f"{commit}^"])
        return result.stdout.strip()
    
    def show_rebase_status(self) -> None:
        """Show current rebase status."""
        try:
            result = self.run_command(["git", "status"], check=False)
            print("Current git status:")
            print(result.stdout)
        except Exception as e:
            logger.error(f"Failed to get rebase status: {e}")
    
    def continue_rebase(self) -> None:
        """Continue rebase after resolving conflicts."""
        logger.info("Continuing rebase...")
        self.run_command(["git", "rebase", "--continue"])
    
    def abort_rebase(self) -> None:
        """Abort current rebase."""
        logger.info("Aborting rebase...")
        self.run_command(["git", "rebase", "--abort"])
    
    def get_commit_info(self, commit: str) -> Dict[str, str]:
        """Get information about a specific commit."""
        try:
            result = self.run_command([
                "git", "show", "--format=%H|%s|%an|%ae|%ad", "--no-patch", commit
            ])
            parts = result.stdout.strip().split('|')
            return {
                "hash": parts[0],
                "subject": parts[1],
                "author": parts[2],
                "email": parts[3],
                "date": parts[4]
            }
        except Exception as e:
            logger.error(f"Failed to get commit info: {e}")
            return {}

class DockerComposeManager:
    """Handles Docker Compose operations for testing."""
    
    def __init__(self, compose_file: str = "docker-compose.yml"):
        self.compose_file = Path(compose_file)
        if not self.compose_file.exists():
            raise FileNotFoundError(f"Docker Compose file not found: {compose_file}")
    
    def run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Execute a docker compose command."""
        full_cmd = ["docker-compose", "-f", str(self.compose_file)] + cmd
        logger.info(f"Running: {' '.join(full_cmd)}")
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                check=check
            )
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker Compose command failed: {e}")
            logger.error(f"Error output: {e.stderr}")
            raise
    
    def build_services(self, services: Optional[List[str]] = None) -> None:
        """Build Docker services."""
        cmd = ["build"]
        if services:
            cmd.extend(services)
        else:
            cmd.append("--no-cache")
        
        logger.info("Building Docker services...")
        self.run_command(cmd)
    
    def run_tests(self, service: Optional[str] = None, command: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run tests using Docker Compose."""
        if service and command:
            cmd = ["run", "--rm", service] + command.split()
        elif service:
            cmd = ["run", "--rm", service]
        else:
            cmd = ["up", "--abort-on-container-exit"]
        
        logger.info("Running tests...")
        return self.run_command(cmd, check=False)
    
    def stop_services(self) -> None:
        """Stop all services."""
        logger.info("Stopping services...")
        self.run_command(["down"], check=False)
    
    def cleanup(self) -> None:
        """Clean up containers and volumes."""
        logger.info("Cleaning up...")
        self.run_command(["down", "-v", "--remove-orphans"], check=False)

def main():
    """Main function to orchestrate the rebase and test process."""
    parser = argparse.ArgumentParser(description="Rebase specific commit and run tests")
    parser.add_argument("commit", help="Commit hash to rebase onto/from")
    parser.add_argument("--mode", choices=["onto", "from", "interactive"], 
                       default="onto", help="Rebase mode")
    parser.add_argument("--branch", help="Branch to work on")
    parser.add_argument("--compose-file", default="docker-compose.yml", 
                       help="Docker Compose file")
    parser.add_argument("--test-service", help="Specific service to run tests on")
    parser.add_argument("--test-command", help="Test command to run")
    parser.add_argument("--skip-build", action="store_true", 
                       help="Skip building Docker services")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Clean up after tests")
    
    args = parser.parse_args()
    
    # Initialize managers
    git_manager = GitRebaseManager()
    
    try:
        # Check if Docker Compose file exists
        docker_manager = DockerComposeManager(args.compose_file)
    except FileNotFoundError as e:
        logger.error(f"Docker Compose setup failed: {e}")
        sys.exit(1)
    
    try:
        # Create backup
        backup_branch = git_manager.backup_current_state()
        logger.info(f"Created backup: {backup_branch}")
        
        # Get commit info
        commit_info = git_manager.get_commit_info(args.commit)
        if commit_info:
            logger.info(f"Working with commit: {commit_info['hash'][:8]} - {commit_info['subject']}")
        
        # Fetch latest changes
        git_manager.fetch_latest()
        
        # Switch to specified branch if provided
        if args.branch:
            git_manager.pull_latest(args.branch)
        
        # Perform rebase based on mode
        if args.mode == "onto":
            git_manager.rebase_onto_commit(args.commit)
        elif args.mode == "from":
            git_manager.rebase_onto_commit(f"{args.commit}^")
        elif args.mode == "interactive":
            git_manager.interactive_rebase_from_commit(args.commit)
            logger.info("Interactive rebase started. Complete it manually, then run tests.")
            return
        
        # Build Docker services if not skipping
        if not args.skip_build:
            docker_manager.build_services()
        
        # Run tests
        test_result = docker_manager.run_tests(args.test_service, args.test_command)
        
        # Report test results
        if test_result.returncode == 0:
            logger.info("✅ Tests passed!")
            print("\n" + "="*50)
            print("TEST RESULTS: PASSED")
            print("="*50)
        else:
            logger.error("❌ Tests failed!")
            print("\n" + "="*50)
            print("TEST RESULTS: FAILED")
            print("="*50)
            if test_result.stderr:
                print("Error output:")
                print(test_result.stderr)
        
        # Show test output
        if test_result.stdout:
            print("\nTest output:")
            print(test_result.stdout)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Operation failed: {e}")
        logger.info(f"You can restore from backup branch: {backup_branch}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        git_manager.abort_rebase()
        sys.exit(1)
    finally:
        # Cleanup if requested
        if args.cleanup:
            docker_manager.cleanup()

if __name__ == "__main__":
    main()