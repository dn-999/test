# LINE chatbot (starter)

## Scope
- Handle each text message independently; do not store or send conversation history.
- Ignore stickers and all other non-text message events.
- n8n runs locally in Docker Compose. A Caddy gateway exposes only n8n's webhook paths to Tailscale Funnel; the n8n editor remains on localhost.

## Start n8n
1. Copy `.env.example` to `.env` and replace `N8N_ENCRYPTION_KEY` with a long random value. `.env` is git-ignored; keep it private.
2. Run `docker compose up -d` and open http://localhost:5678 to create the n8n owner account.
3. Install and sign in to Tailscale on this Windows PC. Enable Funnel for the tailnet and expose local port 8080 with `tailscale funnel 8080`. Do not expose port 5678 through Funnel; it serves the n8n editor.
4. Copy the HTTPS hostname reported by Funnel into `N8N_WEBHOOK_URL` in `.env` (include the trailing slash), then run `docker compose up -d` again.

The LINE webhook URL must be the production URL shown by the n8n Webhook node, under the Funnel hostname. Before activating it, configure LINE webhook signature verification using the channel secret and original request body. Store LINE and cloud model credentials in n8n Credentials, not in workflow text or `.env`.

## Credentials needed
- LINE Messaging API channel secret and channel access token.
- Cloud model API key. Gemini API is a possible free-tier option; model availability, quota and data terms depend on the selected model and account.

## Two-stage test plan
1. Local: confirm the n8n workflow accepts text, passes only the current message to the model, replies successfully, and stops without reply for non-text events.
2. LINE: verify the webhook URL in LINE Developers Console, then use a small test group to send unrelated text messages and stickers/images/audio. Confirm only text gets replies; inspect n8n executions and model usage.
