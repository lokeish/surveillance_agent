# 🛡️ Surveillance Agent

**AI-powered local surveillance system that monitors your cameras 24/7 and keeps you informed — all from your own machine.** 

---

## ✨ Features

- 🎥 **Multi-Camera Feed** — Connect and monitor multiple surveillance cameras simultaneously
- 🕐 **24/7 Monitoring** — Always-on AI agent that never sleeps
- 🚨 **Instant Notifications** — Get real-time alerts on WhatsApp, Telegram, and more
- 🧠 **Video Memory & Insights** — Ask the agent anytime to pull insights from recorded footage
- 🔒 **100% Local & Secure** — Everything runs on your machine. Your data never leaves your system.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| **Python** | Core language |
| **Open Claw** | AI Agent orchestration & notifications |
| **YOLO** | Real-time object detection |

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/lokeish/surveillance_agent.git
cd surveillance_agent

# Install dependencies
pip install -e .

# Configure your cameras
cp config.yaml.example config.yaml

# Run the agent
python main.py
```

---

## 🏗️ Project Structure

```
surveillance_agent/
├── main.py                 # Entry point
├── config.yaml             # Camera & app configuration
├── video_pipeline/         # Stream capture, motion detection & recording
├── video_processing/       # Face detection, recognition & analysis
├── network/                # Camera discovery & scanning
├── app_logging/            # Logging service
└── config/                 # Configuration management
```

---

## 💬 Ask the Agent

At any point, query the agent to get insights from your video memories:

> *"Who visited the front door today?"*
> *"Was there any motion detected last night?"*
> *"Show me a summary of today's activity."*

---

## 🔐 Privacy First

No cloud. No third-party servers. Your footage, your data, your control.

---

## 📄 License

See [LICENSE](LICENSE) for details.
