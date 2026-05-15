param(
  [string]$HostName = "192.168.110.5",
  [string]$User = "root",
  [string]$RemoteDir = "/opt/sandbox-control"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking SSH reachability..."
ssh -o BatchMode=yes -o ConnectTimeout=5 "$User@$HostName" "echo ok"

Write-Host "Packaging project..."
$archive = Join-Path $env:TEMP "sandbox-control.tar"
if (Test-Path $archive) { Remove-Item $archive -Force }
tar --exclude .git --exclude node_modules --exclude .venv --exclude dist -cf $archive .

Write-Host "Uploading to $HostName..."
ssh "$User@$HostName" "mkdir -p $RemoteDir"
scp $archive "$User@$HostName:$RemoteDir/sandbox-control.tar"

Write-Host "Deploying..."
ssh "$User@$HostName" "cd $RemoteDir && tar -xf sandbox-control.tar && cp .env.example .env 2>/dev/null || true && docker compose -f deploy/compose.yml up -d --build"

Write-Host "Done: http://$HostName:8080"
