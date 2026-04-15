Add-Type -TypeDefinition "
using System;
using Microsoft.Win32;
public class PowerEventListener {
    public static void Start() {
        SystemEvents.PowerModeChanged += (s,e) => {
            if (e.Mode == PowerModes.Resume) Console.WriteLine("EVENT:RESUME");
            else if (e.Mode == PowerModes.Suspend) Console.WriteLine("EVENT:SUSPEND");
        };
        Console.WriteLine("LISTENING");
        System.Windows.Forms.Application.Run(new System.Windows.Forms.ApplicationContext());
    }
}
" -ReferencedAssemblies "System.Windows.Forms"
[PowerEventListener]::Start()
