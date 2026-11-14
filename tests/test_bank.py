# 用法：python3 tests/test_bank.py   （句庫來源：讀 corre 最新版；讀不到用備用快照）
# 需要 corre 在隔壁資料夾（../corre）；可用環境變數 CORRE_DIR 指定
import json, os, re, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'index.html').as_uri()
CORRE = pathlib.Path(os.environ.get('CORRE_DIR', ROOT.parent / 'corre'))
fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)
real = {L: json.loads((CORRE / 'bank' / f'{L}.json').read_text(encoding='utf8')) for L in ['A1', 'A2', 'B1']}
with sync_playwright() as p:
    b = p.chromium.launch()
    # 1) 讀得到：句數跟 corre 一致，而且是新的（不是備用快照）
    def run(handler):
        ctx = b.new_context(); ctx.route(re.compile(r'^(?!file:).*'), handler); pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto(URL)
        pg.wait_for_function('window.__bankLive!==undefined', timeout=15000)
        r = pg.evaluate("()=>({live:window.__bankLive,n:SENTENCES.length,per:['A1','A2','B1'].map(L=>SENTENCES.filter(s=>s.lv===L).length),bad:SENTENCES.filter(s=>!s.id||s.t.length!==s.p.length||s.p.length!==s.a.length||s.a.some(x=>x<0||x>4)).length})")
        ctx.close(); return r, errs
    def good(route):
        m = re.search(r'/bank/(A1|A2|B1)\.json', route.request.url)
        if m: route.fulfill(status=200, content_type='application/json', body=json.dumps(real[m.group(1)]))
        else: route.abort()
    r, errs = run(good)
    want = [len(real[L]['sentences']) for L in ['A1', 'A2', 'B1']]
    ok(r['live'] == 3, '三級都讀到 corre 最新版')
    ok(r['per'] == want, f'句數跟 corre 一致 {r["per"]}')
    ok(r['bad'] == 0, '每句漢字、拼音、聲調數量一致，聲調 0～4')
    ok(not errs, '沒有頁面錯誤')
    # 2) 完全讀不到：用備用快照，照樣能玩
    r, errs = run(lambda route: route.abort())
    ok(r['live'] == 0 and r['n'] > 0, f'讀不到時用備用快照（{r["n"]} 句）')
    # 3) 只有 A2 壞掉（格式不對）：A2 維持備用，其他兩級換新
    def partial(route):
        m = re.search(r'/bank/(A1|A2|B1)\.json', route.request.url)
        if not m: return route.abort()
        body = '{"oops":1}' if m.group(1) == 'A2' else json.dumps(real[m.group(1)])
        route.fulfill(status=200, content_type='application/json', body=body)
    r, errs = run(partial)
    ok(r['live'] == 2 and r['per'][1] > 0 and r['per'][0] == want[0], f'A2 格式壞掉只有 A2 用備用 {r["per"]}')
    b.close()
print('\n失敗', len(fails), '項'); raise SystemExit(1 if fails else 0)
