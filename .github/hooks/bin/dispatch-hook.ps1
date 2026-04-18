param(
  [Parameter(Mandatory = $true)]
  [string]$HookName
)

$optHome = $env:COPILOT_OPTIMIZER_HOME
if ([string]::IsNullOrWhiteSpace($optHome)) {
  $optHome = Join-Path $HOME ".copilot-optimizer"
}

$entrypoint = Join-Path $optHome "src/index.mjs"
if (-not (Test-Path $entrypoint)) {
  Write-Error "External optimizer entrypoint not found: $entrypoint"
  exit 1
}

$inputText = [Console]::In.ReadToEnd()
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "node"
$psi.Arguments = ('"{0}" hook {1}' -f $entrypoint, $HookName)
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi
$null = $process.Start()
$process.StandardInput.Write($inputText)
$process.StandardInput.Close()
$output = $process.StandardOutput.ReadToEnd()
$errorText = $process.StandardError.ReadToEnd()
$process.WaitForExit()
if (-not [string]::IsNullOrWhiteSpace($output)) { Write-Output $output }
if ($process.ExitCode -ne 0) {
  if (-not [string]::IsNullOrWhiteSpace($errorText)) { Write-Error $errorText }
  exit $process.ExitCode
}
