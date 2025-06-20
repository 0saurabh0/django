import os
import re
import sys
from enum import Enum
from github import Github
from dataclasses import dataclass
from typing import List


class IssueType(Enum):
    TUTORIAL = "tutorial"
    MISSING_TICKET = "missing_ticket"
    DJANGO_TUTORIAL = "django_tutorial"


class Severity(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Location(Enum):
    TITLE = "title"
    BODY = "body"


class Confidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PatternMatch:
    """Stores information about a matched pattern"""

    pattern: str
    matched_text: str
    location: Location
    context: str  # surrounding text


@dataclass
class QualityIssue:
    """Represents a quality issue found in a PR"""

    type: IssueType
    severity: Severity
    message: str
    matches: List[PatternMatch]

    def should_auto_close(self) -> bool:
        """Determine if this issue warrants auto-closing"""
        if self.type != IssueType.TUTORIAL:
            return False

        # Need at least one match to consider auto-closing
        if not self.matches:
            return False

        # Auto-close if multiple matches
        if len(self.matches) > 1:
            return True

        # Auto-close if single match is high-confidence pattern
        pattern = self.matches[0].pattern
        return pattern in ["first contribution", "first pr", "learning to"]


class Action:
    """Base class for all actions"""

    def act(self, pr):
        pass


class NoAction(Action):
    def act(self, pr):
        print("No quality issues detected - PR looks good!")


@dataclass
class LabelPR(Action):
    label: str

    def act(self, pr):
        pr.add_to_labels(self.label)


@dataclass
class CommentOnPR(Action):
    comment: str

    def act(self, pr):
        print("Quality issues detected")
        pr.create_issue_comment(self.comment)


class ClosePR(Action):
    def act(self, pr):
        pr.edit(state="closed")


def generate_actions(issues: List[QualityIssue]) -> List[Action]:
    """Generate a list of actions to take based on issues found"""
    if not issues:
        return [NoAction()]

    actions = [LabelPR("possibly-tutorial-pr")]

    # Build comment content
    comment = "## PR Quality Check ⚠️\n\nThis PR may need attention:\n"
    should_close = False

    for issue in issues:
        comment += f"\n### {issue.message} (Severity: {issue.severity.value})\n"

        # Add match details for transparency
        if issue.matches:
            comment += "Matches found:\n"
            for match in issue.matches:
                comment += f"- In {match.location.value}: `{match.context}`\n"

        # Determine if we should close based on issue severity and matches
        if issue.should_auto_close():
            should_close = True

    if should_close:
        comment += (
            "\n⚠️ This PR will be automatically closed based on the detected patterns."
        )
        actions.append(ClosePR())

    actions.append(CommentOnPR(comment))
    return actions


def take_actions(actions: List[Action], pr):
    """Execute all actions in sequence"""
    for action in actions:
        try:
            action.act(pr)
        except Exception as e:
            print(f"Failed to execute action {type(action).__name__}: {str(e)}")


def get_context(
    text: str, match_start: int, match_end: int, context_chars: int = 40
) -> str:
    """Get surrounding context for a match"""
    start = max(0, match_start - context_chars)
    end = min(len(text), match_end + context_chars)
    return text[start:end].strip()


def check_pr_quality(title: str, body: str) -> List[QualityIssue]:
    """Perform quality checks and return structured issues"""
    issues = []

    # Check for ticket reference
    ticket_match = re.search(r"#[0-9]+", title)
    if not ticket_match:
        issues.append(
            QualityIssue(
                type=IssueType.MISSING_TICKET,
                severity=Severity.HIGH,
                message="Missing Trac ticket reference in PR title",
                matches=[],
            )
        )

    # Tutorial patterns with confidence levels
    tutorial_patterns = {
        r"\btest\b": Confidence.LOW,
        r"learning": Confidence.MEDIUM,
        r"first contribution": Confidence.HIGH,
        r"first pr": Confidence.HIGH,
        r"tutorial": Confidence.MEDIUM,
        r"toast": Confidence.HIGH,
        r"first patch": Confidence.HIGH,
        r"getting started": Confidence.MEDIUM,
    }

    tutorial_matches = []
    for pattern, confidence in tutorial_patterns.items():
        # Check title - only need one match per pattern
        title_match = re.search(pattern, title, re.I)
        if title_match:
            tutorial_matches.append(
                PatternMatch(
                    pattern=pattern,
                    matched_text=title_match.group(),
                    location=Location.TITLE,
                    context=title,
                )
            )

        # Check body, but only for high-confidence patterns
        if confidence == Confidence.HIGH and body:
            for match in re.finditer(pattern, body, re.I):
                tutorial_matches.append(
                    PatternMatch(
                        pattern=pattern,
                        matched_text=match.group(),
                        location=Location.BODY,
                        context=get_context(body, match.start(), match.end()),
                    )
                )

    if tutorial_matches:
        issues.append(
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="PR appears to be a test or learning exercise",
                matches=tutorial_matches,
            )
        )

    return issues


def main():
    print("Starting PR quality check")

    # Get GitHub token from environment
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    # Get repository and PR information from environment
    github_repository = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")

    if not github_repository or not pr_number:
        print(
            "Error: GITHUB_REPOSITORY and PR_NUMBER environment variables are required"
        )
        sys.exit(1)

    # Initialize GitHub client and get PR data
    g = Github(github_token)
    repo = g.get_repo(github_repository)
    pr = repo.get_pull(int(pr_number))

    title = pr.title
    body = pr.body if pr.body else ""

    print(f'PR #{pr_number}: "{title}"')

    # Check PR quality
    issues = check_pr_quality(title, body)

    # Generate and take actions
    actions = generate_actions(issues)
    take_actions(actions, pr)


if __name__ == "__main__":
    main()
