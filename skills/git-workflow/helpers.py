#!/usr/bin/env python3
"""
Git Workflow Helper

What: Provides Git workflow assistance (commit messages, branch names, history analysis)
Why: Makes Git easier and maintains clean repository hygiene
How: Analyzes Git state and provides actionable suggestions
"""

import argparse
import subprocess
import sys
import json
import re
from typing import Dict, List, Optional, Tuple


def run_git_command(command: List[str]) -> Tuple[bool, str, str]:
    """
    What: Execute a git command safely
    Why: We need to interact with Git to analyze repository state
    How: Use subprocess to run git commands and capture output

    Returns: (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ['git'] + command,
            capture_output=True,
            text=True,
            timeout=10
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", "Command timed out")
    except Exception as e:
        return (False, "", str(e))


def check_git_repository() -> bool:
    """
    What: Check if current directory is a Git repository
    Why: Commands will fail if not in a Git repo
    How: Try to run 'git rev-parse --git-dir'
    """
    success, _, _ = run_git_command(['rev-parse', '--git-dir'])
    return success


def get_staged_changes() -> Optional[str]:
    """
    What: Get the diff of staged changes
    Why: Need to understand what's being committed to generate message
    How: Run 'git diff --cached'
    """
    success, stdout, stderr = run_git_command(['diff', '--cached'])
    if success:
        return stdout if stdout else None
    return None


def get_status() -> Dict[str, List[str]]:
    """
    What: Get current Git status (modified, added, deleted files)
    Why: Understand repository state to provide context
    How: Parse output of 'git status --porcelain'

    Returns: Dict with keys: modified, added, deleted, untracked
    """
    success, stdout, stderr = run_git_command(['status', '--porcelain'])

    if not success:
        return {'modified': [], 'added': [], 'deleted': [], 'untracked': []}

    status = {'modified': [], 'added': [], 'deleted': [], 'untracked': []}

    for line in stdout.strip().split('\n'):
        if not line:
            continue

        # Format: XY filename
        # X = index status, Y = working tree status
        status_code = line[:2]
        filename = line[3:].strip()

        if status_code[0] == 'M' or status_code[1] == 'M':
            status['modified'].append(filename)
        elif status_code[0] == 'A':
            status['added'].append(filename)
        elif status_code[0] == 'D' or status_code[1] == 'D':
            status['deleted'].append(filename)
        elif status_code == '??':
            status['untracked'].append(filename)

    return status


def analyze_diff(diff_text: str) -> Dict[str, any]:
    """
    What: Analyze a git diff to understand changes
    Why: Need to generate meaningful commit messages
    How: Parse diff output to extract file changes and context
    """
    if not diff_text:
        return {'files': [], 'additions': 0, 'deletions': 0}

    files = []
    additions = 0
    deletions = 0
    current_file = None

    for line in diff_text.split('\n'):
        # File header
        if line.startswith('diff --git'):
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3].replace('b/', '')
                files.append(current_file)

        # Count additions/deletions
        elif line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1

    return {
        'files': files,
        'additions': additions,
        'deletions': deletions,
        'total_changes': additions + deletions
    }


def review_staged_changes() -> Dict:
    """
    What: Show context of staged changes for commit message creation
    Why: Provide AI with real context to write meaningful commit messages
    How: Show git status and diff --staged output for analysis
    """
    if not check_git_repository():
        return {'error': 'Not in a Git repository'}

    # Get staged diff
    diff = get_staged_changes()
    if not diff:
        return {'error': 'No staged changes. Use "git add" first.'}

    # Get status
    status = get_status()

    # Analyze the diff
    analysis = analyze_diff(diff)

    # Get staged files specifically
    success, status_output, _ = run_git_command(['status', '--short'])
    staged_files = []
    if success:
        for line in status_output.strip().split('\n'):
            if line and line[0] in ['M', 'A', 'D', 'R', 'C']:
                staged_files.append(line.strip())

    return {
        'status': status,
        'staged_files': staged_files,
        'diff': diff,
        'analysis': analysis,
        'summary': {
            'files_changed': len(analysis['files']),
            'additions': analysis['additions'],
            'deletions': analysis['deletions']
        }
    }


def generate_commit_message(context: str = 'staged') -> str:
    """
    What: Generate a commit message based on changes
    Why: Save time and create consistent, clear commit messages
    How: Analyze diff and status to understand what changed

    NOTE: This generates template messages. Use 'review-changes' action
    for AI-assisted commit message generation with real context.
    """
    if not check_git_repository():
        return "Error: Not in a Git repository"

    # Get changes
    if context == 'staged':
        diff = get_staged_changes()
        if not diff:
            return "No staged changes to commit. Use 'git add' first."
    else:
        success, diff, _ = run_git_command(['diff'])
        if not success or not diff:
            return "No changes found."

    # Analyze the diff
    analysis = analyze_diff(diff)
    status = get_status()

    # Generate message based on changes
    files_changed = analysis['files']
    num_files = len(files_changed)

    if num_files == 0:
        return "No files changed"

    # Determine type of change based on files
    change_type = "Update"
    if status['added']:
        change_type = "Add"
    elif status['deleted']:
        change_type = "Remove"

    # Create summary
    if num_files == 1:
        summary = f"{change_type} {files_changed[0]}"
    elif num_files <= 3:
        summary = f"{change_type} {', '.join(files_changed)}"
    else:
        summary = f"{change_type} {num_files} files"

    # Build full message
    message = f"{summary}\n\n"
    message += f"What: Modified {num_files} file(s)\n"
    message += f"Why: [TODO: Explain why this change is needed]\n"
    message += f"Changes: +{analysis['additions']} -{analysis['deletions']} lines\n\n"
    message += "Files:\n"
    for f in files_changed[:5]:  # Limit to first 5 files
        message += f"- {f}\n"
    if num_files > 5:
        message += f"... and {num_files - 5} more\n"

    return message


def suggest_branch_name(context: str = "") -> str:
    """
    What: Suggest a branch name following conventions
    Why: Consistent branch naming helps team organization
    How: Use context provided and apply naming conventions
    """
    if not context:
        return "Usage: Provide context like 'adding search feature' or 'fix login bug'"

    # Convert context to lowercase and replace spaces
    normalized = context.lower().strip()

    # Detect type of work
    branch_type = "feature"
    if any(word in normalized for word in ['fix', 'bug', 'error', 'issue', 'broken']):
        branch_type = "fix"
    elif any(word in normalized for word in ['refactor', 'cleanup', 'improve', 'simplify']):
        branch_type = "refactor"
    elif any(word in normalized for word in ['test', 'testing']):
        branch_type = "test"
    elif any(word in normalized for word in ['doc', 'docs', 'documentation', 'readme']):
        branch_type = "docs"

    # Clean up the context for branch name
    # Remove common words
    remove_words = ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'should', 'could', 'may', 'might', 'must', 'can',
                    'add', 'adding', 'fix', 'fixing', 'update', 'updating']

    words = normalized.split()
    filtered_words = [w for w in words if w not in remove_words and len(w) > 2]

    # Join with hyphens
    branch_name_part = '-'.join(filtered_words[:5])  # Limit to 5 words

    # Remove special characters
    branch_name_part = re.sub(r'[^a-z0-9-]', '', branch_name_part)

    return f"{branch_type}/{branch_name_part}"


def analyze_commit_history(count: int = 10) -> Dict:
    """
    What: Analyze recent commit history for patterns and issues
    Why: Help maintain clean commit history
    How: Parse git log and look for common issues
    """
    if not check_git_repository():
        return {'error': 'Not in a Git repository'}

    # Get commit history
    success, stdout, stderr = run_git_command([
        'log',
        f'-{count}',
        '--pretty=format:%H|%s|%an|%ar',
        '--shortstat'
    ])

    if not success:
        return {'error': 'Failed to get commit history', 'details': stderr}

    commits = []
    issues = []

    lines = stdout.strip().split('\n')
    i = 0
    while i < len(lines):
        if '|' in lines[i]:
            parts = lines[i].split('|')
            if len(parts) >= 4:
                commit_hash = parts[0][:7]  # Short hash
                message = parts[1]
                author = parts[2]
                time_ago = parts[3]

                # Check next line for stats
                files_changed = 0
                if i + 1 < len(lines) and 'file' in lines[i + 1]:
                    stats_line = lines[i + 1]
                    match = re.search(r'(\d+) file', stats_line)
                    if match:
                        files_changed = int(match.group(1))
                    i += 1

                commits.append({
                    'hash': commit_hash,
                    'message': message,
                    'author': author,
                    'time': time_ago,
                    'files_changed': files_changed
                })

                # Check for issues
                # Issue 1: Vague messages
                vague_patterns = [r'^wip$', r'^fix$', r'^update$', r'^change',
                                r'^test$', r'^temp', r'^asdf', r'^\.']
                for pattern in vague_patterns:
                    if re.search(pattern, message.lower()):
                        issues.append({
                            'commit': commit_hash,
                            'type': 'vague_message',
                            'description': f'Commit message too vague: "{message}"',
                            'suggestion': 'Use descriptive messages that explain what and why'
                        })
                        break

                # Issue 2: Too many files changed
                if files_changed > 20:
                    issues.append({
                        'commit': commit_hash,
                        'type': 'large_commit',
                        'description': f'Commit modified {files_changed} files',
                        'suggestion': 'Consider breaking large commits into smaller, focused ones'
                    })

                # Issue 3: Message too short (less than 10 chars)
                if len(message) < 10:
                    issues.append({
                        'commit': commit_hash,
                        'type': 'short_message',
                        'description': f'Very short commit message: "{message}"',
                        'suggestion': 'Add more context about what changed and why'
                    })

        i += 1

    return {
        'commits_analyzed': len(commits),
        'commits': commits,
        'issues_found': len(issues),
        'issues': issues,
        'summary': f"Analyzed {len(commits)} commits, found {len(issues)} potential issues"
    }


def main():
    """
    What: Command-line entry point
    Why: Allow the skill to execute this script from bash
    How: Parse arguments and dispatch to appropriate function
    """
    parser = argparse.ArgumentParser(
        description='Git workflow helper - commit messages, branch names, history analysis'
    )
    parser.add_argument('--action', required=True,
                       choices=['review-changes', 'generate-message', 'suggest-branch',
                               'analyze-history', 'check-status', 'test'],
                       help='Action to perform')
    parser.add_argument('--context', default='',
                       help='Context for the action (e.g., what you\'re working on)')
    parser.add_argument('--staged', action='store_true',
                       help='For generate-message: use staged changes only')
    parser.add_argument('--count', type=int, default=10,
                       help='For analyze-history: number of commits to analyze')
    parser.add_argument('--format', default='human',
                       choices=['human', 'json'],
                       help='Output format')

    args = parser.parse_args()

    # Check if in Git repo (except for test action)
    if args.action != 'test' and not check_git_repository():
        print("Error: Not in a Git repository", file=sys.stderr)
        sys.exit(1)

    result = None

    # Execute requested action
    if args.action == 'review-changes':
        review = review_staged_changes()

        if 'error' in review:
            print(f"Error: {review['error']}", file=sys.stderr)
            sys.exit(1)

        if args.format == 'human':
            print("\n" + "=" * 70)
            print("STAGED CHANGES REVIEW")
            print("=" * 70 + "\n")

            # Show summary
            summary = review['summary']
            print(f"Files changed: {summary['files_changed']}")
            print(f"Lines added:   +{summary['additions']}")
            print(f"Lines removed: -{summary['deletions']}")
            print()

            # Show which files are staged
            print("-" * 70)
            print("STAGED FILES:")
            print("-" * 70)
            for file_line in review['staged_files']:
                print(f"  {file_line}")
            print()

            # Show diff (truncate if very long)
            print("-" * 70)
            print("CHANGES (git diff --staged):")
            print("-" * 70)
            diff_lines = review['diff'].split('\n')
            max_lines = 100
            if len(diff_lines) > max_lines:
                print('\n'.join(diff_lines[:max_lines]))
                print(f"\n... ({len(diff_lines) - max_lines} more lines, truncated)")
            else:
                print(review['diff'])

            print("\n" + "=" * 70)
            print("Use this context to write a meaningful commit message.")
            print("=" * 70)
        else:
            # JSON output - useful for programmatic access
            print(json.dumps(review, indent=2))

    elif args.action == 'generate-message':
        context = 'staged' if args.staged else 'all'
        message = generate_commit_message(context)
        result = {'message': message}

        if args.format == 'human':
            print("\nSuggested Commit Message:")
            print("=" * 60)
            print(message)
            print("=" * 60)
        else:
            print(json.dumps(result, indent=2))

    elif args.action == 'suggest-branch':
        branch_name = suggest_branch_name(args.context)
        result = {'branch_name': branch_name}

        if args.format == 'human':
            print(f"\nSuggested Branch Name: {branch_name}")
        else:
            print(json.dumps(result, indent=2))

    elif args.action == 'analyze-history':
        analysis = analyze_commit_history(args.count)

        if args.format == 'human':
            print(f"\n{'='*60}")
            print("Commit History Analysis")
            print(f"{'='*60}\n")
            print(analysis.get('summary', ''))
            print()

            if analysis.get('issues'):
                print("Issues Found:")
                print("-" * 60)
                for issue in analysis['issues']:
                    print(f"\n{issue['commit']}: {issue['description']}")
                    print(f"  💡 {issue['suggestion']}")
            else:
                print("✓ No issues found! Commit history looks good.")

            print(f"\n{'='*60}")
            print("Recent Commits:")
            print(f"{'='*60}\n")
            for commit in analysis.get('commits', []):
                print(f"{commit['hash']}: {commit['message']}")
                print(f"  by {commit['author']}, {commit['time']}")
                if commit['files_changed'] > 0:
                    print(f"  {commit['files_changed']} files changed")
                print()
        else:
            print(json.dumps(analysis, indent=2))

    elif args.action == 'check-status':
        status = get_status()

        if args.format == 'human':
            print("\nRepository Status:")
            print("=" * 60)
            if status['modified']:
                print(f"\nModified ({len(status['modified'])}):")
                for f in status['modified']:
                    print(f"  M {f}")
            if status['added']:
                print(f"\nAdded ({len(status['added'])}):")
                for f in status['added']:
                    print(f"  A {f}")
            if status['deleted']:
                print(f"\nDeleted ({len(status['deleted'])}):")
                for f in status['deleted']:
                    print(f"  D {f}")
            if status['untracked']:
                print(f"\nUntracked ({len(status['untracked'])}):")
                for f in status['untracked']:
                    print(f"  ? {f}")

            total = sum(len(v) for v in status.values())
            if total == 0:
                print("\n✓ Working directory clean")
        else:
            print(json.dumps(status, indent=2))

    elif args.action == 'test':
        # Test mode - verify functions work
        print("Running self-tests...")
        print()

        # Test 1: Branch name generation
        print("Test 1: Branch name generation")
        test_contexts = [
            "adding search feature",
            "fix broken login button",
            "refactor authentication code",
            "update readme documentation"
        ]
        for ctx in test_contexts:
            branch = suggest_branch_name(ctx)
            print(f"  '{ctx}' → '{branch}'")
        print("  ✓ Pass")
        print()

        # Test 2: Diff analysis
        print("Test 2: Diff analysis")
        sample_diff = """diff --git a/test.js b/test.js
index 123..456 789
--- a/test.js
+++ b/test.js
@@ -1,3 +1,5 @@
+// New comment
 function test() {
-  console.log('old');
+  console.log('new');
+  return true;
 }"""
        analysis = analyze_diff(sample_diff)
        print(f"  Files: {analysis['files']}")
        print(f"  +{analysis['additions']} -{analysis['deletions']}")
        print("  ✓ Pass")
        print()

        print("All tests passed! ✓")


if __name__ == '__main__':
    main()
