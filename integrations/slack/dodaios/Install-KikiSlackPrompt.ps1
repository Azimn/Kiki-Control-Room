[CmdletBinding()]
param([string] $DodaiosPath = (Join-Path $env:USERPROFILE '.dodaios'))

$ErrorActionPreference = 'Stop'
$checkout = (Resolve-Path -LiteralPath $DodaiosPath).Path
$patch = Join-Path $PSScriptRoot 'side-chat.patch'
$source = Join-Path $PSScriptRoot 'kiki_slack_prompt.py'
$hook = Join-Path $checkout 'dodaios/agentic_ide/side_chat.py'
$target = Join-Path $checkout 'dodaios/agentic_ide/kiki_slack_prompt.py'
$brain = Join-Path $checkout 'dodaios/brain/manager.py'
$memory = Join-Path $checkout 'dodaios/brain/kiki_continuity.py'
if (!(Test-Path -LiteralPath $hook -PathType Leaf) -or
    !(Select-String -LiteralPath $brain -SimpleMatch 'async def render_surface_prompt(' -Quiet) -or
    !(Test-Path -LiteralPath $memory -PathType Leaf) -or
    !(Select-String -LiteralPath $memory -SimpleMatch 'async def _rpc(' -Quiet)) {
    throw 'This checkout is missing the Dodaios prompt renderer or Kiki continuity bridge.'
}
$patchState = 'apply'
& git -C $checkout apply --check $patch 2>$null
if ($LASTEXITCODE -ne 0) {
    & git -C $checkout apply --reverse --check $patch 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'The Dodaios hook changed upstream. Review side-chat.patch before installing.'
    }
    $patchState = 'already applied'
}
if (Test-Path -LiteralPath $target) {
    if ((Get-FileHash -LiteralPath $target).Hash -cne (Get-FileHash -LiteralPath $source).Hash) {
        throw 'A different Kiki Slack prompt module exists. Back it up and review the difference before replacing it.'
    }
} else {
    Copy-Item -LiteralPath $source -Destination $target
}
if ($patchState -eq 'apply') {
    & git -C $checkout apply $patch
    if ($LASTEXITCODE -ne 0) { throw 'Could not apply the checked Dodaios hook.' }
}
Write-Output 'Kiki Slack prompt installed. Restart Dodaios normally, then verify a private recall and a channel reply.'
