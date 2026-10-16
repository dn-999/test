# LINE 聊天機器人（Render 版）

此專案以 Python webhook 服務接收 LINE Messaging API 事件，使用 Gemini 產生自然、簡短的文字回答。Render Web Service 負責公開 HTTPS webhook；Docker Compose 可在本機執行同一個服務。此版本不使用 n8n，也不保存對話記憶。

## 功能範圍

- 每則文字訊息獨立處理，只將當前文字送給 Gemini。
- 只回覆文字訊息；貼圖、圖片、音訊及其他事件不回覆。
- 以原始 request body 和 `x-line-signature` 驗證 LINE 簽章。
- Webhook 驗證成功後立即回 200，在背景呼叫模型並使用 LINE reply API 回覆。
- 不記錄訊息本文、提示詞、模型回答或金鑰。

## 本機啟動

1. 首次使用時複製 `.env.example` 為 `.env`，填入 LINE Channel Secret、LINE Channel Access Token 和 Gemini API Key。若 `.env` 已存在，請保留原檔並手動加入這些設定，不要覆蓋或提交 `.env`。
2. 執行 `docker compose up --build`。
3. 本機健康檢查：`http://localhost:10000/healthz`。
4. 本機 LINE webhook 測試 URL：`http://localhost:10000/webhook`。LINE 平台需要公開 HTTPS URL；本機測試請使用有效測試簽章，或部署至 Render 後設定 LINE Developers Console。

## Render 部署

1. 將本專案推送至 GitHub，於 Render Dashboard 選擇 **New → Web Service** 並連結此 repository。
2. 選擇 **Docker** runtime，Render 會依根目錄的 `Dockerfile` 建置服務；服務綁定 Render 指定的 `PORT`。
3. 在服務的 **Environment** 設定 `LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN` 和 `GEMINI_API_KEY`。不要把金鑰放在 `render.yaml`、Dockerfile 或 GitHub 檔案中。
4. 部署成功後，將 `https://<service>.onrender.com/webhook` 填入 LINE Developers Console 的 Webhook URL，啟用 Use webhook，然後使用 Verify。

Render 免費 Web Service 閒置 15 分鐘後會休眠，喚醒約需一分鐘；LINE webhook 需在約兩秒內收到 2xx，冷啟動可能導致 webhook 逾時。免費方案適合嘗試，不保證穩定即時回覆。需要穩定服務時應評估常駐付費方案或具備快速 webhook ACK 與佇列的架構。

## 測試

先執行 `docker compose --profile test run --build --rm unit-tests` 驗證簽章、事件篩選及模型輸入，再執行 `docker compose up --build` 做本機 health check。之後依 [plan.md](plan.md) 設定 Render/LINE 完成小範圍實測。Render GitHub Secret 與 Render Environment Variables 是不同的設定；在 GitHub 建立的 `GEMINI_API_KEY` 不會自動傳到 Render。

## 安全與資料

- LINE 和 Gemini 金鑰只放在本機 `.env` 或 Render Environment Variables。
- 不記錄 webhook body、訊息內容、prompt、模型輸出或秘密。
- 記憶體中的短期事件 ID 去重只用於避免重複處理，不包含聊天內容；程序重新啟動後會清空。
- 模型供應商會收到當則文字；請勿傳送敏感個資，並自行確認模型的資料政策與配額。
