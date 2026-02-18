# 🎯 FOMO (Fear Of Missing Out) - AI Form Filler + Solana Proof of Existence

[![Built on Solana](https://img.shields.io/badge/Built_on-Solana-9945FF?style=for-the-badge&logo=solana)](https://solana.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google-bard&logoColor=white)](https://deepmind.google/technologies/gemini/)

**FOMO** is an AI-powered document automation tool that extracts data from IDs/forms and anchors proof metadata on Solana so issued documents can be verified later.

> Built for the **Superteam Nepal University Tour Mini-Hack** 🇳🇵🚀

---

## 🧠 One-line Pitch
**From paper-heavy workflows to verifiable digital documents in minutes, not hours.**

## ❗ Problem
In Nepal, many onboarding/compliance processes are still paper-heavy and manual:
- Repetitive form filling causes delays and mistakes.
- Document forgery detection is difficult.
- There is no simple public proof that a document existed at a specific point in time.

## ✅ Solution
FOMO combines AI extraction + human review + Solana immutability:
1. **Extract**: Upload an ID image (e.g., citizenship/license), then Gemini extracts structured fields.
2. **Review**: User edits/corrects the extracted values (human-in-the-loop).
3. **Generate**: App auto-fills selected form templates and exports PDF.
4. **Anchor**: PDF hash + UUID are recorded as a Solana memo transaction.
5. **Verify**: Any verifier can check exact hash match or UUID fallback against stored proof.

## 🔎 Why It’s Interesting
- Practical first step toward **verifiable credential workflows**.
- Works with familiar docs and process flow users already understand.
- Demonstrates immediate real-world utility of Solana beyond trading use cases.

---

## 🏗️ Tech Stack
- **Frontend**: Streamlit (Python)
- **AI Engine**: Google Gemini 1.5 Flash
- **Blockchain**: Solana (Devnet)
- **Wallet UX**: Phantom deep linking
- **Database**: SQLite + SQLAlchemy
- **PDF**: ReportLab + PyMuPDF

---

## 🚀 Core Features
- 📄 **Template-based form filling**
- ⚡ **AI extraction from document images**
- ✏️ **Human review before final output**
- 🟣 **Phantom signing flow** for proof anchoring
- 🔒 **On-chain proof of existence** (memo transaction)
- 🛡️ **Dual verification**:
  - exact SHA-256 hash match
  - UUID fallback for modified-but-related files

---

## 🧪 Verification Modes
1. **Exact Match (Strongest)**
   - Uploaded file hash equals anchored hash.
2. **UUID Match (Resilient)**
   - If file content changed (e.g., Save As), UUID metadata can still map to original proof.

---

## 📦 Setup & Installation

### Prerequisites
- Python 3.10+
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- Phantom wallet configured for **Solana Devnet**

### 1) Clone
```bash
git clone https://github.com/yourusername/fomo-solana.git
cd fomo-solana
```

### 2) Configure env
Create `.env` in repo root:
```env
GEMINI_API_KEY=your_gemini_api_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### 3) Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4) Run
```bash
streamlit run app/frontend/ui.py
```
Open: `http://localhost:8501`

---

## 🧪 Test
```bash
pytest -q
```

---

## 📊 Judging Criteria Mapping
- **Problem clarity** → Defined pain in manual, forge-prone paperwork.
- **Impact** → Faster workflows + auditable proofs.
- **Business case** → B2B model for banks/cooperatives/insurance onboarding flows.
- **UX** → Guided upload → extract → review → generate → verify flow.
- **Technical implementation** → AI extraction, template filling, PDF generation, Solana anchoring, verification.
- **Completeness** → README, setup, tests, architecture, pitch assets.

---

## 👥 Team
- **[Hasan Gaha]**
