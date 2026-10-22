#!/bin/bash
# Supervisor's run of the setup guide on a fresh folder, one real terminal screenshot per step (steps 1-8b).
W="D:/KMITL/NLP/NLP-Year3/team-project/_setup_test"
R="D:/KMITL/NLP/NLP-Year3/team-project/thai-ncd-guideline-qa"
cp "$R/scripts/capture_terminal.ps1" "$W/tools/capture_terminal.ps1"
rm -rf "$W/friend2" "$W/shots"; mkdir -p "$W/friend2" "$W/shots"
LOG="$W/shots/run_log.txt"; : > "$LOG"
step() {
  name="$1"; cwd="$2"; pre="$3"; cmd="$4"; t=$(date +%s)
  powershell -NoProfile -ExecutionPolicy Bypass -File "$W/tools/capture_terminal.ps1" -Command "$cmd" -Out "$W/shots/$name.png" -Cwd "$cwd" -Pre "$pre" -Title "$name" -TimeoutSec 1500 2>&1 | tail -3 | tee -a "$LOG"
  echo "   $name took $(( $(date +%s) - t )) s" | tee -a "$LOG"
}
REPO="$W\\friend2\\thai-ncd-guideline-qa"
ACT='. .\.venv\Scripts\Activate.ps1'
step step01_clone "$W\\friend2" "" 'git clone -b rag/track-b-l1 https://github.com/Chaiporn2005/thai-ncd-guideline-qa; cd thai-ncd-guideline-qa; git log --oneline -1'
step step02_venv "$REPO" "" 'uv venv --python 3.12 .venv; .\.venv\Scripts\Activate.ps1; python --version'
step step03_install "$REPO" "$ACT" 'uv pip install -r requirements-rag.txt -r requirements-agent.txt'
step step04_bundle "$REPO" "$ACT" 'Copy-Item ..\..\drive\ncd_demo_bundle.zip .; (Get-FileHash ncd_demo_bundle.zip -Algorithm SHA256).Hash.ToLower(); python -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip'
step step05_config "$REPO" "$ACT" 'Copy-Item configs\llm\providers.example.yaml configs\llm\providers.yaml; Copy-Item .env.example .env; (Select-String -Path .env -Pattern "^TYPHOON_API_KEY=").Line -replace "=.+","=<มีค่าแล้ว>"; Get-ChildItem .env, configs\llm\providers.yaml | Select-Object Name, Length'
step step06_check "$REPO" "$ACT" 'python -X utf8 demo.py --check'
step step07_warm "$REPO" "$ACT" 'python -X utf8 demo.py --warm'
step step08_cli "$REPO" "$ACT" 'python -X utf8 demo.py "ผู้ป่วยโรคไตเรื้อรังระยะ 3 ควรใช้ยา metformin ขนาดเท่าไร"'
echo "ALL STEPS DONE" | tee -a "$LOG"
