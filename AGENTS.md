# AGENTS.md

## 專案目的

此專案是簡單的 LINE 文字聊天機器人，以 Docker Compose 執行 n8n，透過雲端語言模型產生回覆。

- 每則使用者文字訊息獨立處理，不保存或傳送先前的對話內容。
- 貼圖、圖片、音訊及其他非文字訊息不回覆。
- 在 webhook 工作流程中驗證 LINE 簽章，再處理事件。

目前 `spec.txt` 為空；以上需求來自使用者在對話中提供的規格。若新增或更改需求，先更新 README.md 與工作流程設計，再開始實作。

## 專案結構

- `compose.yaml`：n8n 與 webhook-gateway (Caddy) 的本機服務設定。n8n 編輯器只綁定 `127.0.0.1:5678`；閘道只公開 webhook 路徑。
- `Caddyfile`：將 `/webhook/*` 與 `/webhook-test/*` 轉送至 n8n，其他路徑回傳 404。
- `.env.example`：環境變數範本。複製為 `.env` 後填入本機設定。
- `.env`：本機秘密與 URL 設定，已列入 `.gitignore`，禁止提交、記錄到日誌或貼入對話。
- `README.md`：啟動、設定與操作說明。
- `spec.txt`：功能規格檔；目前尚未填入內容。

## 開發與操作

1. Windows 使用 PowerShell，於專案根目錄執行 Docker Compose 命令。
2. 首次啟動前，將 `.env.example` 複製成 `.env`，並以安全的隨機值設定 `N8N_ENCRYPTION_KEY`。
3. 使用 `docker compose up -d` 啟動，透過 `http://localhost:5678` 操作 n8n；用 `docker compose logs -f n8n` 檢視服務日誌。
4. Tailscale Funnel 應指向本機 webhook 閘道連接埠 `8080`。不可將 n8n 編輯器的 `5678` 連接埠公開至網際網路。
5. LINE 與模型金鑰存放在 n8n Credentials 或未提交的本機 `.env`。不得把秘密寫進 workflow 匯出檔、README、範例或版本控制。
6. 每次使用者訊息只傳給模型當下的文字，不附加歷史訊息，也不新增持久化的聊天紀錄或記憶。
7. LINE webhook 必須以原始 request body 和 `x-line-signature` 驗證簽章；簽章無效時不得呼叫模型或回覆。只處理 `message.type === "text"` 的事件。
8. 變更 Compose 或 Caddy 設定時，維持 n8n 編輯器僅本機可連線，以及 Caddy 僅轉送 webhook 路徑的界線。

## 測試與驗證

使用者要求的驗證分兩階段進行；尚未完成的階段要明確標示為待測，不得宣稱已通過。

### 第一階段：本機整合

- 確認容器啟動，n8n 本機健康端點回應成功。
- 確認 Caddy 對根路徑回傳 404，只轉送 webhook 路徑。
- 用測試 webhook 確認有效 LINE 簽章的文字訊息會呼叫模型並回覆。
- 確認貼圖及其他非文字事件不呼叫模型、不回覆；無效簽章也會被拒絕。
- 確認連續文字訊息彼此獨立，工作流程未傳入或保存前一則訊息。

### 第二階段：LINE 實測

- 在 LINE Developers Console 設定 Funnel HTTPS 下的 n8n production webhook URL，並使用 Verify 確認可連線。
- 以少量測試帳號傳送數則互不相關的文字訊息，以及貼圖、圖片或音訊。
- 確認只有文字事件得到回覆，回覆不依賴先前對話；檢查 n8n 執行紀錄、錯誤與模型用量。

沒有可執行的自動化測試套件時，不要新增測試框架或虛報自動化測試結果。變更完成後只執行與使用者要求相符的驗證。

## 貢獻規則

- 優先維持簡單流程；新增依賴、服務、儲存或對話記憶前，需有明確規格依據。
- 保持 Compose 設定可在 Windows Docker Desktop 使用，持久化 n8n 資料至 named volume。
- 變更環境變數時同步更新 `.env.example` 與 README.md，但範例值不得包含真實秘密。
- 不提交 `.env`、憑證、LINE 使用者內容、執行紀錄或含敏感資料的 workflow 匯出。
- 完成修改時，摘要說明變更、驗證方式及仍待使用者設定的項目。
