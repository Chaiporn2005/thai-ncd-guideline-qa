<#
Capture a REAL screenshot of one command running in its own terminal window (used to make docs/SETUP_GUIDE_TH.md; Windows 10/11, Windows PowerShell 5.1, Windows Terminal).

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/capture_terminal.ps1 -Command "python -X utf8 demo.py --check" -Out docs/images/setup/step05_check.png -Cwd C:\path\to\clone

What it does, and nothing else: opens ONE new Windows Terminal window running the command in -Cwd, waits until the command ends (or -TimeoutSec), copies only that window's rectangle
from the screen into the PNG, then closes that window. It never reads the clipboard, never types keystrokes into other windows and never touches other windows. Because it copies pixels from the
screen, whatever else overlaps that rectangle would be captured too: do not run other windows over it while it works, and never put a secret in -Command (the window shows the command line).
The command's own text output is also saved next to the PNG as <name>.txt (UTF-8) so the screenshot can be checked against what was really printed.
#>
param(
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Cwd = (Get-Location).Path,
    [string]$Title = "capture",
    [string]$Pre = "",   # silent commands run before the shown command, e.g. activating the venv; they are not echoed (never put a secret here either)
    [int]$TimeoutSec = 900,
    [int]$Cols = 104,
    [int]$Rows = 28,
    [int]$HoldSec = 2
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class Win32Cap {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint flags);
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT p);
    public static IntPtr RootAt(int x, int y) { POINT p; p.X = x; p.Y = y; IntPtr w = WindowFromPoint(p); return w == IntPtr.Zero ? IntPtr.Zero : GetAncestor(w, 2); }
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public static IntPtr Find(string title) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h, l) => {
            if (!IsWindowVisible(h)) return true;
            var sb = new StringBuilder(256); GetWindowText(h, sb, 256);
            if (sb.ToString().Contains(title)) { found = h; return false; }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
"@
[Win32Cap]::SetProcessDPIAware() | Out-Null   # without this, on a scaled display (125-200%) only the top-left part of the window is copied
$work = Join-Path ([IO.Path]::GetTempPath()) ("cap_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $work | Out-Null
$unique = "$Title-" + [guid]::NewGuid().ToString("N").Substring(0, 6)
$marker = Join-Path $work "done.txt"
$textOut = [IO.Path]::ChangeExtension((Resolve-Path -LiteralPath (Split-Path -Parent $Out) -ErrorAction SilentlyContinue).Path + "\" + (Split-Path -Leaf $Out), ".txt")
if (-not (Test-Path (Split-Path -Parent $Out))) { New-Item -ItemType Directory -Path (Split-Path -Parent $Out) -Force | Out-Null; $textOut = [IO.Path]::ChangeExtension((Resolve-Path (Split-Path -Parent $Out)).Path + "\" + (Split-Path -Leaf $Out), ".txt") }
$cmdFile = Join-Path $work "cmd.txt"
[IO.File]::WriteAllText($cmdFile, $Command, (New-Object Text.UTF8Encoding($false)))
$preFile = Join-Path $work "pre.txt"
[IO.File]::WriteAllText($preFile, $Pre, (New-Object Text.UTF8Encoding($false)))
$runner = @"
`$Host.UI.RawUI.WindowTitle = '$unique'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new(`$false)
`$OutputEncoding = [Console]::OutputEncoding
`$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath '$Cwd'
`$cmd = [IO.File]::ReadAllText('$cmdFile', [Text.UTF8Encoding]::new(`$false))
`$pre = [IO.File]::ReadAllText('$preFile', [Text.UTF8Encoding]::new(`$false))
if (`$pre.Trim()) { Invoke-Expression `$pre 2>&1 | Out-Null }
`$pfx = if (`$env:VIRTUAL_ENV) { '(' + (Split-Path -Leaf `$env:VIRTUAL_ENV) + ') ' } else { '' }
Write-Host (`$pfx + 'PS ' + (Split-Path -Leaf (Get-Location)) + '> ' + `$cmd) -ForegroundColor Cyan
`$buf = New-Object System.Collections.Generic.List[string]
`$buf.Add(`$pfx + 'PS ' + (Split-Path -Leaf (Get-Location)) + '> ' + `$cmd)
& ([scriptblock]::Create(`$cmd)) *>&1 | ForEach-Object { `$s = if (`$_ -is [System.Management.Automation.ErrorRecord]) { `$_.Exception.Message } else { `$_.ToString() }; Write-Host `$s; `$buf.Add(`$s) }
[IO.File]::WriteAllLines('$textOut', `$buf, [Text.UTF8Encoding]::new(`$false))
'done' | Set-Content -LiteralPath '$marker'
Start-Sleep -Seconds 900
"@
$runFile = Join-Path $work "run.ps1"
[IO.File]::WriteAllText($runFile, $runner, (New-Object Text.UTF8Encoding($true)))
Start-Process -FilePath "wt.exe" -ArgumentList @("-w", "new", "--pos", "0,0", "--size", "$Cols,$Rows", "new-tab", "--title", $unique, "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $runFile)
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while (-not (Test-Path $marker) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
$timedOut = -not (Test-Path $marker)
Start-Sleep -Seconds $HoldSec
$h = [Win32Cap]::Find($unique)
if ($h -eq [IntPtr]::Zero) { Write-Error "terminal window '$unique' not found"; exit 2 }
[Win32Cap]::ShowWindow($h, 9) | Out-Null
$r = New-Object Win32Cap+RECT
# Windows refuses SetForegroundWindow from a background process, so another app (it once was the Claude desktop app, with private chat titles in view) can sit on top of the terminal and would be copied
# instead. Make the terminal TOPMOST, then PROVE that it is the window on top at the centre and at the four corners of its rectangle; otherwise save nothing.
$HWND_TOPMOST = [IntPtr](-1); $SWP = 0x0001 -bor 0x0002 -bor 0x0040   # no size, no move, show
$ok = $false
for ($try = 0; $try -lt 8 -and -not $ok; $try++) {
    [Win32Cap]::SetWindowPos($h, $HWND_TOPMOST, 0, 0, 0, 0, $SWP) | Out-Null
    [Win32Cap]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Milliseconds 700
    [Win32Cap]::GetWindowRect($h, [ref]$r) | Out-Null
    $cx = [int](($r.Left + $r.Right) / 2); $cy = [int](($r.Top + $r.Bottom) / 2)
    $pts = @(@($cx, $cy), @(($r.Left + 40), ($r.Top + 40)), @(($r.Right - 40), ($r.Top + 40)), @(($r.Left + 40), ($r.Bottom - 40)), @(($r.Right - 40), ($r.Bottom - 40)))
    $ok = $true
    foreach ($pt in $pts) { if ([Win32Cap]::RootAt($pt[0], $pt[1]) -ne $h) { $ok = $false } }
}
if (-not $ok) {
    [Win32Cap]::PostMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
    Write-Error "refused to capture: the terminal window is not the window on top of its own rectangle (another window is covering it); nothing was saved"
    exit 3
}
$w = $r.Right - $r.Left; $hgt = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap $w, $hgt
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
$g.Dispose()
# trim the empty lower part of the terminal so the picture ends a little below the last printed line
$bg = $bmp.GetPixel([int]($w / 2), [int]($hgt - 80))
$last = 0
for ($y = $hgt - 70; $y -gt 70; $y -= 2) {
    for ($x = 20; $x -lt ($w - 20); $x += 4) {
        $c = $bmp.GetPixel($x, $y)
        if ([Math]::Abs($c.R - $bg.R) + [Math]::Abs($c.G - $bg.G) + [Math]::Abs($c.B - $bg.B) -gt 60) { $last = $y; break }
    }
    if ($last -gt 0) { break }
}
$cropH = [Math]::Min($hgt - 4, [Math]::Max(260, $last + 45))
if ($cropH -lt $hgt - 4) {
    $rect = New-Object System.Drawing.Rectangle 0, 0, ($w - 2), $cropH
    $cropped = $bmp.Clone($rect, $bmp.PixelFormat)
    $bmp.Dispose(); $bmp = $cropped; $hgt = $cropH
}
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$outW = $bmp.Width; $outH = $bmp.Height
$bmp.Dispose()
[Win32Cap]::PostMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null   # WM_CLOSE: closes only this window
Write-Output ("saved {0} ({1}x{2}){3}" -f $Out, $outW, $outH, $(if ($timedOut) { "  TIMED OUT before the command ended" } else { "" }))
