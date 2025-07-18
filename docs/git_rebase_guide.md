# Git Rebase Guide

## What is Git Rebase?

Git rebase is a command that allows you to integrate changes from one branch into another by moving or combining commits. It essentially "replays" commits from one branch onto another, creating a linear history.

## Basic Rebase Commands

### 1. Simple Rebase
```bash
# Rebase current branch onto another branch
git rebase <target-branch>

# Example: Rebase current branch onto main
git rebase main
```

### 2. Rebase a Specific Branch
```bash
# Rebase a specific branch onto another
git rebase <target-branch> <source-branch>

# Example: Rebase feature-branch onto main
git rebase main feature-branch
```

## Interactive Rebase

Interactive rebase allows you to modify commits during the rebase process:

```bash
# Interactive rebase for the last N commits
git rebase -i HEAD~N

# Example: Interactive rebase for last 3 commits
git rebase -i HEAD~3

# Interactive rebase from a specific commit
git rebase -i <commit-hash>
```

### Interactive Rebase Commands
- `pick` (p): Use the commit as-is
- `reword` (r): Edit the commit message
- `edit` (e): Stop to amend the commit
- `squash` (s): Combine with previous commit
- `fixup` (f): Like squash but discard commit message
- `drop` (d): Remove the commit

## Common Rebase Scenarios

### 1. Update Feature Branch with Latest Main
```bash
# Switch to your feature branch
git checkout feature-branch

# Rebase onto main
git rebase main
```

### 2. Squash Multiple Commits
```bash
# Interactive rebase to combine commits
git rebase -i HEAD~3

# In the editor, change 'pick' to 'squash' for commits you want to combine
```

### 3. Rebase Before Merging
```bash
# Update feature branch with latest main
git checkout feature-branch
git rebase main

# Then merge (creates clean history)
git checkout main
git merge feature-branch
```

## Handling Conflicts

When conflicts occur during rebase:

1. **Resolve conflicts** in the affected files
2. **Stage the resolved files**: `git add <file>`
3. **Continue the rebase**: `git rebase --continue`

### Rebase Conflict Commands
```bash
# Continue after resolving conflicts
git rebase --continue

# Skip the current commit (if needed)
git rebase --skip

# Abort the rebase and return to original state
git rebase --abort
```

## Advanced Options

### Preserve Merge Commits
```bash
# Rebase while preserving merge commits
git rebase -p <target-branch>
# Note: -p is deprecated, use --rebase-merges instead
git rebase --rebase-merges <target-branch>
```

### Rebase with Different Base
```bash
# Rebase commits from one branch onto another
git rebase --onto <new-base> <old-base> <branch>

# Example: Move commits from feature-branch that are after commit ABC onto main
git rebase --onto main ABC feature-branch
```

## Best Practices

1. **Never rebase public/shared branches** - Only rebase local branches or branches you own
2. **Always backup** important work before rebasing
3. **Test after rebasing** to ensure nothing broke
4. **Use interactive rebase** to clean up commit history before pushing
5. **Rebase frequently** to keep feature branches up-to-date

## Useful Aliases

Add these to your `.gitconfig`:

```bash
git config --global alias.rb 'rebase'
git config --global alias.rbi 'rebase -i'
git config --global alias.rbc 'rebase --continue'
git config --global alias.rba 'rebase --abort'
```

## Troubleshooting

### If You Get Lost
```bash
# Check reflog to see recent actions
git reflog

# Reset to a previous state if needed
git reset --hard HEAD@{n}
```

### If Rebase Seems Stuck
```bash
# Check current rebase status
git status

# See what's happening
git rebase --show-current-patch
```

## Example Workflow

```bash
# 1. Start from main branch
git checkout main
git pull origin main

# 2. Create/switch to feature branch
git checkout feature-branch

# 3. Rebase onto latest main
git rebase main

# 4. Resolve any conflicts and continue
# (if conflicts occur)
git add .
git rebase --continue

# 5. Push rebased branch (may need force push)
git push origin feature-branch --force-with-lease
```

Remember: Use `--force-with-lease` instead of `--force` when pushing rebased branches to avoid overwriting others' work.