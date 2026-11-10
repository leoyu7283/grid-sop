# 網格下單 SOP 儀表板

給學生用的網格交易選幣與參數試算工具（派網 Pionex）。

- 網頁每小時由 GitHub Actions 自動抓取 CoinGecko 前 100 大與派網 K 線，重新計算指標並部署到 GitHub Pages。
- 指標：ATR(30)、ER(30)、ADX(14)；週期：4 小時、日線、週線（由日線合成）。
- 最新資料存在 `data` 分支（每次覆蓋，不累積歷史）。抓取失敗時，網頁沿用上一次成功的資料，頁面上方會顯示資料時間。

## 檔案

| 檔案 | 作用 |
|---|---|
| `build_data.py` | 抓資料、算指標，輸出 `data.json` |
| `template.html` | 網頁版面與計算邏輯 |
| `build_html.py` | 把 `data.json` 塞進模板，產生 `index.html` |
| `.github/workflows/update.yml` | 排程：每小時更新並部署（GitHub 排程偶爾會延遲或略過） |

## 手動更新

到 GitHub 的 **Actions** 分頁 → 選「更新資料並部署」→ **Run workflow**。

## 選用：CoinGecko 金鑰

到 Settings → Secrets and variables → Actions，新增 `COINGECKO_API_KEY`（CoinGecko 免費 Demo 金鑰），可降低被限流的機率。沒有設定也能運作。

教學工具，不構成投資建議。
