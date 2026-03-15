import pytest

from kon.core.types import ImageContent
from kon.tools.read import ReadParams, ReadTool


@pytest.fixture
def read_tool():
    return ReadTool()


@pytest.fixture
def image_file(tmp_path):
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    f = tmp_path / "test.png"
    img.save(f)
    return f


@pytest.mark.asyncio
async def test_read_image_file_detected(read_tool, image_file):
    result = await read_tool.execute(ReadParams(path=str(image_file)))

    assert result.success
    assert result.result.startswith("Read image file [image/png]")
    assert result.images is not None
    assert len(result.images) == 1
    assert isinstance(result.images[0], ImageContent)
    assert result.images[0].mime_type == "image/png"
    assert len(result.images[0].data) > 0


@pytest.mark.asyncio
async def test_read_image_file_invalid(read_tool, tmp_path):
    invalid_image = tmp_path / "test.png"
    invalid_image.write_text("not an image")

    result = await read_tool.execute(ReadParams(path=str(invalid_image)))

    assert not result.success
    assert "Failed to read image" in result.result
    assert "Failed to read image" in result.display
