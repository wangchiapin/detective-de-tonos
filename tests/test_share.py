# 聲調偵探：分享成績鈕＋ ?ref=share 記號測試（假 Firebase 記錄 visits／plays 寫入）
# 用法：python3 tests/test_share.py
import json, re, sys, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'index.html').as_uri()
SHARE_URL = 'https://wangchiapin.github.io/detective-de-tonos/?ref=share'
data = (ROOT / 'data.js').read_text(encoding='utf8')
_all = json.loads(data[data.index('=') + 1:].strip().rstrip(';'))
SENT = {''.join(s['t']): s for s in _all}
SENT.update({''.join(s['s']): s for s in _all})   # 简体字形也找得到
_lb = (ROOT / 'tests' / 'test_leaderboard.py').read_text(encoding='utf8')
def grab(name):   # 沿用排行榜測試的假 Firebase
    return re.search(name + r' = """(.*?)"""|' + name + r' = "(.*?)"\n', _lb, re.S)
MOD_APP = grab('MOD_APP').group(2); MOD_FS = grab('MOD_FS').group(1)
# 遊玩紀錄（plays.js）要等登入完成（currentUser）才會寫，所以用會設定 currentUser 的登入替身
MOD_AUTH = "const a={currentUser:null,authStateReady:async()=>{}};export const getAuth=()=>a;export const signInAnonymously=async()=>{a.currentUser={uid:'U1'};return {user:a.currentUser}};export const onAuthStateChanged=(x,cb)=>{setTimeout(()=>cb(a.currentUser),0);return()=>{}};"
FAKE_SYNTH = "window.__spoken=[];Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{getVoices:()=>[{lang:'zh-TW',name:'fake-tw'}],cancel(){},speak(u){window.__spoken.push(u.text)},addEventListener(){}}});window.SpeechSynthesisUtterance=function(t){this.text=t};"
def route(r):
    u = r.request.url
    if 'gstatic.com/firebasejs' in u:
        body = MOD_APP if 'firebase-app' in u else MOD_AUTH if 'firebase-auth' in u else MOD_FS
        return r.fulfill(status=200, content_type='application/javascript', body=body, headers={'access-control-allow-origin': '*'})
    if u.startswith('file:'): return r.continue_()
    r.abort()

def stubs(share='ok', clip='ok', settings=None):
    s = "window.__shared=[];window.__copied=[];"
    if settings: s += "try{localStorage.setItem('hanziGames.settings',%s)}catch(e){}" % json.dumps(json.dumps(settings))
    if share == 'none': s += "try{Object.defineProperty(navigator,'share',{value:undefined,configurable:true});}catch(e){}"
    else:
        body = "window.__shared.push(d);"
        if share == 'abort': body += "const e=new Error('x');e.name='AbortError';throw e;"
        if share == 'hang': body += "await new Promise(r=>setTimeout(r,600));"
        s += "navigator.share=async d=>{%s};" % body
    s += "document.execCommand=()=>%s;" % ('false' if clip == 'fail' else 'true')
    s += "try{Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{%s}},configurable:true});}catch(e){}" % ("throw new Error('no')" if clip == 'fail' else "window.__copied.push(t)")
    return s

fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)

def sentence_now(page):
    return SENT[''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))]
def play(page, wrong=False):
    for q in range(10):
        s = sentence_now(page)
        for i, a in enumerate(s['a']):
            if a:
                t = (1 if a != 1 else 2) if wrong else a
                page.click(f'.syl[data-i="{i}"] .tones button[data-t="{t}"]')
        page.click('#bCheck'); page.click('#bNext')
    page.wait_for_timeout(400)

base = {'v': 1, 'script': 'trad', 'lang': 'es', 'phon': 'pinyin', 'rate': 'normal'}
with sync_playwright() as p:
    b = p.chromium.launch()
    def newpage(share='ok', clip='ok', settings=base, query=''):
        ctx = b.new_context(viewport={'width': 390, 'height': 800}); pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.route('**/*', route); pg.add_init_script(FAKE_SYNTH); pg.add_init_script(stubs(share, clip, settings))
        pg.goto(URL + query); return pg, errs
    def to_result(pg, name='小測', wrong=False, level='A1'):
        if name: pg.fill('#nm', name)
        pg.click(f'#sgLv button[data-v={level}]') if pg.query_selector('#sgLv') else None
        pg.click('#chMode button[data-v=read]'); pg.click('#bStart')
        play(pg, wrong)
    shared = lambda pg: pg.evaluate('window.__shared')
    has = lambda pg: pg.query_selector('#bShare') is not None

    print('結算畫面的分享鈕')
    pg, errs = newpage()
    to_result(pg)
    order = pg.eval_on_selector_all('.card.vprint .row button, .row button', 'els=>els.map(e=>e.id)')
    order = [x for x in order if x in ('bAgain', 'bShare', 'bBoard', 'bHome')]
    ok(order == ['bAgain', 'bShare', 'bBoard', 'bHome'], '分享鈕在「再玩一次」之後、「排行榜」之前 %s' % order)
    ok(has(pg), '有分數：顯示分享鈕')
    ok(pg.inner_text('#bShare').strip() == '分享成績', '按鈕只有中文（跟其他按鈕一樣）：' + pg.inner_text('#bShare'))
    st = pg.evaluate("(()=>{const c=getComputedStyle(document.getElementById('bShare'));return [c.backgroundColor,parseFloat(c.borderTopWidth)]})()")
    ok(st[1] >= 2 and st[0] != 'rgb(43, 43, 43)', '空心外框樣式 %s' % st)
    good, syl = [int(x) for x in re.findall(r'\d+', pg.inner_text('.big'))[:2]]
    pg.click('#bShare'); pg.wait_for_timeout(200)
    s = shared(pg)
    ok(len(s) == 1, '呼叫系統分享選單一次')
    ok(s and s[0]['url'] == SHARE_URL, '連結＝公開頁＋?ref=share：%s' % (s and s[0]['url']))
    ok(s and s[0]['text'].startswith('小測 acertó %d de %d tonos' % (good, syl)) and 'Detective de tonos' in s[0]['text'], '西文句子含暱稱、答對數、遊戲名：%s' % (s and s[0]['text']))
    ok(not errs, '沒有 JS 錯誤 %s' % errs)

    print('沒暱稱／語言／字體')
    pg, errs = newpage()
    to_result(pg, name='', level='A1') if False else None
    pg.click('#sgLv button[data-v=A1]'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart')
    if pg.query_selector('#nmHint') and pg.query_selector('.words') is None:
        pg.fill('#nm', 'x'); pg.click('#bStart')
    pg.evaluate("try{localStorage.removeItem('detectiveTonos.name')}catch(e){}")
    play(pg)
    pg.click('#bShare'); pg.wait_for_timeout(200); s = shared(pg)
    ok(s and (s[0]['text'].startswith('¡Acerté ') or s[0]['text'].startswith('x acertó')), '西文句子：%s' % (s and s[0]['text']))
    for lang, script, label, start in (('en', 'trad', '分享成績', 'Bo got '), ('zh', 'trad', '分享成績', 'Bo在「聲調偵探」猜對了 '), ('zh', 'simp', '分享成绩', 'Bo在「声调侦探」猜对了 ')):
        pg, errs = newpage(settings=dict(base, lang=lang, script=script))
        pg.fill('#nm', 'Bo'); pg.click('#sgLv button[data-v=A1]'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart'); play(pg)
        ok(pg.inner_text('#bShare').strip() == label, '%s/%s 按鈕文字：%s' % (lang, script, pg.inner_text('#bShare')))
        pg.click('#bShare'); pg.wait_for_timeout(200); s = shared(pg)
        ok(s and s[0]['text'].startswith(start), '%s/%s 句子：%s' % (lang, script, s and s[0]['text']))
        if script == 'simp': ok(s and s[0]['title'].startswith('声调侦探') and '聲' not in s[0]['text'], '简体標題與句子沒有繁體字')
    pg, errs = newpage(settings=dict(base, lang='es', script='simp'))
    pg.fill('#nm', 'Bo'); pg.click('#sgLv button[data-v=A1]'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart'); play(pg)
    pg.click('#bShare'); pg.wait_for_timeout(200); s = shared(pg)
    ok(s and s[0]['title'].startswith('声调侦探'), '西文＋简体：標題中文名用简体：%s' % (s and s[0]['title']))

    print('分享選單的各種結果')
    def result_page(**kw):
        pg, errs = newpage(**kw); pg.fill('#nm', '小測'); pg.click('#sgLv button[data-v=A1]'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart'); play(pg); return pg
    pg = result_page(share='abort'); before = pg.inner_text('#bShare')
    pg.click('#bShare'); pg.wait_for_timeout(200)
    ok(pg.inner_text('#bShare') == before and pg.evaluate('window.__copied') == [], '玩家關掉選單：文字不變、不複製')
    pg = result_page(share='none'); pg.click('#bShare'); pg.wait_for_timeout(250)
    cp = pg.evaluate('window.__copied')
    ok(len(cp) == 1 and cp[0].endswith('\n' + SHARE_URL), '不支援分享選單：複製「句子＋連結」')
    ok('已複製' in pg.inner_text('#bShare'), '按鈕顯示已複製')
    pg.wait_for_timeout(2500)
    ok(pg.inner_text('#bShare').strip() == '分享成績', '約 2 秒後文字恢復')
    pg = result_page(share='none', clip='fail'); pg.click('#bShare'); pg.wait_for_timeout(250)
    ok('複製失敗' in pg.inner_text('#bShare'), '連複製也失敗：顯示複製失敗')
    pg = result_page(share='hang')
    pg.evaluate("document.getElementById('bShare').click();document.getElementById('bShare').click()"); pg.wait_for_timeout(900)
    ok(len(shared(pg)) == 1, '連點兩下只分享一次')

    print('0 分不顯示')
    pg, errs = newpage(); pg.fill('#nm', '小測'); pg.click('#sgLv button[data-v=A1]'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart'); play(pg, wrong=True)
    ok(not has(pg), '全錯（0 個答對）：沒有分享鈕')

    print('?ref=share 記號')
    def refcase(query, label, expect):
        pg, errs = newpage(query=query); pg.wait_for_timeout(3000)
        pg.fill('#nm', '小測'); pg.click('#sgLv button[data-v=A1]'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart'); pg.wait_for_timeout(700)
        w = [x for x in pg.evaluate('window.__writes||[]') if x['path'].startswith('visits/') or (x['op'] == 'add' and x['path'] == 'plays')]
        ok(len(w) >= 2 and all((x['data'].get('ref') == expect) if expect else ('ref' not in x['data']) for x in w), '%s %s' % (label, [x['data'].get('ref') for x in w]))
        if expect: ok(pg.evaluate("sessionStorage.getItem('hg.ref')") == expect, '記號暫存在 sessionStorage')
    refcase('?ref=share', '帶 ?ref=share：visits／plays 都有 ref=share', 'share')
    refcase('?ref=SHARE', '大小寫轉小寫', 'share')
    refcase('', '沒帶：不寫 ref', None)
    refcase('?ref=%3Cscript%3E', '不合規的記號不寫入', None)

print('FAILS', len(fails)); sys.exit(1 if fails else 0)
