param([string]$PayloadPath)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$work = Join-Path $root 'build'
$dist = Join-Path $root 'dist'
$python = Join-Path $root '.venv\Scripts\python.exe'
$compiler = Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Windows .NET Framework 4.x compiler was not found.' }
New-Item -ItemType Directory -Path $work,$dist,(Join-Path $work 'temp') -Force | Out-Null
$oldTemp, $oldTmp, $oldConfig, $oldGpu = $env:TEMP, $env:TMP, $env:PYINSTALLER_CONFIG_DIR, $env:PYGFX_DATA_DIR
Push-Location $root
try {
    $env:TEMP = $env:TMP = Join-Path $work 'temp'
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $work 'pyinstaller-cache'
    $env:PYGFX_DATA_DIR = Join-Path $work 'pygfx'
    New-Item -ItemType Directory -Path $env:PYGFX_DATA_DIR -Force | Out-Null
    if (-not $PayloadPath) {
        & $python -B -m PyInstaller --noconfirm --clean --workpath (Join-Path $work 'pyinstaller') --distpath (Join-Path $work 'payload') (Join-Path $PSScriptRoot 'PointLabStudio.spec')
        if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
        $PayloadPath = (Get-ChildItem -LiteralPath (Join-Path $work 'payload') -Filter '*.exe' | Select-Object -First 1).FullName
    }
    $payload = Get-Item -LiteralPath $PayloadPath
    try {
        $null = [Reflection.AssemblyName]::GetAssemblyName($payload.FullName)
        throw 'Use the native PyInstaller payload, not an already wrapped release EXE.'
    } catch [BadImageFormatException] { }
    $version = $payload.VersionInfo.FileVersion
    if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'The payload has no valid release version.' }
    $name = "PointLabStudio-v$version-Windows-x64.exe"
    $metadata = Join-Path $work 'LauncherVersion.cs'
    @"
using System.Reflection;
[assembly: AssemblyTitle("PointLab Studio")]
[assembly: AssemblyProduct("PointLab Studio")]
[assembly: AssemblyVersion("$version.0")]
[assembly: AssemblyFileVersion("$version")]
[assembly: AssemblyInformationalVersion("$version")]
"@ | Set-Content -LiteralPath $metadata -Encoding UTF8
    Add-Type -AssemblyName System.Drawing
    $iconPath = Join-Path $work 'launcher.ico'
    $icon = [Drawing.Icon]::ExtractAssociatedIcon($payload.FullName)
    $iconStream = [IO.File]::Create($iconPath)
    try { $icon.Save($iconStream) } finally { $iconStream.Dispose(); $icon.Dispose() }
    $staging = Join-Path $work $name
    & $compiler /nologo /codepage:65001 /target:winexe /platform:x64 /optimize+ "/out:$staging" "/win32icon:$iconPath" "/resource:$($payload.FullName),PointLabPayload" $metadata (Join-Path $PSScriptRoot 'Launcher.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed.' }
    Move-Item -LiteralPath $staging -Destination (Join-Path $dist $name) -Force
    Write-Output "Built: $(Join-Path $dist $name)"
} finally {
    $env:TEMP, $env:TMP, $env:PYINSTALLER_CONFIG_DIR, $env:PYGFX_DATA_DIR = $oldTemp, $oldTmp, $oldConfig, $oldGpu
    Pop-Location
}
