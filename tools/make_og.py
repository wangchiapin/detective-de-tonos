# 用法：python3 tools/make_og.py   → 產生 og.jpg（1200×630，分享連結的縮圖）
# 右邊的手機畫面是遊戲真實畫面（看句子模式、選 A1、已填幾個聲調）；改了遊戲名稱或畫面風格就重跑一次
import base64, io, pathlib, random
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'og.jpg'

def game_shot(p):
    import json
    data = (ROOT / 'data.js').read_text(encoding='utf8')
    sent = {''.join(s['t']): s for s in json.loads(data[data.index('=') + 1:].strip().rstrip(';'))}
    b = p.chromium.launch()
    pg = b.new_context(viewport={'width': 390, 'height': 900}, device_scale_factor=2).new_page()
    pg.goto((ROOT / 'index.html').as_uri())
    pg.evaluate("localStorage.setItem('hanziGames.settings', JSON.stringify({v:1,script:'trad',lang:'es',phon:'pinyin',rate:'normal'}))")
    for _ in range(60):   # 抽到音節不多、有輕聲的句子，畫面比較好看
        pg.goto((ROOT / 'index.html').as_uri()); pg.click('#sgLv button[data-v=A1]'); pg.click('#bStart')
        hz = ''.join(pg.eval_on_selector_all('.syl .hz', 'els=>els.map(e=>e.textContent)'))
        if 5 <= len(hz) <= 7: break
    s = sent[hz]
    for i, a in enumerate(s['a']):   # 全部填對，按檢查：畫面會顯示 ✓、完整拼音和西文意思
        if a: pg.click(f'.syl[data-i="{i}"] .tones button[data-t="{a}"]')
    pg.click('#bCheck')
    pg.add_style_tag(content='h1,.bar,.note,#hgCopy,#bSpk2,#bNext{display:none!important} #app{padding-top:14px!important} .res .row{display:none!important}')
    png = pg.locator('#app').screenshot()
    b.close(); return base64.b64encode(png).decode()

HTML = """<!doctype html><meta charset=utf-8><style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;background:#f4f0e5;font-family:'Noto Sans CJK TC','Noto Sans TC',sans-serif;color:#3a3a36;position:relative;overflow:hidden}
.l{position:absolute;left:72px;top:0;height:630px;width:600px;display:flex;flex-direction:column;justify-content:center}
h1{font-size:92px;font-weight:700;letter-spacing:.02em;line-height:1.15}
.en{font-size:46px;color:#8a857b;margin-top:2px}
.zh{font-size:30px;color:#55524b;margin-top:44px}
.es{font-size:23px;color:#8a857b;margin-top:6px;line-height:1.35;width:520px}
.brand{font-size:23px;font-weight:700;color:#a4493d;margin-top:34px;letter-spacing:.03em}
.ph{position:absolute;left:742px;top:92px;width:436px;height:640px;border-radius:38px;background:#f6f4ef;border:6px solid #fff;box-shadow:0 8px 28px rgba(60,50,30,.25);overflow:hidden}
.ph img{width:424px;display:block}
</style>
<div class=l><h1>聲調偵探</h1><div class=en>Detective de tonos</div>
<div class=zh>看拼音填聲調，看句子、聽句子都能玩</div>
<div class=es>Pon los tonos al pinyin: lee o escucha la frase</div>
<div class=brand>每天一分鐘 ・ Cada día unos minutos</div></div>
<div class=ph><img src="data:image/png;base64,__IMG__"></div>"""

with sync_playwright() as p:
    shot = game_shot(p)
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    pg.set_content(HTML.replace('__IMG__', shot)); pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT), type='jpeg', quality=88); b.close()
print('寫入', OUT, OUT.stat().st_size // 1024, 'KB')
