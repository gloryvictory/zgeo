param(
    [string]$ProfileRoot
)

$ErrorActionPreference = "Stop"

$pluginRoot = Split-Path -Parent $PSScriptRoot
$pluginName = Split-Path -Leaf $pluginRoot
$metadataPath = Join-Path $pluginRoot "metadata.txt"

if (-not (Test-Path -LiteralPath $metadataPath)) {
    throw "metadata.txt not found: $metadataPath"
}

if (-not $ProfileRoot) {
    $ProfileRoot = Join-Path $env:APPDATA "QGIS\QGIS4\profiles\default\python\plugins"
}

if (-not (Test-Path -LiteralPath $ProfileRoot)) {
    throw "QGIS plugin directory not found: $ProfileRoot"
}

$target = Join-Path $ProfileRoot $pluginName

$versionLine = Select-String -LiteralPath $metadataPath -Pattern '^version=(.+)$'
if (-not $versionLine) {
    throw "version is not defined in metadata.txt"
}
$version = $versionLine.Matches[0].Groups[1].Value.Trim()

$excludedNames = @(
    "__pycache__",
    "dist",
    "scripts",
    "tests",
    ".empryo",
    ".git",
    ".gitignore",
    "AGENTS.md",
    ".idea",
    ".vscode"
)

$excludedDirectories = $excludedNames | Where-Object {
    $_ -ne ".gitignore" -and $_ -ne "AGENTS.md"
}
$excludedFiles = @(".gitignore", "AGENTS.md")

$arguments = @(
    $pluginRoot,
    $target,
    "/MIR",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS",
    "/XJ",
    "/R:1",
    "/W:1",
    "/MT:8",
    "/XD"
) + $excludedDirectories + @("/XF") + $excludedFiles

& robocopy @arguments | Out-Null
$code = $LASTEXITCODE
if ($code -ge 8) {
    throw "robocopy failed with exit code $code"
}

$cachePath = Join-Path $target "__pycache__"
if (Test-Path -LiteralPath $cachePath) {
    Remove-Item -LiteralPath $cachePath -Recurse -Force
}

Write-Host "Updated: $target (version $version)"
Write-Host "Reload in QGIS: Plugins > Manage and Install Plugins > Reload ZGeo"
