$ErrorActionPreference = "Stop"

$sharedDll = Get-ChildItem `
    "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" `
    -Filter "avcodec-*.dll" `
    -Recurse `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -match "Gyan\.FFmpeg\.Shared"
    } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $sharedDll) {
    throw "FFmpeg full-shared installation was not found."
}

$sharedBin = $sharedDll.Directory.FullName

$sitePackages = (
    python -c "import site; print(site.getsitepackages()[0])"
).Trim()

$pthPath = Join-Path `
    $sitePackages `
    "indicf5_ffmpeg_dll_runtime.pth"

$pthLine = (
    "import os,builtins; " +
    "_indicf5_ffmpeg=r'$sharedBin'; " +
    "os.environ['PATH']=" +
    "_indicf5_ffmpeg+os.pathsep+" +
    "os.environ.get('PATH',''); " +
    "builtins._indicf5_ffmpeg_dll_handle=" +
    "os.add_dll_directory(_indicf5_ffmpeg)"
)

$pthLine |
    Set-Content `
        -LiteralPath $pthPath `
        -Encoding ascii

Write-Host "Shared FFmpeg:" $sharedBin
Write-Host "Startup file :" $pthPath
Write-Host "Configuration completed."
