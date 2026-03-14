"""Git utilities for incremental updates and change detection."""

import os
import logging
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from git import Repo, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


class GitChangeDetector:
    """Detects changed files in a git repository since last analysis."""
    
    def __init__(self, repo_path: str, state_file: str = ".cartography/analysis_state.json"):
        self.repo_path = repo_path
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(exist_ok=True)
        
        try:
            self.repo = Repo(repo_path)
            self.is_git = True
        except InvalidGitRepositoryError:
            logger.warning(f"Not a git repository: {repo_path}")
            self.repo = None
            self.is_git = False
    
    def get_current_commit(self) -> Optional[str]:
        """Get the current HEAD commit hash."""
        if not self.is_git:
            return None
        return str(self.repo.head.commit)
    
    def get_file_hash(self, file_path: str) -> str:
        """Compute hash of file content for change detection."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""
    
    def load_state(self) -> Dict:
        """Load previous analysis state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
        return {
            "last_commit": None,
            "file_hashes": {},
            "last_analysis": None
        }
    
    def save_state(self, state: Dict):
        """Save current analysis state."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")
    
    def get_changed_files(self) -> Tuple[List[str], bool]:
        """Get list of files changed since last analysis.
        
        Returns:
            Tuple of (changed_files, needs_full_analysis)
        """
        if not self.is_git:
            # Non-git repo - assume all files need analysis
            return [], True
        
        state = self.load_state()
        current_commit = self.get_current_commit()
        
        # If first run or commit changed, use git diff
        if not state["last_commit"] or state["last_commit"] != current_commit:
            try:
                # Get files changed since last commit
                if state["last_commit"]:
                    diff = self.repo.git.diff('--name-only', state["last_commit"])
                    changed = diff.split('\n')
                else:
                    # First run - get all files
                    changed = []
                    for root, _, files in os.walk(self.repo_path):
                        if '.git' in root:
                            continue
                        for file in files:
                            changed.append(os.path.relpath(os.path.join(root, file), self.repo_path))
                
                # Update state
                state["last_commit"] = current_commit
                state["last_analysis"] = datetime.now().isoformat()
                self.save_state(state)
                
                return changed, False
                
            except Exception as e:
                logger.error(f"Error getting changed files: {e}")
                return [], True
        
        # No changes
        return [], False
    
    def get_files_needing_update(self, all_files: List[str]) -> List[str]:
        """Determine which files need re-analysis based on content changes."""
        if not self.is_git:
            return all_files
        
        state = self.load_state()
        current_commit = self.get_current_commit()
        
        # If commit changed, all files need analysis
        if state["last_commit"] != current_commit:
            return all_files
        
        # Check each file's hash
        needs_update = []
        for file_path in all_files:
            current_hash = self.get_file_hash(file_path)
            prev_hash = state.get("file_hashes", {}).get(file_path)
            
            if current_hash != prev_hash:
                needs_update.append(file_path)
                # Update hash in state
                if "file_hashes" not in state:
                    state["file_hashes"] = {}
                state["file_hashes"][file_path] = current_hash
        
        if needs_update:
            self.save_state(state)
        
        return needs_update
    
    def should_run_incremental(self) -> bool:
        """Determine if incremental update should be used."""
        if not self.is_git:
            return False
        
        state = self.load_state()
        current_commit = self.get_current_commit()
        
        # If commit changed, need full analysis
        if state["last_commit"] != current_commit:
            return False
        
        # Check if any files changed
        changed = self.get_changed_files()[0]
        return len(changed) > 0