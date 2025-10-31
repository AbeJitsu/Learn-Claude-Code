---
name: git-workflow
description: Generate commit messages, suggest branch names, analyze history
version: 1.0.0
author: abereyes
triggers:
  - "commit"
  - "create commit message"
  - "git help"
  - "branch"
---

# Git Workflow Helper

Automates Git operations and maintains clean repository hygiene.

## Features

- **Generate commit messages** from git diff
- **Suggest branch names** following conventions
- **Analyze commit history** for issues
- **Check Git status** in readable format

## Usage

```bash
# Review staged changes (for AI-assisted commit messages)
python3 helpers.py --action review-changes

# Suggest branch name
python3 helpers.py --action suggest-branch --context "fixing login bug"

# Analyze history
python3 helpers.py --action analyze-history --count 10

# Run tests
python3 helpers.py --action test
```

## Workflow

**Creating commit messages:**
1. Stage your changes: `git add .`
2. Run review: `python3 helpers.py --action review-changes`
3. Tool shows what changed (status + diff)
4. AI writes commit message based on actual changes
5. Review and commit

## Examples

**Branch naming**:
- "fixing login bug" → `fix/login-bug`
- "adding search" → `feature/adding-search`
- "refactor auth code" → `refactor/auth-code`

**Commit review**:
Shows staged files, additions/deletions, and full diff context for AI to analyze and write meaningful commit messages (no more "[TODO: Explain why]" templates).

## Value

No more lazy commit messages like "work in progress" or "update". Consistent branch naming. Clean git history.
