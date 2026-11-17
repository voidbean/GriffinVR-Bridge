using System;
using System.Diagnostics;
using System.IO;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal static class Launcher
{
    [StructLayout(LayoutKind.Sequential)]
    struct Throttling { public uint Version, Control, State; }

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool GetProcessInformation(IntPtr process, int kind, ref Throttling policy, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool SetProcessInformation(IntPtr process, int kind, ref Throttling policy, uint size);

    [STAThread]
    static int Main()
    {
        try
        {
            var folder = AppDomain.CurrentDomain.BaseDirectory;
            var start = new ProcessStartInfo(Path.Combine(folder, "overlord-gfl.exe"), @"-singleplayer -mod mods\gfl");
            start.UseShellExecute = false;
            start.WorkingDirectory = folder;
            if (String.IsNullOrEmpty(start.EnvironmentVariables["H2V_VR_BACKEND"]))
                start.EnvironmentVariables["H2V_VR_BACKEND"] = "openvr";
            using (var game = Process.Start(start))
            {
                var policy = new Throttling { Version = 1 };
                uint size = (uint)Marshal.SizeOf(typeof(Throttling));
                if (!GetProcessInformation(game.Handle, 4, ref policy, size))
                    throw new Win32Exception();
                policy.Control |= 1;
                policy.State &= ~1u;
                if (!SetProcessInformation(game.Handle, 4, ref policy, size) ||
                    !GetProcessInformation(game.Handle, 4, ref policy, size))
                    throw new Win32Exception();
                if ((policy.Control & 1) == 0 || (policy.State & 1) != 0)
                    throw new InvalidOperationException("Windows did not apply HighQoS.");
            }
            return 0;
        }
        catch (Exception e)
        {
            MessageBox.Show(e.Message, "MWR GFL VR launcher");
            return 1;
        }
    }
}
