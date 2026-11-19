# run_kfold.ps1 -- start the runs of the final study, each in its own window.
#
# 1. In ONE PowerShell window, from the project root, set the keys (they stay in this window
#    and in the windows it opens; they are written nowhere):
#       $env:OPENAI_API_KEY="..."
#       $env:ANTHROPIC_API_KEY="..."
# 2. Start a phase:
#       .\run_kfold.ps1 -Phase first     # First: 3 runs, documentation guidelines only, 55 descriptions
#       .\run_kfold.ps1 -Phase revised   # Revised: 3 runs, learning with 3 forced iterations, 55 descriptions
#       .\run_kfold.ps1 -Phase train     # Reuse: 5 training rounds (44 descriptions, 3 forced iterations)
#       .\run_kfold.ps1 -Phase test      # Reuse: the test of every round whose training is finished
#    The test phase skips the rounds whose training is not finished (run it again later)
#    and never starts the same test twice.
#       .\run_kfold.ps1 -Phase resume    # after an interruption: continue every run that is not finished
#    (each in its own window; the description that was cut is run again from its start, and the
#    finished descriptions that lost a step are run again, their first attempt kept as history)
#       .\run_kfold.ps1 -Phase watch     # unattended: every 5 minutes, start the test of every round whose
#                                        training is finished, resume (once) a finished run that has failed
#                                        or lost descriptions, and stop when every run and test is complete.
#                                        Leave this window open; the keys set in it pass to the windows it opens.
#
# Options: -Models "openai:gpt-6-luna"   only one model
#          -Folds 1,2                    only these rounds (train / test)
#          -Replicates 1,2,3             only these repetitions (first / revised)
# Each window writes its log in bpmn_pipeline\runs\_kfold_logs\.
param(
    [ValidateSet("first", "revised", "train", "test", "resume", "watch")][string]$Phase = "first",
    [int]$EveryMinutes = 5,
    [string[]]$Models = @("openai:gpt-6-luna", "anthropic:claude-haiku-5-5"),
    [int[]]$Folds = @(1, 2, 3, 4, 5),
    [int[]]$Replicates = @(1, 2, 3)
)
# the runs of the tool-using guideline agents: labels end with _agents, catalogues under agents/
$agentFlag = ""
$agentSuffix = "_agents"
$root = $PSScriptRoot
$py = Join-Path $root "env\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$pipeline = Join-Path $root "bpmn_pipeline"
$runs = Join-Path $pipeline "runs"
$logs = Join-Path $runs "_kfold_logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

foreach ($m in $Models) {
    if ($m.StartsWith("openai:") -and -not $env:OPENAI_API_KEY) { Write-Host "OPENAI_API_KEY is not set in this window" -ForegroundColor Red; exit 1 }
    if ($m.StartsWith("anthropic:") -and -not $env:ANTHROPIC_API_KEY) { Write-Host "ANTHROPIC_API_KEY is not set in this window" -ForegroundColor Red; exit 1 }
}

function Start-Run([string]$name, [string]$arguments) {
    $log = Join-Path $logs "$name.log"
    $command = "`$host.UI.RawUI.WindowTitle = '$name'; `$env:PYTHONIOENCODING = 'utf-8'; " +
               "Set-Location '$pipeline'; & '$py' run_batch.py $arguments 2>&1 | Tee-Object -FilePath '$log'"
    Start-Process powershell -ArgumentList @("-NoExit", "-Command", $command) | Out-Null
    Write-Host "started: $name" -ForegroundColor Green
    Start-Sleep -Seconds 3        # the run folders are named by the second they start
}

# A description lost a step when an INFRASTRUCTURE error stopped it (connection cut,
# timeout, server error): its run must be done again. An agent whose answer was cut at
# the LLM's output limit is a result of the LLM, not a lost step: it is kept and reported.
$infrastructure = 'Connection|timed out|timeout|RemoteProtocol|unreachable|RateLimit|overloaded|Internal server|InternalServer|APIStatusError|ServiceUnavailable|50[0-9]|529'
function Lost-Step([string]$decisionsFile) {
    $text = Get-Content $decisionsFile -Raw
    if ($text -notmatch '"error": null') {
        # the description itself stopped on an error: lost only if it is an infrastructure error
        return ($text -match ('"error": "[^"]*(' + $infrastructure + ')'))
    }
    # the description finished; an agent step is lost only if its error is an infrastructure error
    return ($text -match ('(?s)"status": "agent_error".{0,400}?"detail": "[^"]*(' + $infrastructure + ')'))
}

function Training-Finished([string]$slug, [int]$fold) {
    # finished = the report is written AND no description stopped on an error
    $run = Get-ChildItem -Path $runs -Directory -Filter "batch_*_${slug}_documentation_fold${fold}_forced$agentSuffix" -ErrorAction SilentlyContinue |
        Sort-Object Name | Select-Object -Last 1
    if (-not $run) { return $false }
    if (-not (Get-ChildItem -Path $run.FullName -Filter "report_*.json" -ErrorAction SilentlyContinue)) { return $false }
    $failed = @(Get-ChildItem -Path $run.FullName -Directory -Filter "id_*" | ForEach-Object {
        $d = Join-Path $_.FullName "decisions.json"
        if (-not (Test-Path $d) -or -not (Select-String -Path $d -Pattern '"error": null' -SimpleMatch -Quiet)) { $_.Name }
    })
    if ($failed.Count -gt 0) {
        Write-Host "fold $fold of ${slug}: $($failed.Count) description(s) failed ($($failed -join ', ')): resume $($run.Name) first" -ForegroundColor Yellow
        return $false
    }
    return $true
}

if ($Phase -eq "resume") {
    $slugs = $Models | ForEach-Object { $_.Replace(":", "-").Replace("/", "-") }
    # a run is resumed when it is not finished, or when it finished with descriptions that lost a step
    $open = Get-ChildItem -Path $runs -Directory -Filter "batch_*" | Where-Object { $_.Name -notlike "*dryrun*" } | Where-Object {
        $name = $_.Name
        $unfinished = -not (Get-ChildItem -Path $_.FullName -Filter "report_*.json" -ErrorAction SilentlyContinue)
        $lost = @(Get-ChildItem -Path $_.FullName -Directory -Filter "id_*" | Where-Object {
            $d = Join-Path $_.FullName "decisions.json"
            (Test-Path $d) -and (Lost-Step $d) }).Count -gt 0
        (Test-Path (Join-Path $_.FullName "models.json")) -and ($unfinished -or $lost) -and ($name -like "*_agents") -and
        @($slugs | Where-Object { $name -like "*_$($_)_*" }).Count -gt 0 }
    if (-not $open) { Write-Host "No unfinished run." -ForegroundColor Cyan }
    foreach ($run in $open) {
        # descriptions that finished with a lost step (connection cut, cut answer, agent error) are run again
        $redo = @(Get-ChildItem -Path $run.FullName -Directory -Filter "id_*" | Where-Object {
            $d = Join-Path $_.FullName "decisions.json"
            (Test-Path $d) -and (Lost-Step $d)
        } | ForEach-Object { $_.Name.Substring(3) })
        $extra = if ($redo.Count -gt 0) { " --redo '" + ($redo -join ",") + "'" } else { "" }   # quoted: 07 stays 07
        if ($redo.Count -gt 0) { Write-Host "$($run.Name): run again $($redo -join ', ')" -ForegroundColor Yellow }
        Start-Run "resume_$($run.Name.Substring(6))" "--resume $($run.Name)$extra"
    }
    Write-Host "Logs: $logs"
    exit 0
}

# The descriptions of a run that must be done again: stopped on an error, or finished with a lost step.
function Redo-List([System.IO.DirectoryInfo]$run) {
    return @(Get-ChildItem -Path $run.FullName -Directory -Filter "id_*" | Where-Object {
        $d = Join-Path $_.FullName "decisions.json"
        (-not (Test-Path $d)) -or (-not (Select-String -Path $d -Pattern '"error": null' -SimpleMatch -Quiet)) -or (Lost-Step $d)
    } | ForEach-Object { $_.Name.Substring(3) })
}
function Latest-Run([string]$filter) {
    return Get-ChildItem -Path $runs -Directory -Filter $filter -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
}
function Run-Finished([System.IO.DirectoryInfo]$run) {
    return [bool](Get-ChildItem -Path $run.FullName -Filter "report_*.json" -ErrorAction SilentlyContinue)
}

if ($Phase -eq "watch") {
    $resumed = @{}                        # run name -> when its resume was started (started once, unless it died)
    function Resume-Once([System.IO.DirectoryInfo]$run, [string[]]$redo) {
        $log = Join-Path $logs "resume_$($run.Name.Substring(6)).log"
        $running = (Test-Path $log) -and ((Get-Date) - (Get-Item $log).LastWriteTime).TotalMinutes -lt 30
        if ($resumed.ContainsKey($run.Name)) {                              # started already: wait while it works
            $since = ((Get-Date) - $resumed[$run.Name]).TotalMinutes
            if ($running -or $since -lt 30) { return }
        }
        $extra = if ($redo.Count -gt 0) { " --redo '" + ($redo -join ",") + "'" } else { "" }
        Write-Host "$(Get-Date -Format 'HH:mm') $($run.Name): resume, run again $($redo -join ', ')" -ForegroundColor Yellow
        Start-Run "resume_$($run.Name.Substring(6))" "--resume $($run.Name)$extra"
        $resumed[$run.Name] = Get-Date
    }
    Write-Host "Watching the runs every $EveryMinutes minutes (Ctrl+C to stop; the runs themselves go on)." -ForegroundColor Cyan
    while ($true) {
        $allDone = $true
        foreach ($m in $Models) {
            $slug = $m.Replace(":", "-").Replace("/", "-")
            $short = $m.Split(":")[-1]
            $flags = "--generator $m --orchestrator $m --retriever $m --expert $m"
            # the Revised runs: only watched for their end and their lost descriptions
            foreach ($r in $Replicates) {
                $run = Latest-Run "batch_*_${slug}_documentation_forced_r${r}$agentSuffix"
                if (-not $run) { continue }
                if (-not (Run-Finished $run)) { $allDone = $false; continue }
                $redo = Redo-List $run
                if ($redo.Count -gt 0) { $allDone = $false; Resume-Once $run $redo }
            }
            foreach ($f in $Folds) {
                $train = Latest-Run "batch_*_${slug}_documentation_fold${f}_forced$agentSuffix"
                if (-not $train) { continue }
                if (-not (Run-Finished $train)) { $allDone = $false; continue }
                $redo = Redo-List $train
                if ($redo.Count -gt 0) { $allDone = $false; Resume-Once $train $redo; continue }
                $test = Get-ChildItem -Path $runs -Directory -Filter "batch_*_${slug}_documentation_learned_confirmed_fold$f$agentSuffix" -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -gt $train.Name } | Sort-Object Name | Select-Object -Last 1
                if (-not $test) {
                    $allDone = $false
                    Write-Host "$(Get-Date -Format 'HH:mm') fold $f of ${m}: training finished, starting its test" -ForegroundColor Green
                    Start-Run "test_fold${f}_$short$agentSuffix" "--arm documentation+learned --fold $f $flags$agentFlag"
                    continue
                }
                if (-not (Run-Finished $test)) { $allDone = $false; continue }
                $redo = Redo-List $test
                if ($redo.Count -gt 0) { $allDone = $false; Resume-Once $test $redo }
            }
        }
        if ($allDone) {
            Write-Host "$(Get-Date -Format 'HH:mm') Every run and test is finished and complete. Now: python study_report.py --generator <model>" -ForegroundColor Cyan
            break
        }
        Start-Sleep -Seconds ($EveryMinutes * 60)
    }
    Write-Host "Logs: $logs"
    exit 0
}

foreach ($m in $Models) {
    $slug = $m.Replace(":", "-").Replace("/", "-")
    $short = $m.Split(":")[-1]           # gpt-6-luna, claude-haiku-5-5
    $flags = "--generator $m --orchestrator $m --retriever $m --expert $m"
    if ($Phase -eq "first") {
        foreach ($r in $Replicates) {
            Start-Run "first_r${r}_$short" "--arm documentation --no-learn --next-iterations 0 --replicate $r $flags"
        }
    } elseif ($Phase -eq "revised") {
        foreach ($r in $Replicates) {
            Start-Run "revised_r${r}_$short$agentSuffix" "--arm documentation --next-iterations 3 --force-iterations --promote-confirmed --replicate $r $flags$agentFlag"
        }
    } elseif ($Phase -eq "train") {
        foreach ($f in $Folds) {
            Start-Run "train_fold${f}_$short$agentSuffix" "--arm documentation --fold $f --next-iterations 3 --force-iterations --promote-confirmed $flags$agentFlag"
        }
    } else {
        foreach ($f in $Folds) {
            $train = Get-ChildItem -Path $runs -Directory -Filter "batch_*_${slug}_documentation_fold${f}_forced$agentSuffix" -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
            $existing = Get-ChildItem -Path $runs -Directory -Filter "batch_*_${slug}_documentation_learned_confirmed_fold$f$agentSuffix" -ErrorAction SilentlyContinue |
                Where-Object { $train -and $_.Name -gt $train.Name }
            if ($existing) {
                Write-Host "fold $f of ${m}: test already started ($($existing[-1].Name)), not started again" -ForegroundColor Cyan
                continue
            }
            if (Training-Finished $slug $f) {
                Start-Run "test_fold${f}_$short$agentSuffix" "--arm documentation+learned --fold $f $flags$agentFlag"
            } else {
                Write-Host "fold $f of ${m}: training not finished yet, test not started" -ForegroundColor Yellow
            }
        }
    }
}
Write-Host "Logs: $logs"
