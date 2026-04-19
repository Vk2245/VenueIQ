<div align="center">

<!-- Hero Badges -->
<p>
  <img src="https://img.shields.io/badge/🏆_Google_Services-8_Integrated-4285F4?style=for-the-badge&labelColor=0d1117" alt="8 Google Services">
  <img src="https://img.shields.io/badge/🤖_Gemini-2.5_Flash-EA4335?style=for-the-badge&labelColor=0d1117" alt="Gemini">
  <img src="https://img.shields.io/badge/📊_Live_Sync-Google_Sheets-34A853?style=for-the-badge&labelColor=0d1117" alt="Sheets Sync">
  <img src="https://img.shields.io/badge/♿_WCAG-2.1_AA-9C27B0?style=for-the-badge&labelColor=0d1117" alt="Accessibility">
</p>

<!-- Title Block -->
# 🏟️ VenueIQ

### The Universal AI Venue Intelligence OS
**Scalable Crowd Intelligence for Stadiums, Cinépolis, Delhi Metro, and Beyond**

*Real-time crowd analytics · AI-powered predictive queues · Autonomous incident coordination*

<br>

<!-- Tech Stack Badges -->
<p>
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Firebase-Admin_SDK-FFCA28?style=flat-square&logo=firebase&logoColor=black" alt="Firebase">
  <img src="https://img.shields.io/badge/Google_Sheets-Live_DB-34A853?style=flat-square&logo=google-sheets&logoColor=white" alt="Sheets">
  <img src="https://img.shields.io/badge/NanoBanana-Experimental_AI-FF6B6B?style=flat-square&logo=ai&logoColor=white" alt="NanoBanana">
  <img src="https://img.shields.io/badge/PWA-Installable-5A0FC8?style=flat-square&logo=pwa&logoColor=white" alt="PWA">
</p>

<br>

> **Designed for universal scalability and 100% Google-native integration.** VenueIQ transforms any physical space into a smart, data-driven ecosystem using **Gemini 2.5 Flash** and the **Google Sheets API**.

</div>

<br>

---

<br>

## 🚀 One Engine, Any Venue

VenueIQ is not just for the stadium. Its **Universal Zone Configuration** architecture allows it to scale perfectly across:

- 🍿 **Cinemas**: Manage concession queues and hall occupancy.
- 🚇 **Metro Stations**: Balance platform density and gate flow.
- 🏟️ **Stadiums**: Orchestrate 30,000+ attendee movements.
- 🎸 **Concerts**: Real-time safety and bottleneck detection.

---

## 🛠️ Google Services — Deep Integration Map

VenueIQ leverages **8 Google Services** to provide a production-grade experience on the Spark (Free) tier.

### ⚙️ Backend (Python + AI)

| Service | Integration Point | Purpose |
|:---|:---|:---|
| **Gemini 2.5 Flash** | `gemini_service.py` | The Platform's "Brain" — Analyzing density, predicting wait times, and routing incidents. |
| **Google Sheets API** | `gspread_service.py` | **Live Synchronization** — Real-time persistent logging of every data point for manager auditing. |
| **Firebase Admin SDK** | `main.py` | Core platform security and Firestore fallback management. |
| **Firebase Messaging** | `notification_service.py` | Topic-based push alerts for crowd surges and incident response. |

### 🌐 Frontend (PWA + High-Fidelity)

| Service | Integration Point | Purpose |
|:---|:---|:---|
| **Firebase Analytics** | `index.html` | Real-time attendee behavior tracking and bottleneck heatmapping. |
| **Firebase Auth JS** | `index.html` | Seamless Google Sign-In for managers and staff. |
| **reCAPTCHA v3** | `index.html` | Invisible bot protection for high-traffic incident reporting forms. |
| **Google Fonts** | `index.html` | Inter typography for a prestige, premium corporate visual identity. |

---

## ✨ Innovation Spotlight

### 🍌 NanoBanana Dynamic Thermal Mapping
The mapping layer features an experimental **AI Thermal Scan** simulation. By triggering the `⚡` scan, VenueIQ processes simulated "Gemini Nano" thermal sensor data to generate a real-time, jittered crowd density overlay, allowing managers to see live attendee "breathing" and flow.

### 🔍 AI Command Center
A high-performance **Omnibox** integrated into the header. It provides staff with a single source of truth for searching venue zones, checking gate statuses, or initiating AI-driven coordination tasks.

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "👥 Users"
        ATT["📱 Attendee / Fan PWA"]
        STAFF["💻 Venue Ops Manager"]
    end

    subgraph "🚀 VenueIQ Core"
        API["FastAPI Backend"]
        GEM["🤖 Gemini Intelligence"]
        DB["📊 Sheets Live Sync"]
        NOTIF["📢 FCM Alerts"]
    end

    subgraph "☁️ Google Ecosystem"
        G_AI["Gemini 2.5 Flash"]
        G_SHEETS["Sheets API"]
        G_FCM["Cloud Messaging"]
        G_AUTH["Firebase Guard"]
    end

    ATT -->|"Interact"| API
    STAFF -->|"Monitor"| API
    API --> GEM --> G_AI
    API --> DB --> G_SHEETS
    API --> NOTIF --> G_FCM
```

---

## 🧪 Deployment & Verification

- **PWA Ready**: Register a Service Worker and install directly to Android/iOS/Desktop.
- **Dockerized**: `docker-compose up` for instant local deployment.
- **Test Suite**: 24/24 unit tests covering Auth, Crowd Management, and AI Routing.

---

<div align="center">

### Built for the PromptWars Hackathon 2026
**Theme**: Physical Event Experience
**AI Agent**: Google Antigravity
**Environment**: 100% Google Studio / GCP / Firebase

<sub>Built with ❤️ by Vishal Kumar</sub>

</div>
