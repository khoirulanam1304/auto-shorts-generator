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


def create_context_image(path, context_text, font_path=None):
    w, h = 1000, 120
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if context_text.strip():
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=20, fill=(20, 20, 20, 175))
        font = pick_font(font_path, 42)
        lines = wrap_text(draw, context_text, font, w - 70)[:2]
        y = 18
        for line in lines:
            draw.text((35, y), line, font=font, fill=(245, 245, 245, 255))
            y += 44
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


def get_motion_profile(motion_level):
    if motion_level == "dynamic":
        return {
            "live_pad_w": 54,
            "live_pad_h": 58,
            "live_amp_x": 18,
            "live_amp_y": 14,
            "live_freq_x": 1.05,
            "live_freq_y": 0.88,
            "freeze_pad_w": 42,
            "freeze_pad_h": 48,
            "freeze_amp_x": 10,
            "freeze_amp_y": 8,
            "freeze_freq_x": 0.62,
            "freeze_freq_y": 0.50,
        }
    if motion_level == "subtle":
        return {
            "live_pad_w": 32,
            "live_pad_h": 36,
            "live_amp_x": 10,
            "live_amp_y": 7,
            "live_freq_x": 0.90,
            "live_freq_y": 0.72,
            "freeze_pad_w": 26,
            "freeze_pad_h": 30,
            "freeze_amp_x": 5,
            "freeze_amp_y": 4,
            "freeze_freq_x": 0.48,
            "freeze_freq_y": 0.40,
        }
    return None


def build_slide_x_expr(final_x, start_t, duration, start_from_left=True):
    offscreen_x = -1200 if start_from_left else 1300
    end_t = start_t + duration
    return (
        f"if(lt(t,{start_t:.3f}),{offscreen_x},"
        f"if(lt(t,{end_t:.3f}),{offscreen_x}+({final_x}-({offscreen_x}))*(t-{start_t:.3f})/{duration:.3f},{final_x}))"
    )


def get_structure_timeline(content_structure, output_duration):
    if content_structure != "meaningful":
        return {
            "hook_end": output_duration,
            "context_start": 0.0,
            "comment1_start": 0.0,
            "comment2_start": 0.0,
            "focus_start": 0.0,
            "focus_end": 0.0,
            "replay_start": 0.0,
            "replay_end": 0.0,
        }

    hook_end = min(2.8, output_duration)
    focus_start = min(6.0, output_duration)
    focus_end = min(9.0, output_duration)
    replay_start = min(9.0, output_duration)
    replay_end = output_duration
    return {
        "hook_end": hook_end,
        "context_start": min(1.0, output_duration),
        "comment1_start": min(2.2, output_duration),
        "comment2_start": min(2.8, output_duration),
        "focus_start": focus_start,
        "focus_end": focus_end,
        "replay_start": replay_start,
        "replay_end": replay_end,
    }


def render_video(
    input_video,
    output_video,
    freeze_img,
    hook_img,
    context_img,
    comment1_img,
    comment2_img,
    crf,
    preset,
    style_filter,
    mirror_mode,
    layout_preset,
    motion_level,
    entry_animation,
    anim_start,
    anim_step,
    anim_duration,
    content_structure,
    output_duration,
):
    layout = get_layout_preset(layout_preset)
    live_w = layout["live_w"]
    live_h = layout["live_h"]
    top_y = layout["top_y"]
    left_x = layout["left_x"]
    right_x = layout["right_x"]
    hook_y = top_y + live_h + layout["hook_gap"]
    context_y = hook_y + 270
    comment1_y = hook_y + 260 + layout["comment_gap_1"]
    comment2_y = comment1_y + 250 + layout["comment_gap_2"]
    live_effect = build_effect_filter(style_filter, mirror_mode in {"live", "both"})
    freeze_effect = build_effect_filter(style_filter, mirror_mode == "both")
    motion = get_motion_profile(motion_level)
    timeline = get_structure_timeline(content_structure, output_duration)
    if content_structure == "meaningful":
        # Place context above hook so it stays readable and does not collide with comment cards.
        context_y = max(40, hook_y - 130)

    if content_structure == "meaningful":
        # Avoid comma-heavy ffmpeg expressions (if/between) to keep filter parsing stable on Windows shells.
        focus_gate = f"(gte(t\\,{timeline['focus_start']:.3f})*lt(t\\,{timeline['focus_end']:.3f}))"
        replay_gate = f"(gte(t\\,{timeline['replay_start']:.3f})*lt(t\\,{timeline['replay_end']:.3f}))"
        zoom_expr = f"(1+0.10*{focus_gate}+0.05*{replay_gate})"
        live_effect = f"{live_effect},scale=iw*({zoom_expr}):ih*({zoom_expr}):eval=frame"

    if motion:
        live_scale_w = live_w + motion["live_pad_w"]
        live_scale_h = live_h + motion["live_pad_h"]
        live_panel = (
            f"[0:v]{live_effect},"
            f"scale={live_scale_w}:{live_scale_h}:force_original_aspect_ratio=increase,"
            f"crop={live_w}:{live_h}:x='(in_w-out_w)/2+{motion['live_amp_x']}*sin(t*{motion['live_freq_x']})':"
            f"y='(in_h-out_h)/2+{motion['live_amp_y']}*sin(t*{motion['live_freq_y']})'[live];"
        )

        freeze_scale_w = live_w + motion["freeze_pad_w"]
        freeze_scale_h = live_h + motion["freeze_pad_h"]
        freeze_panel = (
            f"[1:v]{freeze_effect},"
            f"scale={freeze_scale_w}:{freeze_scale_h}:force_original_aspect_ratio=increase,"
            f"crop={live_w}:{live_h}:x='(in_w-out_w)/2+{motion['freeze_amp_x']}*sin(t*{motion['freeze_freq_x']})':"
            f"y='(in_h-out_h)/2+{motion['freeze_amp_y']}*sin(t*{motion['freeze_freq_y']})'[freeze];"
        )
    else:
        live_panel = (
            f"[0:v]{live_effect},scale={live_w}:{live_h}:force_original_aspect_ratio=increase,"
            f"crop={live_w}:{live_h}[live];"
        )
        freeze_panel = (
            f"[1:v]{freeze_effect},scale={live_w}:{live_h}:force_original_aspect_ratio=increase,"
            f"crop={live_w}:{live_h}[freeze];"
        )

    hook_enable = "between(t,0,{:.3f})".format(timeline["hook_end"]) if content_structure == "meaningful" else "1"
    context_enable = (
        "between(t,{:.3f},{:.3f})".format(timeline["context_start"], output_duration)
        if content_structure == "meaningful"
        else "1"
    )
    comment1_enable = (
        "gte(t,{:.3f})".format(timeline["comment1_start"]) if content_structure == "meaningful" else "1"
    )
    comment2_enable = (
        "gte(t,{:.3f})".format(timeline["comment2_start"]) if content_structure == "meaningful" else "1"
    )

    if entry_animation == "slide":
        hook_x_expr = build_slide_x_expr(40, anim_start, anim_duration, start_from_left=True)
        c1_x_expr = build_slide_x_expr(40, anim_start + anim_step, anim_duration, start_from_left=False)
        c2_x_expr = build_slide_x_expr(40, anim_start + (anim_step * 2), anim_duration, start_from_left=True)
        hook_overlay = f"[v2][2:v]overlay=x='{hook_x_expr}':y={hook_y}:enable='{hook_enable}'[v3];"
        context_overlay = (
            f"[v3][3:v]overlay=40:{context_y}:enable='{context_enable}'[v35];"
            if content_structure == "meaningful"
            else "[v3][3:v]overlay=40:{0}[v35];".format(context_y)
        )
        comment1_overlay = f"[v35][4:v]overlay=x='{c1_x_expr}':y={comment1_y}:enable='{comment1_enable}'[v4];"
        comment2_overlay = (
            f"[v4][5:v]overlay=x='{c2_x_expr}':y={comment2_y}:enable='{comment2_enable}',format=yuv420p[outv]"
        )
    else:
        hook_overlay = f"[v2][2:v]overlay=40:{hook_y}:enable='{hook_enable}'[v3];"
        context_overlay = (
            f"[v3][3:v]overlay=40:{context_y}:enable='{context_enable}'[v35];"
            if content_structure == "meaningful"
            else "[v3][3:v]overlay=40:{0}[v35];".format(context_y)
        )
        comment1_overlay = f"[v35][4:v]overlay=40:{comment1_y}:enable='{comment1_enable}'[v4];"
        comment2_overlay = f"[v4][5:v]overlay=40:{comment2_y}:enable='{comment2_enable}',format=yuv420p[outv]"

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        + "crop=1080:1920,boxblur=20:8[bg];"
        + live_panel
        + freeze_panel
        + f"[bg][live]overlay={left_x}:{top_y}[v1];"
        + f"[v1][freeze]overlay={right_x}:{top_y}[v2];"
        + hook_overlay
        + context_overlay
        + comment1_overlay
        + comment2_overlay
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
        str(context_img),
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
        "-t",
        f"{output_duration:.3f}",
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
    parser.add_argument("--context-text", default="", help="Teks konteks singkat agar konten lebih meaningful")
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
    parser.add_argument(
        "--motion-level",
        default="subtle",
        choices=["none", "subtle", "dynamic"],
        help="Intensitas gerak panel live/freeze",
    )
    parser.add_argument(
        "--entry-animation",
        default="slide",
        choices=["none", "slide"],
        help="Animasi masuk untuk hook dan komentar",
    )
    parser.add_argument(
        "--anim-start",
        type=float,
        default=0.15,
        help="Detik mulai animasi panel teks",
    )
    parser.add_argument(
        "--anim-step",
        type=float,
        default=0.28,
        help="Jarak waktu antar animasi hook/komentar",
    )
    parser.add_argument(
        "--anim-duration",
        type=float,
        default=0.34,
        help="Durasi tiap animasi masuk",
    )
    parser.add_argument(
        "--content-structure",
        default="basic",
        choices=["basic", "meaningful"],
        help="Mode alur konten: basic atau meaningful",
    )
    parser.add_argument(
        "--target-duration",
        type=float,
        default=None,
        help="Durasi output target (detik). Default: full source untuk basic, 12 detik untuk meaningful",
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
    if args.anim_start < 0:
        raise ValueError("anim-start tidak boleh negatif")
    if args.anim_step < 0:
        raise ValueError("anim-step tidak boleh negatif")
    if args.anim_duration <= 0:
        raise ValueError("anim-duration harus lebih dari 0")
    if args.target_duration is not None and args.target_duration <= 0:
        raise ValueError("target-duration harus lebih dari 0 jika diisi")

    if args.target_duration is None:
        output_duration = min(duration, 12.0) if args.content_structure == "meaningful" else duration
    else:
        output_duration = min(duration, args.target_duration)

    with tempfile.TemporaryDirectory(prefix="shorts_layout_") as td:
        td_path = Path(td)
        freeze_img = td_path / "freeze.jpg"
        hook_img = td_path / "hook.png"
        context_img = td_path / "context.png"
        comment1_img = td_path / "comment1.png"
        comment2_img = td_path / "comment2.png"

        extract_freeze_frame(input_video, freeze_img, args.freeze_time)
        create_hook_image(hook_img, args.hook, font_path=args.font)
        create_context_image(context_img, args.context_text, font_path=args.font)
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
            context_img=context_img,
            comment1_img=comment1_img,
            comment2_img=comment2_img,
            crf=args.crf,
            preset=args.preset,
            style_filter=args.style_filter,
            mirror_mode=args.mirror_mode,
            layout_preset=args.layout_preset,
            motion_level=args.motion_level,
            entry_animation=args.entry_animation,
            anim_start=args.anim_start,
            anim_step=args.anim_step,
            anim_duration=args.anim_duration,
            content_structure=args.content_structure,
            output_duration=output_duration,
        )

    print(f"Selesai. Output: {output_video}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
