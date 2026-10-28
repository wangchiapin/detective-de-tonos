# 聲調偵探 · Detective de tonos

給 Claude：改這個遊戲前先讀這份，再讀 game-kit 的 README。Ben 的規則：先討論、測好、問過才推（他說「推」才推）；用白話繁體中文說明。

## 玩法
- 句子來自 game-kit 的句庫（A1／A2／B1 各 100 句，共 300 句），畫面只給「沒有聲調的拼音」，玩家自己選聲調（每個音節下面點 1／2／3／4）。
- **看句子**：顯示漢字＋無調拼音。**聽句子**：先唸句子（瀏覽器內建語音），只顯示無調拼音，檢查後才顯示漢字；有「再聽一次」。
- 一次 10 題。算分只算要填的音節；輕聲預填（顯示「輕聲」），不算分。

## 重要決定（2026-10-28，Ben）
- 答案一律用**本調**：一＝yī、不＝bù，三聲連三聲都算三聲。畫面註記「以本調為主」。不篩句子，300 句全用。
- 聽力模式機器會自動變調，畫面也有註記。語音只選 zh-TW／cmn，排除 yue 與 zh-HK。
- 聽力模式先藏漢字，檢查後才顯示。
- 目前沒有排行榜、沒有注音版（共用設定的 phon 不影響這個遊戲）。

## 檔案
- `index.src.html`：遊戲本體（有 `/*@@…@@*/` 佔位）。
- `data.js`：由 `build_data.js` 從 game-kit 的 `bank/A1.json` `A2.json` `B1.json` 產生（一、不已換成本調）。
- `index.html`：**單檔成品**（`build.js` 把資料與共用零件 settings／voicehint／copyright／plays 貼進去），GitHub Pages 讀這個。

## 重新產生
```
node build_data.js ../game-kit/bank   # 句庫有改才需要
node build.js ../game-kit             # 每次改 index.src.html 都要跑
python3 tests/test_game.py            # Playwright 測試
```
各 repo 跟 game-kit 放同一個資料夾。

## 遊玩紀錄
用 game-kit 的 `plays.js`（遊戲代號 `detective_de_tonos`），按「開始」記一局，看結果時記完成。
