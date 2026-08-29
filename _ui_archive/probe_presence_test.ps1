# 验证 fullscreen-presence.js 修复后的探测脚本能产出有效输出
# （原 $pid=0 因 PowerShell 只读变量会抛错 → 永远空输出 → 窗口在 Electron 内始终隐藏 → 卡死）
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class X6W {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr h, uint f);
  [DllImport("user32.dll")] public static extern bool GetMonitorInfo(IntPtr h, ref MONITORINFO mi);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  [StructLayout(LayoutKind.Sequential)] public struct MONITORINFO { public uint cb; public RECT rcMonitor; public RECT rcWork; public uint dwFlags; }
}
"@
$h = [X6W]::GetForegroundWindow()
if ($h -eq [IntPtr]::Zero) { "WINDOWED"; exit }
$fgPid = 0
[X6W]::GetWindowThreadProcessId($h, [ref]$fgPid) | Out-Null
if ($fgPid -eq [int]$env:XIAO6_PID) { "SELF"; exit }
$r = New-Object X6W+RECT; [X6W]::GetWindowRect($h, [ref]$r) | Out-Null
$m = [X6W]::MonitorFromWindow($h, 2)
$mi = New-Object X6W+MONITORINFO; $mi.cb = [System.Runtime.InteropServices.Marshal]::SizeOf($mi)
[X6W]::GetMonitorInfo($m, [ref]$mi) | Out-Null
$mw = $mi.rcMonitor.R - $mi.rcMonitor.L; $mh = $mi.rcMonitor.B - $mi.rcMonitor.T
$ww = $r.R - $r.L; $wh = $r.B - $r.T
if (($ww -ge ($mw-8)) -and ($wh -ge ($mh-8))) { "FULLSCREEN" } else { "WINDOWED" }
