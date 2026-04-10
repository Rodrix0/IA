$ErrorActionPreference = 'SilentlyContinue'
$shell = New-Object -ComObject WScript.Shell

$pathsToScan = @(
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:USERPROFILE\Desktop",
    "C:\Users\Public\Desktop"
)

$apps = @{}

# Parsear .lnk (Accesos Directos Nativos y Steam Win32 wrappers)
foreach ($path in $pathsToScan) {
    if (Test-Path $path) {
        Get-ChildItem -Path $path -Include *.lnk -Recurse | ForEach-Object {
            $shortcut = $shell.CreateShortcut($_.FullName)
            $name = $_.BaseName.ToLowerInvariant().Trim()
            $target = $shortcut.TargetPath

            # Si el target está vacío, ignoramos (casos corruptos o especiales OS)
            if (-Not [string]::IsNullOrWhiteSpace($target)) {
                $apps[$name] = $target
            }
        }
    }
}

# Parsear .url (Juegos de Epic Games, algunos Steam web launchers)
foreach ($path in $pathsToScan) {
    if (Test-Path $path) {
        Get-ChildItem -Path $path -Include *.url -Recurse | ForEach-Object {
             $content = Get-Content $_.FullName -ErrorAction SilentlyContinue
             $urlLine = $content | Where-Object { $_ -match "^URL=(.*)" }
             
             if ($urlLine) {
                 $url = $matches[1].Trim()
                 $name = $_.BaseName.ToLowerInvariant().Trim()
                 $apps[$name] = $url
             }
        }
    }
}

# Retornar como JSON
$apps | ConvertTo-Json -Compress
