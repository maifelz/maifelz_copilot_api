# mAifelZ AI Copilot — Odoo Addon Module

Empower your Odoo users with an enterprise AI Copilot for conversational business intelligence, real-time KPI analysis, revenue calculations, and lead tracking — powered by **mAifelZ Technologies**.

---

## 🚀 Installation & Setup Guide

### Method A: Odoo.sh or Git Submodule (Recommended)
1. Copy or push the `maifelz_ai_copilot` folder into your Odoo repository's custom addons branch:
   ```bash
   git add maifelz_ai_copilot
   git commit -m "feat: add mAifelZ AI Copilot addon"
   git push origin main
   ```
2. In Odoo, activate **Developer Mode**.
3. Go to **Apps** $\rightarrow$ Click **Update Apps List**.
4. Search for `mAifelZ AI Copilot` and click **Install**.

---

### Method B: On-Premise / Docker / Odoo VM
1. Place `maifelz_ai_copilot` inside your `addons_path` directory (e.g. `/mnt/extra-addons/`).
2. Restart your Odoo server:
   ```bash
   sudo systemctl restart odoo
   ```
3. Update App List in Odoo and click **Install**.

---

## 🔑 Activating Your Subscription
1. In Odoo, go to **Settings** $\rightarrow$ **General Settings**.
2. Scroll to the **mAifelZ AI Copilot Configuration** block.
3. Paste the **License Key** issued to you by mAifelZ (e.g., `MFZ-PRO-2026-XXXX`).
4. Click **Verify & Activate License**.
5. Your team can now access the **mAifelZ AI Copilot** app icon from the top menu or dashboard!

---

## 🔒 Security & Architecture
- **Zero AI Logic on Odoo**: No heavy LLMs or confidential prompt engineering reside on the client's Odoo server.
- **Enterprise Control**: All AI queries are authenticated, metered, and processed securely via mAifelZ Cloud infrastructure.
- **Master Kill-Switch**: If a client cancels or defaults, access is toggled off instantly from the mAifelZ Master Admin Console.
