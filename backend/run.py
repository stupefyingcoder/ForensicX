from app.main import app

# Entry module for `uvicorn run:app --reload`

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
