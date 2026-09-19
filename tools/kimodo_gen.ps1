# kimodo_gen.ps1 - text prompt -> Kimodo clip on the remote kimodo.cpp laptop -> External Anims\Kimodo\<Name>.glb
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\kimodo_gen.ps1 -Prompt "..." -Name idle_s42 [-Frames 180 -Seed 42]
#
# Copied from smp-10-rgp-creatures/tools/kimodo_gen.ps1 (2026-09-19) minus the per-creature build step:
# retargeting here is tools/glb_retarget.py run separately. The generator is NVIDIA's Kimodo
# (SOMA-RP-v1.1) as the CPU/Vulkan kimodo.cpp port on the LAN laptop DESKTOP-PQNPNNB (see the
# creatures pack memory note "kimodo-machine"): `generate.ps1 "<prompt>" -Frames N -Steps 50 -Seed S
# -Out <dir>` writes animation.glb (SKINNED, T-pose bind, 30-joint SOMA skeleton, Mixamo-style names)
# + animation.bvh. ~2 min per 90 frames. No constraint input (no start pose, no waypoints).
param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [Parameter(Mandatory = $true)][string]$Name,
    [switch]$NoProfile,                               # do not prepend the skeleton body description
    [int]$Frames = 180,                               # 30 fps
    [int]$Steps = 50,
    [int]$Seed = 42,
    [string]$RemoteHost = "DESKTOP-PQNPNNB",
    [string]$RemoteUser = "vadym",
    [string]$RemoteKimodo = "C:\Users\vadym\Downloads\kmodo\Kimodo",
    [string]$RemoteJobs = "C:\Users\vadym\kimodo_jobs"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Kimodo is trained on HUMAN mocap; the description steers weight, stiffness and pace only.
# The output skeleton is always the SOMA human; proportions are the retarget's job.
$Profile = "A gaunt, stiff, slightly hunched undead skeleton warrior about 1.7 metres tall, with slack bony arms,"
if (-not $NoProfile) {
    $Prompt = $Profile + " " + $Prompt
}
Write-Host "[kimodo] prompt: $Prompt" -ForegroundColor DarkGray

$key = "$env:USERPROFILE\.ssh\kimodo_ed25519"
$dest = Join-Path $root "External Anims\Kimodo"
New-Item -ItemType Directory -Force $dest | Out-Null

$job = "$RemoteJobs\$Name"
# The remote login shell is cmd.exe and an inline PowerShell command loses its quotes on the way
# (the prompt arrived as a comma-split array). Ship the job as a .ps1 and run it with -File.
$safe = $Prompt.Replace("'", "''")
$jobScript = Join-Path $env:TEMP "kimodo_job_$Name.ps1"
@"
Set-Location '$RemoteKimodo'
New-Item -ItemType Directory -Force '$job' | Out-Null
Set-Content -Path '$job\prompt.txt' -Value '$safe' -Encoding UTF8
.\generate.ps1 '$safe' -Frames $Frames -Steps $Steps -Seed $Seed -Out '$job'
exit `$LASTEXITCODE
"@ | Set-Content -Path $jobScript -Encoding ASCII
$remoteJobScript = "$RemoteJobs\job_$Name.ps1"
ssh -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 "$RemoteUser@$RemoteHost" "if not exist $RemoteJobs mkdir $RemoteJobs"
scp -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new $jobScript "${RemoteUser}@${RemoteHost}:$($remoteJobScript.Replace('\', '/'))"
Write-Host "[kimodo] generating '$Name' on $RemoteHost ($Frames f, $Steps steps, seed $Seed)" -ForegroundColor Cyan
$t0 = Get-Date
ssh -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 "$RemoteUser@$RemoteHost" "powershell -NoProfile -ExecutionPolicy Bypass -File $remoteJobScript"
if ($LASTEXITCODE -ne 0) { throw "remote generation failed (exit $LASTEXITCODE)" }
Write-Host ("[kimodo] done in {0:N0} s" -f ((Get-Date) - $t0).TotalSeconds) -ForegroundColor Cyan

foreach ($f in "animation.glb", "animation.bvh", "prompt.txt") {
    scp -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${RemoteUser}@${RemoteHost}:$($job.Replace('\', '/'))/$f" (Join-Path $dest "$Name.$($f.Split('.')[-1])")
}
$glb = Join-Path $dest "$Name.glb"
if (-not (Test-Path $glb)) { throw "no $glb after fetch" }
Write-Host "[kimodo] -> $glb" -ForegroundColor Green
