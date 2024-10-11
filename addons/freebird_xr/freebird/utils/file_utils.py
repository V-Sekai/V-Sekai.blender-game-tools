import os
import shutil
import zipfile
import errno

# loosely based on https://github.com/CGCookie/blender-addon-updater


def clear_folder(dir_path):
    "Empty the contents of the folder"

    from freebird.utils import log

    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
    folders = [f for f in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, f))]

    for f in files:
        try:
            os.remove(os.path.join(dir_path, f))
        except:
            log.warning(f"failed to delete file: {f}")
    for f in folders:
        try:
            shutil.rmtree(os.path.join(dir_path, f))
        except:
            log.warning(f"failed to delete folder: {f}")


def unzip(filepath, outdir):
    "Unzip the file to the output directory"

    with zipfile.ZipFile(filepath, "r") as zfile:
        if not zfile:
            raise RuntimeError("Downloaded file is not a zip, cannot extract")

        # Now extract directly from the first subfolder (not root)
        # this avoids adding the first subfolder to the path length,
        # which can be too long if the download has the SHA in the name.
        zsep = "/"  # Not using os.sep, always the / value even on windows.
        for name in zfile.namelist():
            if zsep not in name:
                continue
            top_folder = name[: name.index(zsep) + 1]
            if name == top_folder + zsep:
                continue  # skip top level folder
            sub_path = name[name.index(zsep) + 1 :]
            if name.endswith(zsep):
                try:
                    os.mkdir(os.path.join(outdir, sub_path))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise RuntimeError("Could not create folder from zip", e)
            else:
                with open(os.path.join(outdir, sub_path), "wb") as outfile:
                    data = zfile.read(name)
                    outfile.write(data)
