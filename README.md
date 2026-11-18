# SRGI RINEX Downloader · Ina-CORS RINEX 批量下载工具

[中文](#中文) | [English](#english)

从印尼 [SRGI 门户](https://srgi.big.go.id) 批量下载 **Ina-CORS RINEX** 数据的命令行工具：给定测站页码范围与年积日范围，自动完成可用性查询、逐站申请、下载、校验、按站打包，并输出缺失日期报告。

A command-line tool that batch-downloads **Ina-CORS RINEX** data from Indonesia's [SRGI portal](https://srgi.big.go.id): give it a station range and a DOY range, and it checks availability, submits one request per station, downloads and verifies the archives, and reports missing days.

```bash
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

---

## 中文

### 特点

- **先查可用性**：逐站查询，明确指出哪些站在该时间窗内根本没有数据（不会反复重试）
- **一站一请求**：避免站点批量接口偶发的串包问题；每个压缩包下载后都会校验“包内站号必须匹配”
- **一站一包**：输出 `by_station/<站号>.zip`，内含 `nav/`（导航）与 `rinex/`（观测）
- **缺日报告**：`report.csv` 列出每站应有天数、实得天数、具体缺失年积日与状态
- **断点续传**：重跑同一条命令，只补缺失的天数
- **零依赖**：仅需 Python 3.8+ 标准库

### 环境要求

Windows（已测试）、Python 3.8+、Google Chrome（仅用于登录）

### 快速开始

```powershell
# 1) 首次登录：会打开专用 Chrome 窗口，登录一次即可，会话保存在 session.json
python srgi_login.py

# 2) 只查可用性，不下载
python srgi_tool.py check --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

# 3) 正式下载（先逐站查可用性，再下载，报告最准确）
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

# 4) 直接开始下载（跳过逐站可用性检查，最快）
python srgi_tool.py run --no-check --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

> **方式 3 与 4 的区别**：方式 3 会先逐站查询可用性（每站约 1–2 分钟），报告能区分“服务器本来没有”和“没下到”；方式 4 不做这个查询，直接按你给的年积日请求，服务器上没有的日期会自动跳过，**下载立刻开始、速度快很多**，报告里的 `缺N天(未核对)` 需要再跑一次 `check` 才能确认原因。两种方式都支持断点续传和 `--retry`。

Windows 下也可以直接双击 `login.bat` 和 `download.bat`。

### 参数

| 参数 | 说明 |
|---|---|
| `--pages 17-24` | 按页码选站（每页 20 站，与网页一致） |
| `--stations crjs-csbl` / `crjs,crjt` | 按站号选站（含首尾） |
| `--year 2026` | 年份 |
| `--doy 212-320` | 年积日，支持 `212-320`、`212,215,300-305` |
| `--out DIR` | 输出目录 |
| `--workers 2` | 并发下载站数，默认 2 |
| `--purpose "only for research"` | 申请时填写的用途 |
| `--no-check` | 跳过逐站可用性检查，直接开始下载（最快） |
| `--retry report.csv` | 只补上次报告里缺的站和天 |

另开窗口看实时进度：

```powershell
while ($true) { Clear-Host; Get-Content 'D:\data\2026\status.txt'; Start-Sleep -Seconds 2 }
```

### 输出

```
D:\data\2026\
├─ by_station\<站号>.zip   每站一个压缩包（nav/ + rinex/）
├─ report.csv              站号、应有天数、实得天数、缺失年积日、状态
├─ status.txt              实时进度
└─ run.log                 日志
```

`report.csv` 的 `status`：

| 状态 | 含义 |
|---|---|
| `完整` | 该站可用日期全部拿到 |
| `无数据` | 服务器上该时间窗本来就没有数据，不会重试 |
| `缺N天` | 服务器有但没下到，见 `missing_doys` |

### 说明

- 会话约 2 小时不用会过期，工具提示后重跑 `srgi_login.py` 即可
- 服务器晚间（北京时间 20:00 之后）明显变慢，白天通常 1–2MB/s
- 下载支持 HTTP Range 断点续传
- `session.json`、`chrome_profile/`、下载的数据都已在 `.gitignore` 中排除

---

## English

### Features

- **Availability first** — queries the portal per station and reports which stations have no data at all for the requested window.
- **One request per station** — avoids the cross-station mixing that the site's batch endpoints occasionally produce; every archive is verified to contain only the requested station before it is merged.
- **One zip per station** — output is `by_station/<code>.zip` with `nav/` (navigation) and `rinex/` (observation) files.
- **Missing-day report** — `report.csv` lists, per station, expected days, downloaded days, the exact missing DOYs and a status.
- **Resumable** — re-run the same command and only the missing days are fetched.
- **No third-party packages** — Python 3.8+ standard library only.

### Requirements

Windows (tested), Python 3.8+, Google Chrome (only for the one-time login).

### Quick start

```powershell
# 1) one-time login: a dedicated Chrome window opens, log in to SRGI
python srgi_login.py

# 2) check availability only (no download)
python srgi_tool.py check --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

# 3) download (checks availability per station first — most accurate report)
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

# 4) start downloading immediately (skips the per-station availability check)
python srgi_tool.py run --no-check --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

> **Mode 3 vs 4**: mode 3 queries each station's availability first (1–2 minutes per
> station) so the report can tell "no data on the server" apart from "not downloaded".
> Mode 4 skips that query and requests the DOY range directly — the server silently
> skips dates it does not have, so **downloading starts immediately and is much faster**;
> rows marked `缺N天(未核对)` can be confirmed later with `check`. Both modes are
> resumable and both support `--retry`.

On Windows you can also double-click `login.bat` and `download.bat`.

### Usage

```
python srgi_tool.py <check|run> [options]

  --pages 17-24            select stations by page (20 stations per page)
  --stations crjs-csbl     select by station code range (inclusive)
  --year 2026              year
  --doy 212-320            day-of-year range (also 212,215,300-305)
  --out DIR                output directory
  --workers 2              parallel station downloads (default 2)
  --purpose "..."          purpose recorded with each request
  --cookies session.json   session file (default next to the script)
  --no-check               skip the availability check and start downloading at once
  --retry report.csv       re-fetch only what is missing
```

Watch progress from another terminal:

```powershell
while ($true) { Clear-Host; Get-Content 'D:\data\2026\status.txt'; Start-Sleep -Seconds 2 }
```

### Output

```
D:\data\2026\
├─ by_station\<code>.zip   one archive per station (nav/ + rinex/)
├─ report.csv              station, expected_days, got_days, missing_doys, status
├─ status.txt              live progress
└─ run.log                 log
```

`report.csv` status column: `完整` / complete, `无数据` / no data, `缺N天` / N days missing.

### Notes

- The session expires after roughly two hours of inactivity; run `srgi_login.py` again when prompted.
- The portal is noticeably slower in the evening (UTC+8, after 20:00).
- Downloads resume with HTTP Range requests, so interrupted runs can continue.
- `session.json`, `chrome_profile/` and downloaded data are git-ignored.

---

## License / 许可

MIT — see [LICENSE](LICENSE).
