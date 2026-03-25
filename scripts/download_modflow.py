import argparse, urllib.request, zipfile, io, tempfile, shutil


def download_modflow(version: str, output_dir: str) -> None:
    tempdir = tempfile.mkdtemp()

    url = f'https://github.com/MODFLOW-ORG/modflow6/releases/download/{version}/mf{version}_win64.zip'
    zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read())).extractall(tempdir)
    shutil.move(tempdir + f'/mf{version}_win64/bin/', output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MODFLOW6 binaries.")
    parser.add_argument("version", help="MODFLOW6 version to download (e.g. 6.5.0)")
    parser.add_argument("output_dir", help="Directory to place the downloaded binaries")
    args = parser.parse_args()
    download_modflow(args.version, args.output_dir)