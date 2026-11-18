"""登录 SRGI：打开专用 Chrome 窗口 -> 手动登录 -> 自动保存 cookie 到 session.json

用法:  python srgi_login.py
"""
import os, sys, time, json, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cdp import WS

PROFILE = os.environ.get("SRGI_PROFILE") or os.path.join(HERE, "chrome_profile")
COOKIES = os.environ.get("SRGI_COOKIES") or os.path.join(HERE, "session.json")
PORT = int(os.environ.get("SRGI_PORT") or 9223)
LOGIN_URL = "https://srgi.big.go.id/login"


def find_chrome():
    cands = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "google-chrome", "chromium", "chrome",
    ]
    for c in cands:
        if c and (os.path.exists(c) if os.path.sep in c else True):
            return c
    return None


def http_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def cdp_up():
    try:
        http_json(f"http://127.0.0.1:{PORT}/json/version")
        return True
    except Exception:
        return False


def main():
    chrome = find_chrome()
    if not chrome:
        print("找不到 Chrome，请先安装 Google Chrome")
        return
    if not cdp_up():
        print("正在打开 Chrome 窗口… 请在弹出的窗口里登录 SRGI（登录一次即可）")
        subprocess.Popen([chrome, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}",
                          "--no-first-run", "--no-default-browser-check", "--window-size=1300,900", LOGIN_URL])
        for _ in range(40):
            time.sleep(1)
            if cdp_up():
                break
        else:
            print("Chrome 调试端口没有起来（可能已有 Chrome 在运行且占用了配置）。")
            print("请关掉本工具打开的 Chrome 窗口后重试。")
            return
    print("等待登录完成（登录成功后会自动保存会话）…")
    t0 = time.time()
    while time.time() - t0 < 900:
        try:
            pages = [p for p in http_json(f"http://127.0.0.1:{PORT}/json/list") if p.get("type") == "page"]
        except Exception:
            pages = []
        target = next((p for p in pages if "srgi.big.go.id" in (p.get("url") or "")), None)
        if target:
            try:
                ws = WS(target["webSocketDebuggerUrl"], timeout=20)
                url = ws.call("Runtime.evaluate", {"expression": "location.href", "returnByValue": True})["result"]["value"]
                if "/login" not in url:
                    ck = ws.call("Network.getAllCookies", {})["cookies"]
                    ck = [c for c in ck if "srgi" in c.get("domain", "")]
                    if any(c["name"] == "srgi_session" for c in ck):
                        json.dump({"cookies": ck, "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"},
                                  open(COOKIES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                        print("登录成功，会话已保存:", COOKIES)
                        ws.close()
                        return
                ws.close()
            except Exception:
                pass
        time.sleep(3)
    print("超时未检测到登录，请重试")


if __name__ == "__main__":
    main()
