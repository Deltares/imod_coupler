import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import httpx
from tqdm import tqdm


def download_imod_collector(tag: str | None) -> None:
    build_id, build_number = _get_build_info(tag)
    folder_name = (tag or "develop") + f"_{build_number}"
    target_folder = Path(".imod_collector") / folder_name

    if target_folder.exists():
        print(
            f"iMOD collector already downloaded at '{target_folder}', remove the folder if you want to enforce re-downloading."
        )
        return

    token = os.environ["TEAMCITY_TOKEN"]
    with httpx.stream(
        "GET",
        f"https://dpcbuild.deltares.nl/app/rest/builds/{build_id}/artifacts/content/imod_coupler_windows.zip",
        headers={"Authorization": f"Bearer {token}"},
    ) as response:
        response.raise_for_status()

        zip_path = Path(".pixi/imod_coupler_windows.zip")
        _download_to_file(response, zip_path)
        _unzip_to_target(target_folder, zip_path)

        os.remove(zip_path)


def _get_build_info(tag: str | None) -> tuple[str, str]:
    token = os.environ["TEAMCITY_TOKEN"]
    tag_string = f",tag:{tag}" if tag else ""
    info_url = f"https://dpcbuild.deltares.nl/app/rest/builds/buildType:iMOD6_IMOD6collectorDaily_ReleaseX64,count:1,branch:main,status:SUCCESS{tag_string}"

    info_response = httpx.get(
        info_url,
        headers={"Authorization": f"Bearer {token}"},
    )
    info_response.raise_for_status()
    info_xml = ET.fromstring(info_response.content)
    return info_xml.attrib["id"], info_xml.attrib["number"]


def _download_to_file(response: httpx.Response, target_path: Path) -> None:
    with open(target_path, "wb") as f:
        progress_bar = tqdm(
            total=int(response.headers["Content-Length"]),
            unit_scale=True,
            unit="B",
            unit_divisor=1024,
            desc="Downloading iMOD collector",
        )
        for chunk in response.iter_bytes(chunk_size=1024):
            if chunk:
                f.write(chunk)
                progress_bar.update(len(chunk))


def _unzip_to_target(target_folder: Path, source_path: Path) -> None:
    with zipfile.ZipFile(source_path) as z:
        for file in tqdm(z.namelist(), desc="Extracting iMOD collector", unit="files"):
            z.extract(file, target_folder)


if __name__ == "__main__":
    download_imod_collector(sys.argv[1] if len(sys.argv) > 1 else None)
