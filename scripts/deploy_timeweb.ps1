# PowerShell helper to run the server deploy script over SSH from Windows
# Usage: .\scripts\deploy_timeweb.ps1 -Host <ip> -User <user> -RepoPath /opt/altbot
param(
    [Parameter(Mandatory=$true)]
    [string]$Host,
    [Parameter(Mandatory=$true)]
    [string]$User,
    [string]$RepoPath = "/opt/altbot",
    [string]$ComposeFile = "docker-compose.prod.yml"
)

# This script requires OpenSSH client (ssh) available in the environment.
$remoteCmd = @(
    "set -euo pipefail",
    "if [ ! -d '$RepoPath' ]; then echo 'Repo not found at $RepoPath'; exit 2; fi",
    "cd $RepoPath",
    "if [ ! -f .env ]; then if [ -f .env.example ]; then cp .env.example .env; echo 'Please edit .env and fill secrets, then re-run this script.'; exit 1; else echo '.env.example not found'; exit 1; fi; fi",
    "sudo bash scripts/deploy_timeweb.sh $RepoPath $ComposeFile"
) -join "; "

Write-Host "Running deploy on $User@$Host..."
ssh $User@$Host $remoteCmd