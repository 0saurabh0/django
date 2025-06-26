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
    CommentOnPR,
    ClosePR,
)


class TestGetContext(unittest.TestCase):
    """Test the get_context function"""

    def test_get_context_normal_case(self):
        text = "This is a test string for context extraction"
        result = get_context(text, match_start=10, match_end=14, context_chars=5)
        self.assertEqual(result, "is a test stri")

    def test_get_context_at_start(self):
        text = "test string"
        result = get_context(text, match_start=0, match_end=4, context_chars=5)
        self.assertEqual(result, "test stri")

    def test_get_context_at_end(self):
        text = "string test"
        result = get_context(text, match_start=7, match_end=11, context_chars=5)
        self.assertEqual(result, "ring test")

    def test_get_context_short_text(self):
        text = "test"
        result = get_context(text, match_start=0, match_end=4, context_chars=10)
        self.assertEqual(result, "test")

    def test_get_context_strips_whitespace(self):
        text = "  test string  "
        result = get_context(text, match_start=2, match_end=6, context_chars=2)
        self.assertEqual(result, "test s")

    def test_get_context_exact_boundaries(self):
        text = "abcdefghij"
        result = get_context(
            text, match_start=3, match_end=6, context_chars=2
        )  # "def" with 2 chars context
        # start = max(0, 3-2) = 1, end = min(10, 6+2) = 8
        # text[1:8] = "bcdefgh"
        self.assertEqual(result, "bcdefgh")

    def test_get_context_zero_context(self):
        text = "hello world"
        result = get_context(text, match_start=6, match_end=11, context_chars=0)
        self.assertEqual(result, "world")


class TestQualityIssue(unittest.TestCase):
    """Test the QualityIssue dataclass and its methods"""

    def test_should_auto_close_non_tutorial(self):
        # Create an issue and manually set its type to something that's not TUTORIAL
        issue = QualityIssue(
            type=IssueType.TUTORIAL,
            severity=Severity.HIGH,
            message="Test issue",
            matches=[],
        )
        # Manually override the type for testing
        issue.type = "not_tutorial"
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
            PatternMatch(r"\btest\b", "test", Location.TITLE, "test context"),
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
                "99999",
                "99999",
                Location.TITLE,
                "test ticket #99999",
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
        matches = [PatternMatch(r"\btest\b", "test", Location.TITLE, "test context")]
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
        self.assertEqual(len(issues), 0)

    def test_tutorial_pattern_in_title(self):
        title = "My learning experience with Django"
        body = "This is a real fix"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, IssueType.TUTORIAL)

        # Check tutorial issue details
        tutorial_issue = issues[0]
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].pattern, "learning")
        self.assertEqual(tutorial_issue.matches[0].location, Location.TITLE)

    def test_high_confidence_pattern_in_body(self):
        title = "Fix authentication bug #12345"
        body = "This is a toast notification. I followed some guide."
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, IssueType.TUTORIAL)

        # Should find "toast" (high confidence, checked in body)
        self.assertEqual(len(issues[0].matches), 1)
        self.assertEqual(issues[0].matches[0].pattern, "toast")
        self.assertEqual(issues[0].matches[0].location, Location.BODY)

    def test_low_confidence_pattern_not_in_body(self):
        title = "Add test for authentication"
        body = "This adds a comprehensive test suite for the authentication module"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)  # Only tutorial issue
        tutorial_issue = issues[0]

        # Should only find "test" in title, not in body (low confidence)
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].location, Location.TITLE)
        self.assertEqual(tutorial_issue.matches[0].pattern, r"\btest\b")

    def test_multiple_patterns_in_title(self):
        title = "My tutorial about learning Django test"
        body = "This is a real change"
        issues = check_pr_quality(title, body)

        tutorial_issue = next(
            issue for issue in issues if issue.type == IssueType.TUTORIAL
        )
        self.assertEqual(len(tutorial_issue.matches), 3)

        patterns_found = [match.pattern for match in tutorial_issue.matches]
        self.assertIn("tutorial", patterns_found)
        self.assertIn("learning", patterns_found)
        self.assertIn(r"\btest\b", patterns_found)

    def test_case_insensitive_matching(self):
        title = "My LEARNING experience with Django"
        body = ""
        issues = check_pr_quality(title, body)

        tutorial_issue = next(
            issue for issue in issues if issue.type == IssueType.TUTORIAL
        )
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].matched_text, "LEARNING")

    def test_toast_pattern_high_confidence(self):
        title = "Fixed bug #123"
        body = "This is a toast notification fix"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)
        tutorial_issue = issues[0]
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].pattern, "toast")
        self.assertEqual(tutorial_issue.matches[0].location, Location.BODY)

    def test_99999_pattern_high_confidence(self):
        title = "Test PR #99999"
        body = "This is just a test"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)
        tutorial_issue = issues[0]
        self.assertEqual(len(tutorial_issue.matches), 2)

        patterns_found = [match.pattern for match in tutorial_issue.matches]
        self.assertIn("99999", patterns_found)
        self.assertIn(r"\btest\b", patterns_found)

    def test_getting_started_pattern(self):
        title = "Getting started with Django #12345"
        body = "This is my first attempt"
        issues = check_pr_quality(title, body)

        self.assertEqual(len(issues), 1)
        tutorial_issue = issues[0]
        self.assertEqual(len(tutorial_issue.matches), 1)
        self.assertEqual(tutorial_issue.matches[0].pattern, "getting started")
        self.assertEqual(tutorial_issue.matches[0].location, Location.TITLE)


class TestGenerateActions(unittest.TestCase):
    """Test the generate_actions function"""

    def test_no_issues_returns_no_action(self):
        actions = generate_actions([])
        self.assertEqual(len(actions), 1)
        self.assertIsInstance(actions[0], NoAction)

    def test_tutorial_issue_auto_close(self):
        matches = [
            PatternMatch(
                "99999",
                "99999",
                Location.TITLE,
                "test PR #99999",
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

        # Should have close + comment (no label - handled by labels.yml)
        self.assertEqual(len(actions), 2)
        self.assertIsInstance(actions[0], ClosePR)
        self.assertIsInstance(actions[1], CommentOnPR)
        self.assertIn("automatically closed", actions[1].comment)

    def test_tutorial_issue_no_auto_close(self):
        matches = [PatternMatch(r"\btest\b", "test", Location.TITLE, "test context")]
        issues = [
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="Tutorial PR",
                matches=matches,
            )
        ]
        actions = generate_actions(issues)

        # Should have comment only (no close for low confidence, no label)
        self.assertEqual(len(actions), 1)
        self.assertIsInstance(actions[0], CommentOnPR)
        self.assertNotIn("automatically closed", actions[0].comment)

    def test_multiple_issues_with_matches(self):
        matches = [
            PatternMatch("tutorial", "tutorial", Location.TITLE, "my tutorial"),
            PatternMatch("learning", "learning", Location.BODY, "I am learning Django"),
        ]
        issues = [
            QualityIssue(
                type=IssueType.TUTORIAL,
                severity=Severity.MEDIUM,
                message="Tutorial PR",
                matches=matches,
            ),
        ]
        actions = generate_actions(issues)

        # Should auto-close due to multiple tutorial matches
        self.assertEqual(len(actions), 2)
        action_types = [type(action).__name__ for action in actions]
        self.assertIn("ClosePR", action_types)
        self.assertIn("CommentOnPR", action_types)

        # Check comment includes match details
        comment_action = next(a for a in actions if isinstance(a, CommentOnPR))
        self.assertIn("Tutorial PR", comment_action.comment)
        self.assertIn("tutorial", comment_action.comment)
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
    unittest.main(verbosity=2)
