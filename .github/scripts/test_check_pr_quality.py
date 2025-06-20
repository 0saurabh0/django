import unittest

from check_pr_quality import (
    IssueType,
    Severity,
    Location,
    PatternMatch,
    QualityIssue,
    get_context,
    check_pr_quality,
    generate_actions,
    NoAction,
    LabelPR,
    CommentOnPR,
    ClosePR,
)


class TestGetContext(unittest.TestCase):
    """Test the get_context function"""

    def test_get_context_normal_case(self):
        text = "This is a test string for context extraction"
        result = get_context(text, 10, 14, 5)  # "test" with 5 chars context
        self.assertEqual(result, "is a test stri")

    def test_get_context_at_start(self):
        text = "test string"
        result = get_context(text, 0, 4, 5)  # "test" at start
        self.assertEqual(result, "test stri")

    def test_get_context_at_end(self):
        text = "string test"
        result = get_context(text, 7, 11, 5)  # "test" at end
        self.assertEqual(result, "ring test")

    def test_get_context_short_text(self):
        text = "test"
        result = get_context(text, 0, 4, 10)
        self.assertEqual(result, "test")

    def test_get_context_strips_whitespace(self):
        text = "  test string  "
        result = get_context(text, 2, 6, 2)
        self.assertEqual(result, "test s")

    def test_get_context_exact_boundaries(self):
        text = "abcdefghij"
        result = get_context(text, 3, 6, 2)  # "def" with 2 chars context
        # start = max(0, 3-2) = 1, end = min(10, 6+2) = 8
        # text[1:8] = "bcdefgh"
        self.assertEqual(result, "bcdefgh")

    def test_get_context_zero_context(self):
        text = "hello world"
        result = get_context(text, 6, 11, 0)  # "world" with no context
        self.assertEqual(result, "world")


class TestPatternMatch(unittest.TestCase):
    """Test the PatternMatch dataclass"""

    def test_pattern_match_creation(self):
        match = PatternMatch(
            pattern="test",
            matched_text="TEST",
            location=Location.TITLE,
            context="This is a TEST case",
        )
        self.assertEqual(match.pattern, "test")
        self.assertEqual(match.matched_text, "TEST")
        self.assertEqual(match.location, Location.TITLE)
        self.assertEqual(match.context, "This is a TEST case")


class TestQualityIssue(unittest.TestCase):
    """Test the QualityIssue dataclass and its methods"""

    def test_should_auto_close_non_tutorial(self):
        issue = QualityIssue(
            type=IssueType.MISSING_TICKET,
            severity=Severity.HIGH,
            message="Missing ticket",
            matches=[],
        )
        self.assertFalse(issue.should_auto_close())

    def test_should_auto_close_tutorial_no_matches(self):
        issue = QualityIssue(
            type=IssueType.TUTORIAL,
            severity=Severity.MEDIUM,
            message="Tutorial PR",
            matches=[],
        )
        self.assertFalse(issue.should_auto_close())

    def test_should_auto_close_tutorial_multiple_matches(self):
        matches = [
            PatternMatch("test", "test", Location.TITLE, "test context"),
            PatternMatch("learning", "learning", Location.BODY, "learning context"),
        ]
        issue = QualityIssue(
            type=IssueType.TUTORIAL,
            severity=Severity.MEDIUM,
            message="Tutorial PR",
            matches=matches,
        )
        self.assertTrue(issue.should_auto_close())

    def test_should_auto_close_tutorial_high_confidence_pattern(self):
        matches = [
            PatternMatch(
                "first contribution",
                "first contribution",
                Location.TITLE,
                "my first contribution",
            )
        ]
        issue = QualityIssue(
            type=IssueType.TUTORIAL,
            severity=Severity.MEDIUM,
            message="Tutorial PR",
            matches=matches,
        )
        self.assertTrue(issue.should_auto_close())

    def test_should_auto_close_tutorial_single_low_confidence(self):
        matches = [PatternMatch("test", "test", Location.TITLE, "test context")]
        issue = QualityIssue(
            type=IssueType.TUTORIAL,
            severity=Severity.MEDIUM,
            message="Tutorial PR",
            matches=matches,
        )
        self.assertFalse(issue.should_auto_close())


class TestCheckPRQuality(unittest.TestCase):
    """Test the check_pr_quality function"""

    def test_valid_pr_with_ticket(self):
        title = "Fixed bug in authentication #12345"
        body = "This PR fixes the authentication issue described in ticket #12345"
        issues = check_pr_quality(title, body)
        self.assertEqual(len(issues), 0)

    def test_missing_ticket_reference(self):
        title = "Fixed bug in authentication"
        body = "This PR fixes the authentication issue"
        issues = check_pr_quality(title, body)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, IssueType.MISSING_TICKET)
        self.assertEqual(issues[0].severity, Severity.HIGH)
        self.assertEqual(len(issues[0].matches), 0)

    def test_tutorial_pattern_in_title(self):
        title = "My first contribution to Django"
        body = "This is a real fix"
        issues = check_pr_quality(title, body)

        # Should have both missing ticket and tutorial issues
        self.assertEqual(len(issues), 2)
        issue_types = [issue.type for issue in issues]
        self.assertIn(IssueType.MISSING_TICKET, issue_types)
        self.assertIn(IssueType.TUTORIAL, issue_types)

        # Check tutorial issue details
        tutorial_issue = next(
            issue for issue in issues if issue.type == IssueType.TUTORIAL
        )
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].pattern, "first contribution")
        self.assertEqual(tutorial_issue.matches[0].location, Location.TITLE)

    def test_high_confidence_pattern_in_body(self):
        title = "Fix authentication bug #12345"
        body = "This is my first pr to Django. I followed some guide."
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, IssueType.TUTORIAL)

        # Should find "first pr" (high confidence, checked in body)
        self.assertEqual(len(issues[0].matches), 1)
        self.assertEqual(issues[0].matches[0].pattern, "first pr")
        self.assertEqual(issues[0].matches[0].location, Location.BODY)

    def test_low_confidence_pattern_not_in_body(self):
        title = "Add test for authentication"
        body = "This adds a comprehensive test suite for the authentication module"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 2)  # missing_ticket + tutorial
        tutorial_issue = next(
            issue for issue in issues if issue.type == IssueType.TUTORIAL
        )

        # Should only find "test" in title, not in body (low confidence)
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].location, Location.TITLE)
        self.assertEqual(tutorial_issue.matches[0].pattern, r"\btest\b")

    def test_multiple_patterns_in_title(self):
        title = "My first contribution - learning Django test"
        body = "This is a real change"
        issues = check_pr_quality(title, body)

        tutorial_issue = next(
            issue for issue in issues if issue.type == IssueType.TUTORIAL
        )
        self.assertEqual(
            len(tutorial_issue.matches), 3
        )  # first contribution, learning, test

        patterns_found = [match.pattern for match in tutorial_issue.matches]
        self.assertIn("first contribution", patterns_found)
        self.assertIn("learning", patterns_found)
        self.assertIn(r"\btest\b", patterns_found)

    def test_case_insensitive_matching(self):
        title = "My FIRST CONTRIBUTION to Django"
        body = ""
        issues = check_pr_quality(title, body)

        tutorial_issue = next(
            issue for issue in issues if issue.type == IssueType.TUTORIAL
        )
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].matched_text, "FIRST CONTRIBUTION")

    def test_toast_pattern_high_confidence(self):
        title = "Fixed bug #123"
        body = "This is a toast notification fix"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)  # Only tutorial issue, no missing ticket
        tutorial_issue = issues[0]
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].pattern, "toast")
        self.assertEqual(tutorial_issue.matches[0].location, Location.BODY)


class TestGenerateActions(unittest.TestCase):
    """Test the generate_actions function"""

    def test_no_issues_returns_no_action(self):
        actions = generate_actions([])
        self.assertEqual(len(actions), 1)
        self.assertIsInstance(actions[0], NoAction)

    def test_missing_ticket_only(self):
        issues = [
            QualityIssue(
                type=IssueType.MISSING_TICKET,
                severity=Severity.HIGH,
                message="Missing Trac ticket reference",
                matches=[],
            )
        ]
        actions = generate_actions(issues)

        # Should have label + comment (no close for missing ticket only)
        self.assertEqual(len(actions), 2)
        self.assertIsInstance(actions[0], LabelPR)
        self.assertIsInstance(actions[1], CommentOnPR)
        self.assertEqual(actions[0].label, "possibly-tutorial-pr")
        self.assertIn("Missing Trac ticket reference", actions[1].comment)
        self.assertNotIn("automatically closed", actions[1].comment)

    def test_tutorial_issue_auto_close(self):
        matches = [
            PatternMatch(
                "first contribution",
                "first contribution",
                Location.TITLE,
                "my first contribution",
            )
        ]
        issues = [
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="Tutorial PR",
                matches=matches,
            )
        ]
        actions = generate_actions(issues)

        # Should have label + close + comment
        self.assertEqual(len(actions), 3)
        self.assertIsInstance(actions[0], LabelPR)
        self.assertIsInstance(actions[1], ClosePR)
        self.assertIsInstance(actions[2], CommentOnPR)
        self.assertIn("automatically closed", actions[2].comment)

    def test_tutorial_issue_no_auto_close(self):
        matches = [PatternMatch("test", "test", Location.TITLE, "test context")]
        issues = [
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="Tutorial PR",
                matches=matches,
            )
        ]
        actions = generate_actions(issues)

        # Should have label + comment (no close for low confidence)
        self.assertEqual(len(actions), 2)
        self.assertIsInstance(actions[0], LabelPR)
        self.assertIsInstance(actions[1], CommentOnPR)
        self.assertNotIn("automatically closed", actions[1].comment)

    def test_multiple_issues_with_matches(self):
        matches = [
            PatternMatch("first pr", "first pr", Location.TITLE, "my first pr"),
            PatternMatch("learning", "learning", Location.BODY, "I am learning Django"),
        ]
        issues = [
            QualityIssue(
                type=IssueType.MISSING_TICKET,
                severity=Severity.HIGH,
                message="Missing ticket",
                matches=[],
            ),
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="Tutorial PR",
                matches=matches,
            ),
        ]
        actions = generate_actions(issues)

        # Should auto-close due to multiple tutorial matches
        self.assertEqual(len(actions), 3)
        action_types = [type(action).__name__ for action in actions]
        self.assertIn("LabelPR", action_types)
        self.assertIn("ClosePR", action_types)
        self.assertIn("CommentOnPR", action_types)

        # Check comment includes both issues and match details
        comment_action = next(a for a in actions if isinstance(a, CommentOnPR))
        self.assertIn("Missing ticket", comment_action.comment)
        self.assertIn("Tutorial PR", comment_action.comment)
        self.assertIn("first pr", comment_action.comment)
        self.assertIn("learning", comment_action.comment)
        self.assertIn("title", comment_action.comment)
        self.assertIn("body", comment_action.comment)

    def test_comment_formatting(self):
        matches = [
            PatternMatch("toast", "toast", Location.BODY, "this is a toast example")
        ]
        issues = [
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="Tutorial-like PR detected",
                matches=matches,
            )
        ]
        actions = generate_actions(issues)

        comment_action = next(a for a in actions if isinstance(a, CommentOnPR))
        comment = comment_action.comment

        # Check comment structure
        self.assertIn("## PR Quality Check ⚠️", comment)
        self.assertIn("### Tutorial-like PR detected (Severity: medium)", comment)
        self.assertIn("Matches found:", comment)
        self.assertIn("- In body: `this is a toast example`", comment)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
