# 🎵 Sacred Music Archive Player

A modern, responsive web application engineered to parse, index, and stream music collections directly from raw Markdown data archives. Built using a lightweight frontend stack, this player delivers a seamless user experience modeled after the clean, functional aesthetic of the **Sacred Music** mobile app.

Features a hybrid client-side architecture that supports both persistent offline file workflows and secure, free cloud-synchronized accounts.

---

## 🤖 AI Disclosure
*This project, including its UI styling, parsing architecture, and foundational components, was designed and developed with the assistance of artificial intelligence.*

---

## ✨ Key Features

- **Dynamic Markdown Parsing Engine:** Eliminates the need for a heavy relational database backend by reading and lexing clean JSON tracking objects directly from a localized structured file (`Sacred_Music_Complete_Archive.md`).
- **Sacred Music Green UI:** Tailored with a deep emerald and leaf green palette mirroring official mobile interfaces, complete with smooth animations and layout states optimized for small smartphone screens.
- **Persistent Dual-Theme Engine:** Fully integrated native Dark Mode that matches system settings (`prefers-color-scheme`) and persists user preferences securely via browser `localStorage`.
- **Hybrid Playlist Management System:**
  - **Offline Mode:** Add/remove songs to a localized queue backed up via browser storage.
  - **JSON Data Portability:** Export your compiled queue directly into a clean, portable `.json` configuration file to back up or share playlists with other users instantly.
  - **Cloud Sync Accounts:** Authenticate securely using an integrated, serverless account module to save, sync, and retrieve playlists across any machine.

---

## 🛠️ Tech Stack & Architecture

- **Frontend:** Semantic HTML5, Modern CSS Variables, Vanilla JavaScript (ES6+ Module Architecture)
- **Database / Auth:** Google Firebase SDK v10 (Firebase Authentication & Cloud Firestore)
- **Data Source Engine:** Direct Asynchronous File Stream / Lexical String Parser

---

## 🚀 Getting Started (How-To Guide)

If you are a first-time user, follow these clear instructions to set up, configure, and run the Sacred Music Archive Player on your local computer or development environment.

### 1. Repository Structure
Ensure your local project directory includes the following layout files:
```text
├── index.html                           # Main web application entry point & logic
├── Sacred_Music_Complete_Archive.md     # Raw markdown repository indexing the tracking assets
└── README.md                            # Project documentation
