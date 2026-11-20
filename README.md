# J.A.R.V.I.S. — Sci-Fi Hologram AI Assistant HUD

[![Live Demo](https://img.shields.io/badge/Live%20Demo-TryCloudflare-blue?style=for-the-badge&logo=cloudflare)](https://programme-bloomberg-big-barnes.trycloudflare.com)
[![GitHub License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

An interactive, futuristic **Arc Reactor Hologram AI Assistant HUD** built on **OpenJarvis**. Features real-time multi-source Gmail inbox ingestion, deep email archive search, work schedule tracking, system telemetry, and voice output synthesis (TTS).

---

## 🌟 Live Demo
Open the live hosted server:  
👉 **[https://programme-bloomberg-big-barnes.trycloudflare.com](https://programme-bloomberg-big-barnes.trycloudflare.com)**  
*(Or run locally on `http://localhost:8090`)*

---

## 🚀 Key Features

- **📥 Full Gmail Archive & Live Inbox Feed:**
  - Real-time synchronization of emails with snippets, sender tags, and timestamps.
  - Deep archive keyword search (e.g. *BookMyShow tickets, SBI bank statements, job offers*).
  - Interactive cards that vocalize and summarize on click.

- **🔵 Sci-Fi Holographic HUD:**
  - Glowing Arc Reactor core with pulsating soundwave frequency visualization.
  - Instant quick-action pills: *Morning Briefing*, *Work Schedule*, *Job Applications*, *Diagnostics*.
  - **⏹ Instant Stop Button:** Pause / kill AI vocalization anytime.

- **🔊 Voice Output (TTS):**
  - Integrated text-to-speech synthesis that vocally delivers morning briefs, summaries, and query answers.

- **⚡ Live System Telemetry & Connectors:**
  - Real-time CPU, RAM, and storage tracking.
  - Active connector badges for Gmail, Google Calendar, Google Drive, and Google Tasks.

---

## 🛠️ Quick Start & Local Run

### 1. Clone the repository
```bash
git clone https://github.com/yashh077/jarvis-hologram-hud.git
cd jarvis-hologram-hud
```

### 2. Install dependencies
```bash
pip install fastapi uvicorn httpx psutil
```

### 3. Start the server
```bash
python server.py
```
Open **`http://localhost:8090`** in any browser.
