# 聲調偵探 · Detective de tonos

給 Claude：改這個遊戲前先讀這份，再讀 game-kit 的 README。Ben 的規則：先討論、測好、問過才推（他說「推」才推）；用白話繁體中文說明。

## 玩法
- 句子來自 game-kit 的句庫（A1／A2／B1 各 100 句，共 300 句），畫面只給「沒有聲調的拼音」，玩家自己選聲調（每個音節下面點 1／2／3／4）。
- **看句子**：顯示漢字＋無調拼音。**聽句子**：先唸句子（瀏覽器內建語音），只顯示無調拼音，檢查後才顯示漢字；上方喇叭可重聽（檢查後下方不再放「再聽一次」按鈕；看句子模式的結果仍有）。
- 一次 10 題。算分只算要填的音節；輕聲預填（顯示「輕聲」），不算分。
- **畫面（2026-10-29 改成偵探筆記本風格）**：右上有「說明」按鈕；標題有放大鏡與偵探帽；聲紋與聲調軌跡；句子長（10 個音節以上）在手機上自動用精簡排版；電腦版（寬 900px 以上）放大版面。
- 玩的畫面右上有「主選單」按鈕（門圖示），離開前會確認。
- 每題有「🚩 這題怪怪的」可回報題目有問題：存到中央專案 subscription-48d3c 的 `game_reports`（game:'tonos'），按了才連線；只有 Ben 在分享區 stats.html「問題回報」看得到。

## 重要決定（2026-10-28，Ben）
- 答案一律用**本調**：一＝yī、不＝bù，三聲連三聲都算三聲。畫面註記「以本調為主」。不篩句子，300 句全用。
- 聽力模式機器會自動變調，畫面也有註記。語音只選 zh-TW／cmn，排除 yue 與 zh-HK。
- 聽力模式先藏漢字，檢查後才顯示。
- 沒有注音版（共用設定的 phon 不影響這個遊戲）。
- **排行榜（2026-10-29，Ben 決定）**：memorma-24dab 的 `tone_boards/{read|listen}/entries/{uid}`，兩個榜（看句子、聽句子）。**只有等級選「全部」玩完 10 題才上榜**（選 A1／A2／B1 是練習，不上榜，這樣大家抽同一批 300 句才公平）；選「全部」要先輸入暱稱（最多 14 字）。分數＝答對率×1000（整數，97.3% 存 973，畫面顯示 ÷10 加 %），每台裝置每榜只留最高分，前 10 名。規則在 game-kit 的 `firebase-rules/memorma-24dab.rules.txt`（要整份貼進 Firebase 才寫得進去）。

## 檔案
- `index.src.html`：遊戲本體（有 `/*@@…@@*/` 佔位）。
- `data.js`：由 `build_data.js` 從 game-kit 的 `bank/A1.json` `A2.json` `B1.json` 產生（一、不已換成本調）。
- `og.jpg`：分享連結的縮圖（1200×630），`index.src.html` 的 `<head>` 有對應的 og 標籤（名稱 `聲調偵探 · Detective de tonos`，要跟分享區卡片一致）。縮圖是 `python3 tools/make_og.py` 用遊戲真實畫面產生的（每次執行會抽不同句子）；改遊戲名稱或畫面風格後要重跑。
- `index.html`：**單檔成品**（`build.js` 把資料與共用零件 settings／voicehint／copyright／plays 貼進去），GitHub Pages 讀這個。

## 重新產生
```
node build_data.js ../game-kit/bank   # 句庫有改才需要
node build.js ../game-kit             # 每次改 index.src.html 都要跑
python3 tests/test_game.py            # Playwright 測試（玩法）
python3 tests/test_leaderboard.py     # 排行榜測試（假 Firebase，對照規則）
python3 tests/test_report.py          # 問題回報測試
```
各 repo 跟 game-kit 放同一個資料夾。

## 遊玩紀錄
用 game-kit 的 `plays.js`（遊戲代號 `detective_de_tonos`），按「開始」記一局，看結果時記完成。
