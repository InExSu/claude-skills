#!/usr/bin/env python3
"""Прогнать .drakon через настоящий движок DrakonHub в headless-браузере.

Зачем: `drakon_tool.py check` ловит только топологические ловушки, которые
удалось формализовать. Редактор же может зависнуть на конструкции, которую
чекер считает корректной. Этот скрипт строит холст реальным
`drakon_canvas.js` и честно сообщает OK / HANG / ERROR.

Usage:
    python3 drakon_try.py render <file.drakon> [ms]   # построить холст
    python3 drakon_try.py        <file.drakon> [ms]   # то же, render по умолчанию
    python3 drakon_try.py stack  <file.drakon>        # стек места зависания

Требования: node, playwright (node-модуль) и chromium в кэше Playwright.
Путь к node-модулям — переменная PLAYWRIGHT_MODULES (по умолчанию
~/node_modules). Клон `stepan-mitkin/drakonhub_desktop` скачивается в кэш
при первом запуске.

Коды вывода: 0 = OK, 1 = HANG, 2 = ERROR.
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache")
REPO = os.path.abspath(os.path.join(CACHE, "drakonhub_desktop"))
PORT = 8765
# Где искать node-модуль playwright. Обычно это ~/node_modules (глобальная
# установка) — путь задаётся переменной PLAYWRIGHT_MODULES.
DEFAULT_NODE_MODULES = os.path.expanduser("~/node_modules")
DEFAULT_TIMEOUT_MS = 20000

# JS, который связывает зависимости drakon_canvas так же, как local.js,
# и строит холст. Вынесен отдельно, чтобы не экранировать кавычки в python.
RENDER_JS = r"""
const { chromium } = require(require.resolve('playwright', { paths: [process.env.PW] }));
const fs = require('fs');
const file = process.argv[2];
const TMO = parseInt(process.argv[3] || '20000');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME_BIN });
  const p = await b.newPage();
  let pageErr = null;
  p.on('pageerror', e => { pageErr = String(e.message).split('\n')[0].slice(0, 300); });
  await p.goto(process.env.URL, { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(2000);
  const diagram = JSON.parse(fs.readFileSync(file, 'utf8'));
  const work = p.evaluate(({ diagram }) => {
    const dc = window.drakon_canvas();
    const _common = window.dh2common();
    const _utils = window.utils();
    const _html = window.html_0_1();
    const _core = window.dh2core();
    _core.dh2common = _common; _core.html = _html; _core.utils = _utils;
    dc.edit_tools = window.edit_tools();
    dc.html = _html;
    dc.tracing = _core;
    dc.utils = _utils;
    dc.gconfig = window.dh2config();
    const w = dc.DrakonCanvas();
    w.init();
    const holder = document.createElement('div');
    document.body.appendChild(holder);
    holder.appendChild(w.render(1200, 800, {}));
    return w.setDiagram('t1', JSON.parse(JSON.stringify(diagram)), undefined, true)
      .then(() => ({ ok: true, nodes: Object.keys(w.visuals.nodes).length }));
  }, { diagram })
    .then(r => ({ status: 'OK', nodes: r.nodes }))
    .catch(e => ({ status: 'ERROR', msg: String(e.message).slice(0, 300) }));
  const res = await Promise.race([work, sleep(TMO).then(() => ({ status: 'HANG' }))]);
  if (res.status === 'OK') {
    console.log('OK\tnodes=' + res.nodes);
  } else if (res.status === 'HANG') {
    console.log('HANG');
  } else {
    console.log('ERROR\t' + (res.msg || '') + (pageErr ? ' | pageerr: ' + pageErr : ''));
  }
  await b.close();
  process.exit(0);
})();
"""

STACK_JS = r"""
const { chromium } = require(require.resolve('playwright', { paths: [process.env.PW] }));
const fs = require('fs');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME_BIN });
  const p = await b.newPage();
  await p.goto(process.env.URL, { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(2000);
  const diagram = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const cdp = await p.context().newCDPSession(p);
  const scripts = new Map();
  cdp.on('Debugger.scriptParsed', e => scripts.set(e.scriptId, e.url));
  await cdp.send('Debugger.enable');
  const paused = new Promise(res => cdp.on('Debugger.paused', res));
  p.evaluate(({ diagram }) => {
    const dc = window.drakon_canvas();
    const _c = window.dh2common(); const _u = window.utils(); const _h = window.html_0_1();
    const _core = window.dh2core(); _core.dh2common = _c; _core.html = _h; _core.utils = _u;
    dc.edit_tools = window.edit_tools(); dc.html = _h; dc.tracing = _core;
    dc.utils = _u; dc.gconfig = window.dh2config();
    const w = dc.DrakonCanvas(); w.init();
    const holder = document.createElement('div'); document.body.appendChild(holder);
    holder.appendChild(w.render(1200, 800, {}));
    return w.setDiagram('t1', JSON.parse(JSON.stringify(diagram)), undefined, true);
  }, { diagram }).catch(() => {});
  await sleep(4000);
  await cdp.send('Debugger.pause');
  const ev = await Promise.race([paused, sleep(15000).then(() => null)]);
  if (!ev) { console.log('NO PAUSE EVENT (возможно, диаграмма отрисовалась)'); process.exit(0); }
  console.log('PAUSED reason:', ev.reason);
  ev.callFrames.slice(0, 25).forEach((f, i) => {
    const url = (scripts.get(f.location.scriptId) || '?').split('/').pop();
    console.log(`  #${i} ${f.functionName || '(anon)'}  ${url}:${f.location.lineNumber + 1}`);
  });
  process.exit(0);
})();
"""


CHROME_REL_PATHS = (
    ("chrome-mac-arm64", "Google Chrome for Testing.app", "Contents",
     "MacOS", "Google Chrome for Testing"),
    ("chrome-mac-x64", "Google Chrome for Testing.app", "Contents",
     "MacOS", "Google Chrome for Testing"),
    ("chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"),
    ("chrome-linux", "chrome"),
    ("chrome-linux", "headless_shell"),
    ("chrome-win", "chrome.exe"),
)


def find_chrome():
    """Найти chromium в кэше Playwright (любая версия, macOS/Linux/Windows)."""
    roots = [
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.expanduser("~/Library/Caches/ms-playwright"),
        os.path.expanduser("~/AppData/Local/ms-playwright"),
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root), reverse=True):
            if not name.startswith("chromium-"):
                continue
            for rel in CHROME_REL_PATHS:
                app = os.path.join(root, name, *rel)
                if os.path.isfile(app):
                    return app
    return None


def port_busy(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_repo():
    """Клонировать drakonhub_desktop в кэш скилла (один раз)."""
    if os.path.isfile(os.path.join(REPO, "drakonhub.html")):
        return REPO
    os.makedirs(CACHE, exist_ok=True)
    if shutil.which("git") is None:
        sys.exit("нужен git для клонирования drakonhub_desktop")
    print("клонирую drakonhub_desktop в", CACHE, "...", file=sys.stderr)
    subprocess.run(
        ["git", "clone", "--depth", "1", "-q",
         "https://github.com/stepan-mitkin/drakonhub_desktop.git", REPO],
        check=True)
    return REPO


def main():
    args = [a for a in sys.argv[1:]]
    mode = "render"
    if args and args[0] in ("render", "stack"):
        mode = args.pop(0)
    if not args:
        sys.exit(__doc__)
    path = os.path.abspath(args[0])
    timeout = args[1] if len(args) > 1 else str(DEFAULT_TIMEOUT_MS)

    if not os.path.isfile(path):
        sys.exit("нет файла: %s" % path)
    try:
        json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        sys.exit("невалидный JSON: %s" % exc)

    node_modules = os.environ.get("PLAYWRIGHT_MODULES", DEFAULT_NODE_MODULES)
    chrome = find_chrome()
    if not chrome:
        sys.exit("не найден chromium в кэше Playwright (~/.cache/ms-playwright)")
    if not os.path.isdir(node_modules):
        sys.exit("не найден node-модуль playwright: %s "
                 "(задайте PLAYWRIGHT_MODULES)" % node_modules)

    repo = ensure_repo()
    server = None
    url = "http://127.0.0.1:%d/drakonhub.html" % PORT
    if not port_busy(PORT):
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
            cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if port_busy(PORT):
                break
            time.sleep(0.1)

    script = RENDER_JS if mode == "render" else STACK_JS
    js_path = os.path.join(CACHE, "drakon_try_%s.js" % mode)
    with open(js_path, "w") as fh:
        fh.write(script)

    env = dict(os.environ,
               CHROME_BIN=chrome,
               PW=node_modules,
               URL=url)
    try:
        proc = subprocess.run(
            ["node", js_path, path] + ([timeout] if mode == "render" else []),
            capture_output=True, text=True, env=env, timeout=180)
    except subprocess.TimeoutExpired:
        print("HANG (процесс не отвечает)")
        return 1
    finally:
        if server:
            server.send_signal(signal.SIGTERM)

    out = proc.stdout.strip()
    print(out if out else (proc.stderr.strip() or "нет вывода"))
    if out.startswith("OK"):
        return 0
    if out.startswith("HANG"):
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
