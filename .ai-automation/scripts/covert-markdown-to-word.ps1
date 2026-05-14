[CmdletBinding()]
param(
	[string]$SourceMdDir = "./sad",
	[string]$TargeOutputDir = "./.workflow-temp/sad-word/",
	[string]$WordDocName = "sad.docx"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command -Name "pandoc" -ErrorAction SilentlyContinue)) {
	throw "pandoc was not found in PATH. Install pandoc first and retry."
}

$resolvedSourceDir = (Resolve-Path -LiteralPath $sourceMdDir).Path

if (-not (Test-Path -LiteralPath $targeOutputDir)) {
	New-Item -ItemType Directory -Path $targeOutputDir -Force | Out-Null
}

$resolvedOutputDir = (Resolve-Path -LiteralPath $targeOutputDir).Path

$markdownFiles = Get-ChildItem -LiteralPath $resolvedSourceDir -Filter "*.md" -File -Recurse |
	Sort-Object -Property FullName

if ($markdownFiles.Count -eq 0) {
	throw "No markdown files were found under '$resolvedSourceDir'."
}

if ([string]::IsNullOrWhiteSpace([System.IO.Path]::GetExtension($wordDocName))) {
	$wordDocName = "$wordDocName.docx"
}

$outputDocPath = Join-Path -Path $resolvedOutputDir -ChildPath $wordDocName

Write-Host "Converting $($markdownFiles.Count) markdown files into '$outputDocPath'..."

# Run pandoc from source directory so relative paths and local assets resolve correctly.
Push-Location -Path $resolvedSourceDir
try {
	$inputMarkdownPaths = $markdownFiles |
		ForEach-Object { [System.IO.Path]::GetRelativePath($resolvedSourceDir, $_.FullName) }

	$tempWordDocName = "{0}.{1}.tmp.docx" -f [System.IO.Path]::GetFileNameWithoutExtension($wordDocName), [Guid]::NewGuid().ToString("N")
	$tempWordDocPath = Join-Path -Path $resolvedSourceDir -ChildPath $tempWordDocName

	$pandocArgs = @("-s", "--toc")
	# DO NOTDELETE
	# $pandocArgs += @( "--lua-filter", "C:\Users\USERNAME\AppData\Roaming\pandoc\lua-filters\test.lua" )

	$pandocArgs += $inputMarkdownPaths
	$pandocArgs += @("-o", $tempWordDocPath)

	& pandoc @pandocArgs

	if ($LASTEXITCODE -ne 0) {
		throw "pandoc failed with exit code $LASTEXITCODE."
	}

	Move-Item -LiteralPath $tempWordDocPath -Destination $outputDocPath -Force
}
finally {
	Pop-Location
}

Write-Host "Word document created: $outputDocPath"
