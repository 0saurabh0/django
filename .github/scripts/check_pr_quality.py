import os
import re
import sys
from github import Github

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

def check_pr_quality(title, body):
    """Perform quality checks and return issues found."""
    issues = []
    
    # Check for ticket reference
    has_ticket = bool(re.search(r'#[0-9]+', title))
    if not has_ticket:
        issues.append("Missing Trac ticket reference in PR title")
    
    # Check for tutorial patterns
    tutorial_pattern = r'test|learning|first contribution|demo|first pr|tutorial|first patch|getting started|first time|new contributor|toast'
    is_tutorial = bool(re.search(tutorial_pattern, title, re.I) or re.search(tutorial_pattern, body, re.I))
    is_django_tutorial = bool(re.search(r'writing.*first patch|intro\/contributing|first django|django.*tutorial', body, re.I))
    
    if is_tutorial:
        issues.append("PR appears to be a test or learning exercise")
        
    if is_django_tutorial:
        issues.append("Appears to be following the 'Writing your first patch to Django' tutorial")
    
    return issues

def take_action_on_issues(pr, issues, is_test_env):
    """Add labels and comments to PR based on issues found."""
    if not issues:
        print("No quality issues detected - PR looks good!")
        return
    
    print("Quality issues detected")
    comment = "## PR Quality Check ⚠️\n\nThis PR may need attention:\n"
    
    for issue in issues:
        comment += f"- {issue}\n"
    
    comment += "\nPlease ensure this is a real contribution with a Trac ticket reference."
    
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