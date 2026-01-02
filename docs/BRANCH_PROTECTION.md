# Branch Protection Configuration

This document describes the branch protection rules configured for the `main` branch to ensure code quality and prevent accidental or harmful changes.

## Quick Start

**To apply branch protection, choose one option:**

### Option A: Automated Setup (Recommended)
```bash
./scripts/github/setup-branch-protection.sh
```

### Option B: GitHub CLI One-Liner
```bash
gh api -X PUT /repos/amendez13/dropboxFamilyPhotoOrganizer/branches/main/protection \
  --input scripts/github/branch-protection-config.json
```

### Option C: Manual Setup
See [Manual Configuration via GitHub UI](#option-2-manual-configuration-via-github-ui) below.

## Overview

Branch protection rules help maintain code quality by requiring specific checks to pass before code can be merged into the `main` branch. This ensures that all changes are reviewed, tested, and meet quality standards.

## Protection Rules for `main` Branch

### Required Status Checks

All CI checks must pass before merging:

**Strict Status Checks:**
- `Lint and Code Quality` - Code formatting, linting, and type checking
- `Test Python 3.10` - Tests on Python 3.10
- `Test Python 3.11` - Tests on Python 3.11
- `Test Python 3.12` - Tests on Python 3.12
- `Validate Configuration` - Configuration file validation
- `CI Status Check` - Final CI status verification

**Non-blocking Checks:**
- `Security Checks` - Security scans (warnings allowed)
- `Integration Tests` - Integration tests (when enabled)

**Configuration:**
- **Require branches to be up to date before merging**: ✅ Enabled
  - This ensures that PRs are tested against the latest `main` before merging
  - Prevents "green build, broken main" scenarios

### Pull Request Requirements

**Require Pull Request Reviews:**
- ❌ Disabled for solo development
  - GitHub doesn't allow PR authors to approve their own PRs
  - For solo developers: Protection still ensures CI passes and conversations are resolved
  - Can be enabled when working with a team by setting `required_approving_review_count`
  - For critical changes: Consider requesting external review even as a solo developer

**Note for Solo Developers:**
- While PR approval is disabled, you still benefit from:
  - Required status checks (all CI must pass)
  - Conversation resolution requirement
  - Linear history enforcement
  - Protection against accidental force pushes/deletions

**Require review from Code Owners:**
- ❌ Disabled (can be enabled if you create a CODEOWNERS file and work with a team)

### Additional Protections

**Require signed commits:**
- ❌ Disabled
- Can be enabled for enhanced security if needed

**Require linear history:**
- ✅ Enabled (Recommended)
- Prevents merge commits, keeps history clean
- Forces use of "Squash and merge" or "Rebase and merge"

**Allow force pushes:**
- ❌ Disabled
- Prevents accidentally overwriting history on `main`

**Allow deletions:**
- ❌ Disabled
- Prevents accidental deletion of the `main` branch

**Require conversation resolution before merging:**
- ✅ Enabled
- All review comments must be resolved before merging

**Lock branch (read-only):**
- ❌ Disabled
- Branch remains writable for maintainers

**Do not allow bypassing the above settings:**
- ✅ Enabled for everyone (no exceptions)
- Even administrators must follow these rules
- Emergency bypass available through GitHub UI if absolutely necessary

### Enforcement Settings

**Include administrators:**
- ✅ Enabled
- Administrators must also follow branch protection rules
- Ensures everyone follows the same workflow

**Allow specified actors to bypass required pull requests:**
- ❌ Disabled
- No one can bypass PR requirements

## Implementation

### Option 1: Using GitHub CLI (Recommended)

Run this command to apply the branch protection configuration:

```bash
gh api -X PUT /repos/amendez13/dropboxFamilyPhotoOrganizer/branches/main/protection \
  --input scripts/github/branch-protection-config.json
```

The configuration file is located at `scripts/github/branch-protection-config.json`.

### Option 2: Manual Configuration via GitHub UI

1. Go to the repository on GitHub
2. Click **Settings** → **Branches**
3. Under "Branch protection rules", click **Add rule**
4. Enter branch name pattern: `main`
5. Configure the following settings:

**Protect matching branches:**
- ☑ Require a pull request before merging
  - ☑ Require approvals: 1
  - ☑ Dismiss stale pull request approvals when new commits are pushed
  - ☐ Require review from Code Owners (optional)

- ☑ Require status checks to pass before merging
  - ☑ Require branches to be up to date before merging
  - Search and add these status checks:
    - `lint / Lint and Code Quality`
    - `test / Test Python (3.10)`
    - `test / Test Python (3.11)`
    - `test / Test Python (3.12)`
    - `validate-config / Validate Configuration`
    - `build-status / CI Status Check`

- ☑ Require conversation resolution before merging
- ☑ Require linear history
- ☐ Require signed commits (optional)
- ☐ Require deployments to succeed before merging
- ☑ Lock branch (make read-only) - Keep unchecked
- ☐ Do not allow bypassing the above settings
- ☑ Include administrators

6. Click **Create** or **Save changes**

## Working with Branch Protection

### For Pull Requests

When you create a pull request:

1. **CI checks will run automatically**
   - All required checks must pass
   - Fix any failures before requesting review

2. **Request a review** (if working with others)
   - At least one approval required
   - Address review comments
   - Resolve all conversations

3. **Merge when ready**
   - All checks must be green ✅
   - All reviews approved ✅
   - All conversations resolved ✅
   - Branch is up to date with `main` ✅

### Merge Strategies

**Recommended: Squash and Merge**
- Combines all PR commits into a single commit
- Keeps `main` history clean and readable
- Easier to revert if needed

**Alternative: Rebase and Merge**
- Replays PR commits on top of `main`
- Maintains individual commit history
- Good for well-organized PR commits

**Not Recommended: Merge Commit**
- Creates a merge commit
- Clutters history
- Disabled by "Require linear history" setting

### Bypassing Protection (Emergency Only)

If you absolutely need to bypass protection (emergency fixes only):

1. Go to Settings → Branches → Edit rule
2. Temporarily uncheck "Include administrators"
3. Push your emergency fix
4. Re-enable "Include administrators" immediately
5. Create a follow-up PR to properly fix the issue

**Note:** This should be extremely rare. Almost all changes should go through the normal PR process.

### Handling Merge Conflicts

If your PR conflicts with `main`:

1. **Update your branch:**
   ```bash
   git checkout your-branch
   git fetch origin
   git rebase origin/main
   ```

2. **Resolve conflicts:**
   - Edit conflicting files
   - Mark as resolved: `git add <file>`
   - Continue rebase: `git rebase --continue`

3. **Force push your branch:**
   ```bash
   git push --force-with-lease origin your-branch
   ```

4. **CI will re-run** on the updated branch

## Solo Developer Workflow

For solo developers (current scenario):

**You still benefit from branch protection:**
- ✅ Forces you to review changes before merging
- ✅ Ensures all tests pass
- ✅ Prevents accidental force pushes to `main`
- ✅ Creates clear history with PRs

**Self-review is acceptable:**
- Create a PR for your changes
- Review your own code (check diffs, read comments)
- Approve your own PR
- Merge when CI passes

**When to skip self-review:**
- Typo fixes in documentation
- Version bumps
- Dependency updates (Dependabot PRs)

## Monitoring and Maintenance

### Regular Reviews

**Weekly:**
- Check open PRs waiting for review
- Verify CI is passing on `main`

**Monthly:**
- Review branch protection settings
- Ensure required checks are still appropriate
- Add new checks as CI pipeline evolves

### Updating Status Checks

When you add new CI jobs:

1. Add them to required status checks in branch protection
2. Update this documentation
3. Update the `branch-protection-config.json` file

When you remove or rename CI jobs:

1. Remove them from required status checks
2. Update this documentation
3. Update the `branch-protection-config.json` file

## Troubleshooting

### "Required status check is expected but not reported"

**Cause:** The status check name doesn't match the job name in CI.

**Solution:**
1. Check the exact status check name in a recent PR
2. Update branch protection to use the exact name
3. Format: `<job-name> / <step-name>`

### "Require branches to be up to date" forcing constant rebases

**Cause:** Multiple PRs being worked on simultaneously.

**Solution:**
- Merge PRs one at a time
- Or disable "Require branches to be up to date" if not critical
- For solo work, this is usually not an issue

### Can't merge even though CI passes

**Possible causes:**
1. Missing required approvals → Approve the PR
2. Unresolved conversations → Resolve all comments
3. Branch not up to date → Rebase or merge `main` into your branch
4. Status check name mismatch → Check exact names

## Security Considerations

**What branch protection protects against:**
- ✅ Accidental pushes to `main`
- ✅ Merging broken code
- ✅ Merging unreviewed changes
- ✅ Force pushing over history
- ✅ Deleting the main branch

**What it doesn't protect against:**
- ❌ Compromised credentials (use 2FA, signed commits)
- ❌ Malicious code in dependencies (use Dependabot, security scans)
- ❌ Secrets in commits (use pre-commit hooks, secret scanning)

**Additional security measures:**
- Enable GitHub's secret scanning (already enabled)
- Use signed commits for critical changes
- Enable branch protection on other important branches (e.g., `develop`, `release/*`)
- Regularly rotate access tokens and secrets

## Best Practices

1. **Always work in feature branches**
   - Never commit directly to `main`
   - Use descriptive branch names: `feature/add-dark-mode`, `fix/auth-bug`

2. **Keep PRs focused and small**
   - Easier to review
   - Faster to merge
   - Less likely to conflict

3. **Write clear PR descriptions**
   - Explain what changed and why
   - Link to related issues
   - Add screenshots for UI changes

4. **Respond to review feedback promptly**
   - Address comments
   - Explain decisions
   - Be open to suggestions

5. **Keep your branch up to date**
   - Regularly rebase on `main`
   - Avoid long-lived feature branches

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Required Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
- [GitHub Pull Request Reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews)

## Changelog

### 2026-01-02 - Initial Configuration

**Added:**
- Branch protection for `main` branch
- Required status checks for CI pipeline
- Pull request review requirements
- Linear history enforcement
- Protection against force pushes and deletions
- This documentation
