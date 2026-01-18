#!/bin/bash
# Script to create and push the main branch

set -e

echo "Creating main branch from WSL-spec-draft content..."

# Ensure we're in the repository root
cd "$(git rev-parse --show-toplevel)"

# Create main branch from the WSL-spec-draft commit (70f0824)
if git show-ref --verify --quiet refs/heads/main; then
    echo "Main branch already exists locally"
else
    git branch main 70f0824d741798a0dfb08f6b946acace95031a2b
    echo "Main branch created locally"
fi

# Push the main branch to origin
echo "Pushing main branch to origin..."
git push origin main

echo "Done! Main branch has been created and pushed."
echo "You can verify it at: https://github.com/tcdent/wsl/tree/main"
