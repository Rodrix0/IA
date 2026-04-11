param(
    [Parameter(Mandatory=$false)]
    [string]$ContactName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$MessageText = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

# Intentamos traer la ventana de WhatsApp al frente.
$wshell = New-Object -ComObject wscript.shell
$success = $wshell.AppActivate("WhatsApp")

if (-not $success) {
    Write-Output "No se encontró la ventana de WhatsApp, asumiendo navegador o app de escritorio..."
    # A veces Chrome dice "WhatsApp - Google Chrome"
    $successChrome = $wshell.AppActivate("WhatsApp - Google Chrome")
    if (-not $successChrome) {
         # Ultimo intento vago a algo que contenga WhatsApp
         $wshell.AppActivate("WhatsApp")
    }
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

# TRUCO DE SEGURIDAD MÁXIMA: Si no encontró a nadie, el foco estará en la barra de búsqueda y 
# escribirá "Hola" pegado al nombre (GabiHola). Para evitarlo, enviamos un ESC
# en caso de que esté trancado, y volvemos a dar ENTER (en el chat esto no borra nada)
# Sin embargo, lo mejor para salir del cuadro de búsqueda es forzar un TAP (Tab) que entra al chat
# si se encontró.
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
Start-Sleep -Milliseconds 200

# Escribir el mensaje
foreach ($char in $MessageText.ToCharArray()) {
    # SendWait se rompe con caracteres especiales de regex, así que usamos envio básico
    if ($char -match '[+^%~(){}]') {
        [System.Windows.Forms.SendKeys]::SendWait("{$char}")
    } else {
        [System.Windows.Forms.SendKeys]::SendWait($char)
    }
}
Start-Sleep -Milliseconds 800

# Enviar el mensaje con Enter
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")

Write-Output "OK - Mensaje ENVIADO"
