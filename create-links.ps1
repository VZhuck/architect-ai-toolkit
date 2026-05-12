param(
    [Parameter()]
    [ValidateSet("claude", "gh", "All")]
    [string]$AiPlatform = "All",
    [ValidateScript({ Test-Path $_ })]
    [string]$TargetRepoRoot = "./",
    [switch] $Force
)

$ErrorActionPreference = "Stop"

function Test-ContainerMapping {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$ContainerMapping
    )

    foreach ($requiredKey in @("TargetContainer", "SourceContainer", "Mappings")) {
        if (-not $ContainerMapping.Contains($requiredKey)) {
            throw "ContainerMapping must contain '$requiredKey'."
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$ContainerMapping["TargetContainer"])) {
        throw "ContainerMapping.TargetContainer cannot be empty."
    }

    if ([string]::IsNullOrWhiteSpace([string]$ContainerMapping["SourceContainer"])) {
        throw "ContainerMapping.SourceContainer cannot be empty."
    }

    if (-not ($ContainerMapping["Mappings"] -is [System.Collections.IDictionary])) {
        throw "ContainerMapping.Mappings must be a dictionary."
    }

    return $true
}

function Resolve-ExistingLinkConflict {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LinkPath,

        [Parameter(Mandatory = $true)]
        [string]$SourcePath,

        [Parameter(Mandatory = $true)]
        [switch]$ForceReplace
    )

    if (-not (Test-Path -LiteralPath $LinkPath)) {
        return $false
    }

    $existingItem = Get-Item -LiteralPath $LinkPath -Force
    $isSymbolicLink = $existingItem.LinkType -eq "SymbolicLink"
    $expectedTarget = (Resolve-Path -LiteralPath $SourcePath).Path
    $actualTarget = $null

    if ($isSymbolicLink) {
        try {
            $actualTarget = (Resolve-Path -LiteralPath $LinkPath).Path
        }
        catch {
            # Broken symlink; treat as mismatch and replace if -Force is set.
            $actualTarget = "<broken>"
        }
    }

    if ($isSymbolicLink -and $actualTarget -eq $expectedTarget) {
        Write-Host "Link already correct: $LinkPath -> $expectedTarget"
        return $true
    }

    if (-not $ForceReplace) {
        throw "Target already exists and differs: $LinkPath. Re-run with -Force to replace."
    }

    Remove-Item -LiteralPath $LinkPath -Recurse -Force
    Write-Host "Replaced existing path: $LinkPath"
    return $false
}

function New-AutomationLinks {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$TargetRepoRoot,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$SourceRepoRoot,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-ContainerMapping $_ })]
        [System.Collections.IDictionary]$ContainerMapping,

        [Parameter(Mandatory = $true)]
        [switch]$ForceReplace
    )

    $targetBaseDir = Join-Path -Path (Resolve-Path -LiteralPath $TargetRepoRoot).Path -ChildPath $ContainerMapping["TargetContainer"]
    $sourceBaseDir = Join-Path -Path (Resolve-Path -LiteralPath $SourceRepoRoot).Path -ChildPath $ContainerMapping["SourceContainer"]

    if (-not (Test-Path -LiteralPath $targetBaseDir)) {
        New-Item -ItemType Directory -Path $targetBaseDir | Out-Null
        Write-Host "Created folder: $targetBaseDir"
    }

    $resolvedTargetBaseDir = (Resolve-Path -LiteralPath $targetBaseDir).Path

    foreach ($sourceName in $ContainerMapping["Mappings"].Keys) {
        $linkName = $ContainerMapping["Mappings"][$sourceName]
        $sourcePath = Join-Path -Path $sourceBaseDir -ChildPath $sourceName
        $linkPath = Join-Path -Path $resolvedTargetBaseDir -ChildPath $linkName

        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Source path does not exist: $sourcePath"
        }

        if (Resolve-ExistingLinkConflict -LinkPath $linkPath -SourcePath $sourcePath -ForceReplace:$ForceReplace) {
            continue
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
$mappedPaths = [ordered]@{
    "gh"              = @{
        TargetContainer = ".github"
        SourceContainer = ".ai-automation"
        Mappings        = [ordered]@{
            "agents"          = "agents"
            "skills"          = "skills"
            "instructions"    = "instructions"
        }
    }
    "claude"          = @{
        TargetContainer = ".claude"
        SourceContainer = ".ai-automation"
        Mappings        = [ordered]@{
            "agents"          = "agents"
            "skills"          = "skills"
            "instructions"    = "rules"
            "instructions.md" = "CLAUDE.md"
            "scripts"         = "scripts"
        }
    }
    "shared" = @{
        TargetContainer = ".ai-automation"
        SourceContainer = ".ai-automation"
        Mappings        = [ordered]@{
            "scripts" = "scripts"
        }
    }
}

$initFileMapping = @{
    "gh"     = @{
        TargetContainer = ".github"
        SourceContainer = ".ai-automation"
        Mappings        = [ordered]@{
            "instructions.md"  = "copilot-instructions.md"
        }
    }
    "claude" = @{
        TargetContainer = "./"
        SourceContainer = ".ai-automation"
        Mappings        = [ordered]@{
            "instructions.md" = "CLAUDE.md"
        }
    }
}

function New-MainPlatformFile {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$TargetRepoRoot,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$SourceRepoRoot,

        [Parameter(Mandatory = $true)]
        [string]$Platform,

        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$InitFileMapping
    )

    if (-not $InitFileMapping.Contains($Platform)) {
        throw "Init file mapping not found for platform '$Platform'."
    }

    $platformMapping = $InitFileMapping[$Platform]
    if (-not (Test-ContainerMapping -ContainerMapping $platformMapping)) {
        throw "Invalid init file mapping for platform '$Platform'."
    }

    $resolvedTargetRepoRoot = (Resolve-Path -LiteralPath $TargetRepoRoot).Path
    $resolvedSourceRepoRoot = (Resolve-Path -LiteralPath $SourceRepoRoot).Path

    $targetBaseDir = Join-Path -Path $resolvedTargetRepoRoot -ChildPath $platformMapping["TargetContainer"]
    $sourceBaseDir = Join-Path -Path $resolvedSourceRepoRoot -ChildPath $platformMapping["SourceContainer"]

    if (-not (Test-Path -LiteralPath $targetBaseDir)) {
        New-Item -ItemType Directory -Path $targetBaseDir | Out-Null
        Write-Host "Created folder: $targetBaseDir"
    }

    foreach ($sourceName in $platformMapping["Mappings"].Keys) {
        $targetName = $platformMapping["Mappings"][$sourceName]
        $sourceFilePath = Join-Path -Path $sourceBaseDir -ChildPath $sourceName
        $targetFilePath = Join-Path -Path $targetBaseDir -ChildPath $targetName

        if (Test-Path -LiteralPath $targetFilePath) {
            Write-Host "Main platform file already exists: $targetFilePath"
            Write-Host "  (Not modified, even with -Force)"
            continue
        }

        if (-not (Test-Path -LiteralPath $sourceFilePath)) {
            Write-Host "Source file not found: $sourceFilePath"
            continue
        }

        Copy-Item -LiteralPath $sourceFilePath -Destination $targetFilePath
        Write-Host "Created main platform file: $targetFilePath"
    }
}

foreach ($platform in $mappedPaths.Keys) {
    if ($AiPlatform -eq "All" -or $platform -eq $AiPlatform -or $platform -eq "shared") {
        $config = $mappedPaths[$platform]

        New-AutomationLinks -TargetRepoRoot $TargetRepoRoot -SourceRepoRoot $PSScriptRoot -ContainerMapping $config -ForceReplace:$Force
    }
}

# Create main platform files one time using mapping metadata.
foreach ($platform in $initFileMapping.Keys) {
    if ($AiPlatform -eq "All" -or $platform -eq $AiPlatform) {
        New-MainPlatformFile -TargetRepoRoot $TargetRepoRoot -SourceRepoRoot $PSScriptRoot -Platform $platform -InitFileMapping $initFileMapping
    }
}