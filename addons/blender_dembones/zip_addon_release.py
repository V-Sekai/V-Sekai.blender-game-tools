import os
import zipfile
from pathlib import Path

def zip_dir(directory: Path, zip_path: str, exclude_folders):
    """
    Compress a directory (ZIP file).
    """
    if os.path.exists(directory):
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as out_zip_file:
            # The root directory within the ZIP file.
            rootdir = os.path.basename(directory)

            for dirpath, dirnames, filenames in os.walk(directory):
                dirnames[:] = [d for d in dirnames if d not in exclude_folders]
                for filename in filenames:

                    # Write the file named filename to the archive,
                    # giving it the archive name 'arcname'.
                    filepath   = os.path.join(dirpath, filename)
                    parentpath = os.path.relpath(filepath, directory)
                    arcname    = os.path.join(rootdir, parentpath)

                    out_zip_file.write(filepath, arcname)

if __name__ == "__main__":
    VERSION = (1, 0, 1)

    version = "_".join(str(num) for num in VERSION)
    exclude_folders = ["non-public", "releases", "__pycache__", ".git"]

    current_dir = Path(__file__).resolve().parent
    releases_dir = current_dir / "releases"
    zip_name = f"{current_dir.name}_{version}.zip"
    zip_path = releases_dir / zip_name

    zip_dir(directory=current_dir, zip_path=zip_path, exclude_folders=exclude_folders)