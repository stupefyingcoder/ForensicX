FROM python:3.12-slim

WORKDIR /app

# System deps for OpenCV + Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install CPU-only torch/torchvision first so the generic version specifiers in
# requirements.txt are already satisfied and pip does NOT pull the ~2GB CUDA
# wheels (no GPU on Hugging Face's free CPU Spaces). Cuts image size and build time.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Download model weights at build time.
# Real-ESRGAN general (compact ~5MB each) powers the default "realesrgan" model.
# Real-ESRGAN x4plus (~64MB) and BSRGAN (~64MB) are the heavier RRDBNet models;
# HF free CPU Spaces have 16GB RAM so they fit. SRGAN is omitted — it needs a
# privately-trained srgan_generator.pth that is not publicly downloadable.
RUN mkdir -p weights && \
    (test -f weights/realesr-general-x4v3.pth || curl -L -o weights/realesr-general-x4v3.pth "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth") && \
    (test -f weights/realesr-general-wdn-x4v3.pth || curl -L -o weights/realesr-general-wdn-x4v3.pth "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth") && \
    (test -f weights/RealESRGAN_x4plus.pth || curl -L -o weights/RealESRGAN_x4plus.pth "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth") && \
    (test -f weights/BSRGAN.pth || curl -L -o weights/BSRGAN.pth "https://github.com/cszn/KAIR/releases/download/v1.0/BSRGAN.pth")

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
