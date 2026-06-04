# 🎵 Sacred Music Archive Player

A lightweight, responsive web application engineered to parse, index, and stream music collections directly from raw Markdown data archives. Built using a modern frontend stack, this player delivers a seamless user experience modeled after the clean, functional aesthetic of the **Sacred Music** mobile app.

Features a hybrid client-side architecture that supports both persistent offline file workflows and secure, serverless cloud-synchronized accounts.

---

## 🚀 Live Demo

Access the fully deployed application directly in your browser:
🔗 **[Launch Sacred Music Web App](https://lzurch3r.github.io/Church-Music-Web-App/)**

---

## ✨ Key Features

- **Dynamic Markdown Parsing Engine:** Eliminates the need for a heavy relational database backend by reading and lexing clean JSON tracking objects directly from a localized structured file (`Sacred_Music_Complete_Archive.md`).
- **Sacred Music Green UI:** Tailored with a deep emerald and leaf green palette mirroring official mobile interfaces, complete with smooth animations and layout states optimized for small smartphone screens.
- **Persistent Dual-Theme Engine:** Fully integrated native Dark Mode that matches system settings (`prefers-color-scheme`) and persists user preferences securely via browser `localStorage`.
- **Hybrid Playlist Management System:**
  - **Offline Mode:** Add/remove songs to a localized queue backed up via browser storage.
  - **JSON Data Portability:** Export your compiled queue directly into a clean, portable `.json` configuration file to back up or share playlists with other users instantly.
  - **Cloud Sync Accounts:** Authenticated user sign-in modules let you save, sync, and retrieve playlists securely in the cloud across any machine.

---

## 🛠️ Tech Stack & Architecture

- **Frontend:** Semantic HTML5, Modern CSS Variables, Vanilla JavaScript (ES6+ Module Architecture)
- **Database / Auth:** Google Firebase SDK v10 (Firebase Authentication & Cloud Firestore)
- **Data Source Engine:** Direct Asynchronous File Stream / Lexical String Parser

---

## 📖 How-To Guide for First-Time Users

Getting started with the app is quick and easy. Follow these steps to listen, search, and manage your playlists.

### 1. Launching the App
Simply click the production link: **[https://lzurch3r.github.io/Church-Music-Web-App/](https://lzurch3r.github.io/Church-Music-Web-App/)**. Because the application is fully optimized for web environments, it requires zero installation or browser extensions.

### 2. Navigating Collections & Playing Tracks
- At the top of the dashboard, you will see a grid layout of available **Collection Cards** representing different book directories. Clicking a card instantly filters the main viewport to show only tracks from that specific compilation.
- To listen to a song, click on the title card row. The bottom **Media Dock Drawer** will instantly load the streaming asset and begin playing.

### 3. Using the Search Matrix
The search input in the header functions as a dynamic client-side filtering matrix. As you type, the visible track list automatically isolates matches by title or keyword in real-time.

### 4. Backing Up and Sharing Playlists Offline
- Click the **+** symbol beside any indexed track to populate your sidebar queue.
- Under **My Playlist**, click **📤 File Save** to generate and download a clean `sacred_music_playlist.json` text file straight to your machine.
- To share your setup, send that file to another user. They can open the web app, click **📥 File Load**, and view or play your shared queue effortlessly.

---

## 📈 Future Roadmap

Planned enhancements for future iterations of the platform include:

- [ ] **Full Media Library Optimization:** Scale up parsing capabilities to ingest thousands of tracks, adding automatic client-side caching to minimize networking overhead.
- [ ] **Full Official Hymnal Library Integration:** Incorporate the complete text, sheet music indexing, and streaming audio links for the entire library of official global music print editions.
- [ ] **Interactive Media Controls:** Enhance the core player with continuous background playback, custom playback speeds, and a global keyboard shortcuts layout.
- [ ] **Persistent Global Audio Queue:** Implement true gapless playback sequencing to automatically cycle down through current playlist queues or book collections.
- [ ] **Shared Public Playlists:** Allow authenticated users to publish custom collections, generating unique sharing links so other community members can listen to curated tracks directly in the cloud.

---

## 🤖 AI Development Statement

This repository and its codebase were developed with the assistance of Artificial Intelligence (AI). AI was utilized to help prototype layout configurations, refactor responsive stylesheet properties, optimize the lexical string parser framework, and generate comprehensive documentation.
