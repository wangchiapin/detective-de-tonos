# 用法：python3 tests/test_leaderboard.py   （假 Firebase；把遊戲實際寫出的資料拿去對 game-kit 規則的 Python 版）
import json, re, sys, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'index.html').as_uri()
data = (ROOT / 'data.js').read_text(encoding='utf8')
SENT = {''.join(s['t']): s for s in json.loads(data[data.index('=') + 1:].strip().rstrip(';'))}

FAKE_SYNTH = """
window.__spoken=[];
Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{getVoices:()=>[{lang:'zh-TW',name:'fake-tw'}],cancel(){},speak(u){window.__spoken.push(u.text)},addEventListener(){}}});
window.SpeechSynthesisUtterance=function(t){this.text=t};
"""
MOD_APP = "export const initializeApp=()=>({}); export const getApp=()=>({});"
MOD_AUTH = "export const getAuth=()=>({currentUser:null}); export const signInAnonymously=async()=>({user:{uid:'U1'}});"
MOD_FS = """
const W=()=>{window.__writes=window.__writes||[];window.__store=window.__store||{};return window};
const TS={__ts:true};
export const getFirestore=()=>({});
export const serverTimestamp=()=>TS;
export const collection=(db,...p)=>({path:p.join('/')});
export const doc=(db,...p)=>({path:p.join('/'),id:p[p.length-1]});
export const query=(c)=>c; export const orderBy=()=>0; export const limit=()=>0; export const where=()=>0;
export const getDoc=async(r)=>{const d=W().__store[r.path];return {exists:()=>!!d,data:()=>d};};
export const setDoc=async(r,data)=>{W().__writes.push({path:r.path,data:JSON.parse(JSON.stringify(data)),op:'set'});W().__store[r.path]=data;};
export const addDoc=async(c,data)=>{W().__writes.push({path:c.path,data,op:'add'});return {id:'P1'};};
export const updateDoc=async(r,data)=>{W().__writes.push({path:r.path,data,op:'update'});};
export const getDocs=async(c)=>{const docs=Object.keys(W().__store).filter(k=>k.startsWith(c.path+'/')).map(k=>({id:k.split('/').pop(),data:()=>W().__store[k]}));return {docs,empty:!docs.length,forEach(f){docs.forEach(f)}};};
"""
def route(r):
    u = r.request.url
    if 'gstatic.com/firebasejs' in u:
        body = MOD_APP if 'firebase-app' in u else MOD_AUTH if 'firebase-auth' in u else MOD_FS
        return r.fulfill(status=200, content_type='application/javascript', body=body, headers={'access-control-allow-origin': '*'})
    if u.startswith('file:'): return r.continue_()
    r.abort()

# --- game-kit 規則（tone_boards）的 Python 版 ---
def isint(x): return isinstance(x, int) and not isinstance(x, bool)
def rule_ok(path, d, uid='U1'):
    p = path.split('/')
    return (len(p) == 4 and p[0] == 'tone_boards' and p[1] in ('read', 'listen') and p[2] == 'entries' and p[3] == uid
            and set(d) == {'name', 'score', 'updatedAt'} and isinstance(d['name'], str) and 1 <= len(d['name']) <= 14
            and isint(d['score']) and 0 <= d['score'] <= 1000 and d['updatedAt'] == {'__ts': True})

fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)

def sentence_now(page, mode):
    if mode == 'listen': return SENT[page.evaluate('window.__spoken')[-1]]
    return SENT[''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))]
def play(page, mode, wrong_every=0):
    """玩完 10 題；wrong_every=N 表示每題都選錯（>0）或全對（0）"""
    for q in range(10):
        s = sentence_now(page, mode)
        for i, a in enumerate(s['a']):
            if a:
                t = a if not wrong_every else (1 if a != 1 else 2)
                page.click(f'.syl[data-i="{i}"] .tones button[data-t="{t}"]')
        page.click('#bCheck'); page.click('#bNext')
    page.wait_for_timeout(400)

with sync_playwright() as p:
    b = p.chromium.launch()
    def newpage():
        ctx = b.new_context(viewport={'width': 390, 'height': 800}); pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.route('**/*', route); pg.add_init_script(FAKE_SYNTH); pg.goto(URL); return pg, errs
    W = lambda pg: [w for w in pg.evaluate('window.__writes||[]') if w['path'].startswith('tone_boards')]

    # 1. 全部＋聽句子 全對 → 上傳 listen 榜、1000 分
    pg, errs = newpage()
    pg.fill('#nm', '小測'); pg.click('#chMode button[data-v=listen]'); pg.click('#bStart')
    play(pg, 'listen')
    w = W(pg)
    ok(len(w) == 1 and w[0]['path'] == 'tone_boards/listen/entries/U1' and rule_ok(w[0]['path'], w[0]['data']), '全部＋聽句子：寫入 listen 榜且合規 ' + json.dumps(w, ensure_ascii=False))
    ok(w and w[0]['data']['score'] == 1000 and w[0]['data']['name'] == '小測', '全對＝1000 分、暱稱正確')
    ok('已上傳' in pg.inner_text('#lbMsg'), '畫面顯示已上傳')
    ok('100.0%' in pg.inner_text('.score'), '結算顯示答對率 100.0%')
    # 2. 同一台再玩一局全錯 → 不會把最高分蓋掉
    pg.click('#bAgain'); play(pg, 'listen', wrong_every=1)
    w2 = W(pg)
    ok(len(w2) == 1, '較低分不再寫入（仍只有 1 筆）')
    ok('維持' in pg.inner_text('#lbMsg'), '畫面顯示排行榜維持原樣')
    # 3. 看句子榜是另一個榜；全錯也可上榜（分數 0）
    pg.click('#bHome'); pg.click('#chMode button[data-v=read]'); pg.click('#bStart'); play(pg, 'read', wrong_every=1)
    w3 = W(pg)
    ok(len(w3) == 2 and w3[1]['path'] == 'tone_boards/read/entries/U1' and rule_ok(w3[1]['path'], w3[1]['data']) and w3[1]['data']['score'] == 0, '看句子是獨立的 read 榜；分數 0 合規')
    ok(not errs, '沒有 JS 錯誤 %s' % errs)

    # 4. 選 A1：不上榜
    pg, errs = newpage()
    pg.click('#sgLv button[data-v=A1]'); pg.click('#bStart'); play(pg, 'read')
    ok(len(W(pg)) == 0, '選 A1 不寫入排行榜')
    ok('不上排行榜' in pg.inner_text('#lbMsg'), 'A1 結算顯示「不上排行榜」')

    # 5. 榜單畫面：排序、百分比、自己標「你」
    pg, errs = newpage()
    pg.evaluate("""window.__store={
      'tone_boards/read/entries/A':{name:'甲',score:850},
      'tone_boards/read/entries/U1':{name:'我',score:973},
      'tone_boards/read/entries/C':{name:'丙',score:1000},
      'tone_boards/listen/entries/D':{name:'丁',score:600}}""")
    pg.click('#bBoard'); pg.wait_for_selector('.lbrow')
    rows = pg.eval_on_selector_all('.lbrow', 'els=>els.map(e=>e.innerText.replace(/\\s+/g," ").trim())')
    ok([r.split(' ')[1] for r in rows] == ['丙', '我', '甲'], '看句子榜依分數排序：' + str(rows))
    ok('100.0%' in rows[0] and '97.3%' in rows[1] and '85.0%' in rows[2], '分數顯示成百分比')
    ok('你' in rows[1] and pg.query_selector('.lbrow.me') is not None, '自己的那一列有標記')
    pg.click('#sgBoard button[data-v=listen]'); pg.wait_for_function("document.querySelectorAll('.lbrow').length===1")
    ok('丁' in pg.inner_text('#lbBody') and '60.0%' in pg.inner_text('#lbBody'), '切到聽句子榜')
    pg.click('#bBack'); ok('聲調偵探' in pg.inner_text('h1') and pg.query_selector('#bStart') is not None, '返回首頁')
    # 6. 暱稱限制
    pg.fill('#nm', '一二三四五六七八九十一二三四五六七八'); 
    ok(len(pg.input_value('#nm')) <= 14, '暱稱最多 14 字（輸入框 maxlength）')
    ok(not errs, '沒有 JS 錯誤 %s' % errs)
    b.close()
print('\n失敗 %d 項' % len(fails)); sys.exit(1 if fails else 0)
