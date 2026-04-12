param(
    [Parameter(Mandatory=$false)]
    [string]$ContactName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$MessageText = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

$wshell = New-Object -ComObject wscript.shell

# Buscamos la app nativa de WhatsApp o cualquier navegador que tenga la pestaña de WhatsApp ACTIVA
$waProcess = Get-Process | Where-Object { $_.MainWindowTitle -match "(?i)WhatsApp" -or $_.ProcessName -match "(?i)WhatsApp" } | Sort-Object MainWindowTitle -Descending | Select-Object -First 1

if ($waProcess) {
    Write-Output "WhatsApp encontrado abierto (Process: $($waProcess.ProcessName) | Title: $($waProcess.MainWindowTitle)). Traiéndolo al frente..."
    $wshell.AppActivate($waProcess.Id) | Out-Null
} else {
    Write-Output "WhatsApp no está abierto. Abriendo WhatsApp Web automáticamente..."
    Start-Process "https://web.whatsapp.com"
    # Le damos 12 segundos para que el navegador se abra, cargue la página y se inicie la sesión
    Start-Sleep -Seconds 12
}

# Dar tiempo a que la ventana obtenga el foco
Start-Sleep -Milliseconds 800

# Presionar TAB varias veces o ESC para soltar el foco actual y luego buscar
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
Start-Sleep -Milliseconds 300

# El shortcut nativo para buscar un chat en WhatsApp Web/Desktop suele ser TAB unas veces
# O usar la navegación universal Tabular hacia "Buscar o empezar un nuevo chat"
# Pero el más robusto para WhatsApp Desktop / Web en Chrome suele ser Ctrl+Alt+/
[System.Windows.Forms.SendKeys]::SendWait("^%(/)")
Start-Sleep -Milliseconds 500

# Limpiar por si había algo escrito
[System.Windows.Forms.SendKeys]::SendWait('^a')
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait('{BACKSPACE}')
Start-Sleep -Milliseconds 200

# Escribir el nombre del contacto letra por letra para que reaccione la búsqueda
foreach ($char in $ContactName.ToCharArray()) {
    [System.Windows.Forms.SendKeys]::SendWait($char)
    Start-Sleep -Milliseconds 50
}
Start-Sleep -Milliseconds 1500

# Presionar DOWN y luego Enter para asegurar que entra al chat y no se queda en blanco
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}")
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Start-Sleep -Milliseconds 1000

# Escribir el mensaje
[System.Windows.Forms.SendKeys]::SendWait($MessageText)
Start-Sleep -Milliseconds 800

# Enviar el mensaje con Enter
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")

Write-Output "OK - Mensaje ENVIADO"
