#!/bin/bash
# FINAL supervisor run of docs/SETUP_GUIDE_TH.md (as pushed at the commit shown in step 1) on a brand-new folder, one real terminal screenshot per step.
W="D:/KMITL/NLP/NLP-Year3/team-project/_setup_test"
rm -rf "$W/friend3" "$W/shots3"; mkdir -p "$W/friend3" "$W/shots3"
cp "D:/KMITL/NLP/NLP-Year3/team-project/thai-ncd-guideline-qa/scripts/capture_terminal.ps1" "$W/tools/capture_terminal.ps1"
LOG="$W/shots3/run_log.txt"; : > "$LOG"
step() {
  name="$1"; cwd="$2"; pre="$3"; cmd="$4"; t=$(date +%s)
  powershell -NoProfile -ExecutionPolicy Bypass -File "$W/tools/capture_terminal.ps1" -Command "$cmd" -Out "$W/shots3/$name.png" -Cwd "$cwd" -Pre "$pre" -Title "$name" -TimeoutSec 1500 2>&1 | tail -3 | tee -a "$LOG"
  echo "   $name took $(( $(date +%s) - t )) s" | tee -a "$LOG"
}
REPO="$W\friend3\thai-ncd-guideline-qa"
ACT='. .\.venv\Scripts\Activate.ps1'
step step01_clone "$W\friend3" "" 'git clone -b rag/track-b-l1 https://github.com/Chaiporn2005/thai-ncd-guideline-qa; cd thai-ncd-guideline-qa; git log --oneline -1'
step step02_venv "$REPO" "" 'uv venv --python 3.12 .venv; .\.venv\Scripts\Activate.ps1; python --version'
step step03_install "$REPO" "$ACT" 'uv pip install -r requirements-rag.txt -r requirements-agent.txt'
step step04_bundle "$REPO" "$ACT" 'Copy-Item ..\..\drive\ncd_demo_bundle.zip .; (Get-FileHash ncd_demo_bundle.zip -Algorithm SHA256).Hash.ToLower(); python -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip'
step step05_config "$REPO" "$ACT" 'Copy-Item configs\llm\providers.example.yaml configs\llm\providers.yaml; if (-not (Test-Path .env)) { Copy-Item .env.example .env }; (Select-String -Path .env -Pattern "^TYPHOON_API_KEY=").Line -replace "=.+","=<มีค่าแล้ว>"; git status --short'
step step06_check "$REPO" "$ACT" 'python -X utf8 demo.py --check'
step step07_warm "$REPO" "$ACT" 'python -X utf8 demo.py --warm'
step step08_cli "$REPO" "$ACT" 'python -X utf8 demo.py "ผู้ป่วยโรคไตเรื้อรังระยะ 3 ควรใช้ยา metformin ขนาดเท่าไร"'
step extra_offline_sim "$REPO" "$ACT; \$env:HF_HUB_OFFLINE='1'; \$env:HTTPS_PROXY='http://127.0.0.1:9'; \$env:HTTP_PROXY='http://127.0.0.1:9'" 'python -X utf8 demo.py --warm; python -X utf8 demo.py "ยา glipizide ควรกินก่อนอาหารเท่าไร (คำถามใหม่ ไม่มีในแคช)"'
echo "ALL STEPS DONE" | tee -a "$LOG"
