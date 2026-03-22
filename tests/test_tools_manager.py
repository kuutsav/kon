import zipfile
from pathlib import Path

import pytest

from kon.tools_manager import _extract_binary


def test_extract_binary_rejects_zip_path_traversal(tmp_path: Path):
    archive = tmp_path / "malicious.zip"
    dest = tmp_path / "dest"
    dest.mkdir()

    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")

    with pytest.raises(ValueError, match="escapes target directory"):
        _extract_binary(archive, "evil.txt", dest)
