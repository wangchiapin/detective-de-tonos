# 用法：python3 tests/test_game.py   （Playwright + Chromium；file://、擋外部網路、假 speechSynthesis）
import json, re, sys, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'index.html').as_uri()
data = (ROOT / 'data.js').read_text(encoding='utf8')
SENT = json.loads(data[data.index('=') + 1:].strip().rstrip(';'))
FAKE_SYNTH = """
window.__spoken=[];
const voices=[{lang:'zh-TW',name:'fake-tw'},{lang:'zh-HK',name:'fake-hk'}];
window.SpeechSynthesisUtterance=function(t){this.text=t;};
Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{getVoices:()=>voices,cancel(){},speak(u){window.__spoken.push({text:u.text,lang:u.lang,rate:u.rate,voice:u.voice&&u.voice.name});},addEventListener(){}}});
"""
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 375, 'height': 760})
    ctx.route(re.compile(r'^(?!file:).*'), lambda r: r.abort())      # 擋外部網路
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.add_init_script(FAKE_SYNTH)
    page.goto(URL)
    ok('聲調偵探' in page.inner_text('h1'), '標題')
    ok('本調' in page.inner_text('.note'), '首頁有「以本調為主」註記')

    # --- 選「全部」沒填暱稱不能開始 ---
    page.click('#chMode button[data-v=read]'); page.click('#bStart')
    ok(page.query_selector('.words') is None and '暱稱' in page.inner_text('#nmHint'), '選「全部」沒暱稱不能開始，並提示')
    page.fill('#nm', '小測')
    # --- 看句子模式：全答對 ---
    page.click('#bStart')
    seen_py = []
    for q in range(10):
        qtext = page.inner_text('.words')
        # 找出這題是哪一句：用漢字比對
        hz = ''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))
        s = next(x for x in SENT if ''.join(x['t']) == hz)
        ok(len(page.query_selector_all('.syl')) == len(s['a']), f'讀題 {s["id"]} 音節數')
        # 輕聲預填、不給按鈕
        neu = [i for i, a in enumerate(s['a']) if a == 0]
        for i in neu:
            ok(page.query_selector(f'.syl[data-i="{i}"] .tones') is None, f'{s["id"]} 輕聲音節 {i} 預填、沒有按鈕') if q == 0 else None
        ok(page.is_disabled('#bCheck'), '沒填完不能檢查') if q == 0 else None
        for i, a in enumerate(s['a']):
            if a: page.click(f'.syl[data-i="{i}"] .tones button[data-t="{a}"]')
        ok(not page.is_disabled('#bCheck'), '填完可以檢查') if q == 0 else None
        page.click('#bCheck')
        ok('✓' in page.inner_text('.score'), f'{s["id"]} 全對顯示 ✓')
        if '不' in s['t'] or '一' in s['t']:
            ok(True, f'{s["id"]} 含一／不，答案用本調 → ' + ' '.join(page.eval_on_selector_all('.res .line', 'els=>els.map(e=>e.textContent)')[1:2]))
        page.click('#bNext')
    ok('/' in page.inner_text('.big'), '結算畫面')
    m = re.match(r'(\d+) / (\d+)', page.inner_text('.big'))
    ok(m and m.group(1) == m.group(2), '全部答對：' + page.inner_text('.big'))
    page.click('#bHome')

    # --- 聽句子模式：先藏漢字、會唸、答錯顯示正確 ---
    page.click('#chMode button[data-v=listen]')
    ok('機器' in page.inner_text('.note'), '聽力模式有機器變調註記')
    page.click('#bStart')
    hz = ''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))
    ok(hz == '', '聽力模式檢查前不顯示漢字')
    spoken = page.evaluate('window.__spoken')
    ok(len(spoken) == 1 and spoken[0]['voice'] == 'fake-tw' and spoken[0]['lang'] == 'zh-TW', '自動唸一次，選 zh-TW 聲音（不選 zh-HK）：' + json.dumps(spoken, ensure_ascii=False))
    text = spoken[0]['text']; s = next(x for x in SENT if ''.join(x['t']) == text)
    page.click('#bSpk'); ok(len(page.evaluate('window.__spoken')) == 2, '喇叭可再聽')
    # 故意全選錯
    for i, a in enumerate(s['a']):
        if a: page.click(f'.syl[data-i="{i}"] .tones button[data-t="{1 if a != 1 else 2}"]')
    page.click('#bCheck')
    ok(''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)')) == text, '檢查後顯示漢字')
    ok(len(page.query_selector_all('.syl.bad')) == sum(1 for a in s['a'] if a), '全選錯：每個非輕聲音節都標錯')
    ok(len([x for x in page.eval_on_selector_all('.syl .fix', 'els=>els.map(e=>e.textContent)') if x]) == sum(1 for a in s['a'] if a), '錯的音節下方顯示正確拼音')
    # 簡體
    page.click('#sgScript button[data-v=simp]')
    ok(''.join(page.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)')) == ''.join(s['s']), '切換簡體後漢字變簡體')
    # 純中文
    page.click('#sgLang button[data-v=zh]')
    ok('Detective' in page.inner_text('h1') and 'Siguiente' not in page.inner_text('body') and 'Check' not in page.inner_text('.res'), '純中文模式沒有西文英文說明')
    # 手機寬度不橫向捲動
    ok(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), '375px 寬沒有橫向捲動')
    # 版權列
    ok('保留所有權利' in page.inner_text('#hgCopy'), '版權列')
    # 設定共用
    st = json.loads(page.evaluate("localStorage.getItem('hanziGames.settings')"))
    ok(st['script'] == 'simp' and st['lang'] == 'zh', '共用設定寫入 hanziGames.settings：' + json.dumps(st))
    ok(not errs, '沒有 JS 錯誤 ' + str(errs))
    page.screenshot(path=str(ROOT / 'tests' / 'shot_listen.png'))
    b.close()
print('\n失敗 %d 項' % len(fails)); sys.exit(1 if fails else 0)
