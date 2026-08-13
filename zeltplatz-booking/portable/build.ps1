# Builds the portable Windows test ZIP (embedded Python + built UI).
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File zeltplatz-booking\portable\build.ps1
$ErrorActionPreference = "Stop"

$PythonVersion = "3.12.10"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

$PortableDir = $PSScriptRoot
$AddonDir = Split-Path $PortableDir -Parent
$StageRoot = Join-Path $PortableDir "build"
$Stage = Join-Path $StageRoot "Zeltplatz-Buchung-Test"
$DistDir = Join-Path $PortableDir "dist"
$ZipPath = Join-Path $DistDir "Zeltplatz-Buchung-Test.zip"
$CacheDir = Join-Path $StageRoot "cache"

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Befehl '$Name' nicht gefunden. Bitte installieren und PATH prüfen."
    }
}

function Invoke-Download($Url, $OutFile) {
    Write-Host "Lade $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

Assert-Command "npm"
Assert-Command "tar"

Write-Host "Frontend bauen ..."
Push-Location (Join-Path $AddonDir "frontend")
try {
    if (-not (Test-Path "node_modules")) {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install fehlgeschlagen" }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build fehlgeschlagen" }
    if (-not (Test-Path "dist\index.html")) {
        throw "Frontend-Build fehlt: dist\index.html"
    }
}
finally {
    Pop-Location
}

if (Test-Path $Stage) {
    Remove-Item $Stage -Recurse -Force
}
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

$PyZip = Join-Path $CacheDir "python-embed.zip"
if (-not (Test-Path $PyZip)) {
    Invoke-Download $PythonUrl $PyZip
}

$PyDir = Join-Path $Stage "python"
New-Item -ItemType Directory -Path $PyDir -Force | Out-Null
Expand-Archive -Path $PyZip -DestinationPath $PyDir -Force

$Pth = Get-ChildItem -Path $PyDir -Filter "python*._pth" | Select-Object -First 1
if (-not $Pth) { throw "python*._pth nicht im Embeddable-Paket gefunden" }
@(
    "python312.zip"
    "."
    "Lib\site-packages"
    "import site"
) | Set-Content -Path $Pth.FullName -Encoding ascii

$GetPip = Join-Path $CacheDir "get-pip.py"
if (-not (Test-Path $GetPip)) {
    Invoke-Download $GetPipUrl $GetPip
}

$PythonExe = Join-Path $PyDir "python.exe"
Write-Host "pip installieren ..."
& $PythonExe $GetPip --no-warn-script-location --no-cache-dir
if ($LASTEXITCODE -ne 0) { throw "get-pip.py fehlgeschlagen" }

$Req = Join-Path $PortableDir "requirements-runtime.txt"
Write-Host "Python-Pakete installieren ..."
& $PythonExe -m pip install --no-cache-dir --no-warn-script-location -r $Req
if ($LASTEXITCODE -ne 0) { throw "pip install fehlgeschlagen" }

Write-Host "Anwendung kopieren ..."
$BackendSrc = Join-Path $AddonDir "backend"
$BackendDst = Join-Path $Stage "app\backend"
New-Item -ItemType Directory -Path $BackendDst -Force | Out-Null
robocopy $BackendSrc $BackendDst /E `
    /XD .venv __pycache__ .testdata .pytest_cache tests alembic `
    /XF *.pyc *.pyo `
    /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy backend fehlgeschlagen (Code $LASTEXITCODE)" }

$FrontDst = Join-Path $Stage "app\frontend\dist"
New-Item -ItemType Directory -Path $FrontDst -Force | Out-Null
robocopy (Join-Path $AddonDir "frontend\dist") $FrontDst /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy frontend fehlgeschlagen (Code $LASTEXITCODE)" }

Copy-Item (Join-Path $PortableDir "launch.py") (Join-Path $Stage "launch.py") -Force
Copy-Item (Join-Path $PortableDir "Start.bat") (Join-Path $Stage "Start.bat") -Force
Copy-Item (Join-Path $PortableDir "Stop.bat") (Join-Path $Stage "Stop.bat") -Force
Copy-Item (Join-Path $PortableDir "Reset-Demodaten.bat") (Join-Path $Stage "Reset-Demodaten.bat") -Force
Copy-Item (Join-Path $PortableDir "ANLEITUNG.txt") (Join-Path $Stage "ANLEITUNG.txt") -Force

# Drop pip caches / leftover installer from the staged Python tree
$PipJunk = @(
    (Join-Path $PyDir "get-pip.py")
)
foreach ($item in $PipJunk) {
    if (Test-Path $item) { Remove-Item $item -Force }
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Write-Host "ZIP schreiben: $ZipPath"
Push-Location $StageRoot
try {
    tar -a -c -f $ZipPath "Zeltplatz-Buchung-Test"
    if ($LASTEXITCODE -ne 0) { throw "ZIP-Erstellung fehlgeschlagen" }
}
finally {
    Pop-Location
}

$Zip = Get-Item $ZipPath
Write-Host ("Fertig: {0} ({1:N1} MB)" -f $Zip.FullName, ($Zip.Length / 1MB))
