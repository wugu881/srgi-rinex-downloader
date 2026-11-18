r"""SRGI Ina-CORS RINEX 通用下载工具

用法示例:
  # 1) 首次或会话过期后登录（会打开一个专用 Chrome 窗口，手动登录一次即可）
  python srgi_tool.py login

  # 2) 只检查可用性，不下载：第17页到第24页，2026年 212-320
  python srgi_tool.py check --pages 17-24 --year 2026 --doy 212-320

  # 3) 直接跑完整流程（检查+下载+校验+报告）
  python srgi_tool.py run --pages 17-24 --year 2026 --doy 212-320 --out D:\data\2026

  # 4) 指定测站范围（按站点列表顺序，含首尾）
  python srgi_tool.py run --stations crjs-csbl --year 2026 --doy 212-320

  # 5) 只补上次缺的（读取报告，自动重下缺日期的站）
  python srgi_tool.py run --retry D:\data\2026\report.csv

输出:
  <out>/by_station/<站号>.zip    每个站一个压缩包（nav/ + rinex/）
  <out>/report.csv              每站应有天数/实得天数/缺失清单/状态
  <out>/status.txt              实时进度（可用 PowerShell 循环查看）
"""
import os, sys, json, time, re, zipfile, shutil, threading, argparse, csv, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "https://srgi.big.go.id"
PAT = re.compile(r"^([a-z0-9]{4})(\d{3})0\.(\d{2})[a-z]$")


# ---------------------------------------------------------------- session
def make_session(cookie_file):
    import urllib.request, http.cookiejar
    cfg = json.load(open(cookie_file, encoding="utf-8"))
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    for c in cfg["cookies"]:
        cj.set_cookie(http.cookiejar.Cookie(0, c["name"], c["value"], None, False, c["domain"], True,
                     c["domain"].startswith("."), c.get("path", "/"), True, c.get("secure", True),
                     int(c["expires"]) if c.get("expires", -1) > 0 else None, False, None, None, {"HttpOnly": None}, False))
    return op, cfg.get("ua", "Mozilla/5.0"), cj


class Api:
    def __init__(self, cookie_file):
        self.op, self.ua, self.cj = make_session(cookie_file)

    def save_cookies(self, path):
        out = []
        for c in self.cj:
            out.append({"name": c.name, "value": c.value, "domain": c.domain, "path": c.path,
                        "expires": c.expires if c.expires else -1, "secure": bool(c.secure),
                        "httpOnly": True})
        if out:
            json.dump({"cookies": out, "ua": self.ua}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- protobuf helpers
    @staticmethod
    def varint(n):
        out = b""
        while True:
            b = n & 0x7F
            n >>= 7
            if n:
                out += bytes([b | 0x80])
            else:
                return out + bytes([b])

    @classmethod
    def field(cls, num, data):
        if isinstance(data, str):
            data = data.encode()
        return cls.varint((num << 3) | 2) + cls.varint(len(data)) + data

    @staticmethod
    def parse_pb(b):
        out = []
        i = 0
        while i < len(b):
            key = 0; shift = 0
            while True:
                c = b[i]; i += 1
                key |= (c & 0x7F) << shift
                shift += 7
                if not c & 0x80:
                    break
            fn, wt = key >> 3, key & 7
            if wt == 0:
                v = 0; shift = 0
                while True:
                    c = b[i]; i += 1
                    v |= (c & 0x7F) << shift
                    shift += 7
                    if not c & 0x80:
                        break
                out.append((fn, 0, v))
            elif wt == 2:
                ln = 0; shift = 0
                while True:
                    c = b[i]; i += 1
                    ln |= (c & 0x7F) << shift
                    shift += 7
                    if not c & 0x80:
                        break
                out.append((fn, 2, b[i:i + ln])); i += ln
            else:
                break
        return out

    @classmethod
    def split_frames(cls, text):
        frames = []; i = 0; n = len(text)
        import base64
        while i < n:
            if text[i] in "\r\n":
                i += 1; continue
            ok = False
            for k in range(8, n - i + 1, 4):
                try:
                    dec = base64.b64decode(text[i:i + k], validate=True)
                except Exception:
                    continue
                if len(dec) < 5:
                    continue
                ln = int.from_bytes(dec[1:5], "big")
                if len(dec) == 5 + ln:
                    frames.append(dec[5:]); i += k; ok = True; break
            if not ok:
                break
        return frames

    def grpc(self, method, payload):
        import base64, struct, urllib.request
        body = base64.b64encode(b"\x00" + struct.pack(">I", len(payload)) + payload)
        req = urllib.request.Request(BASE + "/middleware-cors/files.FilesService/" + method, data=body,
                                     headers={"User-Agent": self.ua, "Accept": "application/grpc-web-text",
                                              "Content-Type": "application/grpc-web-text", "X-Grpc-Web": "1",
                                              "X-User-Agent": "grpc-web-javascript/0.1", "Origin": BASE,
                                              "Referer": BASE + "/rinex/v1/carts"})
        return self.op.open(req, timeout=300).read().decode()

    def get(self, url, headers=None, timeout=120):
        import urllib.request
        h = {"User-Agent": self.ua}
        h.update(headers or {})
        return self.op.open(urllib.request.Request(url, headers=h), timeout=timeout)

    # ---- endpoints
    def stations(self):
        txt = self.grpc("StasiunV1", self.field(1, "stasiun"))
        out = []
        for f in self.split_frames(txt):
            p = self.parse_pb(f)
            if p and p[0][0] == 1:
                out.append(p[0][2].decode())
        return out

    def available_days(self, code, year_tag, doy_set=None):
        txt = self.grpc("GetFilesV1", self.field(1, code))
        doys = set()
        pat = re.compile(r"^" + re.escape(code) + r"(\d{3})0\." + year_tag + r"d\.gz$", re.I)
        for f in self.split_frames(txt):
            p = dict((fn, v) for fn, wt, v in self.parse_pb(f))
            name = p.get(1, b"").decode(errors="replace")
            m = pat.match(name)
            if m:
                d = int(m.group(1))
                if doy_set is None or d in doy_set:
                    doys.add(d)
        return doys

    def request_zip(self, entries, purpose):
        names = [e["filename"] for e in entries]
        payload = (self.field(1, json.dumps(entries, separators=(",", ":"))) +
                   self.field(2, json.dumps(names, separators=(",", ":"))) +
                   self.field(3, purpose) + self.field(4, "27389"))
        txt = self.grpc("DownloadAllConversiMoveToSrgi", payload)
        for f in self.split_frames(txt):
            p = self.parse_pb(f)
            if p and p[0][0] == 1:
                return p[0][2].decode()
        return None


# ---------------------------------------------------------------- helpers
def parse_range(spec):
    out = set()
    for part in re.split(r"[,;\s]+", str(spec).strip()):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def parse_station_range(all_codes, spec):
    if "-" in spec:
        a, b = spec.split("-", 1)
        i, j = all_codes.index(a), all_codes.index(b)
        if i > j:
            i, j = j, i
        return all_codes[i:j + 1]
    return [c.strip() for c in spec.split(",") if c.strip()]


def pages_to_codes(all_codes, spec, per_page=20):
    lo, hi = (int(x) for x in spec.split("-"))
    return all_codes[(lo - 1) * per_page: hi * per_page]


def entry(code, doy, year_tag, year):
    return {"doy": doy, "status_file": True, "bg_selected": "bg-primary", "lock": True,
            "filename": f"{code}{doy:03d}0.{year_tag}d.gz", "path": f"{year}/{code}",
            "type": "nowYear" if year == time.localtime().tm_year else "lastYear",
            "stasiun": code, "total": None}


def merge_zip(part, target_path, code):
    existing = set()
    if os.path.exists(target_path):
        with zipfile.ZipFile(target_path) as z:
            existing = set(z.namelist())
    added = 0
    with zipfile.ZipFile(part) as zs:
        infos = [i for i in zs.infolist()
                 if PAT.match(os.path.basename(i.filename)) and os.path.basename(i.filename).startswith(code)]
        with zipfile.ZipFile(target_path, "a" if existing else "w", zipfile.ZIP_DEFLATED, compresslevel=5) as zd:
            for info in infos:
                if info.filename in existing:
                    continue
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = info.external_attr
                with zs.open(info) as fs, zd.open(zi, "w") as fd:
                    shutil.copyfileobj(fs, fd, 1 << 20)
                added += 1
    return added


def days_in_zip(path):
    with zipfile.ZipFile(path) as z:
        doys = {}
        for n in z.namelist():
            m = PAT.match(os.path.basename(n))
            if m:
                doys.setdefault(m.group(1), set()).add(int(m.group(2)))
        return doys


def main():
    ap = argparse.ArgumentParser(description="SRGI Ina-CORS RINEX 批量下载")
    ap.add_argument("cmd", choices=["check", "run", "login"])
    ap.add_argument("--stations", help="站号范围，如 crjs-csbl 或 crjs,crjt")
    ap.add_argument("--pages", help="页码范围（每页20站），如 17-24")
    ap.add_argument("--year", type=int, default=time.localtime().tm_year)
    ap.add_argument("--doy", default="1-365", help="年积日范围，如 212-320 或 212,215,300-305")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
    ap.add_argument("--cookies", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json"))
    ap.add_argument("--purpose", default="only for research")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--retry", help="读取上次 report.csv，只补缺失")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    if args.cmd == "login":
        print("请先运行: python srgi_login.py   （会打开专用 Chrome 窗口）")
        return

    out = os.path.abspath(args.out)
    by = os.path.join(out, "by_station")
    tmp = os.path.join(out, "_tmp_zips")
    os.makedirs(by, exist_ok=True)
    os.makedirs(tmp, exist_ok=True)
    logf = open(os.path.join(out, "run.log"), "a", encoding="utf-8")

    def log(msg):
        line = time.strftime("%Y-%m-%d %H:%M:%S") + "  " + msg
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    if not os.path.exists(args.cookies):
        print("还没有登录会话：请先运行  python srgi_login.py  （或双击 登录.bat）")
        return
    api = Api(args.cookies)
    all_codes = api.stations()
    if args.retry:
        rows_in = list(csv.DictReader(open(args.retry, encoding="utf-8-sig")))
        codes = [r["station"] for r in rows_in if r.get("station")]
        plan = {r["station"]: parse_range(r["expected_doys"]) for r in rows_in if r.get("expected_doys")}
        if not plan:
            log("这个报告是旧格式（没有 expected_doys 列），请用 --doy 重新指定范围，或重新生成报告")
            return
        if not codes:
            log("报告里没有测站，退出"); return
    else:
        codes = pages_to_codes(all_codes, args.pages) if args.pages else parse_station_range(all_codes, args.stations)
        plan = {}

    year_tag = str(args.year)[-2:]
    doy_all = parse_range(args.doy)
    log(f"stations: {len(codes)} ({codes[0]}..{codes[-1]}), year {args.year}, doys {len(doy_all)} ({min(doy_all)}-{max(doy_all)})")

    # 1) availability（以“本次关心的日期集合”为准）
    avail = {}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    targets = {c: (set(plan[c]) if plan and c in plan else doy_all) for c in codes}

    def check_one(code):
        try:
            a = Api(args.cookies)
            return code, a.available_days(code, year_tag, targets[code])
        except Exception:
            return code, None

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(check_one, c): c for c in codes}
        done = 0
        for fut in as_completed(futs):
            code, a = fut.result()
            avail[code] = a
            done += 1
            if done % 5 == 0:
                log(f"  检查可用性 {done}/{len(codes)}")

    need = {}
    for code in codes:
        a = avail.get(code)
        if a is None:
            continue
        got = set()
        p = os.path.join(by, f"{code}.zip")
        if os.path.exists(p):
            try:
                got = set(days_in_zip(p).get(code, set()))
            except Exception:
                got = set()
        miss = a - got
        if miss:
            need[code] = sorted(miss)
    log(f"  可用性检查完成: 需要补 {len(need)} 个站, {sum(len(v) for v in need.values())} 站-天")

    # 2) download
    MAX_RETRY = 3
    if args.cmd == "run" and need and not args.check_only:
        status_path = os.path.join(out, "status.txt")
        prog = {"done": 0, "total": len(need), "cur": set(), "ok": 0, "fail": 0}
        plock = threading.Lock()

        def write_status():
            while True:
                with plock:
                    d, t, cur = prog["done"], prog["total"], set(prog["cur"])
                    ok, bad = prog["ok"], prog["fail"]
                pct = 100 * d / t if t else 100
                bar = "#" * int(pct / 2.5) + "-" * (40 - int(pct / 2.5))
                lines = ["=" * 70,
                         f" SRGI 下载进度  {time.strftime('%H:%M:%S')}",
                         "=" * 70,
                         f" 总体 [{bar}] {pct:5.1f}%   完成 {d}/{t} 站 (成功 {ok} / 失败 {bad})",
                         f" 正在下载: {', '.join(sorted(cur)) if cur else '-'}",
                         "-" * 70,
                         f" 输出: {by}",
                         f" 报告: {os.path.join(out, 'report.csv')}",
                         "-" * 70]
                try:
                    with open(status_path, "w", encoding="utf-8-sig") as f:
                        f.write("\n".join(lines) + "\n")
                except Exception:
                    pass
                time.sleep(2)

        threading.Thread(target=write_status, daemon=True).start()

        def worker(q):
            while True:
                code = q.get()
                if code is None:
                    return
                with plock:
                    prog["cur"].add(code)
                ok = False
                for attempt in range(MAX_RETRY):
                    try:
                        ok = do_station(api, code, need[code], year_tag, args.year, by, tmp, args.purpose, log)
                    except Exception:
                        log(f"  {code}: EXC {traceback.format_exc()[-200:]}")
                    if ok:
                        break
                    time.sleep(5)
                with plock:
                    prog["cur"].discard(code)
                    prog["done"] += 1
                    prog["ok" if ok else "fail"] += 1
                q.task_done()

        import queue
        q = queue.Queue()
        for c in need:
            q.put(c)
        ths = [threading.Thread(target=worker, args=(q,), daemon=True) for _ in range(max(1, args.workers))]
        for t in ths:
            t.start()
        q.join()

    # 3) final report
    rows = []
    for code in codes:
        a = avail.get(code)
        if a is None:
            rows.append([code, "", "", "", "", "", "查询失败"]); continue
        p = os.path.join(by, f"{code}.zip")
        got = set()
        if os.path.exists(p):
            try:
                got = set(days_in_zip(p).get(code, set()))
            except Exception:
                pass
        missing = a - got
        status = "无数据" if not a else ("完整" if not missing else f"缺{len(missing)}天")
        rows.append([code, len(a), len(got), len(missing),
                     " ".join(str(d) for d in sorted(missing)),
                     " ".join(str(d) for d in sorted(a)), status])

    rp = os.path.join(out, "report.csv")
    with open(rp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["station", "expected_days", "got_days", "missing_count", "missing_doys", "expected_doys", "status"])
        w.writerows(rows)

    ok = sum(1 for r in rows if r[6] == "完整")
    nodata = sum(1 for r in rows if r[6] == "无数据")
    bad = [r for r in rows if r[6] not in ("完整", "无数据")]
    log(f"完成: 完整 {ok}, 无数据 {nodata}, 待补 {len(bad)}")
    for r in bad[:30]:
        log(f"  {r[0]}: {r[6]}  {r[4][:80]}")
    log(f"报告: {rp}")
    try:
        api.save_cookies(args.cookies)
    except Exception:
        pass
    if bad:
        log("如需只补这些站: python srgi_tool.py run --retry " + rp)


def do_station(api, code, doys, year_tag, year, by, tmp, purpose, log):
    entries = [entry(code, d, year_tag, year) for d in sorted(doys)]
    zname = api.request_zip(entries, purpose)
    if not zname:
        log(f"  {code}: 提交失败"); return False
    deadline = time.time() + 3600
    url = BASE + "/zip_middleware_cors/" + zname
    total = None
    while total is None and time.time() < deadline:
        try:
            r = api.op.open(__import__("urllib.request", fromlist=["Request"]).Request(url, method="HEAD",
                            headers={"User-Agent": api.ua}), timeout=45)
            total = int(r.headers.get("Content-Length") or 0)
        except Exception:
            time.sleep(10)
    if not total:
        log(f"  {code}: 打包超时"); return False
    dest = os.path.join(tmp, zname)
    while time.time() < deadline:
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have >= total:
            break
        try:
            h = {"User-Agent": api.ua}
            if have:
                h["Range"] = f"bytes={have}-"
            r = api.get(url, h, timeout=60)
            with open(dest, "ab" if have else "wb") as f:
                while True:
                    c = r.read(1 << 20)
                    if not c:
                        break
                    f.write(c)
        except Exception:
            time.sleep(3)
    if not os.path.exists(dest) or os.path.getsize(dest) < total:
        log(f"  {code}: 下载不完整"); return False
    got = days_in_zip(dest)
    if code not in got:
        log(f"  {code}: 包里不是这个站的数据({sorted(got)})"); return False
    added = merge_zip(dest, os.path.join(by, f"{code}.zip"), code)
    log(f"  {code}: 补 {len(got[code])} 天, 合并 {added} 个文件")
    return True


if __name__ == "__main__":
    main()
