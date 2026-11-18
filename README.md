# SRGI RINEX Downloader

A command-line tool to batch-download **Ina-CORS RINEX** data from Indonesia's
[SRGI portal](https://srgi.big.go.id).

Give it a station range and a DOY range — it checks availability, submits one
request per station, downloads the packaged zip, verifies the content, and
produces **one zip per station** plus a CSV report of missing days.

```
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

## Features

- **Availability first** — queries the portal per station and reports which
  stations have no data at all for the requested window.
- **One request per station** — avoids the cross-station mixing the site's
  batch requests occasionally produce; every downloaded zip is verified to
  contain only the requested station before it is merged.
- **One zip per station** — output is `by_station/<code>.zip` containing
  `nav/` (navigation) and `rinex/` (observation) files.
- **Missing-day report** — `report.csv` lists, per station, expected days,
  downloaded days, the exact missing DOYs and a status
  (`complete` / `no data` / `N days missing`).
- **Resumable** — re-run the same command and only the missing days are fetched.
- **No third-party packages** — Python 3.8+ standard library only.

## Requirements

- Windows (tested), Python 3.8+, Google Chrome (only for the one-time login)

## Quick start

```powershell
# 1) one-time login: a dedicated Chrome window opens, log in to SRGI
python srgi_login.py

# 2) check availability only (no download)
python srgi_tool.py check --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

# 3) download
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

On Windows you can also double-click `login.bat` and `download.bat`.

## Usage

```
python srgi_tool.py <check|run> [options]

  --pages 17-24              select stations by page (20 stations per page)
  --stations crjs-csbl       select by station code range (inclusive)
  --year 2026                year
  --doy 212-320              day-of-year range (also 212,215,300-305)
  --out DIR                  output directory
  --workers 2                parallel station downloads (default 2)
  --purpose "only for research"   purpose recorded with each request
  --cookies session.json     session file (default next to the script)

  --retry report.csv         re-fetch only what is missing
```

Watch progress from another terminal:

```powershell
while ($true) { Clear-Host; Get-Content 'D:\data\2026\status.txt'; Start-Sleep -Seconds 2 }
```

## Output

```
D:\data\2026\
├─ by_station\<code>.zip   one archive per station (nav/ + rinex/)
├─ report.csv              station, expected_days, got_days, missing_doys, status
├─ status.txt              live progress
└─ run.log                 log
```

`report.csv` status column:

| status | meaning |
|---|---|
| `完整` / complete | every available day was downloaded |
| `无数据` / no data | the portal has nothing for this station in that window |
| `缺N天` / N missing | available on the portal but not downloaded; see `missing_doys` |

## Notes

- The session expires after roughly two hours of inactivity; run
  `srgi_login.py` again when prompted.
- The portal is noticeably slower in the evening (UTC+8, after 20:00).
- Downloads resume with HTTP Range requests, so interrupted runs can continue.
- `session.json`, `chrome_profile/` and downloaded data are git-ignored.

## License

MIT — see [LICENSE](LICENSE).

---

[简体中文说明](README.zh-CN.md)
