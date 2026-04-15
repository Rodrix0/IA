Add-Type -TypeDefinition @"
using System;
using Microsoft.Win32;

public class PowerEventListener {
    public static void Start() {
        // Eventos de Energía Clásicos (Sleep/Resume)
        SystemEvents.PowerModeChanged += (s,e) => {
            if (e.Mode == PowerModes.Resume) Console.WriteLine("EVENT:RESUME");
            else if (e.Mode == PowerModes.Suspend) Console.WriteLine("EVENT:SUSPEND");
        };

        // Eventos de Sesión de Windows (Bloquear UI WIN+L, o Modern Standby Lock)
        SystemEvents.SessionSwitch += (s,e) => {
            if (e.Reason == SessionSwitchReason.SessionUnlock) Console.WriteLine("EVENT:UNLOCK");
            else if (e.Reason == SessionSwitchReason.SessionLock) Console.WriteLine("EVENT:LOCK");
        };

        Console.WriteLine("LISTENING");
        System.Windows.Forms.Application.Run(new System.Windows.Forms.ApplicationContext());
    }
}
"@ -ReferencedAssemblies "System.Windows.Forms"

[PowerEventListener]::Start()
