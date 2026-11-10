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
$install = !(Test-Path -LiteralPath $target)
if (!$install) {
    $installedHash = (Get-FileHash -LiteralPath $target).Hash
    if ($installedHash -cne (Get-FileHash -LiteralPath $source).Hash) {
        if ($installedHash -cne '497A3E0D9967079678F09DE94E0D524F7FD35D9F5B65B3DADD185B6EC73B7EE9') {
            throw 'A locally modified Kiki Slack prompt module exists. Review it before replacing it.'
        }
        $install = $true
    }
}
if ($install) {
    Copy-Item -LiteralPath $source -Destination $target -Force
}
if ($patchState -eq 'apply') {
    & git -C $checkout apply $patch
    if ($LASTEXITCODE -ne 0) { throw 'Could not apply the checked Dodaios hook.' }
}
Write-Output 'Kiki Slack prompt installed. Restart Dodaios normally, then verify a private recall and a channel reply.'
