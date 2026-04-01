from __future__ import annotations

import shutil
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
	path = Path(path)
	path.mkdir(parents=True, exist_ok=True)
	return path


def clean_temp_dir(temp_dir: str | Path) -> None:
	temp_dir = Path(temp_dir)
	if not temp_dir.exists():
		return

	for child in temp_dir.iterdir():
		if child.name == ".gitkeep":
			continue
		if child.is_dir():
			shutil.rmtree(child, ignore_errors=True)
		else:
			child.unlink(missing_ok=True)

