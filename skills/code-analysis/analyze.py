#!/usr/bin/env python3
"""
Code Readability Analyzer

What: Checks if code is accessible to non-developers
Why: Ensures code can be understood by everyone on the team, not just developers
How: Analyzes naming, comments, jargon, and documentation to score readability
"""

import argparse
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

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
# Why: These are unclear to non-developers and should be spelled out
# How: We check variable names against this list
CRYPTIC_ABBREVIATIONS = [
    r'\b(usr|u)(_|[A-Z])',  # usr, u_ - should be "user"
    r'\b(tkn|tok)(_|[A-Z])',  # tkn, tok - should be "token"
    r'\b(msg)(_|[A-Z])',  # msg - should be "message"
    r'\b(cfg|conf)(_|[A-Z])',  # cfg, conf - should be "config"
    r'\b(ctx)(_|[A-Z])',  # ctx - should be "context"
    r'\b(req)(_|[A-Z])',  # req - should be "request"
    r'\b(res|resp)(_|[A-Z])',  # res, resp - should be "response"
    r'\b(arr)(_|[A-Z])',  # arr - should be "array" or better name
    r'\b(obj)(_|[A-Z])',  # obj - should be specific name
    r'\b(tmp|temp)(_|[A-Z])',  # tmp, temp - should be descriptive
    r'\b(val)(_|[A-Z])',  # val - should be "value" or better
    r'\b(idx)(_|[A-Z])',  # idx - should be "index"
    r'\b(len)(_|[A-Z])',  # len - should be "length"
    r'\b(num)(_|[A-Z])',  # num - should be "number" or specific
    r'\b(str)(_|[A-Z])',  # str - should be descriptive
    r'\b(cnt)(_|[A-Z])',  # cnt - should be "count"
    r'\b(proc)(_|[A-Z])',  # proc - should be "process"
    r'\b(calc)(_|[A-Z])',  # calc - should be "calculate"
]

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
}


class ReadabilityIssue:
    """
    What: Represents a single readability issue found in code
    Why: We need to track and report each issue with context
    How: Stores line number, type of issue, and suggested fix
    """
    def __init__(self, line_num: int, issue_type: str, description: str,
                 code_snippet: str = "", suggestion: str = ""):
        self.line_num = line_num
        self.issue_type = issue_type
        self.description = description
        self.code_snippet = code_snippet
        self.suggestion = suggestion

    def to_dict(self):
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
        How: Use regex patterns to detect common abbreviations
        """
        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue

            # Check for cryptic abbreviations
            for pattern in CRYPTIC_ABBREVIATIONS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Extract the variable name context
                    start = max(0, match.start() - 10)
                    end = min(len(line), match.end() + 20)
                    snippet = line[start:end].strip()

                    self.issues.append(ReadabilityIssue(
                        line_num=line_num,
                        issue_type='cryptic_naming',
                        description='Variable name uses unclear abbreviation',
                        code_snippet=snippet,
                        suggestion='Use full, descriptive names like "userToken" instead of "usr_tkn"'
                    ))

            # Check for single-letter variables (except in loops)
            if not re.search(r'\b(for|while)\b', line):
                single_letters = re.finditer(r'\b([a-z])\s*=', line)
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
        code_line_count = 0
        comment_line_count = 0
        uncommented_code_lines = 0

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Check if it's a comment
            is_comment = (stripped.startswith('#') or
                         stripped.startswith('//') or
                         stripped.startswith('/*') or
                         stripped.startswith('*'))

            if is_comment:
                comment_line_count += 1
                uncommented_code_lines = 0  # Reset counter
            elif stripped:
                code_line_count += 1
                uncommented_code_lines += 1

                # Flag sections with too much code without comments
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
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Only check comments
            if not (stripped.startswith('#') or stripped.startswith('//')):
                continue

            # Remove comment markers
            comment_text = re.sub(r'^[#/]+\s*', '', stripped)

            # Check for jargon
            for jargon in TECHNICAL_JARGON:
                if jargon.lower() in comment_text.lower():
                    # Check if there's an explanation (= sign or "is" or "means")
                    has_explanation = any(marker in comment_text for marker in ['=', ' is ', ' means ', ':'])

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

                    # Look for What/Why/How documentation in previous lines
                    has_what = False
                    has_why = False
                    has_how = False

                    # Check previous 10 lines for documentation
                    start = max(0, line_num - 11)
                    for check_line in lines[start:line_num - 1]:
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
        score = 100

        if total_lines == 0:
            return 0

        # Deduct points based on issue density
        issue_density = len(self.issues) / total_lines

        # Categorize issues and apply different weights
        issue_weights = {
            'cryptic_naming': 3,
            'missing_comments': 5,
            'insufficient_comments': 10,
            'unexplained_jargon': 4,
            'missing_documentation': 5,
        }

        for issue in self.issues:
            weight = issue_weights.get(issue.issue_type, 2)
            score -= weight

        # Floor at 0
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
    parser = argparse.ArgumentParser(
        description='Analyze code readability for non-developers'
    )
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

    args = parser.parse_args()

    # Create analyzer
    analyzer = CodeReadabilityAnalyzer(strictness=args.strictness)

    # Analyze the file
    result = analyzer.analyze_file(args.path)

    # Output results
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"Code Readability Analysis")
        print(f"{'='*60}\n")
        print(f"File: {result.get('file', 'N/A')}")
        print(f"Language: {result.get('language', 'N/A')}")
        print(f"Total Lines: {result.get('total_lines', 0)}")
        print(f"Issues Found: {result.get('issues_found', 0)}")
        print(f"Readability Score: {result.get('readability_score', 0)}/100")
        print(f"\nSummary: {result.get('summary', 'N/A')}\n")

        if result.get('issues'):
            print(f"{'='*60}")
            print("Issues Found:")
            print(f"{'='*60}\n")

            for issue in result['issues']:
                print(f"Line {issue['line']}: {issue['description']}")
                if issue.get('code'):
                    print(f"  Code: {issue['code']}")
                if issue.get('suggestion'):
                    print(f"  💡 Suggestion: {issue['suggestion']}")
                print()


if __name__ == '__main__':
    main()
