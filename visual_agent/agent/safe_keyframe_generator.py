import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STORYBOARD = BASE_DIR / "outputs" / "keyframes" / "storyboard.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "keyframes" / "safe_images"
DEFAULT_SAFE_STORYBOARD = BASE_DIR / "outputs" / "keyframes" / "storyboard_safe.json"
DEFAULT_PRODUCT_DIR = BASE_DIR / "assets" / "product_images"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def palette(index: int) -> Tuple[str, str, str]:
    themes = [
        ("#efe9df", "#d8c8b5", "#1f7acb"),
        ("#edf2ee", "#c7d8cf", "#2b8a5f"),
        ("#f1ece6", "#d7c4a8", "#b95d3b"),
        ("#eaf0f6", "#c7d3df", "#4f6ea9"),
    ]
    return themes[index % len(themes)]


def product_images(product_dir: Path) -> List[Path]:
    paths: List[Path] = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        paths.extend(sorted(product_dir.glob(ext)))
    return paths


def trim_white_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    xs: List[int] = []
    ys: List[int] = []
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0 and not (r > 242 and g > 242 and b > 242):
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return rgba
    cropped = rgba.crop((max(0, min(xs) - 8), max(0, min(ys) - 8), min(width, max(xs) + 9), min(height, max(ys) + 9)))
    pixels = cropped.load()
    for y in range(cropped.height):
        for x in range(cropped.width):
            r, g, b, a = pixels[x, y]
            if r > 245 and g > 245 and b > 245:
                pixels[x, y] = (255, 255, 255, 0)
            elif r > 232 and g > 232 and b > 232:
                pixels[x, y] = (r, g, b, int(a * 0.35))
    return cropped


def paste_product(canvas: Image.Image, product_path: Path, box: Tuple[int, int, int, int]) -> None:
    product = trim_white_background(Image.open(product_path))
    max_w = box[2] - box[0]
    max_h = box[3] - box[1]
    scale = min(max_w / product.width, max_h / product.height)
    size = (max(1, int(product.width * scale)), max(1, int(product.height * scale)))
    product = product.resize(size, Image.Resampling.LANCZOS)
    x = box[0] + (max_w - product.width) // 2
    y = box[1] + (max_h - product.height) // 2
    shadow = Image.new("RGBA", product.size, (0, 0, 0, 0))
    alpha = product.getchannel("A").filter(ImageFilter.GaussianBlur(8))
    shadow.putalpha(alpha.point(lambda value: int(value * 0.22)))
    canvas.alpha_composite(shadow, (x + 8, y + 10))
    canvas.alpha_composite(product, (x, y))


def round_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill: str, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_tv(draw: ImageDraw.ImageDraw, index: int) -> None:
    round_rect(draw, [78, 108, 642, 476], 24, "#191a1e")
    round_rect(draw, [98, 128, 622, 438], 18, "#26333f")
    accent = palette(index)[2]
    draw.rectangle([120, 152, 600, 206], fill=accent)

    if index % 4 == 0:
        draw.rectangle([126, 222, 594, 395], fill="#151719")
        draw.rectangle([126, 310, 594, 395], fill="#31424f")
    elif index % 4 == 1:
        for row in range(2):
            for col in range(3):
                x0 = 130 + col * 150
                y0 = 232 + row * 82
                round_rect(draw, [x0, y0, x0 + 126, y0 + 54], 12, "#f7fbff")
                draw.rectangle([x0 + 14, y0 + 16, x0 + 94, y0 + 28], fill="#6d7d8d")
    elif index % 4 == 2:
        round_rect(draw, [132, 230, 310, 330], 18, "#f7fbff")
        round_rect(draw, [330, 230, 508, 330], 18, "#f7fbff")
        round_rect(draw, [132, 354, 560, 404], 16, "#ffcf5a")
    else:
        draw.rectangle([130, 230, 590, 392], fill="#233642")
        for x in [160, 270, 380, 490]:
            draw.ellipse([x, 272, x + 46, 318], fill="#f0c04f")


def draw_console(draw: ImageDraw.ImageDraw, index: int, canvas: Image.Image, products: List[Path]) -> None:
    round_rect(draw, [95, 820, 625, 1015], 22, "#c6b49f")
    if products:
        preferred = [7, 3, 5, 6, 2, 4, 1, 0]
        product_path = products[preferred[index % len(preferred)] % len(products)]
        paste_product(canvas, product_path, (145, 690, 575, 875))
    else:
        round_rect(draw, [212, 745, 508, 862], 26, "#202226")
        round_rect(draw, [242, 776, 478, 820], 13, palette(index)[2])
        draw.ellipse([456, 788, 476, 808], fill="#78e08f")

    draw.line([508, 805, 570, 805, 570, 506, 610, 506], fill="#111318", width=12)
    draw.line([508, 805, 570, 805, 570, 506, 610, 506], fill="#34383d", width=6)
    round_rect(draw, [594, 488, 644, 526], 6, "#2e3036")

    round_rect(draw, [136, 910, 264, 936], 13, "#24262b")
    draw.ellipse([252, 892, 318, 958], fill="#1b1d22")
    draw.ellipse([262, 902, 308, 948], fill="#464b55")
    round_rect(draw, [430, 910, 552, 936], 13, "#24262b")
    draw.ellipse([374, 892, 440, 958], fill="#1b1d22")
    draw.ellipse([384, 902, 430, 948], fill="#464b55")
    round_rect(draw, [322, 890, 398, 980], 18, "#15171a")
    for yy in [912, 936, 960]:
        draw.ellipse([350, yy, 370, yy + 20], fill="#50565f")


def draw_hands(draw: ImageDraw.ImageDraw, index: int) -> None:
    skin = "#d6a275"
    if index % 3 == 0:
        round_rect(draw, [58, 664, 225, 735], 34, skin)
        round_rect(draw, [35, 690, 156, 772], 38, skin)
        round_rect(draw, [185, 672, 265, 704], 16, skin)
        round_rect(draw, [256, 666, 330, 718], 12, "#202226")
    elif index % 3 == 1:
        round_rect(draw, [500, 640, 690, 710], 34, skin)
        round_rect(draw, [565, 672, 705, 755], 38, skin)
        round_rect(draw, [440, 652, 532, 708], 12, "#202226")
    else:
        round_rect(draw, [120, 654, 300, 730], 34, skin)
        round_rect(draw, [420, 654, 600, 730], 34, skin)
        round_rect(draw, [306, 650, 414, 718], 14, "#15171a")


def draw_safe_keyframe(shot: Dict[str, Any], index: int, output_path: Path, products: List[Path]) -> None:
    wall, floor, _ = palette(index)
    width, height = 720, 1280
    image = Image.new("RGBA", (width, height), wall)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 760, width, height], fill=floor)
    for y in range(760, height):
        shade = max(170, 215 - int((y - 760) * 0.045))
        draw.line([(0, y), (width, y)], fill=(shade, max(150, shade - 16), max(130, shade - 34)))

    draw_tv(draw, index)
    draw_console(draw, index, image, products)
    draw_hands(draw, index)

    # No faces or identifiable people: only hands and products are drawn.
    image = image.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def build_safe_storyboard(storyboard: Dict[str, Any]) -> Dict[str, Any]:
    safe = json.loads(json.dumps(storyboard, ensure_ascii=False))
    style = safe.setdefault("style_guide", {})
    style["safety"] = "Keyframes contain no visible faces and no identifiable real people; hands, products, TV UI, and living-room environment only."
    for shot in safe.get("storyboard", []):
        shot["keyframe_safety"] = "no visible face, no identifiable person, hands/products/TV only"
        shot["subtitle"] = ""
        shot["camera"] = f"{shot.get('camera', '')}; no face in first frame, hands only".strip("; ")
        shot["motion"] = f"{shot.get('motion', '')}; AI actors may enter after first frame as fictional ad characters".strip("; ")
    return safe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate no-face safe keyframes for Seedance input-image review.")
    parser.add_argument("--storyboard", default=str(DEFAULT_STORYBOARD), help="Input storyboard JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for safe Sxx.png keyframes.")
    parser.add_argument("--safe-storyboard", default=str(DEFAULT_SAFE_STORYBOARD), help="Output storyboard with safety notes.")
    parser.add_argument("--product-dir", default=str(DEFAULT_PRODUCT_DIR), help="Directory containing K7 product images.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    storyboard = read_json(Path(args.storyboard))
    output_dir = Path(args.output_dir)
    products = product_images(Path(args.product_dir))
    for index, shot in enumerate(storyboard.get("storyboard", [])):
        shot_id = str(shot.get("shot_id") or f"S{index + 1:02d}").upper()
        draw_safe_keyframe(shot, index, output_dir / f"{shot_id}.png", products)

    safe_storyboard = build_safe_storyboard(storyboard)
    write_json(Path(args.safe_storyboard), safe_storyboard)
    result = {
        "safe_storyboard": str(Path(args.safe_storyboard)),
        "output_dir": str(output_dir),
        "product_images": [str(path) for path in products],
        "keyframe_count": len(storyboard.get("storyboard", [])),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
