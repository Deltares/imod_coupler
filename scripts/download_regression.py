import argparse, urllib.request, zipfile, io, tempfile, shutil


def download_coupler_binaries(version: str, output_dir: str) -> None:
    tempdir = tempfile.mkdtemp()

    url = f'https://github.com/Deltares/imod_coupler/releases/download/v{version}/imod_coupler_windows.zip'
    zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read())).extractall(tempdir)
    shutil.move(tempdir , output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download imod_coupler binaries.")
    parser.add_argument("version", help="imod_coupler version to download (e.g. 2025.11.0)")
    parser.add_argument("output_dir", help="Directory to place the downloaded binaries")
    args = parser.parse_args()
    download_coupler_binaries(args.version, args.output_dir)