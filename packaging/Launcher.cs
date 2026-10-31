using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;

internal static class Launcher
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBox(IntPtr window, string text, string caption, uint flags);

    private static bool CanWrite(string directory)
    {
        if (String.IsNullOrWhiteSpace(directory)) return false;
        try
        {
            Directory.CreateDirectory(directory);
            string probe = Path.Combine(directory, ".write-" + Guid.NewGuid().ToString("N"));
            using (var stream = new FileStream(probe, FileMode.CreateNew, FileAccess.Write,
                       FileShare.None, 1, FileOptions.DeleteOnClose))
                stream.WriteByte(0);
            return true;
        }
        catch (Exception error)
        {
            if (error is IOException || error is UnauthorizedAccessException ||
                error is System.Security.SecurityException || error is ArgumentException)
                return false;
            throw;
        }
    }

    private static string Under(string parent, string child)
    {
        return String.IsNullOrWhiteSpace(parent) ? null : Path.Combine(parent, child);
    }

    private static string SelectHome(string executableDirectory)
    {
        string[] candidates = {
            Environment.GetEnvironmentVariable("POINTLAB_HOME"),
            Under(Environment.GetEnvironmentVariable("APPDATA"), "PointLabStudio"),
            Under(Environment.GetEnvironmentVariable("LOCALAPPDATA"), "PointLabStudio"),
            Path.Combine(executableDirectory, ".PointLabStudio"),
            Under(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".pointlabstudio")
        };
        foreach (string candidate in candidates)
            if (CanWrite(candidate)) return Path.GetFullPath(candidate);
        throw new IOException("无法创建可写的数据目录。请将 EXE 移到您有写入权限的文件夹后重试。");
    }

    private static string CreateRuntime(string home)
    {
        string[] candidates = {
            Environment.GetEnvironmentVariable("TMP"),
            Environment.GetEnvironmentVariable("TEMP"),
            Under(Environment.GetEnvironmentVariable("LOCALAPPDATA"), "PointLabStudio\\Runtime"),
            Path.Combine(home, "Runtime")
        };
        foreach (string candidate in candidates)
        {
            if (!CanWrite(candidate)) continue;
            string directory = Path.Combine(Path.GetFullPath(candidate), "PointLab-" + Guid.NewGuid().ToString("N"));
            try
            {
                // A separate private directory isolates concurrent starts and extracted DLLs.
                var security = new DirectorySecurity();
                security.SetAccessRuleProtection(true, false);
                security.AddAccessRule(new FileSystemAccessRule(WindowsIdentity.GetCurrent().User,
                    FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit,
                    PropagationFlags.None, AccessControlType.Allow));
                Directory.CreateDirectory(directory, security);
                if (CanWrite(directory)) return directory;
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
            catch (System.Security.SecurityException) { }
            RemoveRuntime(directory);
        }
        throw new IOException("无法创建运行目录。请将 EXE 移到您有写入权限的文件夹后重试。");
    }

    private static string Quote(string argument)
    {
        // Windows quoting must double backslashes before quotes and the closing quote.
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in argument)
        {
            if (c == '\\') { slashes++; continue; }
            result.Append('\\', c == '"' ? slashes * 2 + 1 : slashes);
            result.Append(c);
            slashes = 0;
        }
        return result.Append('\\', slashes * 2).Append('"').ToString();
    }

    private static void RemoveRuntime(string directory)
    {
        if (String.IsNullOrEmpty(directory)) return;
        for (int attempt = 0; attempt < 4; attempt++)
        {
            try
            {
                if (Directory.Exists(directory)) Directory.Delete(directory, true);
                return;
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
            Thread.Sleep(200);
        }
    }

    [STAThread]
    private static int Main(string[] args)
    {
        string runtime = null;
        try
        {
            string home = SelectHome(AppDomain.CurrentDomain.BaseDirectory);
            runtime = CreateRuntime(home);
            string payload = Path.Combine(runtime, "PointLabStudio.exe");
            using (Stream resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("PointLabPayload"))
            using (var output = new FileStream(payload, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                if (resource == null) throw new IOException("程序资源不完整，请重新下载 EXE。");
                resource.CopyTo(output);
            }

            var quoted = new List<string>();
            foreach (string argument in args) quoted.Add(Quote(argument));
            var start = new ProcessStartInfo(payload, String.Join(" ", quoted));
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.WorkingDirectory = Environment.CurrentDirectory;
            start.EnvironmentVariables["TMP"] = runtime;
            start.EnvironmentVariables["TEMP"] = runtime;
            start.EnvironmentVariables["POINTLAB_HOME"] = home;
            // A stale inherited cache path must not bypass the verified writable home.
            start.EnvironmentVariables["PYGFX_DATA_DIR"] = Path.Combine(home, "pygfx");
            Directory.CreateDirectory(start.EnvironmentVariables["PYGFX_DATA_DIR"]);
            using (Process child = Process.Start(start))
            {
                child.WaitForExit();
                return child.ExitCode;
            }
        }
        catch (Exception error)
        {
            MessageBox(IntPtr.Zero, "PointLab Studio 启动失败：\n\n" + error.Message,
                       "PointLab Studio", 0x10);
            return 1;
        }
        finally { RemoveRuntime(runtime); }
    }
}
