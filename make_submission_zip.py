"""
Automated Package & Hygiene Verification for MechanismTrace-DDI
Module D: Builds a clean submission ZIP file under the 50 MB limit,
excluding git history, virtual environments, caches, and secret keys.
"""
import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Target output zip name
SUBMISSION_ZIP = BASE_DIR / "MechanismTrace_DDI_Submission.zip"

# Directories and files to exclude strictly
EXCLUDED_PATTERNS = {
    ".git", ".gitignore", ".pytest_cache", "__pycache__", ".venv", "venv",
    ".env", ".DS_Store", "test_submission.zip", "MechanismTrace_DDI_Submission.zip"
}

# File extensions to exclude
EXCLUDED_EXTENSIONS = {".pyc", ".pyo", ".pyd"}


def should_include_file(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDED_PATTERNS:
            return False
        if part.startswith(".") and part not in [".env.example"]:
            return False
    if path.suffix in EXCLUDED_EXTENSIONS:
        return False
    return True


def build_submission_zip():
    print("=" * 70)
    print("📦 BUILDING CLEAN SUBMISSION ZIP PACKAGE")
    print(f"   Root Directory: {BASE_DIR}")
    print("=" * 70)

    if SUBMISSION_ZIP.exists():
        SUBMISSION_ZIP.unlink()

    included_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(SUBMISSION_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_PATTERNS and not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                if not should_include_file(file_path):
                    continue

                # Relative path inside the archive
                arcname = file_path.relative_to(BASE_DIR)
                zf.write(file_path, arcname)
                included_files += 1
                total_uncompressed_bytes += file_path.stat().st_size

    zip_size_bytes = SUBMISSION_ZIP.stat().st_size
    zip_size_kb = round(zip_size_bytes / 1024, 2)
    zip_size_mb = round(zip_size_bytes / (1024 * 1024), 2)

    print(f"\n✅ Packaged {included_files} files successfully.")
    print(f"📦 Archive Path: {SUBMISSION_ZIP}")
    print(f"📊 Compressed Zip Size: {zip_size_kb} KB ({zip_size_mb} MB)")
    print(f"🛡️  Max Limit: 50.0 MB | Headroom: {round(50.0 - zip_size_mb, 2)} MB remaining")

    assert zip_size_bytes < 50 * 1024 * 1024, "ERROR: Archive exceeds 50MB limit!"
    print("🎉 Submission package verified compliant with HackerRank requirements!\n")


if __name__ == "__main__":
    build_submission_zip()
