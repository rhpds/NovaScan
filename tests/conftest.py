import pytest
import sys
from pathlib import Path


@pytest.fixture(autouse=True)
def _add_src_to_path():
    src = str(Path(__file__).parent.parent / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


@pytest.fixture
def project_root():
    return Path(__file__).parent.parent


@pytest.fixture
def src_root(project_root):
    return project_root / "src"
