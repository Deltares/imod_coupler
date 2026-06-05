import argparse
import io
import shutil
import tempfile
import urllib.request
import zipfile


def download_ribasim(version: str, output_dir: str) -> None:
    tempdir = tempfile.mkdtemp()

    url = f"https://github.com/Deltares/Ribasim/releases/download/v{version}/ribasim_windows.zip"
    zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read())).extractall(tempdir)
    shutil.move(tempdir + "/ribasim", output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Ribasim binaries.")
    parser.add_argument("version", help="Ribasim version to download (e.g. 2025.6.0)")
    parser.add_argument("output_dir", help="Directory to place the downloaded binaries")
    args = parser.parse_args()
    download_ribasim(args.version, args.output_dir)
