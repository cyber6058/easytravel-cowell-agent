from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps
import pymupdf

from ..errors import ValidationError


SUPPORTED_IMAGE_SUFFIXES = {
    ".bmp",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
}
SUPPORTED_LAYOUTS = {"auto", "single", "2x2", "2x1", "1x2"}
SUPPORTED_ROTATIONS = {"auto", "0", "90", "180", "270"}


@dataclass(frozen=True, slots=True)
class PassportImageArtifact:
    record_id: str
    page_number: int
    crop_number: int
    path: Path
    sha256: str
    width: int
    height: int
    rotation_degrees: int
    crop_box: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class PassportImagePreparation:
    source_path: Path
    source_sha256: str
    output_dir: Path
    page_count: int
    passport_count: int
    artifacts: tuple[PassportImageArtifact, ...]
    warnings: tuple[str, ...]


def prepare_passport_images(
    source_path: Path,
    output_dir: Path,
    *,
    layout: str = "auto",
    rotation: str = "auto",
) -> PassportImagePreparation:
    source = source_path.expanduser().resolve()
    target = output_dir.expanduser().resolve()
    if not source.exists():
        raise ValidationError("Passport source does not exist", {"path": str(source)})
    if layout not in SUPPORTED_LAYOUTS:
        raise ValidationError("Unsupported passport page layout", {"layout": layout})
    if rotation not in SUPPORTED_ROTATIONS:
        raise ValidationError("Unsupported passport rotation", {"rotation": rotation})
    if target.exists() and any(target.iterdir()):
        raise ValidationError(
            "Passport output directory must be new or empty",
            {"path": str(target)},
        )
    target.mkdir(parents=True, exist_ok=True)

    pages = tuple(_source_pages(source))
    artifacts: list[PassportImageArtifact] = []
    warnings: list[str] = []
    for page_number, page_image in enumerate(pages, 1):
        regions, detected_layout = _page_regions(page_image, layout)
        if layout == "auto" and detected_layout == "single":
            warnings.append(
                f"page {page_number}: kept as one image; visually verify crop and orientation"
            )
        for crop_number, box in enumerate(regions, 1):
            crop = page_image.crop(box)
            degrees = _rotation_for_crop(
                crop,
                rotation=rotation,
                detected_layout=detected_layout,
            )
            if degrees:
                crop = crop.rotate(degrees, expand=True)
            record_id = f"P{page_number:03d}-{crop_number:02d}"
            path = target / f"{record_id}.jpg"
            crop.save(path, "JPEG", quality=94, optimize=True, subsampling=0)
            artifacts.append(
                PassportImageArtifact(
                    record_id=record_id,
                    page_number=page_number,
                    crop_number=crop_number,
                    path=path,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    width=crop.width,
                    height=crop.height,
                    rotation_degrees=degrees % 360,
                    crop_box=box,
                )
            )

    if not artifacts:
        raise ValidationError("No passport images were found in the source")
    source_hash = (
        hashlib.sha256(source.read_bytes()).hexdigest()
        if source.is_file()
        else _directory_hash(source)
    )
    manifest = {
        "schema_version": 1,
        "type": "passport_image_preparation",
        "source_path": str(source),
        "source_sha256": source_hash,
        "page_count": len(pages),
        "passport_count": len(artifacts),
        "artifacts": [
            {
                **asdict(artifact),
                "path": str(artifact.path),
                "crop_box": list(artifact.crop_box),
            }
            for artifact in artifacts
        ],
        "warnings": warnings,
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return PassportImagePreparation(
        source_path=source,
        source_sha256=source_hash,
        output_dir=target,
        page_count=len(pages),
        passport_count=len(artifacts),
        artifacts=tuple(artifacts),
        warnings=tuple(warnings),
    )


def _source_pages(path: Path) -> Iterable[Image.Image]:
    if path.is_dir():
        images = sorted(
            item
            for item in path.iterdir()
            if item.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        )
        if not images:
            raise ValidationError("Passport image directory contains no supported files")
        for image_path in images:
            with Image.open(image_path) as image:
                yield ImageOps.exif_transpose(image).convert("RGB")
        return
    if path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
        with Image.open(path) as image:
            yield ImageOps.exif_transpose(image).convert("RGB")
        return
    if path.suffix.lower() != ".pdf":
        raise ValidationError(
            "Passport source must be a PDF, supported image, or image directory",
            {"suffix": path.suffix.lower()},
        )
    try:
        document = pymupdf.open(path)
    except Exception as error:
        raise ValidationError("Invalid passport PDF", {"path": str(path)}) from error
    with document:
        for page in document:
            embedded_long_edge = max(
                (max(item[2], item[3]) for item in page.get_images(full=True)),
                default=0,
            )
            target_long_edge = min(max(2600, embedded_long_edge), 5000)
            scale = min(6.0, target_long_edge / max(page.rect.width, page.rect.height))
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            yield Image.frombytes(
                "RGB", (pixmap.width, pixmap.height), pixmap.samples
            )


def _page_regions(
    image: Image.Image, layout: str
) -> tuple[tuple[tuple[int, int, int, int], ...], str]:
    detected = _detect_layout(image) if layout == "auto" else layout
    if detected in {"top-half", "bottom-half"}:
        halves = _grid_boxes(image, rows=2, columns=1)
        return ((halves[0] if detected == "top-half" else halves[1]),), detected
    rows, columns = {
        "single": (1, 1),
        "2x2": (2, 2),
        "2x1": (2, 1),
        "1x2": (1, 2),
    }[detected]
    boxes = _grid_boxes(image, rows=rows, columns=columns)
    if len(boxes) == 1:
        return boxes, detected

    densities = [_ink_density(image.crop(box)) for box in boxes]
    maximum = max(densities, default=0.0)
    kept = tuple(
        box
        for box, density in zip(boxes, densities, strict=True)
        if density >= 0.008 and density >= maximum * 0.22
    )
    return kept or ((0, 0, image.width, image.height),), detected


def _detect_layout(image: Image.Image) -> str:
    gray = _analysis_gray(image)
    x_profile, y_profile = _dark_profiles(gray)
    x_gutter = _gutter_strength(x_profile)
    y_gutter = _gutter_strength(y_profile)
    if x_gutter <= 0.42 and y_gutter <= 0.65:
        return "2x2"
    if y_gutter <= 0.25:
        top_box, bottom_box = _grid_boxes(image, rows=2, columns=1)
        top_density = _ink_density(image.crop(top_box))
        bottom_density = _ink_density(image.crop(bottom_box))
        if bottom_density >= 0.02 and bottom_density >= top_density * 2:
            return "bottom-half"
        if top_density >= 0.02 and top_density >= bottom_density * 2:
            return "top-half"
    return "single"


def _analysis_gray(image: Image.Image) -> Image.Image:
    copy = ImageOps.grayscale(image)
    scale = min(1.0, 420 / max(copy.width, copy.height))
    if scale < 1.0:
        copy = copy.resize(
            (max(1, round(copy.width * scale)), max(1, round(copy.height * scale)))
        )
    return copy


def _dark_profiles(gray: Image.Image) -> tuple[list[float], list[float]]:
    width, height = gray.size
    columns = [0] * width
    rows = [0] * height
    for index, value in enumerate(gray.tobytes()):
        if value < 238:
            x = index % width
            y = index // width
            columns[x] += 1
            rows[y] += 1
    return (
        [value / height for value in columns],
        [value / width for value in rows],
    )


def _gutter_strength(profile: list[float]) -> float:
    length = len(profile)
    window = max(1, round(length * 0.015))
    start = round(length * 0.35)
    end = round(length * 0.65)
    gutter = min(
        sum(profile[max(0, index - window) : min(length, index + window + 1)])
        / (min(length, index + window + 1) - max(0, index - window))
        for index in range(start, end)
    )
    sides = profile[round(length * 0.08) : round(length * 0.32)] + profile[
        round(length * 0.68) : round(length * 0.92)
    ]
    side_mean = sum(sides) / len(sides) if sides else 0.0
    if side_mean <= 0.005:
        return 1.0
    return gutter / side_mean


def _grid_boxes(
    image: Image.Image, *, rows: int, columns: int
) -> tuple[tuple[int, int, int, int], ...]:
    boxes = []
    for row in range(rows):
        top = round(image.height * row / rows)
        bottom = round(image.height * (row + 1) / rows)
        for column in range(columns):
            left = round(image.width * column / columns)
            right = round(image.width * (column + 1) / columns)
            margin_x = max(2, round((right - left) * 0.015))
            margin_y = max(2, round((bottom - top) * 0.015))
            boxes.append(
                (
                    max(0, left + margin_x),
                    max(0, top + margin_y),
                    min(image.width, right - margin_x),
                    min(image.height, bottom - margin_y),
                )
            )
    return tuple(boxes)


def _ink_density(image: Image.Image) -> float:
    gray = _analysis_gray(image)
    pixels = gray.tobytes()
    return sum(value < 238 for value in pixels) / max(1, len(pixels))


def _rotation_for_crop(
    crop: Image.Image,
    *,
    rotation: str,
    detected_layout: str,
) -> int:
    if rotation != "auto":
        return int(rotation)
    if detected_layout != "single" and crop.height > crop.width * 1.12:
        return 90
    return 0


def _directory_hash(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        item
        for item in path.iterdir()
        if item.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )
    for item in files:
        digest.update(item.name.encode("utf-8"))
        digest.update(hashlib.sha256(item.read_bytes()).digest())
    return digest.hexdigest()
