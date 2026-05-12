using module .\ai-platform.psm1

param(
    [Parameter()]
    [ValidateSet("claude", "gh", "All")]
    [string]$AiPlatform = "All",
    [ValidateScript({ Test-Path $_ })]
    [string]$TargetRepoRoot = "./",
    [switch] $Force
)

$ErrorActionPreference = "Stop"

function New-AutomationLinks {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$TargetBaseDir,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$SourceBaseDir,

        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Mappings,

        [Parameter(Mandatory = $true)]
        [switch]$ForceReplace
    )
    
    foreach ($sourceName in $Mappings.Keys) {
        $linkName = $Mappings[$sourceName]
        $sourcePath = Join-Path -Path $SourceBaseDir -ChildPath $sourceName
        $linkPath = Join-Path -Path $TargetBaseDir -ChildPath $linkName

        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Source path does not exist: $sourcePath"
        }

        if (Test-Path -LiteralPath $linkPath) {
            $existingItem = Get-Item -LiteralPath $linkPath -Force
            $isSymbolicLink = $existingItem.LinkType -eq "SymbolicLink"
            $expectedTarget = (Resolve-Path -LiteralPath $sourcePath).Path
            $actualTarget = $null

            if ($isSymbolicLink) {
                try {
                    $actualTarget = (Resolve-Path -LiteralPath $linkPath).Path
                }
                catch {
                    # Broken symlink; treat as mismatch and replace if -Force is set.
                    $actualTarget = "<broken>"
                }
            }

            if ($isSymbolicLink -and $actualTarget -eq $expectedTarget) {
                Write-Host "Link already correct: $linkPath -> $expectedTarget"
                continue
            }

            if (-not $ForceReplace) {
                throw "Target already exists and differs: $linkPath. Re-run with -Force to replace."
            }

            Remove-Item -LiteralPath $linkPath -Recurse -Force
            Write-Host "Replaced existing path: $linkPath"
        }

        try {
            New-Item -ItemType SymbolicLink -Path $linkPath -Target $sourcePath | Out-Null
            Write-Host "Created symbolic link: $linkPath -> $sourcePath"
        }
        catch {
            # On Windows without admin/developer mode, symlink creation may fail.
            # Junction fallback only works for directories.
            $isDirectory = (Get-Item -LiteralPath $sourcePath).PSIsContainer
            if ($IsWindows -and $isDirectory -and $_.Exception.Message -like "*Administrator privilege required*") {
                New-Item -ItemType Junction -Path $linkPath -Target $sourcePath | Out-Null
                Write-Host "Created junction (symlink fallback): $linkPath -> $sourcePath"
            }
            else {
                throw
            }
        }
    }
}

# Single mapping table per platform.
# Each entry: Container = folder under repo root for the platform's links.
#             Mappings  = ordered map of <source-name-under-.ai-automation> -> <link-name-under-container>.
$mappedFolders = [ordered]@{
    "gh"     = @{
        Container = ".github"
        Mappings  = [ordered]@{
            "agents"          = "agents"
            "skills"          = "skills"
            "instructions"    = "instructions"
            "instructions.md" = "copilot-instructions.md"
        }
    }
    "claude" = @{
        Container = ".claude"
        Mappings  = [ordered]@{
            "agents"          = "agents"
            "skills"          = "skills"
            "instructions"    = "rules"
            "instructions.md" = "CLAUDE.md"
        }
    }
}


$targetRepoRoot = Resolve-Path -Path $TargetRepoRoot
$sourceBaseDir = Resolve-Path -Path ".ai-automation"

foreach ($platform in $mappedFolders.Keys) {
    if ($AiPlatform -eq "All" -or $platform -eq $AiPlatform) {
        $config = $mappedFolders[$platform]
        $targetBaseDir = Join-Path -Path $targetRepoRoot -ChildPath $config.Container

        if (-not (Test-Path -LiteralPath $targetBaseDir)) {
            New-Item -ItemType Directory -Path $targetBaseDir | Out-Null
            Write-Host "Created folder: $targetBaseDir"
        }

        New-AutomationLinks -TargetBaseDir $targetBaseDir -SourceBaseDir $sourceBaseDir -Mappings $config.Mappings -ForceReplace:$Force
    }
}