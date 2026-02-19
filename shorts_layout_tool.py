import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def run_cmd(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + proc.stdout
            + "\nSTDERR:\n"
            + proc.stderr
        )
    return proc


def ensure_tools():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg tidak ditemukan di PATH.")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe tidak ditemukan di PATH.")


def probe_duration(video_path):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    proc = run_cmd(cmd)
    return float(proc.stdout.strip())


def pick_font(font_path, size):
    candidates = []
    if font_path:
        candidates.append(font_path)
    candidates.extend(
        [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def obfuscate_username(source):
    base = source.strip().lstrip("@") or "user"
    if len(base) <= 2:
        return "u***"
    if len(base) <= 5:
        return base[0] + ("*" * (len(base) - 1))
    return base[:2] + ("*" * (len(base) - 4)) + base[-2:]


def draw_anonymous_avatar(draw, x, y, size, bg, fg, outline):
    # Anonymous style avatar (head + shoulder shape) to avoid using real identities.
    draw.ellipse((x, y, x + size, y + size), fill=bg, outline=outline, width=2)

    head = int(size * 0.34)
    head_x = x + (size - head) // 2
    head_y = y + int(size * 0.16)
    draw.ellipse((head_x, head_y, head_x + head, head_y + head), fill=fg)

    shoulder_w = int(size * 0.68)
    shoulder_h = int(size * 0.34)
    shoulder_x = x + (size - shoulder_w) // 2
    shoulder_y = y + int(size * 0.56)
    draw.rounded_rectangle(
        (shoulder_x, shoulder_y, shoulder_x + shoulder_w, shoulder_y + shoulder_h),
        radius=shoulder_h // 2,
        fill=fg,
    )


def get_comment_theme_colors(comment_theme):
    if comment_theme == "dark":
        return {
            "outer_bg": (24, 24, 24),
            "card_fill": (31, 31, 31),
            "card_outline": (60, 60, 60),
            "avatar_bg": (48, 50, 54),
            "avatar_fg": (149, 154, 160),
            "avatar_outline": (78, 82, 88),
            "name_color": (232, 236, 242),
            "text_color": (240, 240, 240),
            "meta_color": (170, 170, 170),
        }
    return {
        "outer_bg": (245, 245, 245),
        "card_fill": (255, 255, 255),
        "card_outline": (225, 225, 225),
        "avatar_bg": (233, 236, 241),
        "avatar_fg": (158, 167, 178),
        "avatar_outline": (210, 216, 224),
        "name_color": (32, 38, 46),
        "text_color": (20, 20, 20),
        "meta_color": (120, 120, 120),
    }


def create_hook_image(path, hook_text, font_path=None):
    w, h = 1000, 260
    img = Image.new("RGB", (w, h), (145, 145, 145))
    draw = ImageDraw.Draw(img)

    font = pick_font(font_path, 64)
    lines = wrap_text(draw, hook_text, font, w - 90)
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append((bbox[3] - bbox[1]) + 10)
    total_h = sum(line_heights)

    y = (h - total_h) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (w - line_w) // 2
        draw.text((x, y), line, font=font, fill=(0, 0, 0))
        y += line_heights[i]

    img.save(path)


def create_comment_image(path, text, replying_to="@username", font_path=None, comment_theme="light"):
    w, h = 1000, 250
    theme = get_comment_theme_colors(comment_theme)
    img = Image.new("RGB", (w, h), theme["outer_bg"])
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=24,
        fill=theme["card_fill"],
        outline=theme["card_outline"],
        width=2,
    )
    draw_anonymous_avatar(
        draw,
        x=30,
        y=35,
        size=88,
        bg=theme["avatar_bg"],
        fg=theme["avatar_fg"],
        outline=theme["avatar_outline"],
    )

    name_font = pick_font(font_path, 36)
    text_font = pick_font(font_path, 50)
    meta_font = pick_font(font_path, 36)

    anon_name = obfuscate_username(replying_to)
    draw.text((150, 28), anon_name, font=name_font, fill=theme["name_color"])

    lines = wrap_text(draw, text, text_font, w - 180)
    lines = lines[:2]

    y = 74
    for line in lines:
        draw.text((150, y), line, font=text_font, fill=theme["text_color"])
        y += 60

    draw.text((150, h - 62), "Replying to @******", font=meta_font, fill=theme["meta_color"])
    img.save(path)


def extract_freeze_frame(video_path, output_image, freeze_time):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(freeze_time),
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(output_image),
    ]
    run_cmd(cmd)


def build_effect_filter(style_filter, mirror):
    filters = []
    if mirror:
        filters.append("hflip")

    if style_filter == "cinematic":
        filters.extend(
            [
                "eq=contrast=1.12:brightness=-0.03:saturation=1.10",
                "colorbalance=rs=0.02:gs=0.01:bs=-0.01",
                "unsharp=5:5:0.7:5:5:0.0",
            ]
        )
    elif style_filter == "vivid":
        filters.extend(
            [
                "eq=contrast=1.10:brightness=0.01:saturation=1.30",
                "unsharp=5:5:0.8:5:5:0.0",
            ]
        )
    elif style_filter == "cool":
        filters.extend(
            [
                "eq=contrast=1.06:saturation=1.08",
                "colorbalance=bs=0.03:gs=0.01:rs=-0.01",
            ]
        )
    elif style_filter == "warm":
        filters.extend(
            [
                "eq=contrast=1.06:saturation=1.12",
                "colorbalance=rs=0.03:gs=0.01:bs=-0.02",
            ]
        )

    return ",".join(filters) if filters else "null"


def get_layout_preset(layout_preset):
    presets = {
        "compact": {
            "live_w": 520,
            "live_h": 860,
            "top_y": 70,
            "left_x": 20,
            "right_x": 540,
            "hook_gap": 18,
            "comment_gap_1": 24,
            "comment_gap_2": 16,
        },
        "balanced": {
            "live_w": 540,
            "live_h": 960,
            "top_y": 80,
            "left_x": 20,
            "right_x": 520,
            "hook_gap": 20,
            "comment_gap_1": 30,
            "comment_gap_2": 20,
        },
        "cinema": {
            "live_w": 550,
            "live_h": 1020,
            "top_y": 52,
            "left_x": 10,
            "right_x": 520,
            "hook_gap": 14,
            "comment_gap_1": 18,
            "comment_gap_2": 14,
        },
    }
    return presets[layout_preset]


def render_video(
    input_video,
    output_video,
    freeze_img,
    hook_img,
    comment1_img,
    comment2_img,
    crf,
    preset,
    style_filter,
    mirror_mode,
    layout_preset,
):
    layout = get_layout_preset(layout_preset)
    live_w = layout["live_w"]
    live_h = layout["live_h"]
    top_y = layout["top_y"]
    left_x = layout["left_x"]
    right_x = layout["right_x"]
    hook_y = top_y + live_h + layout["hook_gap"]
    comment1_y = hook_y + 260 + layout["comment_gap_1"]
    comment2_y = comment1_y + 250 + layout["comment_gap_2"]
    live_effect = build_effect_filter(style_filter, mirror_mode in {"live", "both"})
    freeze_effect = build_effect_filter(style_filter, mirror_mode == "both")

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=20:8[bg];"
        f"[0:v]{live_effect},scale={live_w}:{live_h}:force_original_aspect_ratio=increase,crop={live_w}:{live_h}[live];"
        f"[1:v]{freeze_effect},scale={live_w}:{live_h}:force_original_aspect_ratio=increase,crop={live_w}:{live_h}[freeze];"
        f"[bg][live]overlay={left_x}:{top_y}[v1];"
        f"[v1][freeze]overlay={right_x}:{top_y}[v2];"
        f"[v2][2:v]overlay=40:{hook_y}[v3];"
        f"[v3][3:v]overlay=40:{comment1_y}[v4];"
        f"[v4][4:v]overlay=40:{comment2_y},format=yuv420p[outv]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-loop",
        "1",
        "-i",
        str(freeze_img),
        "-loop",
        "1",
        "-i",
        str(hook_img),
        "-loop",
        "1",
        "-i",
        str(comment1_img),
        "-loop",
        "1",
        "-i",
        str(comment2_img),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-shortest",
        str(output_video),
    ]
    run_cmd(cmd)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate shorts layout: blur background, live/freeze panel, hook text, and two comment boxes."
    )
    parser.add_argument("--input", required=True, help="Path video input")
    parser.add_argument("--output", required=True, help="Path video output")
    parser.add_argument("--hook", required=True, help="Teks hook di panel tengah")
    parser.add_argument("--comment1", required=True, help="Teks komentar box pertama")
    parser.add_argument("--comment2", required=True, help="Teks komentar box kedua")
    parser.add_argument("--replying-to", default="@market2143", help="Handle untuk teks Replying to")
    parser.add_argument("--freeze-time", type=float, default=0.30, help="Detik untuk ambil freeze frame")
    parser.add_argument("--font", default=None, help="Path font .ttf opsional")
    parser.add_argument("--crf", type=int, default=20, help="Kualitas x264 (lebih kecil = lebih bagus)")
    parser.add_argument("--preset", default="medium", help="x264 preset: ultrafast..veryslow")
    parser.add_argument(
        "--style-filter",
        default="cinematic",
        choices=["none", "cinematic", "vivid", "cool", "warm"],
        help="Filter warna untuk panel video",
    )
    parser.add_argument(
        "--mirror-mode",
        default="live",
        choices=["none", "live", "both"],
        help="Mode mirror horizontal",
    )
    parser.add_argument(
        "--comment-theme",
        default="light",
        choices=["light", "dark"],
        help="Tema kotak komentar",
    )
    parser.add_argument(
        "--layout-preset",
        default="balanced",
        choices=["compact", "balanced", "cinema"],
        help="Preset ukuran dan jarak layout panel",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_tools()

    input_video = Path(args.input)
    output_video = Path(args.output)

    if not input_video.exists():
        raise FileNotFoundError(f"Input video tidak ditemukan: {input_video}")

    duration = probe_duration(input_video)
    if args.freeze_time < 0 or args.freeze_time > max(0.0, duration - 0.05):
        raise ValueError(f"freeze-time harus di antara 0 dan {max(0.0, duration - 0.05):.2f} detik")

    with tempfile.TemporaryDirectory(prefix="shorts_layout_") as td:
        td_path = Path(td)
        freeze_img = td_path / "freeze.jpg"
        hook_img = td_path / "hook.png"
        comment1_img = td_path / "comment1.png"
        comment2_img = td_path / "comment2.png"

        extract_freeze_frame(input_video, freeze_img, args.freeze_time)
        create_hook_image(hook_img, args.hook, font_path=args.font)
        create_comment_image(
            comment1_img,
            args.comment1,
            replying_to=args.replying_to,
            font_path=args.font,
            comment_theme=args.comment_theme,
        )
        create_comment_image(
            comment2_img,
            args.comment2,
            replying_to=args.replying_to,
            font_path=args.font,
            comment_theme=args.comment_theme,
        )

        render_video(
            input_video=input_video,
            output_video=output_video,
            freeze_img=freeze_img,
            hook_img=hook_img,
            comment1_img=comment1_img,
            comment2_img=comment2_img,
            crf=args.crf,
            preset=args.preset,
            style_filter=args.style_filter,
            mirror_mode=args.mirror_mode,
            layout_preset=args.layout_preset,
        )

    print(f"Selesai. Output: {output_video}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
