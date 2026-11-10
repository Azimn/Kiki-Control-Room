[CmdletBinding()]
param(
    [string] $DodaiosPath = (Join-Path $env:USERPROFILE '.dodaios'),
    [string] $SlackPolicyPath = (Join-Path $env:LOCALAPPDATA 'KikiSlack/slack.json')
)

$ErrorActionPreference = 'Stop'
$checkout = (Resolve-Path -LiteralPath $DodaiosPath).Path
$patch = Join-Path $PSScriptRoot 'main-agent.patch'
$legacyPatch = Join-Path $PSScriptRoot 'side-chat.patch'
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
$policy = Get-Content -LiteralPath $SlackPolicyPath -Raw | ConvertFrom-Json
$dm = $policy.dodaios_chat.session
$channel = $policy.peer_exchange.dodaios_session
$model = $policy.dodaios_chat.model
if (!$model -or (!$dm -and !$channel) -or ($dm -and $dm -eq $channel) -or
    ($dm -and ($dm -cnotmatch '^[a-f0-9-]{12,64}$' -or
               @($policy.allowed_users).Count -ne 1 -or @($policy.allowed_channels).Count -ne 1 -or
               $policy.allowed_channels[0] -cnotmatch '^D[A-Z0-9]+$')) -or
    ($channel -and ($channel -cnotmatch '^[a-f0-9-]{12,64}$' -or
                   $policy.peer_exchange.channel -cnotmatch '^[CG][A-Z0-9]+$'))) {
    throw 'Slack policy does not contain valid dedicated Dodaios session bindings.'
}
$binding = Join-Path $checkout 'integrations/kiki-continuity/slack-sessions.json'
$bindingDirectory = Split-Path -Parent $binding
$patchState = 'apply'
& git -C $checkout apply --check $patch 2>$null
if ($LASTEXITCODE -ne 0) {
    & git -C $checkout apply --reverse --check $patch 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'The main Dodaios agent path changed upstream. Review main-agent.patch before installing.'
    }
    $patchState = 'already applied'
}
$install = !(Test-Path -LiteralPath $target)
if (!$install) {
    $installedHash = (Get-FileHash -LiteralPath $target).Hash
    if ($installedHash -cne (Get-FileHash -LiteralPath $source).Hash) {
        if ($installedHash -cne 'CBF8646A9F505F7FFF411B9F85E40A80BA3FF50B151E8F840110E54F2B146542' -and $installedHash -cne '497A3E0D9967079678F09DE94E0D524F7FD35D9F5B65B3DADD185B6EC73B7EE9' -and $installedHash -cne '46EC0E125B2984E169DEE0285975E7D08660AD65ED808A90D0E3583F15A10392' -and $installedHash -cne 'D991AE159B2FE2480AFCDD246130899F01E7B4C5F6B9C17F60EC81B296D06A0B' -and $installedHash -cne 'FF640560E22586B4402787E38FA842CA6F01959549A3218E80D4D8D196B28EB9') {
            throw 'A locally modified Kiki Slack prompt module exists. Review it before replacing it.'
        }
        $install = $true
    }
}
$legacyHook = Select-String -LiteralPath $hook -SimpleMatch 'import slack_system_prompt' -Quiet
if ($legacyHook) {
    & git -C $checkout apply --reverse --check $legacyPatch
    if ($LASTEXITCODE -ne 0) { throw 'Review the old Slack side-chat hook before upgrading.' }
}
if ($install) {
    Copy-Item -LiteralPath $source -Destination $target -Force
}
if ($patchState -eq 'apply') {
    & git -C $checkout apply $patch
    if ($LASTEXITCODE -ne 0) { throw 'Could not apply the checked Dodaios hook.' }
}
if ($legacyHook) {
    & git -C $checkout apply --reverse $legacyPatch
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove the checked legacy Slack side-chat hook.' }
}
New-Item -ItemType Directory -Path $bindingDirectory -Force | Out-Null
$bindingJson = @{ model = $model; dm = $dm; channel = $channel } | ConvertTo-Json
$tempBinding = Join-Path $bindingDirectory ('slack-sessions-' + [guid]::NewGuid().ToString('N') + '.tmp')
[IO.File]::WriteAllText($tempBinding, $bindingJson, [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $tempBinding -Destination $binding -Force
Write-Output 'Kiki main-agent Slack route installed. Restart Dodaios normally, then verify a private recall and a channel reply.'
