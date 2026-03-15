# Feature: Show changelog on update

## Summary
When running `redictum update`, show not only the available version number but also the list of changes/improvements included in the new version.

## Problem
Currently `redictum update` only checks and displays the version number to update to. The user has no idea *what* changed — they have to manually visit GitHub to read the changelog before deciding whether to update.

## Desired Behavior
- `redictum update` shows the new version number **and** a summary of changes
- User can make an informed decision about whether to update

## Open Questions
- **Source of changelog data**: fetch from GitHub Release notes? Parse CHANGELOG.md from the repo? Use GitHub API (`gh api`)?
- **Display format**: full changelog section? Condensed bullet points? Truncate if too long?
- **Multiple versions**: if user is 3 versions behind, show all intermediate changelogs or just the target version?
- **Offline fallback**: what to show if changelog fetch fails (network issues)?

## Notes
- GitHub Releases already contain structured release notes — easiest source
- Could use GitHub API: `https://api.github.com/repos/iiifx/redictum-terminal-py/releases/latest`
- Consider colorized output for readability (headers, bullet points)
