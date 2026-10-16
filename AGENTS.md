# AGENTS.md

## 專案目的

此專案是以 Render Web Service 部署的簡易 LINE 文字聊天機器人，使用 Python/FastAPI 接收 webhook，呼叫 Gemini 產生回答，再透過 LINE Reply API 回覆。Docker Compose 用於本機開發。此路線暫不使用 n8n。

- 每則訊息獨立處理，不保存或傳送先前對話內容。
- 只回覆文字事件；貼圖、圖片、音訊及其他非文字事件不回覆。
- 必須以原始 request body 和 `x-line-signature` 驗證 LINE 簽章。
- 使用者需求變更時，先更新 README.md 與 plan.md，再實作。

## 專案結構

- `app/main.py`：FastAPI health endpoint、簽章驗證、事件篩選、快速 ACK 與短期事件去重。
- `app/providers.py`：Gemini 與 LINE Reply API 客戶端。
- `tests/test_webhook.py`：Python 標準函式庫 unittest，使用合成 payload 驗證核心行為。
- `Dockerfile`、`requirements.txt`：Render 與本機共用建置設定。
- `compose.yaml`：Windows Docker Desktop 本機服務與 `test` profile，僅將 `127.0.0.1:10000` 開放給本機。
- `.dockerignore`：避免將本機設定、Git 資料與快取送入 Docker build context。
- `render.yaml`：Render Blueprint，秘密使用 `sync: false`，不得加入真實值。
- `.env.example`：本機環境變數範本。
- `.env`：本機秘密，已加入 `.gitignore`；禁止讀取、提交、寫入日誌或貼入對話，除非使用者明確要求處理其內容。
- `README.md`：建置、部署及操作說明。
- `plan.md`、`hackmd-slides.md`：系統設計、兩階段測試計畫與簡報。
- `spec.txt`：功能規格檔；未填內容時以使用者在對話明確提供的規格為準。

## 開發與操作

1. Windows 使用 PowerShell，於專案根目錄執行 Docker Compose。
2. 本機將 `.env.example` 複製/合併為 `.env`，填入 LINE Channel Secret、LINE Channel Access Token 與 Gemini API Key；範例佔位值不可直接用於實際呼叫。
3. `docker compose up --build` 啟動本機服務；健康端點為 `http://localhost:10000/healthz`。
4. Render 從 GitHub repository 以 Dockerfile 建置，服務監聽 `0.0.0.0:$PORT`。秘密只在 Render Dashboard 的 Environment 設定。
5. GitHub repository secret 不會自動傳入 Render。禁止將真實秘密放在原始碼、`render.yaml`、Dockerfile、README、測試資料或 workflow。
6. 每次模型請求只包含當則文字與固定系統指示，不保存對話歷史或訊息本文。
7. Webhook 必須先驗證 HMAC-SHA256 簽章；只排入文字事件。先回 2xx ACK，再於背景處理模型和 LINE 回覆。
8. 日誌限非敏感錯誤類別，不得記錄訊息本文、prompt、模型輸出、完整 provider error、token 或 API key。
9. Render Free 閒置休眠及冷啟動風險須在文件與驗收中說清楚；不得宣稱為穩定即時服務。

## 測試與驗證

使用者要求兩階段測試；未執行的項目需標為待測，不能宣稱通過。

### 第一階段：本機整合

- Compose 容器啟動，`/healthz` 回 200。
- 用合成原始 body 確認有效簽章可 ACK；無效簽章遭拒且不呼叫模型/LINE。
- 文字事件排入背景處理；非文字事件不回覆。
- 重複 `webhookEventId` 不重複處理；不同訊息不共用對話內容。
- 日誌不包含內容或秘密。

### 第二階段：Render/LINE 實測

- Render 部署完成，Dashboard Secret 設定完成，`/healthz` 可連線。
- LINE Developers Console Verify 成功，測試文字與非文字訊息。
- 檢查模型用量、錯誤與 LINE webhook timeout/redelivery，尤其觀察 Render Free 冷啟動。

沒有現成自動測試套件時，不新增大型測試框架；只執行與需求相符的最小驗證。

## 貢獻規則

- 優先維持簡單，不新增資料庫、持久記憶、服務或依賴，除非有明確需求。
- 修改環境變數時同步更新 `.env.example`、README.md 與 plan.md；範例不得含真實秘密。
- 不修改或讀取 `.env` 以外的使用者秘密，不提交 `.env`、憑證、訊息內容、執行記錄或敏感匯出檔。
- 保持 Docker Compose 可在 Windows Docker Desktop 執行；不將本機服務綁定至所有網路介面。
- 完成時摘要變更、實際驗證及待使用者設定項目。
