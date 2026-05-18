# CallGraph AI 🎙️

Minimalistic developer guide to running the project.

## 🚀 How to Run the Project (Backend + Frontend)

The application runs from a single FastAPI server which automatically serves the frontend files.

### 1. Setup Environment (Backend)
```powershell
cd backend
python -m venv venv

# If you get an 'Execution Policies' error, run this first:
# Set-ExecutionPolicy Unrestricted -Scope Process

.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Keys
Add your API keys to `backend/.env` (see `backend/.env.example`).
*(Optional) Verify keys:* `python test_keys.py`

### 3. Start the Server
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access the Frontend
Once the server is running, the frontend is automatically served!
Open your browser and go to: **[http://localhost:8000](http://localhost:8000)**

*(Note: The frontend code is located in the `frontend/` folder. It consists of pure HTML/JS/CSS. You don't need Node.js or `npm` to run it, the backend handles it completely).*
