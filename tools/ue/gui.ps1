# Drive the desktop for the UE 5.4 build (no MCP there): screenshots, clicks, keys, clipboard, window focus.
#   powershell -File tools/ue/gui.ps1 shot OUT.png [x y w h]     full screen (or a region) to PNG; prints the screen size
#   powershell -File tools/ue/gui.ps1 click X Y [right|double]    mouse click at screen pixels
#   powershell -File tools/ue/gui.ps1 keys "^v"                    SendKeys syntax (^ ctrl, + shift, % alt, {ENTER})
#   powershell -File tools/ue/gui.ps1 clip FILE                    put a UTF-8 text file on the clipboard
#   powershell -File tools/ue/gui.ps1 getclip OUT                  clipboard text to a file
#   powershell -File tools/ue/gui.ps1 focus TITLE_SUBSTRING        bring the first matching top-level window forward
#   powershell -File tools/ue/gui.ps1 windows                      list visible top-level windows (handle, rect, title)
param([string]$cmd, [string]$a1, [string]$a2, [string]$a3, [string]$a4, [string]$a5)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@
[W]::SetProcessDPIAware() | Out-Null

function Get-Windows {
  $list = New-Object System.Collections.ArrayList
  $cb = [W+EnumProc]{ param($h, $l)
    if ([W]::IsWindowVisible($h)) {
      $sb = New-Object System.Text.StringBuilder 512
      [W]::GetWindowText($h, $sb, 512) | Out-Null
      if ($sb.Length -gt 0) { $r = New-Object W+RECT; [W]::GetWindowRect($h, [ref]$r) | Out-Null
        [void]$list.Add([pscustomobject]@{H=$h; L=$r.L; T=$r.T; R=$r.R; B=$r.B; Title=$sb.ToString()}) }
    }; return $true }
  [W]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
  return $list
}

switch ($cmd) {
  "shot" {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $x = 0; $y = 0; $w = $b.Width; $h = $b.Height
    if ($a2) { $x = [int]$a2; $y = [int]$a3; $w = [int]$a4; $h = [int]$a5 }
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($x, $y, 0, 0, (New-Object System.Drawing.Size $w, $h))
    $bmp.Save($a1, [System.Drawing.Imaging.ImageFormat]::Png)
    "screen {0}x{1}" -f $b.Width, $b.Height
  }
  "click" {
    [W]::SetCursorPos([int]$a1, [int]$a2) | Out-Null; Start-Sleep -Milliseconds 80
    if ($a3 -eq "right") { [W]::mouse_event(8, 0, 0, 0, [IntPtr]::Zero); [W]::mouse_event(16, 0, 0, 0, [IntPtr]::Zero) }
    else {
      [W]::mouse_event(2, 0, 0, 0, [IntPtr]::Zero); [W]::mouse_event(4, 0, 0, 0, [IntPtr]::Zero)
      if ($a3 -eq "double") { Start-Sleep -Milliseconds 60; [W]::mouse_event(2, 0, 0, 0, [IntPtr]::Zero); [W]::mouse_event(4, 0, 0, 0, [IntPtr]::Zero) }
    }
  }
  "burst" {   # burst OUTPREFIX COUNT INTERVAL_MS X Y W H [clickX clickY]: optional click, then COUNT region captures
    $n = [int]$a2; $ms = [int]$a3; $p = $a4.Split(","); $x = [int]$p[0]; $y = [int]$p[1]; $w = [int]$p[2]; $h = [int]$p[3]
    if ($a5) { $c = $a5.Split(","); [W]::SetCursorPos([int]$c[0], [int]$c[1]) | Out-Null; Start-Sleep -Milliseconds 60
               [W]::mouse_event(2, 0, 0, 0, [IntPtr]::Zero); [W]::mouse_event(4, 0, 0, 0, [IntPtr]::Zero) }
    $bmp = New-Object System.Drawing.Bitmap $w, $h; $g = [System.Drawing.Graphics]::FromImage($bmp)
    for ($i = 0; $i -lt $n; $i++) {
      $g.CopyFromScreen($x, $y, 0, 0, (New-Object System.Drawing.Size $w, $h))
      $bmp.Save(("{0}_{1:D2}.png" -f $a1, $i), [System.Drawing.Imaging.ImageFormat]::Png); Start-Sleep -Milliseconds $ms
    }
  }
  "move" { [W]::SetCursorPos([int]$a1, [int]$a2) | Out-Null }
  "drag" {   # left-button drag X1 Y1 -> X2 Y2 in small steps (Slate needs the intermediate moves)
    [W]::SetCursorPos([int]$a1, [int]$a2) | Out-Null; Start-Sleep -Milliseconds 100
    [W]::mouse_event(2, 0, 0, 0, [IntPtr]::Zero); Start-Sleep -Milliseconds 100
    for ($i = 1; $i -le 20; $i++) {
      $x = [int]$a1 + ([int]$a3 - [int]$a1) * $i / 20; $y = [int]$a2 + ([int]$a4 - [int]$a2) * $i / 20
      [W]::SetCursorPos([int]$x, [int]$y) | Out-Null; Start-Sleep -Milliseconds 25
    }
    Start-Sleep -Milliseconds 100; [W]::mouse_event(4, 0, 0, 0, [IntPtr]::Zero)
  }
  "scroll" { [W]::SetCursorPos([int]$a1, [int]$a2) | Out-Null; [W]::mouse_event(0x800, 0, 0, [uint32]([int]$a3 * 120), [IntPtr]::Zero) }
  "keys" { [System.Windows.Forms.SendKeys]::SendWait($a1) }
  "fgis" {   # exit 1 unless the foreground window's title contains $a1 (guard before Ctrl+A / Delete)
    $sb = New-Object System.Text.StringBuilder 512; [W]::GetWindowText([W]::GetForegroundWindow(), $sb, 512) | Out-Null
    $t = $sb.ToString(); if ($t -like "*$a1*") { "fg ok: $t" } else { "fg is '$t', not '$a1'"; exit 1 }
  }
  "paste" {   # Ctrl+V with real key events (Slate ignores some SendKeys chords)
    [W]::keybd_event(0x11, 0, 0, [IntPtr]::Zero); [W]::keybd_event(0x56, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 40
    [W]::keybd_event(0x56, 0, 2, [IntPtr]::Zero); [W]::keybd_event(0x11, 0, 2, [IntPtr]::Zero)
  }
  "clip" { [System.Windows.Forms.Clipboard]::SetText([System.IO.File]::ReadAllText($a1)) }
  "getclip" { [System.IO.File]::WriteAllText($a1, [System.Windows.Forms.Clipboard]::GetText()) }
  "windows" { Get-Windows | ForEach-Object { "{0}`t{1},{2},{3},{4}`t{5}" -f $_.H, $_.L, $_.T, $_.R, $_.B, $_.Title } }
  "focus" {
    $w = Get-Windows | Where-Object { $_.Title -like "*$a1*" } | Select-Object -First 1
    # SW_MAXIMIZE (SW_RESTORE un-maximised the editor); an Alt tap first, or Windows refuses the foreground change
    if ($w) { [W]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [W]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)
              [W]::ShowWindow($w.H, 3) | Out-Null; [W]::SetForegroundWindow($w.H) | Out-Null; "{0},{1},{2},{3} {4}" -f $w.L, $w.T, $w.R, $w.B, $w.Title }
    else { "no window"; exit 1 }
  }
}
