import colorsys
import hashlib
import os
import uuid
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageSequence

# Shiny artwork settings
HOLO_ALPHA = 35
BORDER_RATIO = 0.012
MAX_DIMENSION = 512
ANIMATION_FRAMES = 16
FRAME_DURATION_MS = 220  # 16 x 220ms = a 3.52-second loop

CACHE_DIR = Path(__file__).resolve().parent.parent / 'files' / 'cache' / 'shiny'
CACHE_VERSION = 'holo-border-v2'


def _color(hue):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.85, 1.0)
    return (round(r * 255), round(g * 255), round(b * 255))


def _holographic_base(frame):
    image = frame.copy().convert('RGBA')
    width, height = image.size
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Same subtle left-to-right holographic gradient as the static version.
    for x in range(width):
        r, g, b = colorsys.hsv_to_rgb(x / max(1, width - 1), 0.75, 1.0)
        draw.line((x, 0, x, height - 1), fill=(round(r * 255), round(g * 255), round(b * 255), HOLO_ALPHA))

    return Image.alpha_composite(image, overlay).convert('RGB')


def _rainbow_border(base, phase):
    image = base.copy()
    draw = ImageDraw.Draw(image)
    width, height = image.size
    thickness = max(4, round(min(width, height) * BORDER_RATIO))
    thickness = min(thickness, width, height)

    # Move a single continuous rainbow around the perimeter.
    perimeter = 2 * (width + height)
    for x in range(width):
        top = (x / perimeter + phase) % 1.0
        bottom = ((width + height + (width - x)) / perimeter + phase) % 1.0
        draw.line((x, 0, x, thickness - 1), fill=_color(top))
        draw.line((x, height - thickness, x, height - 1), fill=_color(bottom))
    for y in range(height):
        right = ((width + y) / perimeter + phase) % 1.0
        left = ((2 * width + height + (height - y)) / perimeter + phase) % 1.0
        draw.line((width - thickness, y, width - 1, y), fill=_color(right))
        draw.line((0, y, thickness - 1, y), fill=_color(left))
    return image


def _load_source_frames(image_path):
    frames = []
    durations = []
    with Image.open(image_path) as source:
        for frame in ImageSequence.Iterator(source):
            image = frame.convert('RGBA')
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            frames.append(_holographic_base(image))
            durations.append(max(20, int(frame.info.get('duration') or 100)))
            # Avoid expanding huge source GIFs into hundreds of images in memory.
            if len(frames) >= 80:
                break
    if not frames:
        raise ValueError(f'No frames found in {image_path}')
    return frames, durations


def _render_shiny(image_path, destination):
    source_frames, durations = _load_source_frames(image_path)
    total_source_ms = sum(durations)
    result_frames = []

    for i in range(ANIMATION_FRAMES):
        if len(source_frames) == 1:
            source_index = 0
        else:
            # Sample the original animation while the border completes one loop.
            timestamp = (i * FRAME_DURATION_MS) % total_source_ms
            source_index = 0
            elapsed = durations[0]
            while source_index < len(durations) - 1 and timestamp >= elapsed:
                source_index += 1
                elapsed += durations[source_index]

        frame = _rainbow_border(source_frames[source_index], i / ANIMATION_FRAMES)
        # GIF's limited palette can slightly soften rainbow colours.
        result_frames.append(frame.quantize(colors=256, method=Image.Quantize.FASTOCTREE))

    # A unique temporary name avoids two simultaneous requests corrupting the cache.
    temporary = destination.with_name(f'{destination.stem}-{uuid.uuid4().hex}.tmp.gif')
    try:
        result_frames[0].save(
            temporary,
            save_all=True,
            append_images=result_frames[1:],
            duration=FRAME_DURATION_MS,
            loop=0,
            optimize=False,
            disposal=2,
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def get_card_file(image_path, shiny):
    image_path = Path(image_path)
    if not shiny:
        return discord.File(image_path, filename=image_path.name)

    stat = image_path.stat()
    signature = (
        f'{image_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}|'
        f'{CACHE_VERSION}|{HOLO_ALPHA}|{BORDER_RATIO}|{MAX_DIMENSION}|'
        f'{ANIMATION_FRAMES}|{FRAME_DURATION_MS}'
    )
    cache_key = hashlib.sha256(signature.encode('utf-8')).hexdigest()[:16]
    filename = f'{image_path.stem}_{cache_key}_shiny.gif'
    cached_path = CACHE_DIR / filename

    if not cached_path.is_file():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _render_shiny(image_path, cached_path)

    return discord.File(cached_path, filename=filename)
