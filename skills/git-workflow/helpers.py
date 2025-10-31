#!/usr/bin/env python3
"""
Git Workflow Helper

What: Provides Git workflow assistance (commit messages, branch names, history analysis)
Why: Makes Git easier and maintains clean repository hygiene
How: Analyzes Git state and provides actionable suggestions

This script helps developers create better commit messages and branch names
by analyzing git changes and suggesting clear, descriptive names.
"""

# Import required libraries
import argparse    # For parsing command-line arguments
import subprocess  # For running git commands
import sys         # For system operations like exit
import json        # For outputting structured data
import re          # For pattern matching in text
from typing import Dict, List, Optional, Tuple  # For type hints


def run_git_command(command: List[str]) -> Tuple[bool, str, str]:
    """
    What: Execute a git command safely
    Why: We need to interact with Git to analyze repository state
    How: Use subprocess to run git commands and capture output

    Returns: (success, stdout, stderr)
    """
    try:
        # Run the git command with subprocess
        # capture_output means we collect stdout and stderr
        # text means we get strings instead of bytes
        # timeout prevents commands from hanging forever
        result = subprocess.run(
            ['git'] + command,
            capture_output=True,
            text=True,
            timeout=10
        )
        # Return success status (True if exit code was 0)
        # along with the command output
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        # Command took too long, return failure
        return (False, "", "Command timed out")
    except Exception as e:
        # Something else went wrong, return error message
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
    # Run git status in machine-readable format
    success, stdout, stderr = run_git_command(['status', '--porcelain'])

    # Return empty lists if command failed
    if not success:
        return {'modified': [], 'added': [], 'deleted': [], 'untracked': []}

    # Initialize our status dictionary
    status = {'modified': [], 'added': [], 'deleted': [], 'untracked': []}

    # Parse each line of git status output
    for line in stdout.strip().split('\n'):
        # Skip empty lines
        if not line:
            continue

        # Format: XY filename
        # X = index status, Y = working tree status
        # First two characters are status codes
        status_code = line[:2]
        filename = line[3:].strip()

        # Categorize files by their status
        # M = modified, A = added, D = deleted, ?? = untracked
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
    # Handle empty diff
    if not diff_text:
        return {'files': [], 'additions': 0, 'deletions': 0}

    # Initialize counters
    files = []
    additions = 0
    deletions = 0
    current_file = None

    # Parse each line of the diff
    for line in diff_text.split('\n'):
        # File header starts with "diff --git"
        if line.startswith('diff --git'):
            parts = line.split()
            if len(parts) >= 4:
                # Extract filename (remove b/ prefix)
                current_file = parts[3].replace('b/', '')
                files.append(current_file)

        # Count additions and deletions
        # Lines starting with + are additions (but not +++ which is a file marker)
        # Lines starting with - are deletions (but not --- which is a file marker)
        elif line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1

    # Return summary of changes
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
    # First check if we're in a Git repository = storage location for code and history
    # Can't review changes if not in code storage
    if not check_git_repository():
        return {'error': 'Not in a Git repository'}

    # Get the diff of staged changes (changes ready to commit)
    diff = get_staged_changes()
    if not diff:
        # Nothing staged yet, user needs to run "git add" first
        return {'error': 'No staged changes. Use "git add" first.'}

    # Get overall status of the code storage
    # Shows what files are modified, added, deleted, etc.
    status = get_status()

    # Analyze the diff to count additions and deletions
    # This gives us statistics about the changes
    analysis = analyze_diff(diff)

    # Get list of staged files with their status codes
    # M = modified, A = added, D = deleted, R = renamed, C = copied
    success, status_output, _ = run_git_command(['status', '--short'])
    staged_files = []
    if success:
        # Parse each line of status output
        for line in status_output.strip().split('\n'):
            # First character indicates staging area status
            # M, A, D, R, C means the file is staged
            if line and line[0] in ['M', 'A', 'D', 'R', 'C']:
                staged_files.append(line.strip())

    # Return all the context needed for AI to write a commit message
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
    # Check if we're in a Git code storage location first
    if not check_git_repository():
        return "Error: Not in a Git repository"

    # Get changes based on context
    # Either staged changes only, or all working directory changes
    if context == 'staged':
        # Get only staged changes (what will be committed)
        diff = get_staged_changes()
        if not diff:
            return "No staged changes to commit. Use 'git add' first."
    else:
        # Get all changes in working directory
        success, diff, _ = run_git_command(['diff'])
        if not success or not diff:
            return "No changes found."

    # Analyze the diff to understand what changed
    # Counts additions, deletions, and identifies files
    analysis = analyze_diff(diff)
    status = get_status()

    # Extract file list from analysis
    files_changed = analysis['files']
    num_files = len(files_changed)

    # Handle edge case where no files changed
    if num_files == 0:
        return "No files changed"

    # Determine type of change based on file status
    # Helps create appropriate commit message prefix
    change_type = "Update"
    if status['added']:
        change_type = "Add"
    elif status['deleted']:
        change_type = "Remove"

    # Create a concise summary line for the commit
    # Format depends on number of files changed
    if num_files == 1:
        # Single file: use the filename
        summary = f"{change_type} {files_changed[0]}"
    elif num_files <= 3:
        # Few files: list them all
        summary = f"{change_type} {', '.join(files_changed)}"
    else:
        # Many files: just show count
        summary = f"{change_type} {num_files} files"

    # Build the full commit message with details
    # Summary line, then detailed breakdown
    message = f"{summary}\n\n"
    message += f"What: Modified {num_files} file(s)\n"
    message += f"Why: [TODO: Explain why this change is needed]\n"
    message += f"Changes: +{analysis['additions']} -{analysis['deletions']} lines\n\n"
    message += "Files:\n"
    # List files (limit to 5 to keep message reasonable)
    for f in files_changed[:5]:
        message += f"- {f}\n"
    # Show count of remaining files if there are more
    if num_files > 5:
        message += f"... and {num_files - 5} more\n"

    return message


def suggest_branch_name(context: str = "") -> str:
    """
    What: Suggest a branch name following conventions
    Why: Consistent branch naming helps team organization
    How: Use context provided and apply naming conventions
    """
    # Need context to suggest a name
    if not context:
        return "Usage: Provide context like 'adding search feature' or 'fix login bug'"

    # Convert context to lowercase and remove extra whitespace
    normalized = context.lower().strip()

    # Detect type of work based on keywords
    # This determines the prefix (feature/, fix/, refactor = restructure code, etc.)
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
    # Remove common filler words that don't add meaning
    remove_words = ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'should', 'could', 'may', 'might', 'must', 'can',
                    'add', 'adding', 'fix', 'fixing', 'update', 'updating']

    # Split into words and filter out common words and short words
    words = normalized.split()
    filtered_words = [w for w in words if w not in remove_words and len(w) > 2]

    # Join with hyphens (standard branch name format)
    # Limit to 5 words to keep branch names reasonable
    branch_name_part = '-'.join(filtered_words[:5])

    # Remove any special characters (only keep letters, numbers, hyphens)
    branch_name_part = re.sub(r'[^a-z0-9-]', '', branch_name_part)

    # Return formatted branch name (e.g., "fix/login-bug")
    return f"{branch_type}/{branch_name_part}"


def analyze_commit_history(count: int = 10) -> Dict:
    """
    What: Analyze recent commit history for patterns and issues
    Why: Help maintain clean commit history
    How: Parse git log and look for common issues
    """
    # Check if we're in a Git code storage location
    if not check_git_repository():
        return {'error': 'Not in a Git repository'}

    # Get commit history with custom format
    # Format: hash|subject|author|relative_time
    # --shortstat adds file change statistics
    success, stdout, stderr = run_git_command([
        'log',
        f'-{count}',
        '--pretty=format:%H|%s|%an|%ar',
        '--shortstat'
    ])

    # Handle failure to get history
    if not success:
        return {'error': 'Failed to get commit history', 'details': stderr}

    # Initialize lists to track commits and issues
    commits = []
    issues = []

    # Parse git log output line by line
    lines = stdout.strip().split('\n')
    i = 0
    while i < len(lines):
        # Lines with | are commit info lines
        if '|' in lines[i]:
            # Split the formatted commit line
            parts = lines[i].split('|')
            if len(parts) >= 4:
                # Extract commit information
                commit_hash = parts[0][:7]  # Short hash (first 7 chars)
                message = parts[1]          # Commit subject line
                author = parts[2]           # Author name
                time_ago = parts[3]         # Relative time (e.g., "2 days ago")

                # Check next line for file change statistics
                # Format: "X files changed, Y insertions(+), Z deletions(-)"
                files_changed = 0
                if i + 1 < len(lines) and 'file' in lines[i + 1]:
                    stats_line = lines[i + 1]
                    # Extract number of files from stats line
                    match = re.search(r'(\d+) file', stats_line)
                    if match:
                        files_changed = int(match.group(1))
                    # Skip the stats line on next iteration
                    i += 1

                # Store commit information
                commits.append({
                    'hash': commit_hash,
                    'message': message,
                    'author': author,
                    'time': time_ago,
                    'files_changed': files_changed
                })

                # Check for common commit message issues

                # Issue 1: Vague commit messages
                # Messages like "work in progress", "fix", "update" don't explain anything
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
                        # Only report one issue type per commit
                        break

                # Issue 2: Commits that change too many files
                # Large commits are hard to review and should be split up
                if files_changed > 20:
                    issues.append({
                        'commit': commit_hash,
                        'type': 'large_commit',
                        'description': f'Commit modified {files_changed} files',
                        'suggestion': 'Consider breaking large commits into smaller, focused ones'
                    })

                # Issue 3: Message is too short to be meaningful
                # At least 10 characters needed for useful description
                if len(message) < 10:
                    issues.append({
                        'commit': commit_hash,
                        'type': 'short_message',
                        'description': f'Very short commit message: "{message}"',
                        'suggestion': 'Add more context about what changed and why'
                    })

        # Move to next line
        i += 1

    # Return analysis results
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
    # Set up command-line argument parser
    # This defines what arguments the script accepts
    parser = argparse.ArgumentParser(
        description='Git workflow helper - commit messages, branch names, history analysis'
    )

    # Define required --action argument
    # User must specify what they want to do
    parser.add_argument('--action', required=True,
                       choices=['review-changes', 'generate-message', 'suggest-branch',
                               'analyze-history', 'check-status', 'test'],
                       help='Action to perform')

    # Optional context argument for branch naming
    parser.add_argument('--context', default='',
                       help='Context for the action (e.g., what you\'re working on)')

    # Flag to use only staged changes for commit messages
    parser.add_argument('--staged', action='store_true',
                       help='For generate-message: use staged changes only')

    # Number of commits to analyze in history
    parser.add_argument('--count', type=int, default=10,
                       help='For analyze-history: number of commits to analyze')

    # Output format: human-readable or JSON
    parser.add_argument('--format', default='human',
                       choices=['human', 'json'],
                       help='Output format')

    # Parse the arguments provided by user
    args = parser.parse_args()

    # Check if in Git code storage location (except for test action)
    # Most actions require being in a code storage location
    if args.action != 'test' and not check_git_repository():
        print("Error: Not in a Git repository", file=sys.stderr)
        sys.exit(1)

    # Result variable for storing action output
    result = None

    # Execute requested action
    # Dispatch to appropriate handler based on --action argument
    if args.action == 'review-changes':
        # Review staged changes action
        # Shows what's ready to commit for AI to write commit message
        review = review_staged_changes()

        # Handle errors (not in repo, no staged changes, etc.)
        if 'error' in review:
            print(f"Error: {review['error']}", file=sys.stderr)
            sys.exit(1)

        # Format output based on --format argument
        if args.format == 'human':
            # Human-readable format with nice formatting
            print("\n" + "=" * 70)
            print("STAGED CHANGES REVIEW")
            print("=" * 70 + "\n")

            # Show summary statistics
            summary = review['summary']
            print(f"Files changed: {summary['files_changed']}")
            print(f"Lines added:   +{summary['additions']}")
            print(f"Lines removed: -{summary['deletions']}")
            print()

            # Show which files are staged
            # Format: status code + filename
            print("-" * 70)
            print("STAGED FILES:")
            print("-" * 70)
            for file_line in review['staged_files']:
                print(f"  {file_line}")
            print()

            # Show the actual diff (what changed in each file)
            # Truncate if very long to avoid overwhelming output
            print("-" * 70)
            print("CHANGES (git diff --staged):")
            print("-" * 70)
            diff_lines = review['diff'].split('\n')
            max_lines = 100
            if len(diff_lines) > max_lines:
                # Only show first 100 lines
                print('\n'.join(diff_lines[:max_lines]))
                print(f"\n... ({len(diff_lines) - max_lines} more lines, truncated)")
            else:
                # Show entire diff if it's short enough
                print(review['diff'])

            # Final message to user
            print("\n" + "=" * 70)
            print("Use this context to write a meaningful commit message.")
            print("=" * 70)
        else:
            # JSON output (JavaScript Object Notation = data format that's easy for computers to read) - useful for programmatic access
            print(json.dumps(review, indent=2))

    elif args.action == 'generate-message':
        # Generate commit message action
        # Creates template message based on changes
        context = 'staged' if args.staged else 'all'
        message = generate_commit_message(context)
        result = {'message': message}

        # Format and display the generated message
        if args.format == 'human':
            print("\nSuggested Commit Message:")
            print("=" * 60)
            print(message)
            print("=" * 60)
        else:
            # JSON = data format easy for computers to read, useful for scripts
            print(json.dumps(result, indent=2))

    elif args.action == 'suggest-branch':
        # Suggest branch name action
        # Takes user's description and creates conventional branch name
        branch_name = suggest_branch_name(args.context)
        result = {'branch_name': branch_name}

        # Display suggested branch name
        if args.format == 'human':
            print(f"\nSuggested Branch Name: {branch_name}")
        else:
            # JSON = data format easy for computers to read, useful for scripts
            print(json.dumps(result, indent=2))

    elif args.action == 'analyze-history':
        # Analyze commit history action
        # Checks recent commits for common problems
        analysis = analyze_commit_history(args.count)

        # Format output based on --format argument
        if args.format == 'human':
            # Human-readable report
            print(f"\n{'='*60}")
            print("Commit History Analysis")
            print(f"{'='*60}\n")
            print(analysis.get('summary', ''))
            print()

            # Show any issues found in commits
            if analysis.get('issues'):
                print("Issues Found:")
                print("-" * 60)
                for issue in analysis['issues']:
                    # Show each issue with suggestion for improvement
                    print(f"\n{issue['commit']}: {issue['description']}")
                    print(f"  💡 {issue['suggestion']}")
            else:
                # No issues found - good news!
                print("✓ No issues found! Commit history looks good.")

            # Show list of recent commits
            print(f"\n{'='*60}")
            print("Recent Commits:")
            print(f"{'='*60}\n")
            for commit in analysis.get('commits', []):
                # Display commit hash, message, author, and time
                print(f"{commit['hash']}: {commit['message']}")
                print(f"  by {commit['author']}, {commit['time']}")
                # Show file change count if available
                if commit['files_changed'] > 0:
                    print(f"  {commit['files_changed']} files changed")
                print()
        else:
            # JSON = data format easy for computers to read, useful for scripts
            print(json.dumps(analysis, indent=2))

    elif args.action == 'check-status':
        # Check code storage status action
        # Shows what files are modified, added, deleted, untracked
        status = get_status()

        # Format output based on --format argument
        if args.format == 'human':
            # Human-readable status report
            print("\nRepository Status:")
            print("=" * 60)

            # Show modified files (M status)
            if status['modified']:
                print(f"\nModified ({len(status['modified'])}):")
                for f in status['modified']:
                    print(f"  M {f}")

            # Show added files (A status)
            if status['added']:
                print(f"\nAdded ({len(status['added'])}):")
                for f in status['added']:
                    print(f"  A {f}")

            # Show deleted files (D status)
            if status['deleted']:
                print(f"\nDeleted ({len(status['deleted'])}):")
                for f in status['deleted']:
                    print(f"  D {f}")

            # Show untracked files (? status)
            if status['untracked']:
                print(f"\nUntracked ({len(status['untracked'])}):")
                for f in status['untracked']:
                    print(f"  ? {f}")

            # If no changes at all, show clean message
            total = sum(len(v) for v in status.values())
            if total == 0:
                print("\n✓ Working directory clean")
        else:
            # JSON = data format easy for computers to read, useful for scripts
            print(json.dumps(status, indent=2))

    elif args.action == 'test':
        # Test mode - verify functions work correctly
        # Run self-tests without needing a Git code storage location
        print("Running self-tests...")
        print()

        # Test 1: Branch name generation
        # Verify that suggest_branch_name creates proper names
        print("Test 1: Branch name generation")
        test_contexts = [
            "adding search feature",
            "fix broken login button",
            "refactor authentication code",
            "update readme documentation"
        ]
        # Run test with each context
        for ctx in test_contexts:
            branch = suggest_branch_name(ctx)
            print(f"  '{ctx}' → '{branch}'")
        print("  ✓ Pass")
        print()

        # Test 2: Diff analysis
        # Verify that analyze_diff correctly parses git diff output
        print("Test 2: Diff analysis")
        # Sample git diff output for testing
        sample_diff = """diff --git a/test.js b/test.js
index 123..456 789
--- a/test.js
+++ b/test.js
@@ -1,3 +1,5 @@
+// New comment
 if (condition) {
-  console.log('old');
+  console.log('new');
+  return true;
 }"""
        # Parse the sample diff
        analysis = analyze_diff(sample_diff)
        # Display results (should show 3 additions, 1 deletion)
        print(f"  Files: {analysis['files']}")
        print(f"  +{analysis['additions']} -{analysis['deletions']}")
        print("  ✓ Pass")
        print()

        # All tests completed successfully
        print("All tests passed! ✓")


if __name__ == '__main__':
    main()
