# SRGI RINEX 批量下载工具

[English](README.md) | [简体中文](README.zh-CN.md)

从印尼 [SRGI 门户](https://srgi.big.go.id) 批量下载 **Ina-CORS RINEX** 数据的命令行工具。

输入「测站范围 + 年积日范围」，自动完成 **可用性查询 → 逐站申请 → 下载 → 校验 → 按站打包 → 出报告**。

```
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

## 特点

- **先查可用性**：逐站查询，明确指出哪些站在该时间窗内根本没有数据
- **一站一请求**：避免站点批量接口偶发的串包问题，每个压缩包下载后都会校验站号
- **一站一包**：输出 `by_station/<站号>.zip`，内含 `nav/`（导航）与 `rinex/`（观测）
- **缺日报告**：`report.csv` 列出每站应有天数、实得天数、具体缺失年积日与状态
- **断点续传**：重跑同一条命令，只补缺失的天数
- **零依赖**：仅需 Python 3.8+ 标准库

## 环境要求

- Windows（已测试）、Python 3.8+、Google Chrome（仅用于登录）

## 快速开始

```powershell
# 1) 首次登录：会打开专用 Chrome 窗口，登录一次即可
python srgi_login.py

# 2) 只查可用性，不下载
python srgi_tool.py check --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

# 3) 正式下载
python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026
```

Windows 下也可以直接双击 `login.bat` 和 `download.bat`。

## 参数

| 参数 | 说明 |
|---|---|
| `--pages 17-24` | 按页码选站（每页 20 站） |
| `--stations crjs-csbl` / `crjs,crjt` | 按站号选站（含首尾） |
| `--year 2026` | 年份 |
| `--doy 212-320` | 年积日，支持 `212-320`、`212,215,300-305` |
| `--out DIR` | 输出目录 |
| `--workers 2` | 并发下载站数，默认 2 |
| `--purpose "only for research"` | 申请时填写的用途 |
| `--cookies session.json` | 会话文件 |
| `--retry report.csv` | 只补上次报告里缺的站和天 |

另开一个窗口看实时进度：

```powershell
while ($true) { Clear-Host; Get-Content 'D:\data\2026\status.txt'; Start-Sleep -Seconds 2 }
```

## 输出

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

## 说明

- 会话约 2 小时不用会过期，工具提示后重跑 `srgi_login.py` 即可
- 服务器晚间（北京时间 20:00 之后）明显变慢
- 下载支持 HTTP Range 断点续传
- `session.json`、`chrome_profile/`、下载的数据都已在 `.gitignore` 中排除

## 许可

MIT，见 [LICENSE](LICENSE)。
