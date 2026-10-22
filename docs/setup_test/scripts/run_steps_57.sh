#!/bin/bash
# re-take steps 5 and 7 only (same fresh folder): step 5 printed no file listing (PowerShell objects were not converted to text), step 7 showed a tool artefact line
W="D:/KMITL/NLP/NLP-Year3/team-project/_setup_test"
REPO="$W\friend2\thai-ncd-guideline-qa"; ACT='. .\.venv\Scripts\Activate.ps1'; LOG="$W/shots/run_log_57.txt"; : > "$LOG"
step() { name="$1"; cwd="$2"; pre="$3"; cmd="$4"; t=$(date +%s)
  powershell -NoProfile -ExecutionPolicy Bypass -File "$W/tools/capture_terminal.ps1" -Command "$cmd" -Out "$W/shots/$name.png" -Cwd "$cwd" -Pre "$pre" -Title "$name" -TimeoutSec 1500 2>&1 | tail -3 | tee -a "$LOG"
  echo "   $name took $(( $(date +%s) - t )) s" | tee -a "$LOG"; }
step step05_config "$REPO" "$ACT" 'Copy-Item configs\llm\providers.example.yaml configs\llm\providers.yaml; Copy-Item .env.example .env; (Select-String -Path .env -Pattern "^TYPHOON_API_KEY=").Line -replace "=.+","=<มีค่าแล้ว>"; Get-ChildItem .env, configs\llm\providers.yaml | ForEach-Object { $_.Name + "   " + $_.Length + " bytes" }'
step step07_warm "$REPO" "$ACT" 'python -X utf8 demo.py --warm'
echo "DONE57" | tee -a "$LOG"
