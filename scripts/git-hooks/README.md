# Git Hooks

This directory contains Git hook templates for the project.

## Available Hooks

### post-checkout

Automatically switches the Pulumi stack to match the current Git branch when you checkout a branch.

**Example:**

```bash
$ git checkout dev
Switched to branch 'dev'
🔄 Switched Pulumi stack: main → dev

$ git checkout main
Switched to branch 'main'
🔄 Switched Pulumi stack: dev → main
```

If a Pulumi stack doesn't exist for the branch you're checking out, the hook silently stays on the current stack.

## Installation

Run the setup script from the repository root:

```bash
./scripts/setup-git-hooks.sh
```

Or install manually:

```bash
cp scripts/git-hooks/post-checkout .git/hooks/post-checkout
chmod +x .git/hooks/post-checkout
```

## Note

Git hooks are not committed to the repository (they live in `.git/hooks/` which is gitignored). Each developer needs to install them locally using the setup script above.
