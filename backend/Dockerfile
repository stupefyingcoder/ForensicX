FROM python:3.12-slim

WORKDIR /app

# System deps for OpenCV + Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download lightweight model weights only (SRGAN ~8MB, Real-ESRGAN compact ~5MB each)
# BSRGAN/x4plus omitted — too heavy for 8GB machines
RUN mkdir -p weights && \
    (test -f weights/realesr-general-x4v3.pth || curl -L -o weights/realesr-general-x4v3.pth "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth") && \
    (test -f weights/realesr-general-wdn-x4v3.pth || curl -L -o weights/realesr-general-wdn-x4v3.pth "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth")

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
