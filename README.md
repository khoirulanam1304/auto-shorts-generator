# Auto Shorts Layout Tool

Tool ini bikin video Shorts 9:16 dengan layout:
- Background dari video asli + blur
- Panel atas kiri: video bergerak
- Panel atas kanan: freeze frame dari video asli
- Panel tengah: teks hook
- Dua panel bawah: tampilan mirip screenshot komentar

## Requirement
- Python 3.9+
- ffmpeg + ffprobe tersedia di PATH

Install dependency Python:

```bash
pip install -r requirements.txt
```

## Cara Pakai

```bash
python shorts_layout_tool.py ^
  --input input.mp4 ^
  --output output_hook.mp4 ^
  --hook "Sederhana, tapi gerakannya sulit diabaikan" ^
  --comment1 "Tenang-tenang, tapi bikin fokus ke satu titik" ^
  --comment2 "Biasa kelihatannya, beda rasanya" ^
  --replying-to "@market2143" ^
  --style-filter cinematic ^
  --mirror-mode live ^
  --comment-theme dark ^
  --layout-preset balanced
```

## Opsi Penting
- `--freeze-time` detik untuk ambil frame freeze (default `0.30`)
- `--font` path font `.ttf` jika mau style teks sendiri
- `--crf` kualitas output video (default `20`, lebih kecil = lebih bagus)
- `--preset` kecepatan encode (`ultrafast` sampai `veryslow`)
- `--style-filter` filter panel video: `none|cinematic|vivid|cool|warm` (default `cinematic`)
- `--mirror-mode` mirror horizontal: `none|live|both` (default `live`)
- `--comment-theme` tema kotak komentar: `light|dark` (default `light`)
- `--layout-preset` preset tata letak: `compact|balanced|cinema` (default `balanced`)
