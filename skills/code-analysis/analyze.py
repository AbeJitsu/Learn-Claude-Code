#!/usr/bin/env python3
"""
Code Readability Analyzer

What: Checks if code is accessible to non-developers
Why: Ensures code can be understood by everyone on the team, not just developers
How: Analyzes naming, comments, jargon, and documentation to score readability

This tool helps teams write code that managers, stakeholders, and new team members
can understand without needing deep programming knowledge.
"""

# Import required libraries
import argparse  # For command-line argument parsing
import os        # For file system operations
import re        # For pattern matching in code
import json      # For JSON output format
from pathlib import Path        # For file path handling
from typing import Dict, List, Tuple  # For type hints

# What: Common technical jargon that needs explanation
# Why: Non-developers won't understand these terms
# How: We flag these in comments unless they're followed by an explanation
TECHNICAL_JARGON = [
    'API', 'REST', 'CRUD', 'DTO', 'JSON', 'XML', 'HTTP', 'SQL',
    'OAuth', 'JWT', 'PKCE', 'async', 'await', 'promise', 'callback',
    'middleware', 'endpoint', 'payload', 'schema', 'ORM', 'migration',
    'refactor', 'deprecated', 'polymorphism', 'inheritance', 'instantiate',
    'serialize', 'deserialize', 'hydrate', 'repository', 'factory',
    'singleton', 'dependency injection', 'IoC', 'webhook', 'CORS'
]

# What: Cryptic abbreviations commonly used in variable names
# Why: These are truly unclear to non-developers and should be spelled out
# How: We check variable names against this list (only the most cryptic ones)
CRYPTIC_ABBREVIATIONS = [
    r'\b(usr)(_|[A-Z])',  # usr - should be "user"
    r'\b(tkn|tok)(_|[A-Z])',  # tkn, tok - should be "token"
    r'\b(cfg|conf)(_|[A-Z])',  # cfg, conf - should be "config"
    r'\b(ctx)(_|[A-Z])',  # ctx - should be "context"
    r'\b(tmp|temp)(_|[A-Z])',  # tmp, temp - should be descriptive
    r'\b(idx)(_|[A-Z])',  # idx - should be "index"
    r'\b(cnt)(_|[A-Z])',  # cnt - should be "count"
    r'\b(proc)(_|[A-Z])',  # proc - should be "process"
    r'\b(calc)(_|[A-Z])',  # calc - should be "calculate"
]

# Note: Removed common abbreviations that are widely understood:
# - num, str, len (standard and clear in context)
# - msg, req, res, resp (common in web/API contexts, API = Application Programming Interface, how programs talk to each other)
# - arr, obj, val (commonly understood programming terms)

# What: Supported file extensions and their languages
# Why: We need to know which language we're analyzing
# How: Map file extension to language name
SUPPORTED_EXTENSIONS = {
    '.py': 'python',      # Python files
    '.js': 'javascript',  # JavaScript files
    '.ts': 'typescript',  # TypeScript files
    '.jsx': 'javascript', # React JavaScript files
    '.tsx': 'typescript', # React TypeScript files
    '.java': 'java',      # Java files
    '.go': 'go',          # Go files
    '.rb': 'ruby',        # Ruby files
    '.php': 'php',        # PHP files
}


class ReadabilityIssue:
    """
    What: Represents a single readability issue found in code
    Why: We need to track and report each issue with context
    How: Stores line number, type of issue, and suggested fix
    """
    def __init__(self, line_num: int, issue_type: str, description: str,
                 code_snippet: str = "", suggestion: str = ""):
        """
        What: Initialize a new readability issue
        Why: Set up all the details about what's wrong
        How: Store the line number, issue type, description, and suggestion
        """
        self.line_num = line_num
        self.issue_type = issue_type
        self.description = description
        self.code_snippet = code_snippet
        self.suggestion = suggestion

    def to_dict(self):
        """
        What: Convert issue to dictionary format
        Why: Makes it easy to output as JSON or display in reports
        How: Create dict with all issue details
        """
        return {
            'line': self.line_num,
            'type': self.issue_type,
            'description': self.description,
            'code': self.code_snippet,
            'suggestion': self.suggestion
        }


class CodeReadabilityAnalyzer:
    """
    What: Main analyzer that checks code readability
    Why: Ensures code is accessible to non-developers
    How: Runs multiple checks on code files and generates a report
    """

    def __init__(self, strictness: str = 'standard'):
        self.strictness = strictness
        self.issues: List[ReadabilityIssue] = []

    def _strip_strings_and_comments(self, line: str) -> str:
        """
        What: Remove string literals and comments from a line
        Why: We only want to check actual code, not examples in strings/comments
        How: Use regex to strip quoted strings and comment markers
        """
        # Remove string literals (both single and double quotes)
        # This handles most common cases but not all edge cases
        line_cleaned = re.sub(r'"[^"]*"', '""', line)  # Remove double-quoted strings
        line_cleaned = re.sub(r"'[^']*'", "''", line_cleaned)  # Remove single-quoted strings

        # Remove comments (anything after # or //)
        line_cleaned = re.sub(r'#.*$', '', line_cleaned)
        line_cleaned = re.sub(r'//.*$', '', line_cleaned)

        return line_cleaned

    def analyze_file(self, file_path: str) -> Dict:
        """
        What: Analyze a single file for readability issues
        Why: Check if non-developers can understand this code
        How: Run all readability checks and collect issues
        """
        if not os.path.exists(file_path):
            return {'error': f'File not found: {file_path}'}

        # Check if file type is supported
        ext = Path(file_path).suffix
        if ext not in SUPPORTED_EXTENSIONS:
            return {'error': f'Unsupported file type: {ext}'}

        # Read the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return {'error': f'Could not read file: {str(e)}'}

        # Reset issues for this file
        self.issues = []

        # Run all checks
        self._check_cryptic_names(lines)
        self._check_comments(lines)
        self._check_jargon_in_comments(lines)
        self._check_section_documentation(lines)

        # Calculate readability score
        score = self._calculate_readability_score(len(lines))

        return {
            'file': file_path,
            'language': SUPPORTED_EXTENSIONS[ext],
            'total_lines': len(lines),
            'issues_found': len(self.issues),
            'readability_score': score,
            'issues': [issue.to_dict() for issue in self.issues],
            'summary': self._generate_summary(score)
        }

    def _check_cryptic_names(self, lines: List[str]):
        """
        What: Check for cryptic variable and function names
        Why: Non-developers can't understand abbreviations
        How: Use regex patterns to detect common abbreviations in actual code only
        """
        in_docstring = False
        docstring_marker = None

        # Loop through each line in the file
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstring blocks (""" or ''')
            # We don't want to check code examples inside docstrings
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    # Starting a docstring
                    in_docstring = True
                    docstring_marker = '"""' if '"""' in line else "'''"
                    # Check if it ends on the same line (single-line docstring)
                    if line.count(docstring_marker) >= 2:
                        in_docstring = False
                else:
                    # Ending a docstring
                    in_docstring = False
                continue

            # Skip if inside docstring (don't check documentation text)
            if in_docstring:
                continue

            # Skip comment-only lines (already just documentation)
            if stripped.startswith('#') or stripped.startswith('//'):
                continue

            # Clean the line - remove strings and comments before checking
            # This prevents flagging examples like "usr_tkn" in comments
            line_cleaned = self._strip_strings_and_comments(line)

            # Skip if nothing left after cleaning (line was all comments/strings)
            if not line_cleaned.strip():
                continue

            # Check for cryptic abbreviations in the cleaned line
            # These patterns match things like usr_, tkn_, cfg_, etc.
            for pattern in CRYPTIC_ABBREVIATIONS:
                matches = re.finditer(pattern, line_cleaned)
                for match in matches:
                    # Extract the variable name context from the cleaned line
                    start = max(0, match.start() - 10)
                    end = min(len(line_cleaned), match.end() + 20)
                    snippet = line_cleaned[start:end].strip()

                    self.issues.append(ReadabilityIssue(
                        line_num=line_num,
                        issue_type='cryptic_naming',
                        description='Variable name uses unclear abbreviation',
                        code_snippet=snippet,
                        suggestion='Use full, descriptive names like "userToken" instead of "usr_tkn"'
                    ))

            # Check for single-letter variables (except in loops) in cleaned line
            if not re.search(r'\b(for|while)\b', line_cleaned):
                single_letters = re.finditer(r'\b([a-z])\s*=', line_cleaned)
                for match in single_letters:
                    if match.group(1) not in ['i', 'j', 'k']:  # Common loop counters
                        self.issues.append(ReadabilityIssue(
                            line_num=line_num,
                            issue_type='cryptic_naming',
                            description=f'Single-letter variable "{match.group(1)}" is not descriptive',
                            code_snippet=line.strip(),
                            suggestion='Use descriptive names that explain what the variable holds'
                        ))

    def _check_comments(self, lines: List[str]):
        """
        What: Check if code has adequate comments
        Why: Comments help non-developers understand what's happening
        How: Count code lines vs comment lines, flag uncommented sections
        """
        # Initialize counters for tracking comment coverage
        code_line_count = 0
        comment_line_count = 0
        uncommented_code_lines = 0

        # Go through each line and categorize it
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip empty lines (don't count these)
            if not stripped:
                continue

            # Check if it's a comment
            # We look for common comment markers across languages
            is_comment = (stripped.startswith('#') or
                         stripped.startswith('//') or
                         stripped.startswith('/*') or
                         stripped.startswith('*'))

            if is_comment:
                comment_line_count += 1
                uncommented_code_lines = 0  # Reset counter when we hit a comment
            elif stripped:
                code_line_count += 1
                uncommented_code_lines += 1

                # Flag sections with too much code without comments
                # 10+ lines without comments is hard for non-devs to follow
                if uncommented_code_lines > 10 and self.strictness in ['standard', 'strict']:
                    self.issues.append(ReadabilityIssue(
                        line_num=line_num,
                        issue_type='missing_comments',
                        description='Large section of code (10+ lines) without explanatory comments',
                        code_snippet=f'Lines {line_num - 9} to {line_num}',
                        suggestion='Add comments explaining what this section does and why'
                    ))
                    uncommented_code_lines = 0  # Reset after flagging

        # Overall comment ratio check
        # We want at least 20% of lines to be comments
        if code_line_count > 0:
            comment_ratio = comment_line_count / code_line_count
            if comment_ratio < 0.2:  # Less than 20% comments
                self.issues.append(ReadabilityIssue(
                    line_num=0,
                    issue_type='insufficient_comments',
                    description=f'Low comment ratio: {comment_ratio:.1%} (aim for at least 20%)',
                    suggestion='Add more comments explaining what the code does, why it exists, and how it works'
                ))

    def _check_jargon_in_comments(self, lines: List[str]):
        """
        What: Check if comments contain unexplained technical jargon
        Why: Non-developers won't understand technical terms
        How: Look for jargon words in comments without explanations
        """
        # Loop through each line looking for technical terms
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Only check comments (not code)
            if not (stripped.startswith('#') or stripped.startswith('//')):
                continue

            # Remove comment markers to get the actual text
            comment_text = re.sub(r'^[#/]+\s*', '', stripped)

            # Check for jargon terms from our list
            # Use word boundaries to avoid matching ORM = Object-Relational Mapping inside words like "format"
            for jargon in TECHNICAL_JARGON:
                # Only match whole words, not substrings
                pattern = r'\b' + re.escape(jargon.lower()) + r'\b'
                if re.search(pattern, comment_text.lower()):
                    # Check if there's an explanation
                    # Look for = sign, "is", "means", or : which usually introduce explanations
                    has_explanation = any(marker in comment_text for marker in ['=', ' is ', ' means ', ':'])

                    # Flag jargon without explanation
                    if not has_explanation:
                        self.issues.append(ReadabilityIssue(
                            line_num=line_num,
                            issue_type='unexplained_jargon',
                            description=f'Technical term "{jargon}" used without explanation',
                            code_snippet=comment_text,
                            suggestion=f'Add explanation like: "{jargon} = [plain English explanation]"'
                        ))

    def _check_section_documentation(self, lines: List[str]):
        """
        What: Check if code sections have What/Why/How documentation
        Why: This format helps non-developers understand purpose and context
        How: Look for function/class definitions and check for proper docs
        """
        # Patterns for function/class definitions
        definition_patterns = [
            r'^\s*def\s+\w+',  # Python function
            r'^\s*class\s+\w+',  # Python/Java/etc class
            r'^\s*function\s+\w+',  # JavaScript function
            r'^\s*const\s+\w+\s*=\s*\(.*\)\s*=>',  # Arrow function
        ]

        in_function = False
        function_line = 0

        for line_num, line in enumerate(lines, 1):
            # Check if this is a function/class definition
            for pattern in definition_patterns:
                if re.search(pattern, line):
                    in_function = True
                    function_line = line_num

                    # Look for What/Why/How documentation in docstring (next 10 lines after function def)
                    has_what = False
                    has_why = False
                    has_how = False

                    # Check next 10 lines for documentation (docstring comes after def)
                    end = min(len(lines), line_num + 10)
                    for check_line in lines[line_num:end]:
                        if 'what:' in check_line.lower():
                            has_what = True
                        if 'why:' in check_line.lower():
                            has_why = True
                        if 'how:' in check_line.lower():
                            has_how = True

                    # Only flag if missing all three (lenient) or any (strict)
                    if self.strictness == 'strict':
                        if not has_what:
                            self.issues.append(ReadabilityIssue(
                                line_num=function_line,
                                issue_type='missing_documentation',
                                description='Function/class missing "What" documentation',
                                code_snippet=line.strip(),
                                suggestion='Add comment: "What: [describe what this does]"'
                            ))
                        if not has_why:
                            self.issues.append(ReadabilityIssue(
                                line_num=function_line,
                                issue_type='missing_documentation',
                                description='Function/class missing "Why" documentation',
                                code_snippet=line.strip(),
                                suggestion='Add comment: "Why: [explain the business reason]"'
                            ))
                        if not has_how:
                            self.issues.append(ReadabilityIssue(
                                line_num=function_line,
                                issue_type='missing_documentation',
                                description='Function/class missing "How" documentation',
                                code_snippet=line.strip(),
                                suggestion='Add comment: "How: [explain how it connects to the system]"'
                            ))
                    elif not (has_what or has_why or has_how):
                        self.issues.append(ReadabilityIssue(
                            line_num=function_line,
                            issue_type='missing_documentation',
                            description='Function/class lacks What/Why/How documentation',
                            code_snippet=line.strip(),
                            suggestion='Add comments explaining: What it does, Why it exists, How it fits in'
                        ))

    def _calculate_readability_score(self, total_lines: int) -> int:
        """
        What: Calculate a readability score from 0-100
        Why: Give users a quick sense of how readable their code is
        How: Start at 100, deduct points for each issue type
        """
        # Start with a perfect score
        score = 100

        # Handle edge case of empty file
        if total_lines == 0:
            return 0

        # Deduct points based on issue density
        # More issues relative to file size means lower score
        issue_density = len(self.issues) / total_lines

        # Categorize issues and apply different weights
        # More serious issues (like missing comments) deduct more points
        issue_weights = {
            'cryptic_naming': 3,           # Unclear names hurt readability
            'missing_comments': 5,          # Uncommented code is hard to follow
            'insufficient_comments': 10,    # Overall low comment ratio is serious
            'unexplained_jargon': 4,        # Jargon blocks non-dev understanding
            'missing_documentation': 5,     # Missing What/Why/How hurts comprehension
        }

        # Deduct points for each issue found
        for issue in self.issues:
            weight = issue_weights.get(issue.issue_type, 2)
            score -= weight

        # Floor at 0 (can't go negative)
        return max(0, score)

    def _generate_summary(self, score: int) -> str:
        """
        What: Generate a human-readable summary
        Why: Help users understand what the score means
        How: Return plain English assessment based on score
        """
        if score >= 90:
            return "Excellent! This code is very accessible to non-developers."
        elif score >= 75:
            return "Good readability. Minor improvements would help non-developers."
        elif score >= 60:
            return "Moderate readability. Several areas need clearer explanations."
        elif score >= 40:
            return "Below average. Non-developers will struggle with this code."
        else:
            return "Poor readability. Major improvements needed for accessibility."


def main():
    """
    What: Command-line entry point for the analyzer
    Why: Allow the skill to execute this script from bash
    How: Parse arguments and run the analysis
    """
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(
        description='Analyze code readability for non-developers'
    )

    # Define all the command-line options
    parser.add_argument('--path', required=True, help='Path to file or directory to analyze')
    parser.add_argument('--focus', default='all',
                       choices=['naming', 'comments', 'jargon', 'documentation', 'all'],
                       help='Focus area for analysis')
    parser.add_argument('--audience', default='non-dev',
                       choices=['non-dev', 'new-team-member', 'stakeholder', 'everyone'],
                       help='Target audience for readability')
    parser.add_argument('--strictness', default='standard',
                       choices=['lenient', 'standard', 'strict'],
                       help='How strict the analysis should be')
    parser.add_argument('--format', default='human',
                       choices=['human', 'json'],
                       help='Output format')

    # Parse the arguments provided by the user
    args = parser.parse_args()

    # Create analyzer with the requested strictness level
    analyzer = CodeReadabilityAnalyzer(strictness=args.strictness)

    # Analyze the file and get results
    result = analyzer.analyze_file(args.path)

    # Output results in the requested format
    if args.format == 'json':
        # JSON format (JavaScript Object Notation = data format computers can easily read) - useful for tools and scripts
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output format
        # Print header with file information
        print(f"\n{'='*60}")
        print(f"Code Readability Analysis")
        print(f"{'='*60}\n")
        print(f"File: {result.get('file', 'N/A')}")
        print(f"Language: {result.get('language', 'N/A')}")
        print(f"Total Lines: {result.get('total_lines', 0)}")
        print(f"Issues Found: {result.get('issues_found', 0)}")
        print(f"Readability Score: {result.get('readability_score', 0)}/100")
        print(f"\nSummary: {result.get('summary', 'N/A')}\n")

        # Print detailed issues if any were found
        if result.get('issues'):
            print(f"{'='*60}")
            print("Issues Found:")
            print(f"{'='*60}\n")

            # Loop through each issue and display details
            for issue in result['issues']:
                print(f"Line {issue['line']}: {issue['description']}")
                if issue.get('code'):
                    print(f"  Code: {issue['code']}")
                if issue.get('suggestion'):
                    print(f"  💡 Suggestion: {issue['suggestion']}")
                print()


if __name__ == '__main__':
    main()
