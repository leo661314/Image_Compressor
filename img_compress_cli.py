#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import ImageColor
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compress an image to a target max size (KB) with best possible quality (MVP skeleton)."
    )
    parser.add_argument("--input", required=True, help="Input image path (jpg/png).")
    parser.add_argument(
        "--out-fmt",
        required=True,
        choices=["jpg", "webp", "png"],
        help="Output format.",
    )
    parser.add_argument("--target-kb", required=True, type=int, help="Target max size in KB (reserved for later).")
    parser.add_argument("--out-dir", default="./output", help="Output directory.")
    parser.add_argument("--bg", default="#ffffff", help="Background color for PNG->JPG flatten (reserved for later).")

    # Quality bounds (reserved for later)
    parser.add_argument("--q-min", type=int, default=25, help="Min quality for JPG/WebP (reserved for later).")
    parser.add_argument("--q-max", type=int, default=95, help="Max quality for JPG/WebP (reserved for later).")

    return parser.parse_args()

# -------------------------
# A) Input / Args
# -------------------------
def load_image(path: str) -> Image.Image:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {p}")
    # Load into memory to avoid lazy file handle issues
    with Image.open(p) as im:
        return im.copy()

# -------------------------
# B) Normalize
# -------------------------
def normalize_for_output(img:Image.Image, out_fmt:str, bg:str) -> Image.Image:
    """
    Prepare image so it can be saved in out_fmt.
    - JPEG does not support alpha; flatten RGBA/LA/P modes with transparency onto a background.
    """
    if out_fmt == "jpg":
        # If image has alpha, flatten onto background
        has_alpha = (img.mode in ("RGBA", "LA")) or (img.mode == "P" and "transparency" in img.info)
        if has_alpha:
            bg_rgb = ImageColor.getrgb(bg)  # e.g. "#ffffff" -> (255,255,255)
            base = Image.new("RGB", img.size, bg_rgb)

            # Ensure we have RGBA for alpha_composite
            rgba = img.convert("RGBA")
            base_rgba = base.convert("RGBA")
            composed = Image.alpha_composite(base_rgba, rgba)
            return composed.convert("RGB")

        # No alpha: just ensure RGB
        if img.mode != "RGB":
            return img.convert("RGB")

        return img

    # For PNG/WebP, keep as-is (you can extend later)
    return img
# -------------------------
# C) Encode / Size helpers
# -------------------------
def encode_to_bytes(img: Image.Image, out_fmt: str, quality: Optional[int] = None, **extra) -> bytes:
    fmt_map = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}
    pil_fmt = fmt_map[out_fmt]

    params: Dict[str, Any] = {}

    if out_fmt in ("jpg", "webp") and quality is not None:
        params["quality"] = int(quality)

    if out_fmt == "png":
        # Lossless optimization (MVP)
        params["optimize"] = True
        # compress_level: 0 (fastest, biggest) .. 9 (slowest, smallest)
        # Use a sensible default; you can tune later
        params["compress_level"] = 9

    # Allow overriding from caller if needed
    params.update(extra)
    buf = io.BytesIO()
    img.save(buf, format=pil_fmt, **params)
    return buf.getvalue()
def size_kb(data: bytes) -> float:
    return len(data) / 1024.0
def find_best_quality_lossy(img: Image.Image, out_fmt: str, target_kb: int, q_min: int, q_max: int):
    """
    Return: (best_bytes, best_q, iterations, status)
      status: "ok" | "already_ok_at_qmax" | "no_solution_within_bounds"
    """
    def S(q: int) -> tuple[bytes, float]:
        b = encode_to_bytes(img, out_fmt, quality=q)
        return b, size_kb(b)

    # Probe q_max
    b_max, s_max = S(q_max)
    if s_max <= target_kb:
        return b_max, q_max, 1, "already_ok_at_qmax"

    # Probe q_min
    b_min, s_min = S(q_min)
    if s_min > target_kb:
        return b_min, q_min, 2, "no_solution_within_bounds"

    # Binary search for highest feasible q
    lo, hi = q_min, q_max
    best_b, best_q = b_min, q_min
    iterations = 2  # already probed two points

    while lo <= hi:
        mid = (lo + hi) // 2
        b_mid, s_mid = S(mid)
        iterations += 1

        if s_mid <= target_kb:
            best_b, best_q = b_mid, mid
            lo = mid + 1  # try higher quality
        else:
            hi = mid - 1  # too big, lower quality

    return best_b, best_q, iterations, "ok"

# -------------------------
# D) Compression policy dispatcher (MVP)
# -------------------------
def compress(img: Image.Image, args: argparse.Namespace):
    # Dispatch by output format
    if args.out_fmt in ("jpg", "webp"):
        out_bytes, best_q, iters, status = find_best_quality_lossy(
            img=img,
            out_fmt=args.out_fmt,
            target_kb=args.target_kb,
            q_min=args.q_min,
            q_max=args.q_max,
        )
        meta = {
            "status": status,
            "out_fmt": args.out_fmt,
            "quality": best_q,
            "iterations": iters,
            "width": img.width,
            "height": img.height,
            "final_kb": round(size_kb(out_bytes), 2),
            "target_kb": args.target_kb,
            "q_min": args.q_min,
            "q_max": args.q_max,
        }
        return out_bytes, meta

    elif args.out_fmt == "png":
        return compress_png_mvp(img, args.target_kb)
    else:
        raise ValueError(f"Unsupported out_fmt: {args.out_fmt}")

def compress_png_mvp(img: Image.Image, target_kb: int) -> tuple[bytes, dict]:
    out_bytes = encode_to_bytes(img, "png")
    final = round(size_kb(out_bytes), 2)
    status = "ok" if final <= target_kb else "png_over_target"
    meta = {
        "status": status,
        "out_fmt": "png",
        "quality": None,
        "iterations": 0,
        "width": img.width,
        "height": img.height,
        "final_kb": final,
        "target_kb": target_kb,
        "note": "PNG is lossless; MVP only applies lossless optimization.",
    }
    return out_bytes, meta

# -------------------------
# E) Output path + writing
# -------------------------
def build_output_path(args: argparse.Namespace, meta: Dict[str, Any]) -> Path:
    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = in_path.stem
    ext = meta["out_fmt"]  # jpg/webp/png
    filename = f"{stem}_out.{ext}"
    return out_dir / filename
def write_bytes(path: Path, out_bytes: bytes) -> None:
    with open(path, "wb") as f:
        f.write(out_bytes)

# -------------------------
# main
# -------------------------
def main() -> None:
    args = parse_args()
    img = load_image(args.input)
    img = normalize_for_output(img, args.out_fmt, args.bg)
    out_bytes, meta = compress(img, args)
    out_path = build_output_path(args, meta)
    write_bytes(out_path, out_bytes)
    print(f"Output: {out_path}")
    print("Meta:", meta)

if __name__ == "__main__":
    main()