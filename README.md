# Tank Pilot

Tank Pilot adalah sistem pemantauan dan pengendalian tangki berbasis IoT yang memungkinkan Anda mengelola banyak tangki secara terpusat dari satu dashboard web yang intuitif. Tank Pilot menggabungkan keandalan ESP32, kekuatan platform ThingsBoard, dan antarmuka web modern untuk memberikan kontrol real-time atas level kapasitas tanki, status pompa, dan mode operasi  kapan pun dan di mana pun.

## Fitur

- Pemantauan Real-Time
- Kontrol Pompa
- Tambah Perangkat
- Hapus Perangkat

## Instalasi

1. clone repository:
```
git clone https://github.com/farelsatrio/tank-pilot.git
```

2. masuk ke direktori proyek:
```
cd tank pilot
```

3. copy .env.example
```
cp .env.example .env
```

4. build image:
```
docker build -t tank-pilot .
```

5. jalankan image:
```
docker run --name tank-pilot -d -p 80:8000 tank-pilot
```

## Penggunaan

1. buat device di thingsboard
2. upload file tank-pilot.ino ke esp32
3. tambah perangkat dengan mengklik tanda plus di kanan atas
4. pilih mode yang akan digunakan (otomatis atau manual)

