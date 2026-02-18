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
3.  **Proof of Existence**: The final generated PDF is hashed (SHA-256) and assigned a **Unique ID (UUID)**. unique ID. This proof is stored on the Solana Blockchain as a "Memo" transaction, creating an **immutable digital certificate**.

### ✅ Robust Verification
We use a dual-layer verification system to ensure documents can always be verified, even if they are modified (e.g., "Save As" in a browser):
1.  **Exact Match**: Checks the SHA-256 hash of the file. (Most Secure)
2.  **UUID Fallback**: Checks the embedded UUID in the PDF metadata if the hash doesn't match. (Resilient)

---

## 🏗️ Tech Stack
-   **Frontend**: Streamlit (Python)
-   **AI Engine**: Google Gemini 1.5 Flash
-   **Blockchain**: Solana (Devnet)
-   **Wallet**: Phantom (via Deep Linking)
-   **Data**: SQLite & SQLAlchemy
-   **PDF Generation**: ReportLab & PyMuPDF

---

## 🚀 Features
-   **📄 Smart Template Selection**: Choose from bank forms, government applications, etc.
-   **⚡ AI-Powered Extraction**: Upload an image, get structured data in seconds.
-   **✏️ Human-in-the-Loop**: Review and edit the AI's output before finalizing.
-   **🟣 Phantom Deep Linking**: Connect your mobile or desktop wallet seamlessly.
-   **🔒 On-Chain Verification**: One-click to sign a transaction and mint a "Proof of Existence" on Solana.
-   **🛡️ Tamper Check**: Detects if a document has been modified since issuance.

---

## 📦 Setup & Installation

### Prerequisites
-   Python 3.10+
-   Google Gemini API Key covering [Google AI Studio](https://aistudio.google.com/)
-   Phantom Wallet (Mobile or Extension) connected to **Solana Devnet**.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/fomo-solana.git
cd fomo-solana
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```bash
cp .env.example .env  # If example exists, otherwise create new
```

Add your keys:
```env
# Get key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key

# Admin Credentials (Optional - for dashboard)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### 3. Install Dependencies
It is recommended to use a virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install packages
pip install -r requirements.txt
```

### 4. Run the App
```bash
streamlit run app/frontend/ui.py
```
Access the app at `http://localhost:8501`.

---

## 🧪 Testing Verification
1.  **Fill a Form**: Complete a form generation flow.
2.  **Verify (Exact)**: Download the PDF and upload it to the "Verify" page. It should be "Verified".
3.  **Verify (Modified)**: Open the PDF, "Save As" a copy, and upload the copy. It should be "Verified with Warnings".

---

## 👥 Team
-   **[Your Name]** - Full Stack Developer
-   *(Add other team members)*

---

*Made with ❤️ in Nepal for the Solana Ecosystem.*
