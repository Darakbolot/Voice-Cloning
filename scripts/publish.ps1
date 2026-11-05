# Run from a normal Windows PowerShell session as the workspace owner.
# No ACL changes, token revocation, history rewriting, or force push.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE). Stopping." }
}

foreach ($program in @('git', 'python', 'node', 'gh')) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
        throw "Required command missing: $program. For GitHub CLI, install it and run gh auth login first."
    }
}

$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') { throw 'Expected branch main; inspect the branch before publishing.' }
$origin = & git remote get-url origin
if ($LASTEXITCODE -ne 0) { throw 'origin is missing. Use the URL already documented in this project; do not guess a URL.' }
$originUri = [Uri]$origin.Trim()
if ($originUri.Scheme -ne 'https' -or $originUri.Host -ne 'github.com' -or $originUri.UserInfo) {
    throw 'Expected a GitHub HTTPS remote without embedded credentials.'
}
$repositoryName = $originUri.AbsolutePath.Trim('/') -replace '\.git$', ''
if ($repositoryName.Split('/').Count -ne 2) { throw 'Unexpected repository URL.' }

$isPrivate = & gh repo view $repositoryName --json isPrivate --jq '.isPrivate'
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify repository visibility. Run gh auth login and check account access.' }
if (($isPrivate -join '').Trim() -ne 'true') { throw 'Repository is not Private. Stopping without uploading.' }

$lockPath = & git rev-parse --git-path index.lock
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve Git index path.' }
if (Test-Path -LiteralPath $lockPath) { throw 'Git index.lock exists. Check active Git processes before removing any lock manually.' }

$remoteRefs = @(& git ls-remote origin)
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect remote history. No staging, commit, or push was performed.' }
if ($remoteRefs.Count -gt 0) {
    Invoke-Checked -Program git -Arguments @('fetch', 'origin')
    throw 'Remote has existing history. Stop and follow docs/publishing.md to inspect and preserve it before publishing.'
}

Invoke-Checked -Program python -Arguments @('scripts/check_project.py')
Invoke-Checked -Program node -Arguments @('--check', 'apps/suwawa/static/app.js')
Invoke-Checked -Program python -Arguments @('scripts/audit_repository.py')
Invoke-Checked -Program git -Arguments @('status', '--short')
Invoke-Checked -Program git -Arguments @('add', '--', '.env.example', '.gitattributes', '.gitignore', 'README.md', 'apps', 'training', 'third_party', 'docs', 'scripts', 'tests', 'data/README.md')
Invoke-Checked -Program python -Arguments @('scripts/audit_repository.py')
Invoke-Checked -Program git -Arguments @('diff', '--cached', '--name-only')

& git diff --cached --quiet
$stagedChanges = $LASTEXITCODE
if ($stagedChanges -gt 1) { throw 'Cannot inspect index.' }
if ($stagedChanges -eq 1) {
    Invoke-Checked -Program git -Arguments @('commit', '-m', 'Initial commit: organize and secure Voice Cloning project')
}
$localCommit = & git rev-parse --verify HEAD
if ($LASTEXITCODE -ne 0) { throw 'There is no commit to publish.' }
Invoke-Checked -Program python -Arguments @('scripts/audit_repository.py')
# Recheck visibility immediately before uploading.
$isPrivate = & gh repo view $repositoryName --json isPrivate --jq '.isPrivate'
if ($LASTEXITCODE -ne 0 -or ($isPrivate -join '').Trim() -ne 'true') { throw 'Private visibility could not be confirmed.' }
Invoke-Checked -Program git -Arguments @('push', '-u', 'origin', 'main')
$remoteMain = @(& git ls-remote origin refs/heads/main)
if ($LASTEXITCODE -ne 0 -or $remoteMain.Count -ne 1) { throw 'Cannot verify remote main after push.' }
$remoteCommit = ($remoteMain[0] -split '\s+')[0]
if ($localCommit.Trim() -ne $remoteCommit) { throw 'Remote main does not match the local commit.' }
Write-Host "Verified push to Private repository: $repositoryName (main $remoteCommit)"
