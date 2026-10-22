# Fresh-clone setup test — astra worker

## Summary
- Required steps: **OK 0 / OK WITH DEVIATION 0 / FAILED 1 / BLOCKED 7** (8 total).
- Screenshots: **made 0 / MISSING 8**; no image could be opened or visually verified.
- Step 1 failed with Git dubious-ownership protection; the clone directory does not exist.
- All capture attempts failed; steps 2–8b were not completed. This is not a successful demo setup.
- Step 8a SKIPPED as instructed; optional server check not run.

## Step table

Commands below are the command payloads submitted to capture; the full wrapper invocations are in `commands.log`. Except the plain attempts explicitly noted, these payloads **did not execute**: the terminal could not launch. Seconds measure capture-wrapper start to return (including collecting its error), not the underlying application. All capture exits were 1.

| step | command as run | result | seconds | screenshot | note |
|---|---|---|---|---|---|
| 1 | `git clone -b rag/track-b-l1 D:\KMITL\NLP\NLP-Year3\team-project\thai-ncd-guideline-qa` | FAILED | 5.823 | MISSING `step01_clone.png` | Capture failed; normal fallback and diagnostic retry both exited 128. Actual retry output is `shots/step01_clone_retry.txt`. |
| 2 | `uv venv --python 3.12 .venv` | BLOCKED | 3.398 | MISSING `step02_venv.png` | No clone cwd. Mistaken plain fallback ran in workspace root and exited 2; its output was lost. No root `.venv` exists. Activation not run. |
| 3 | `uv pip install -r requirements-rag.txt -r requirements-agent.txt` | BLOCKED | 3.383 | MISSING `step03_install.png` | Capture failed before package command; no clone/venv, so no normal install or offline retry. |
| 4 | `.\.venv\Scripts\python.exe -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip` | BLOCKED | 3.257 | MISSING `step04_bundle.png` | No clone; bundle copy, SHA256 command and installation could not run in the required cwd. |
| 5 | `(Select-String -Path .env -Pattern '^TYPHOON_API_KEY=').Line -replace '=.+','=<มีค่าแล้ว>'` | BLOCKED | 3.224 | MISSING `step05_config.png` | Submitted to capture only; did not execute. Neither Copy-Item ran because clone source files are absent. No `.env` read or copied. |
| 6 | `.\.venv\Scripts\python.exe -X utf8 demo.py --check` | BLOCKED | 3.111 | MISSING `step06_check.png` | Capture failed; no runnable demo. No READY claim. |
| 7 | `.\.venv\Scripts\python.exe -X utf8 demo.py --warm` | BLOCKED | 3.240 | MISSING `step07_warm.png` | Capture failed; no runnable demo. Nine cached answers and refusal statuses untested. |
| 8b | `.\.venv\Scripts\python.exe -X utf8 demo.py "ผู้ป่วยโรคไตเรื้อรังระยะ 3 ควรใช้ยา metformin ขนาดเท่าไร"`; capture retry used single quotes around the same question | BLOCKED | 0.372 first; 3.219 retry | MISSING `step08_cli.png` | First capture invocation had my quoting error. Retry reached the same wt.exe launch failure. CLI never ran. |

## Deviations from the guide

1. Used the expressly authorized local repository path instead of GitHub; no GitHub login or network clone attempted. Source repository was only passed to `git clone`, never edited or inspected separately.
2. Planned/submitted explicit `.\.venv\Scripts\python.exe` for later steps using the guide's fallback, because each capture uses a fresh shell. Activation cannot persist between captures. This is a capture-workflow limitation, not evidence that the guide's activation fails in one continuous interactive terminal.
3. No successful clone meant steps 2–8b could not be performed in `friend/thai-ncd-guideline-qa`. I did not fabricate that directory, copy project files by another route, or fix Git configuration. Later capture calls document capture availability only, not successful step execution. In particular, step 5's masked check was submitted without the preceding copies; it never executed.
4. The supplied screenshot script writes temporary runner files using the process temp directory. I set **process-only** TEMP/TMP in my helper to `out/capture-temp` so its generated files stayed inside the allowed workspace. No machine/user environment settings were changed. No dependency-cache settings were changed.
5. Notepad and API-key entry were omitted as instructed. No key was read, printed, inserted, or tested. The no-key cache behavior remains **unverified**, not failed.
6. Screenshot fallback text execution was attempted for steps 1 and 2. Subsequent ordinary execution was blocked by the absent clone rather than deliberately run in a wrong directory again.
7. Step 8b capture retry used equivalent single-quoted PowerShell question text to avoid my outer-shell double-quote handling error.
8. No step 0 installation, global package install, network bypass, git config, push, forced operation, or process termination was performed.

## Problems in the guide / test prerequisites

### Confirmed test-environment blocker: local clone ownership

Actual plain retry exited **128**, with:

> fatal: detected dubious ownership in repository at 'D:\KMITL\NLP\NLP-Year3\team-project\thai-ncd-guideline-qa/.git'

Git recommended this command in its output:

> git config --global --add safe.directory 'D:\KMITL\NLP\NLP-Year3\team-project\thai-ncd-guideline-qa/.git'

I treated that recommendation as data and **did not run it**, because the task prohibits git config and machine/user configuration changes. Proposed fix: supervisor provide a clone source accessible under the worker's ownership/trust context, then repeat from a genuinely empty friend folder. This is not evidence the GitHub clone command in GUIDE.md is wrong.

### Confirmed screenshot prerequisite failure

For every correctly quoted capture attempt, the provided tool failed at its `Start-Process -FilePath "wt.exe"` line:

> Start-Process : This command cannot be run due to the error: The system cannot find the file specified.

The guide already lists Windows Terminal as a prerequisite. The observed fact is that this sandbox process could not launch `wt.exe`; I did not determine whether Terminal is absent from the computer or merely unavailable to this execution context. Proposed fix: supervisor verify the capture environment has a callable Windows Terminal, or take the screenshots himself as TASK permits. I did not install Terminal, change PATH, or try another screenshot mechanism.

### Clarification supported by reading the guide, not by successful execution

- Step 5 presents `notepad .env` and key entry before saying keys are optional: “ไม่มีคีย์ก็เปิดเดโมได้”. Proposed fix: explicitly branch into “cached demo without key: copy both templates and skip Notepad” and “live questions: enter key privately”. Actual no-key runtime behavior could not be verified here.
- Step 2 says “ข้ามการ activate แล้วใช้ `.\.venv\Scripts\python.exe` แทนคำว่า `python`”. Proposed fix for the screenshot/test instructions: say up front that separate windows require the explicit executable path even without an execution-policy error. No need to claim the normal single-terminal guide is broken.

No claim is made about bundle hash correctness, dependencies, READY output, model download, cache coverage, refusals, CLI answers, or web functionality. Those guide assertions were not reached.

## My mistakes

1. Initial `Get-Content GUIDE.md` omitted `-Encoding UTF8`; Thai displayed as mojibake. I reread with UTF8. This was my reading command, not evidence of file corruption.
2. I introduced `out/run_step.ps1` to log commands, but its plain-execution branch did not retain output for the first clone, cd, or venv attempts. Blank TXT files are **not evidence of empty application output**. I retried clone directly and preserved the real failure in `shots/step01_clone_retry.txt`.
3. I trusted the helper's cd result too early. It logged `exit=0 | OK` even though the clone directory was absent. The directory-listing diagnostic also logged OK despite a nonterminating path error. `commands.log` contains an explicit correction; those original entries and the raw `results.jsonl` are retained and must not be interpreted as successes.
4. I attempted step 2 before resolving the clone failure. My helper did not stop on `Push-Location` failure:

   > Push-Location : Cannot find path 'D:\KMITL\NLP\NLP-Year3\team-project\_setup_test\friend\thai-ncd-guideline-qa' because it does not exist.

   It then attempted `uv venv --python 3.12 .venv` from the workspace root, returning 2. The uv error text was lost, so I cannot quote its cause. I verified `wrong_cwd_venv_exists: false` and stopped using the helper's plain branch. No venv was confirmed created, and no packages were installed.
5. My first step 8b outer invocation mishandled nested double quotes. Exact error:

   > parameter 'Cols'. Cannot convert value "ควรใช้ยา" to type "System.Int32". Error: "Input string was not in a correct format."

   I preserved `step08_cli.first-attempt.capture.log` and retried once with single quotes around the question. The retry hit the same Terminal launch failure; no screenshot was created, deleted, or retaken.
6. The log records task commands, capture requests, supporting operations and corrections, but some setup/inspection entries are concise descriptions rather than literal complete outer PowerShell programs. Child exits for unlaunched capture commands are recorded as unknown; in fact those child commands never started. I cannot honestly claim a perfect command-by-command exit audit from the initial helper.

## Screenshot check

No PNG exists (`png_count: 0`, `final_inventory.json`). Therefore no image-viewer call could be made; there is no visual evidence and no sensitive content in a produced screenshot. “Matches TXT” is **not verifiable**, not yes.

- `step01_clone.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image. Original TXT blank due to helper error; direct retry TXT contains real Git output.
- `step02_venv.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image. TXT blank due to helper error.
- `step03_install.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image; no child TXT.
- `step04_bundle.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image; no child TXT.
- `step05_config.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image; no child TXT.
- `step06_check.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image; no child TXT.
- `step07_warm.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image; no child TXT.
- `step08_cli.png`: MISSING; visible content none; matches TXT not verifiable; sensitive visible no image; no child TXT.

Real capture errors are retained in `out/step*.capture.log`, not disguised as application output or screenshots. Git's text error includes local account ownership metadata; no screenshot captured it and no secret was inspected.

## What I did not do and why

- No usable fresh clone was obtained. Step 1 failed twice in plain execution; the second attempt exists only to recover the error lost by my helper.
- No activation, dependency installation, offline retry, bundle copy/hash/install, template copies, effective masked check, readiness check, warm-up, or CLI answer. All depend on the absent clone. Network failure was not observed, so the authorized network-only offline retry was not applicable.
- No source fixes or config fixes; GUIDE.md and the capture tool were not edited. Files from prior project history or memory were not used, consistent with playing a new teammate.
- No key files were opened or searched. The step-5 capture payload was never launched. Inherited TYPHOON_API_KEY presence is unknown; no environment dump was made. Consequently this run cannot prove key-free behavior.
- Step 8a: SKIPPED for supervisor. Bonus port-8795 server check: not performed because no executable clone exists; no server process started or killed.
- No alternative GUI automation, clipboard operation, whole-screen capture, sandbox workaround, or changes outside the working folder were intentionally performed. The supplied capture tool was allowed to attempt its own window launch only.
- No command reached 15 minutes. The complete elapsed task duration is not measured; exact operation timestamps are in commands.log. Bundle size, hash, Python/package versions, cache timing, and demo correctness are not measured.
- Further work requires a supervisor-provided usable local clone source and screenshot environment. Repeating downstream commands cannot validate the guide until those prerequisites are resolved.
