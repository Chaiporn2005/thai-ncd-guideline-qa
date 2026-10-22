# Serve data/raw on localhost so the part-1 review page can open the PDFs at the right page.
Set-Location (Join-Path $PSScriptRoot "..")
python -m http.server 8765 --bind 127.0.0.1 --directory data/raw
