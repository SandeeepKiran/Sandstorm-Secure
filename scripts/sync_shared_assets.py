"""Copy the shared design-system files from the dashboard into demo/ and landing/.

The dashboard folder sandstorm/web/static/ is the master copy. The demo and the
landing page are standalone static sites, so they keep identical copies.
A test (test_shared_assets_are_identical) fails if the copies drift.

Run from the project folder:  python scripts/sync_shared_assets.py
"""

from __future__ import annotations

import pathlib
import shutil

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "sandstorm" / "web" / "static"
TARGET_DIRS = (REPO_ROOT / "demo", REPO_ROOT / "landing")
SHARED_FILES = (
    "style.css",
    "ui.js",
    "vendor/inter-latin-wght-normal.woff2",
    "vendor/LICENSE-inter-OFL.txt",
    "vendor/LICENSE-lucide.txt",
)


def main() -> None:
    for target_dir in TARGET_DIRS:
        for relative in SHARED_FILES:
            destination = target_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_DIR / relative, destination)
        print(f"Synced {len(SHARED_FILES)} files to {target_dir.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
