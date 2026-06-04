# GitHub Repository Setup

## CheckSum

```bash
cd ~/Documents/checksum

# Create repo (choose org)
gh repo create rhpds/checksum --private --source=. --remote=origin \
  --description "RHDP capacity scanner — scan demo repos, recommend provisioning tiers"

# Or under personal
gh repo create jkershaw/checksum --private --source=. --remote=origin

# Push
git push -u origin main
```

## LiftOff

```bash
cd ~/Documents/liftoff

# Create repo
gh repo create rhpds/liftoff --private --source=. --remote=origin \
  --description "RHDP provisioning engine — three-tier AgnosticV catalog items for AI demos"

# Push
git push -u origin main
```

## Prerequisites

```bash
# Install gh CLI if not present
brew install gh

# Authenticate
gh auth login
```

## After Push

1. Enable GitHub Actions (Settings → Actions → Allow all actions)
2. Add branch protection for main (require PR reviews)
3. Add topics: `rhdp`, `capacity-planning`, `agnosticv`, `openshift`
