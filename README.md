# Learn Claude Code Plugin

Demonstrates Claude Code's 4 extension technologies: **Plugins**, **Agent Skills**, **Subagents**, and **MCP Servers**.

## What Works NOW

### Git Workflow (Production Ready)
```bash
cd skills/git-workflow

# Review staged changes for commit (shows context for AI to write message)
python3 helpers.py --action review-changes

# Suggest branch name
python3 helpers.py --action suggest-branch --context "fixing login"

# Run tests
python3 helpers.py --action test
```

### Code Readability (Works with caveats)
```bash
cd skills/code-analysis

# Check code readability
python3 analyze.py --path your-file.py --strictness lenient
```

**Note**: Has false positives on documentation. Works fine on actual code.

## Installation

```bash
# Copy to Claude Code plugins
cp -r "Learn Claude Code" ~/.claude/plugins/

# Or symlink for development
ln -s "/path/to/Learn Claude Code" ~/.claude/plugins/learn-claude-code
```

## The 4 Technologies

1. **Plugin** (.claude-plugin/plugin.json) - Bundles everything
2. **Skills** (skills/) - Domain expertise, progressive disclosure
3. **Subagent** (agents/ui-tester.md) - UI testing specialist
4. **MCP** (.mcp.json) - Puppeteer browser automation (requires Node.js)

## Requirements

- Python 3.7+ (for skills)
- Git (for git-workflow)
- Node.js 16+ (optional, for UI testing)

## Value

**Git workflow**: No more lazy commit messages like "work in progress" or "update". Get context for AI to write clear commit messages, auto-suggest branch names.

**Code readability**: Check if non-developers can understand your code.

**UI testing**: Browser automation for accessibility and visual testing (requires Node.js setup).
