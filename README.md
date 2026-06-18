# Forensic Enhancement Web App

Product-style fullstack app for forensic image enhancement analysis with:

- FastAPI backend
- React + Vite frontend
- Model comparison: `SRGAN`, `Real-ESRGAN x4v3`, `Bicubic`
- Metrics: `PSNR`, `LPIPS`, `SSIM`, OCR confidence/edit distance, face similarity proxy
- Batch experiments and report export

## Project Layout

- `backend/` FastAPI service, DB models, job worker, inference/metrics pipeline
- `frontend/` React app (Login, Dashboard, Case Detail, Run Comparison, Metrics, Research Export)
- `docs/` research paper and black-book templates

## Backend Setup

```powershell
cd d:\BE_Final_Year_Project\forensic-enhancement-webapp\backend
# reuse existing venv if desired:
# d:\BE_Final_Year_Project\super-resolution-image-enhancer-main\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend Setup

```powershell
cd d:\BE_Final_Year_Project\forensic-enhancement-webapp\frontend
npm install
npm run dev
```

Frontend runs on `http://127.0.0.1:5173`, backend on `http://127.0.0.1:8000`.

Set frontend API base (optional):

```powershell
cd d:\BE_Final_Year_Project\forensic-enhancement-webapp\frontend
copy .env.example .env
```

## Validation

```powershell
cd d:\BE_Final_Year_Project\forensic-enhancement-webapp\backend
d:\BE_Final_Year_Project\super-resolution-image-enhancer-main\.venv\Scripts\python.exe -m pytest -q

cd d:\BE_Final_Year_Project\forensic-enhancement-webapp\frontend
npm run build
```

## API Summary

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/cases`
- `GET /api/cases`
- `GET /api/cases/{id}`
- `POST /api/cases/{id}/images`
- `POST /api/runs`
- `GET /api/runs/{id}`
- `GET /api/runs/{id}/results`
- `POST /api/experiments/batch`
- `GET /api/experiments/{id}/summary`
- `GET /api/experiments/{id}/csv`
- `POST /api/reports/generate`
- `GET /api/reports/{id}`
- `GET /api/files?path=...`

## Important Forensic Note

Enhanced images may contain synthetic detail. This system is an analytical support tool and not direct evidence reconstruction.
