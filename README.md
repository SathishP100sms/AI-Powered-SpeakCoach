# 🎙️ SpeakCoach AI — Real-Time Spoken English Tutor

SpeakCoach AI is a **real-time AI-powered spoken English coaching web app** designed to help users improve communication skills through **text + voice interaction**.

It acts like a **human English trainer**, providing:

* Grammar correction
* Natural sentence improvement
* Interview preparation
* Real-time voice conversation

---

## 🚀 Features

### 🧠 AI-Powered Coaching

* Context-aware responses using **Gemini LLM**
* Human-like conversation flow
* Smart feedback and corrections

### 📝 Grammar Correction Mode

* Detects mistakes in user input
* Provides:

  * Corrected sentence
  * Explanation
  * Better spoken version

### 💬 Conversation Mode

* Natural real-life conversation practice
* Friendly AI interaction
* Improves fluency and confidence

### 🎯 Interview Mode

* Simulates real HR interviews
* Evaluates:

  * Grammar
  * Clarity
  * Structure
* Provides score + better answers

### 🎤 Voice Input (Speech-to-Text)

* Uses **Whisper (faster-whisper)**
* Converts user speech into text in real-time

### 🔊 AI Voice Response (Text-to-Speech)

* Uses **Edge-TTS**
* Converts AI responses into natural human voice

### ⚡ Real-Time Experience

* Instant responses
* Voice + text interaction
* Interactive UI

---

## 🏗️ Tech Stack

### Backend

* FastAPI
* Gemini API (Google GenAI)
* Faster-Whisper (Speech Recognition)
* Edge-TTS (Text-to-Speech)
* Pydub (Audio Processing)

### Frontend

* HTML, CSS, JavaScript
* Glassmorphism UI
* Typing Animation
* Voice Wave Animation

---

## 📂 Project Structure

```
AI-Powered-SpeakCoach/
│
├── backend/
│   ├── main.py          # FastAPI server
│   ├── model.py         # Core AI logic (LLM + Whisper + TTS)
│   ├── utils.py         # Prompt + configs
│   
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│
├── README.md
|
├── requirements.txt
|
├── .python-version
```

---

## ⚙️ Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/sathishp100sms/ai-powered-speakcoach.git
cd speakcoach-ai
```

---

### 2️⃣ Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

---

### 3️⃣ Add API Key

Create `.env` file or set environment variable:

```
GEMINI_API_KEY=your_gemini_api_key
```

---

### 4️⃣ Run Backend

```bash
uvicorn main:app --reload
```

Server will run at locally:

```
http://127.0.0.1:8000
```

---

### 5️⃣ Run Frontend

Just open:

```
frontend/index.html
```

---

## 🔗 API Endpoints

### ✅ Chat

```
POST /chat
```

Request:

```json
{
  "message": "I go to market yesterday",
  "mode": "grammar"
}
```

---

## 🌐 Deployment

### Frontend

* Vercel / Netlify

### Backend

* Render

> ⚠️ Note: Audio playback should be handled in frontend for production.

---

## 🎯 Future Improvements

* 🔄 Streaming responses (real-time typing effect)
* 🌍 Multi-language support
* 📊 Progress tracking dashboard
* 🎧 Frontend-based audio playback
* 🧠 Personalized learning paths

---

## 📜 License

This project is open-source and available under the MIT [LICENSE](LICENSE).

---

## 💡 Author

**Sathish P**
AI/ML Developer | Building real-world AI products 🚀

---
