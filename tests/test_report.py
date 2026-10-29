# 用法：python3 tests/test_report.py   （假 Firebase；測「🚩 這題怪怪的」回報，並把送出的資料拿去對 Firestore 規則 game_reports 的 tonos 分支（Python 版））
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
MOD_APP = "export const initializeApp=(c,n)=>{(window.__apps=window.__apps||[]).push({pid:c&&c.projectId,name:n});return {}}; export const getApp=()=>{throw new Error('no app')};"
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
export const addDoc=async(c,data)=>{W().__writes.push({path:c.path,data:JSON.parse(JSON.stringify(data)),op:'add'});return {id:'P1'};};
export const updateDoc=async(r,data)=>{W().__writes.push({path:r.path,data,op:'update'});};
export const getDocs=async(c)=>({docs:[],empty:true,forEach(){}});
"""
MOD_FS_FAIL = MOD_FS.replace("export const addDoc=async(c,data)=>{", "export const addDoc=async(c,data)=>{throw new Error('offline');")

def make_route(fs_body):
    def route(r):
        u = r.request.url
        if 'gstatic.com/firebasejs' in u:
            body = MOD_APP if 'firebase-app' in u else MOD_AUTH if 'firebase-auth' in u else fs_body
            return r.fulfill(status=200, content_type='application/javascript', body=body, headers={'access-control-allow-origin': '*'})
        if u.startswith('file:'): return r.continue_()
        r.abort()
    return route

# --- game-kit 規則（game_reports 的 tonos 分支）的 Python 版 ---
KEYS = {'game', 'why', 'note', 'id', 'lv', 'mode', 'han', 'py', 'ans', 'pick', 'lang', 'ver', 'done', 'at'}
def sz(x, lo, hi): return isinstance(x, str) and lo <= len(x) <= hi
def rule_ok(path, d):
    return (path == 'game_reports' and set(d) == KEYS and d['game'] == 'tonos'
            and d['why'] in ('wrong', 'voice', 'text', 'other')
            and sz(d['note'], 0, 100) and sz(d['id'], 1, 12) and d['lv'] in ('A1', 'A2', 'B1')
            and d['mode'] in ('read', 'listen') and sz(d['han'], 1, 40) and sz(d['py'], 1, 120)
            and sz(d['ans'], 1, 160) and sz(d['pick'], 1, 160) and d['lang'] in ('es', 'en', 'zh')
            and sz(d['ver'], 0, 12) and d['done'] is False and d['at'] == {'__ts': True})

fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)

def sentence_now(page, mode):
    if mode == 'listen': return SENT[page.evaluate('window.__spoken')[-1]]
    return SENT[''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))]
def fill(page, s, wrong=False):
    for i, a in enumerate(s['a']):
        if a:
            t = (1 if a != 1 else 2) if wrong else a
            page.click(f'.syl[data-i="{i}"] .tones button[data-t="{t}"]')
def W(pg): return [w for w in pg.evaluate('window.__writes||[]') if w['path'] == 'game_reports']

with sync_playwright() as p:
    b = p.chromium.launch()
    def newpage(fs=MOD_FS):
        ctx = b.new_context(viewport={'width': 390, 'height': 800}); pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.route('**/*', make_route(fs)); pg.add_init_script(FAKE_SYNTH); pg.goto(URL)
        pg.click('#sgLv button[data-v=A1]'); return pg, errs

    # 1. 看句子：答對後才出現按鈕；選原因才能送；送出資料合規
    pg, errs = newpage()
    pg.click('#bStart')
    ok(pg.query_selector('#bRep') is None, '還沒破案：沒有回報按鈕')
    s = sentence_now(pg, 'read'); fill(pg, s); pg.click('#bCheck')
    ok(pg.query_selector('#bRep') is not None and '這題怪怪的' in pg.inner_text('#bRep'), '破案後出現「🚩 這題怪怪的」')
    pg.click('#bRep')
    chips = pg.eval_on_selector_all('#rep .rw button', 'els=>els.map(e=>e.dataset.w)')
    ok(chips == ['wrong', 'text', 'other'], '看句子模式的原因：沒有「聲音怪怪」 ' + str(chips))
    ok(pg.get_attribute('#repNote', 'maxlength') == '100', '備註最多 100 字（maxlength）')
    pg.click('#repSend')
    ok('請先選' in pg.inner_text('#rep') and len(W(pg)) == 0, '沒選原因不能送出，也沒有寫入')
    pg.click('#rep .rw button[data-w=wrong]'); pg.fill('#repNote', '第三個字好像怪怪的'); pg.click('#repSend')
    pg.wait_for_selector('#rep .repmsg.ok')
    w = W(pg); d = w[0]['data'] if w else {}
    ok(len(w) == 1 and rule_ok(w[0]['path'], d), '寫入 game_reports 一筆且合規 ' + json.dumps(w, ensure_ascii=False))
    ok(d.get('game') == 'tonos' and d.get('why') == 'wrong' and d.get('note') == '第三個字好像怪怪的', 'game／原因／備註正確')
    ok(d.get('id') == s['id'] and d.get('lv') == s['lv'] and d.get('han') == ''.join(s['t']) and d.get('py') == ' '.join(s['p']), '句子編號、等級、漢字、無聲調拼音正確')
    ok(d.get('mode') == 'read' and d.get('done') is False and d.get('at') == {'__ts': True}, '模式、done:false、伺服器時間')
    ok(d.get('ans') == d.get('pick') and d.get('ans') != d.get('py'), '全答對：玩家答案＝標準答案，且有加聲調符號')
    ok('已送出' in pg.inner_text('#rep') and pg.query_selector('#repSend') is None, '送出後顯示已送出，沒有重複送出的按鈕')
    apps = pg.evaluate('window.__apps||[]')
    ok(any(a['pid'] == 'subscription-48d3c' and a['name'] == 'central' for a in apps), '連到中央專案 subscription-48d3c')
    pg.click('#bNext')
    ok(pg.query_selector('#bRep') is None and pg.query_selector('.repmsg.ok') is None, '下一題：還沒破案不顯示回報，舊的「已送出」清掉')
    # 取消
    s2 = sentence_now(pg, 'read'); fill(pg, s2, wrong=True); pg.click('#bCheck')
    ok(pg.query_selector('#bRep') is not None and pg.query_selector('.repbox') is None, '下一題破案後：恢復成小字按鈕')
    pg.click('#bRep'); pg.click('#repCancel')
    ok(pg.query_selector('#bRep') is not None and pg.query_selector('.repbox') is None and len(W(pg)) == 1, '取消：回到小字按鈕、沒有多寫入')
    # 答錯也能回報：玩家答案和標準答案不同
    pg.click('#bRep'); pg.click('#rep .rw button[data-w=text]'); pg.click('#repSend'); pg.wait_for_selector('#rep .repmsg.ok')
    w = W(pg); d2 = w[1]['data']
    ok(len(w) == 2 and rule_ok('game_reports', d2) and d2['why'] == 'text' and d2['note'] == '', '答錯的題也能回報，備註可空白')
    ok(d2['pick'] != d2['ans'] and len(d2['pick'].split()) == len(d2['ans'].split()), '玩家答案跟標準答案不同，音節數一樣')
    ok(not errs, '沒有 JS 錯誤 %s' % errs)

    # 2. 聽句子：多一個「聲音怪怪」
    pg, errs = newpage()
    pg.click('#chMode button[data-v=listen]'); pg.click('#bStart')
    s = sentence_now(pg, 'listen'); fill(pg, s); pg.click('#bCheck'); pg.click('#bRep')
    chips = pg.eval_on_selector_all('#rep .rw button', 'els=>els.map(e=>e.dataset.w)')
    ok(chips == ['wrong', 'voice', 'text', 'other'], '聽句子模式的原因含 voice ' + str(chips))
    pg.click('#rep .rw button[data-w=voice]'); pg.click('#repSend'); pg.wait_for_selector('#rep .repmsg.ok')
    w = W(pg)
    ok(len(w) == 1 and rule_ok(w[0]['path'], w[0]['data']) and w[0]['data']['why'] == 'voice' and w[0]['data']['mode'] == 'listen', '聽力回報：why=voice、mode=listen 且合規')
    ok(not errs, '沒有 JS 錯誤 %s' % errs)

    # 3. 簡體／英文介面也能送（lang 欄位要在規則允許的範圍）
    pg, errs = newpage()
    pg.click('#sgScript button[data-v=simp]'); pg.click('#sgLang button[data-v=en]'); pg.click('#bStart')
    s = sentence_now(pg, 'read') if False else None
    hz = ''.join(pg.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))
    s = next(x for x in SENT.values() if ''.join(x['s']) == hz)
    fill(pg, s); pg.click('#bCheck'); pg.click('#bRep'); pg.click('#rep .rw button[data-w=other]'); pg.click('#repSend'); pg.wait_for_selector('#rep .repmsg.ok')
    w = W(pg)
    ok(len(w) == 1 and rule_ok(w[0]['path'], w[0]['data']) and w[0]['data']['lang'] == 'en' and w[0]['data']['han'] == ''.join(s['t']), '簡體＋英文介面：han 仍存繁體字，lang=en 合規')

    # 4. 送出失敗：顯示失敗訊息、可以再試
    pg, errs = newpage(MOD_FS_FAIL)
    pg.click('#bStart'); s = sentence_now(pg, 'read'); fill(pg, s); pg.click('#bCheck'); pg.click('#bRep')
    pg.click('#rep .rw button[data-w=wrong]'); pg.click('#repSend'); pg.wait_for_selector('#rep .repmsg.no')
    ok('失敗' in pg.inner_text('#rep') and not pg.is_disabled('#repSend') and len(W(pg)) == 0, '連線失敗：顯示失敗、按鈕可再按、沒有寫入')
    ok(not errs, '沒有 JS 錯誤 %s' % errs)
    b.close()
print('\n失敗 %d 項' % len(fails)); sys.exit(1 if fails else 0)
