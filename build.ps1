[CmdletBinding()]
param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if ($PythonPath) {
    $python = (Resolve-Path -LiteralPath $PythonPath).Path
    $pythonArguments = @()
} elseif (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
    $pythonArguments = @()
} elseif ($pythonCommand = Get-Command python -ErrorAction SilentlyContinue) {
    $python = $pythonCommand.Source
    $pythonArguments = @()
} elseif ($pyCommand = Get-Command py -ErrorAction SilentlyContinue) {
    $python = $pyCommand.Source
    $pythonArguments = @("-3.12")
} else {
    throw "Python 3.12 or a project .venv is required."
}

& $python @pythonArguments -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller is not installed. Run: python -m pip install -e ".[build]"'
}

$entryPoint = Join-Path $projectRoot "src\clopen_entry.py"
$sourcePath = Join-Path $projectRoot "src"
$distPath = Join-Path $projectRoot "dist"
$buildPath = Join-Path $projectRoot "build"
$resourcePath = Join-Path $projectRoot "src\clopen\resources"
$qmlPath = Join-Path $projectRoot "src\clopen\qml"
$iconPath = Join-Path $resourcePath "clopen.ico"

$oldArtifactDir = Join-Path $distPath "Clopen-LiquidGlass"
if (Test-Path -LiteralPath $oldArtifactDir) {
    Remove-Item -LiteralPath $oldArtifactDir -Recurse -Force
}

& $python @pythonArguments -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name "Clopen-LiquidGlass" `
    --icon $iconPath `
    --add-data "$resourcePath;clopen/resources" `
    --add-data "$qmlPath;clopen/qml" `
    --hidden-import PySide6.QtQml `
    --hidden-import PySide6.QtQuick `
    --hidden-import PySide6.QtQuickControls2 `
    --paths $sourcePath `
    --distpath $distPath `
    --workpath $buildPath `
    --specpath $buildPath `
    $entryPoint

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed while building Clopen-LiquidGlass.exe."
}

$artifact = Join-Path $distPath "Clopen-LiquidGlass\Clopen-LiquidGlass.exe"
if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
    throw "Expected build artifact was not created: $artifact"
}

$releaseDocuments = @(
    "LICENSE",
    "README.md",
    "PRIVACY.md",
    "THIRD_PARTY_NOTICES.md"
)
foreach ($document in $releaseDocuments) {
    $sourceDocument = Join-Path $projectRoot $document
    Copy-Item -LiteralPath $sourceDocument -Destination $oldArtifactDir -Force
}

Write-Host "Built: $artifact"
