# Gunakan gambar dasar Python resmi yang ramping
FROM python:3.11-slim

# Atur direktori kerja di dalam container
WORKDIR /app

# Salin file requirements terlebih dahulu untuk caching yang efisien
COPY requirements.txt .

# Instal semua library yang dibutuhkan
# --no-cache-dir untuk menjaga ukuran tetap kecil
RUN pip install --no-cache-dir -r requirements.txt

# Salin sisa kode aplikasi Anda
COPY . .

# Beri tahu Docker port mana yang akan diekspos
EXPOSE 7860

# Perintah untuk menjalankan aplikasi saat container dimulai
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]