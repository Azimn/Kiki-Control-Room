# Kiki OpenClaw Windows bootstrap. Run on the laptop, not the existing Jan PC.
[CmdletBinding()]
param([switch]$AuditOnly,[switch]$SkipInstall,[switch]$SkipHub,[switch]$SkipOnboarding)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$privateDir=Join-Path $env:LOCALAPPDATA 'KikiOpenClawPilot'
$workspace=Join-Path $HOME '.openclaw\workspace'
$bundle=Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'workspace'
function FindCli {
  $c=Get-Command openclaw -ErrorAction SilentlyContinue
  if($c){return $c.Source}
  $p=Join-Path $HOME '.openclaw\bin\openclaw.cmd'
  if(Test-Path $p){return $p}
  return $null
}
if([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT){throw 'Windows only'}
Write-Host ('OpenClaw CLI: '+[bool](FindCli))
Write-Host ('Ollama: '+[bool](Get-Command ollama -ErrorAction SilentlyContinue))
Write-Host ('Hermes: '+[bool](Get-Command hermes -ErrorAction SilentlyContinue))
Write-Host ('WSL: '+[bool](Get-Command wsl.exe -ErrorAction SilentlyContinue))
if($AuditOnly){Write-Host 'Read-only audit complete.';return}
New-Item -ItemType Directory -Path $privateDir -Force | Out-Null
$config=Join-Path $HOME '.openclaw\openclaw.json'
if(Test-Path $config){
  Copy-Item -LiteralPath $config -Destination (Join-Path $privateDir ('openclaw-config-'+(Get-Date -Format yyyyMMddHHmmss)+'.bak'))
  Write-Host 'Saved existing OpenClaw config locally, no secrets printed.'
}
$custom=([bool]$env:OPENCLAW_WORKSPACE_DIR) -or ([bool]$env:OPENCLAW_STATE_DIR) -or
  (([bool]$env:OPENCLAW_PROFILE) -and $env:OPENCLAW_PROFILE -ne 'default')
if(-not $custom -and -not (Test-Path $config)){New-Item -ItemType Directory -Path $workspace -Force | Out-Null}
foreach($name in @('AGENTS.md','SOUL.md','IDENTITY.md')){
  $from=Join-Path $bundle $name
  if(-not (Test-Path $from)){throw "Missing profile file: $name"}
  Copy-Item -LiteralPath $from -Destination (Join-Path $privateDir $name) -Force
  if(-not $custom -and -not (Test-Path $config)){
    $to=Join-Path $workspace $name
    if(-not (Test-Path $to)){Copy-Item -LiteralPath $from -Destination $to}
    else{Write-Host "Existing $name preserved; staged candidate available locally."}
  }
}
$cli=FindCli
if(-not $cli -and -not $SkipInstall){
  $installer=Join-Path $privateDir 'official-install.ps1'
  Invoke-WebRequest -UseBasicParsing -Uri 'https://openclaw.ai/install.ps1' -OutFile $installer
  & $installer -NoOnboard
  if(-not $?){throw 'Official CLI installation failed'}
  $cli=FindCli
  if(-not $cli){throw 'OpenClaw CLI not detected after install'}
}
if($cli -and -not $SkipOnboarding){
  Write-Host 'Official model and Gateway onboarding is starting.'
  & $cli onboard --install-daemon
  if(-not $?){throw 'Gateway onboarding failed'}
  & $cli gateway status --json
  if(-not $?){Write-Warning 'Gateway status not verified, use Hub Command Center'}
}
if(-not $SkipInstall -and -not $SkipHub){
  $hub=Join-Path $privateDir 'OpenClawCompanion-Setup-x64.exe'
  Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/openclaw/openclaw-windows-node/releases/latest/download/OpenClawCompanion-Setup-x64.exe' -OutFile $hub
  if((Get-AuthenticodeSignature -FilePath $hub).Status -ne 'Valid'){throw 'Hub installer signature invalid'}
  $proc=Start-Process -FilePath $hub -Wait -PassThru
  if($proc.ExitCode -ne 0){throw "Hub installer failed: $($proc.ExitCode)"}
}
Write-Host 'Setup stage completed. Connect Windows Hub to the existing Gateway using Advanced setup.'
Write-Host 'Original Jan PC and Telegram polling remain unchanged until verified migration.'
