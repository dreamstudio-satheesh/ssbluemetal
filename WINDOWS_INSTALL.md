# Windows Installation & Build Guide

## Option A: Run directly (Python required)

### 1. Install Python
- Download **Python 3.13+** from https://www.python.org/downloads/
- ✅ Check **"Add Python to PATH"** during installation

### 2. Copy the project
Copy the `billing/` folder to your Windows PC — e.g.:
```
C:\KalQuarry\billing\
```

### 3. Open Command Prompt
```cmd
cd C:\KalQuarry\billing
```

### 4. Setup virtual environment & install
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the app
```cmd
python main.py
```
Default login: `admin` / `admin123`

---

## Option B: Build standalone .exe (no Python needed)

### 1. Follow steps 1–4 from Option A

### 2. Install PyInstaller & build
```cmd
pip install pyinstaller
pyinstaller --onefile --windowed --name "KalQuarry" main.py
```

### 3. The .exe is at:
```
C:\KalQuarry\billing\dist\KalQuarry.exe
```
You can copy this single file to any Windows PC and run it directly.

---

## Option C: One-click launcher (`.bat` file)

Save this as `run.bat` inside `C:\KalQuarry\`:

```batch
@echo off
cd /d "C:\KalQuarry\billing"
call venv\Scripts\activate
python main.py
pause
```

Double-click `run.bat` to launch.

---

## Quick reference

| Command | Purpose |
|---------|---------|
| `python main.py` | Run the app |
| `pyinstaller --onefile --windowed --name "KalQuarry" main.py` | Build .exe |
| `python -m venv venv` | Create virtual env |
| `venv\Scripts\activate` | Activate virtual env |
| `pip install -r requirements.txt` | Install dependencies |

---

## Troubleshooting

### "No module named PySide6" error

**Cause:** You skipped the virtual environment or didn't install dependencies.

**Fix — run these 3 commands in order:**

```cmd
cd C:\KalQuarry\billing
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Make sure you see `(venv)` at the start of the command prompt line after step 3. If you don't see `(venv)`, the virtual environment is not activated — run `venv\Scripts\activate` again.

### "pip is not recognized"

**Cause:** Python was not added to PATH during installation.

**Fix:** Re-run the Python installer and ✅ check **"Add Python to PATH"**, then restart Command Prompt.
