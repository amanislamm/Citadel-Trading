#!/usr/bin/env bash
# One-shot: create a PUBLIC GitHub repo and push. Needs GitHub CLI: brew install gh && gh auth login
set -e
cd "$(dirname "$0")"
NAME="${1:-citadel-trading-toolkit}"
[ -d .git ] || git init -b main
git add -A && git commit -m "Trading challenge toolkit" || true
gh repo create "$NAME" --public --source=. --remote=origin --push
echo "Done. Share: $(gh repo view --json url -q .url)"
echo "Public repo: partner can just git clone it. To give push access: gh api -X PUT repos/$(gh api user -q .login)/$NAME/collaborators/PARTNER_USERNAME"
