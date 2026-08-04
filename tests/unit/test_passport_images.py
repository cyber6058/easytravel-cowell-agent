from PIL import Image, ImageDraw

from cowell_cli.infrastructure.passport_images import prepare_passport_images


def _passport_page(path):
    image = Image.new("RGB", (1000, 1400), "white")
    draw = ImageDraw.Draw(image)
    for left, top, right, bottom in (
        (40, 40, 460, 650),
        (540, 40, 960, 650),
        (40, 750, 460, 1360),
    ):
        draw.rectangle(
            (left, top, right, bottom), fill="#dddddd", outline="black", width=5
        )
        for y in range(top + 80, bottom - 50, 45):
            draw.line((left + 40, y, right - 40, y), fill="black", width=4)
    image.save(path)


def test_auto_layout_splits_three_occupied_cells_and_rotates_them(tmp_path):
    source = tmp_path / "page.png"
    output = tmp_path / "prepared"
    _passport_page(source)

    result = prepare_passport_images(source, output, layout="auto")

    assert result.page_count == 1
    assert result.passport_count == 3
    assert [artifact.record_id for artifact in result.artifacts] == [
        "P001-01",
        "P001-02",
        "P001-03",
    ]
    assert all(artifact.rotation_degrees == 90 for artifact in result.artifacts)
    assert all(artifact.width > artifact.height for artifact in result.artifacts)
    assert (output / "manifest.json").is_file()


def test_single_layout_preserves_a_full_open_passport_page(tmp_path):
    source = tmp_path / "page.png"
    output = tmp_path / "prepared"
    image = Image.new("RGB", (1000, 1400), "#dddddd")
    image.save(source)

    result = prepare_passport_images(source, output, layout="single")

    assert result.passport_count == 1
    assert result.artifacts[0].rotation_degrees == 0
    assert result.artifacts[0].width == 970
    assert result.artifacts[0].height == 1358


def test_auto_layout_keeps_only_the_dense_half_of_an_open_passport(tmp_path):
    source = tmp_path / "page.png"
    output = tmp_path / "prepared"
    image = Image.new("RGB", (1000, 1400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((25, 735, 975, 1375), fill="#cccccc", outline="black", width=5)
    for y in range(800, 1330, 40):
        draw.line((70, y, 930, y), fill="black", width=4)
    image.save(source)

    result = prepare_passport_images(source, output, layout="auto")

    assert result.passport_count == 1
    assert result.artifacts[0].rotation_degrees == 0
    assert result.artifacts[0].width > result.artifacts[0].height
    assert result.warnings == ()


def test_bmp_photo_source_is_supported(tmp_path):
    source = tmp_path / "passport.bmp"
    output = tmp_path / "prepared"
    Image.new("RGB", (800, 500), "#cccccc").save(source)

    result = prepare_passport_images(source, output, layout="single")

    assert result.passport_count == 1
    assert result.artifacts[0].width > result.artifacts[0].height
