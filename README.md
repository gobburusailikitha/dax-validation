# 📊 DAX Validator (FastAPI + React)

A simple tool to validate **DAX expressions** using a **FastAPI backend** and a **React frontend**.

---

## 🚀 Project Setup

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd dax_validation

### 2. Backend  Setup
cd backend
python -m venv venv
.\venv\Scripts\activate    
pip install -r requirements.txt

### 3. Backend RUN 
uvicorn main:app --reload --host 0.0.0.0 --port 8000

### 4. Frontend Setup 
cd frontend
npm install


###5. Frontend Run 
npm start
