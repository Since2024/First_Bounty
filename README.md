# 🎯 FOMO (Fear Of Missing Out) - AI Form Filler

[![Built on Solana](https://img.shields.io/badge/Built_on-Solana-9945FF?style=for-the-badge&logo=solana)](https://solana.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google-bard&logoColor=white)](https://deepmind.google/technologies/gemini/)

**FOMO** is an AI-powered document automation tool that extracts data from IDs and forms using Google Gemini and **verifies the document's existence on the Solana Blockchain**.

> Built for the **Superteam Nepal University Tour Hackathon**. 🇳🇵🚀

---

## 💡 The Problem
In Nepal, government and banking paperwork is manual, repetitive, and prone to errors. Important documents are often lost or forged because there is no easy way to digitally verify their authenticity or existence at a specific point in time.

## 🛠️ The Solution
**FOMO** solves this by combining **Generative AI** with **Blockchain Immutability**:
1.  **AI Extraction**: Users upload an image (Citizenship, License, etc.), and Gemini extracts the text instantly.
2.  **Auto-Filling**: The data is mapped to industry-standard templates (KYC, Account Opening).
3.  **Proof of Existence**: The final generated PDF is hashed (SHA-256), and this hash is stored on the Solana Blockchain as a "Memo" transaction. This creates an **immutable digital certificate** that proves the document existed in that state.

---

## 🏗️ Tech Stack
-   **Frontend**: Streamlit (Python)
-   **AI Engine**: Google Gemini 1.5 Flash
-   **Blockchain**: Solana (Devnet)
-   **Wallet**: Phantom (via Deep Linking)
-   **Data**: SQLite

---

## 🚀 Features
-   **📄 Smart Template Selection**: Choose from bank forms, government applications, etc.
-   **⚡ AI-Powered Extraction**: Upload an image, get structured data in seconds.
-   **✏️ Human-in-the-Loop**: Review and edit the AI's output before finalizing.
-   **🟣 Phantom Deep Linking**: Connect your mobile or desktop wallet seamlessly.
-   **🔒 On-Chain Verification**: One-click to sign a transaction and mint a "Proof of Existence" on Solana.

---

## 📦 Setup & Installation

### Prerequisites
-   Python 3.10+
-   Google Gemini API Key
-   Phantom Wallet (Mobile or Extension)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/fomo-solana.git
cd fomo-solana
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```env
# Get key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key

# Admin Credentials (Optional)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### 4. Run the App
```bash
streamlit run app/frontend/ui.py
# Access at http://localhost:8501
```

---

## 🎥 Demo
*(Add your demo video link here)*

---

## 👥 Team
-   **[Your Name]** - Full Stack Developer
-   *(Add other team members)*

---

*Made with ❤️ in Nepal for the Solana Ecosystem.*
