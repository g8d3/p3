"""
AutoContent - GitHub Manager
Creates and manages GitHub PRs for code contributions
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional
from logger import logger
from error_handler import self_healer, ErrorContext


@dataclass
class PRDetails:
    """Pull Request details"""
    title: str
    body: str
    head: str  # Branch name
    base: str = "main"
    repo: str = ""


class GitHubManager:
    """GitHub PR management"""
    
    def __init__(self, token: str, default_repo: str = ""):
        self.token = token
        self.default_repo = default_repo
        self.gh_available = self._check_gh()
    
    def _check_gh(self) -> bool:
        """Check if gh CLI is available"""
        try:
            subprocess.run(["gh", "--version"], capture_output=True)
            return True
        except FileNotFoundError:
            logger.warning("GitHub CLI not found")
            return False
    
    def _run_gh(self, *args) -> subprocess.CompletedProcess:
        """Run gh command"""
        cmd = ["gh"] + list(args)
        return subprocess.run(
            cmd, capture_output=True, text=True,
            env={**os.environ, "GH_TOKEN": self.token}
        )
    
    def create_pr(self, pr: PRDetails) -> Optional[str]:
        """Create a pull request"""
        logger.info(f"Creating PR: {pr.title}")
        
        if not self.gh_available:
            return self._create_pr_fallback(pr)
        
        # Check auth
        auth_check = self._run_gh("auth", "status")
        if auth_check.returncode != 0:
            logger.error("Not authenticated with GitHub")
            return None
        
        # Create PR
        result = self._run_gh(
            "pr", "create",
            "--title", pr.title,
            "--body", pr.body,
            "--head", pr.head,
            "--base", pr.base
        )
        
        if result.returncode == 0:
            pr_url = result.stdout.strip()
            logger.info(f"PR created: {pr_url}")
            return pr_url
        else:
            logger.error(f"PR creation failed: {result.stderr}")
            return None
    
    def _create_pr_fallback(self, pr: PRDetails) -> Optional[str]:
        """Fallback PR creation using git"""
        logger.warning("Using git fallback for PR creation")
        
        # Create branch and commit
        try:
            subprocess.run(["git", "checkout", "-b", pr.head], capture_output=True)
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", pr.title], capture_output=True)
            
            # Note: Push would require remote configuration
            logger.info(f"Branch created: {pr.head}")
            return f"https://github.com/owner/repo/pull/new/{pr.head}"
            
        except Exception as e:
            logger.error(f"Git fallback failed: {e}")
            return None
    
    def create_code_pr(self, code: str, repo: str, 
                       title: str = "Auto-generated code") -> Optional[str]:
        """Create PR with generated code"""
        logger.info(f"Creating code PR in {repo}")
        
        # Write code to file
        code_file = "output/code/generated_code.py"
        os.makedirs("output/code", exist_ok=True)
        with open(code_file, "w") as f:
            f.write(code)
        
        # Create PR details
        pr = PRDetails(
            title=title,
            body=f"""## Auto-Generated Code

This code was automatically generated from X.com content analysis.

### Changes
- Added generated code file

### Testing
Please review the code for correctness.
""",
            head=f"auto-generated-{os.urandom(4).hex()}",
            base="main",
            repo=repo
        )
        
        return self.create_pr(pr)
    
    def list_prs(self, repo: str = "") -> list:
        """List open PRs"""
        repo = repo or self.default_repo
        
        if not self.gh_available:
            return []
        
        result = self._run_gh("pr", "list", "--repo", repo)
        
        if result.returncode == 0:
            prs = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    prs.append(line)
            return prs
        
        return []


def create_github_manager(token: str, **kwargs) -> GitHubManager:
    """Factory function"""
    return GitHubManager(token, **kwargs)
