import os
import re
import sys
from github import Github
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PatternMatch:
    """Stores information about a matched pattern"""
    pattern: str
    matched_text: str
    location: str  # 'title' or 'body'
    context: str   # surrounding text

@dataclass
class QualityIssue:
    """Represents a quality issue found in a PR"""
    type: str  # 'tutorial', 'missing_ticket', 'django_tutorial'
    severity: str  # 'high', 'medium', 'low'
    message: str
    matches: List[PatternMatch]
    
    def should_auto_close(self) -> bool:
        """Determine if this issue warrants auto-closing"""
        if self.type == 'tutorial':
            # Only auto-close if we have multiple matches or specific high-confidence patterns
            high_confidence_patterns = ['first contribution', 'first pr', 'learning to']
            return len(self.matches) > 1 or any(
                any(p in m.pattern for p in high_confidence_patterns)
                for m in self.matches
            )
        return False

def get_context(text: str, match_start: int, match_end: int, context_chars: int = 40) -> str:
    """Get surrounding context for a match"""
    start = max(0, match_start - context_chars)
    end = min(len(text), match_end + context_chars)
    return text[start:end].strip()

def initialize_github():
    """Initialize GitHub client and return it along with environment information."""
    # Get GitHub token from environment
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    # Initialize GitHub client
    g = Github(github_token)
    
    # Get repository and PR information from environment
    github_repository = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")
    
    # Determine environment
    is_test_env = os.environ.get("ACT") == "true" or not pr_number or not github_repository
    print(f"Environment: {'TEST' if is_test_env else 'PRODUCTION'}")
    
    return g, github_repository, pr_number, is_test_env

def get_pr_data(g, github_repository, pr_number, is_test_env):
    """Get PR title and body either from API or test environment."""
    if is_test_env:
        # If testing with specific PR data
        title = os.environ.get("PR_TITLE", "Test PR title")
        body = os.environ.get("PR_BODY", "Test PR body")
        pr_number = os.environ.get("PR_NUMBER", "1")
        pr = None
    else:
        # Get real PR data from GitHub API
        repo = g.get_repo(github_repository)
        pr = repo.get_pull(int(pr_number))
        title = pr.title
        body = pr.body if pr.body else ""
    
    print(f"PR #{pr_number}: \"{title}\"")
    return pr, title, body, pr_number

def check_pr_quality(title: str, body: str) -> List[QualityIssue]:
    """Perform quality checks and return structured issues"""
    issues = []
    
    # Check for ticket reference
    ticket_match = re.search(r'#[0-9]+', title)
    if not ticket_match:
        issues.append(QualityIssue(
            type='missing_ticket',
            severity='high',
            message="Missing Trac ticket reference in PR title",
            matches=[]
        ))
    
    # Tutorial patterns with confidence levels
    tutorial_patterns = {
        r'\btest\b': 'low',
        r'learning': 'medium',
        r'first contribution': 'high',
        r'first pr': 'high',
        r'tutorial': 'medium',
        r'toast': 'high',
        r'first patch': 'high',
        r'getting started': 'medium',
    }
    
    tutorial_matches = []
    for pattern, confidence in tutorial_patterns.items():
        # Check title
        for match in re.finditer(pattern, title, re.I):
            tutorial_matches.append(PatternMatch(
                pattern=pattern,
                matched_text=match.group(),
                location='title',
                context=get_context(title, match.start(), match.end())
            ))
        
        # Check body, but only for high-confidence patterns
        if confidence == 'high' and body:
            for match in re.finditer(pattern, body, re.I):
                tutorial_matches.append(PatternMatch(
                    pattern=pattern,
                    matched_text=match.group(),
                    location='body',
                    context=get_context(body, match.start(), match.end())
                ))
    
    if tutorial_matches:
        issues.append(QualityIssue(
            type='tutorial',
            severity='medium',
            message="PR appears to be a test or learning exercise",
            matches=tutorial_matches
        ))
    
    return issues

def take_action_on_issues(pr, issues: List[QualityIssue], is_test_env):
    """Take appropriate action based on detailed issue information"""
    if not issues:
        print("No quality issues detected - PR looks good!")
        return
    
    print("Quality issues detected")
    comment = "## PR Quality Check ⚠️\n\nThis PR may need attention:\n"
    
    should_close = False
    for issue in issues:
        comment += f"\n### {issue.message} (Severity: {issue.severity})\n"
        
        # Add match details for transparency
        if issue.matches:
            comment += "Matches found:\n"
            for match in issue.matches:
                comment += f"- In {match.location}: `{match.context}`\n"
        
        # Determine if we should close based on issue severity and matches
        if issue.should_auto_close():
            should_close = True
    
    if should_close:
        comment += "\n⚠️ This PR will be automatically closed based on the detected patterns."
    
    # Log findings regardless of environment
    print("Would add label: possibly-tutorial-pr")
    print(f"Would add comment: {comment}")
    
    # Skip API calls in test environment
    if not is_test_env:
        try:
            # Add label
            pr.add_to_labels("possibly-tutorial-pr")
            
            # Add comment
            pr.create_issue_comment(comment)
            
            # Auto-close PR if necessary
            if should_close:
                pr.edit(state="closed")
        except Exception as e:
            print(f"Failed to make API calls: {str(e)}")

def main():
    print("Starting PR quality check")
    
    # Initialize GitHub and get environment information
    g, github_repository, pr_number, is_test_env = initialize_github()
    
    # Get PR data
    pr, title, body, pr_number = get_pr_data(g, github_repository, pr_number, is_test_env)
    
    # Check PR quality
    issues = check_pr_quality(title, body)
    
    # Take action if issues found
    take_action_on_issues(pr, issues, is_test_env)

if __name__ == "__main__":
    main()