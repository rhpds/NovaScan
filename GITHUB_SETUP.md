# GitHub Repository Setup

## NovaScan

Repo: https://github.com/rhpds/NovaScan

```bash
cd ~/Documents/novascan
git remote add origin https://github.com/rhpds/NovaScan.git
git push -u origin main
```

## LiftOff

```bash
cd ~/Documents/liftoff
# Create repo via GitHub UI or gh CLI, then:
git remote add origin https://github.com/rhpds/LiftOff.git
git push -u origin main
```

## Prerequisites

```bash
# Install gh CLI (RHEL/Fedora)
sudo dnf install gh

# Or download from https://github.com/cli/cli/releases

# Authenticate
gh auth login
```

## After Push

1. Enable GitHub Actions (Settings → Actions → Allow all actions)
2. Add branch protection for main (require PR reviews)
3. Add topics: `rhdp`, `capacity-planning`, `agnosticv`, `openshift`
