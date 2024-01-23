import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
import zlib
from pathlib import Path

UESAVE_TYPE_MAPS = [
    ".worldSaveData.CharacterSaveParameterMap.Key=Struct",
    ".worldSaveData.FoliageGridSaveDataMap.Key=Struct",
    ".worldSaveData.FoliageGridSaveDataMap.ModelMap.InstanceDataMap.Key=Struct",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Key=Struct",
    ".worldSaveData.ItemContainerSaveData.Key=Struct",
    ".worldSaveData.CharacterContainerSaveData.Key=Struct",
]
UESAVE_MAP_ARGS = []
for map_type in UESAVE_TYPE_MAPS:
    UESAVE_MAP_ARGS.append("--type")
    UESAVE_MAP_ARGS.append(map_type)


def download_file(url: str, output_path: Path):
    with urllib.request.urlopen(url) as dl:  # noqa: S310
        with open(output_path, "wb") as f:
            f.write(dl.read())


def unzip_file(zip_file: Path, output_path: Path):
    with zipfile.ZipFile(zip_file, "r") as f:
        f.extractall(output_path)


def deserialize_sav(sav_path: Path, output_folder: Path, uesave_exe: Path):
    with open(sav_path, "rb") as f:
        # Read the file
        data = f.read()
        uncompressed_len = int.from_bytes(data[0:4], byteorder="little")
        compressed_len = int.from_bytes(data[4:8], byteorder="little")
        magic_bytes = data[8:11]
        save_type = data[11]
        # Check for magic bytes
        if magic_bytes != b"PlZ":
            print(f"File {sav_path} is not a save file, found {magic_bytes} instead of P1Z")
            exit(1)
        # Valid save types
        if save_type not in [0x30, 0x31, 0x32]:
            print(f"File {sav_path} has an unknown save type: {save_type}")
            exit(1)
        # We only have 0x31 (single zlib) and 0x32 (double zlib) saves
        if save_type not in [0x31, 0x32]:
            print(f"File {sav_path} uses an unhandled compression type: {save_type}")
            exit(1)
        if save_type == 0x31:
            # Check if the compressed length is correct
            if compressed_len != len(data) - 12:
                print(f"File {sav_path} has an incorrect compressed length: {compressed_len}")
                exit(1)
        # Decompress file
        uncompressed_data = zlib.decompress(data[12:])
        if save_type == 0x32:
            # Check if the compressed length is correct
            if compressed_len != len(uncompressed_data):
                print(f"File {sav_path} has an incorrect compressed length: {compressed_len}")
                exit(1)
            # Decompress file
            uncompressed_data = zlib.decompress(uncompressed_data)
        # Check if the uncompressed length is correct
        if uncompressed_len != len(uncompressed_data):
            print(f"File {sav_path} has an incorrect uncompressed length: {uncompressed_len}")
            exit(1)
        # Save the uncompressed file
        with open(output_folder / f"{sav_path.name}.gvas", "wb") as f:
            f.write(uncompressed_data)
        # Convert to json with uesave
        # Run uesave.exe with the uncompressed file piped as stdin
        # Standard out will be the json string
        uesave_run = subprocess.run(
            [  # noqa: S603
                uesave_exe,
                "to-json",
                "--output",
                output_folder / f"{sav_path.name}.json",
                *UESAVE_MAP_ARGS,
            ],
            input=uncompressed_data,
            capture_output=True,
        )

        # Check if the command was successful
        if uesave_run.returncode != 0:
            print(f"uesave.exe failed to convert {sav_path} (return {uesave_run.returncode})")
            print(uesave_run.stdout.decode("utf-8"))
            print(uesave_run.stderr.decode("utf-8"))
            exit(1)

    return (
        output_folder / f"{sav_path.name}.json",
        output_folder / f"{sav_path.name}.gvas",
    )


def generate_sav(json_path: Path, gvas_path: Path, sav_path: Path, uesave_exe: Path):
    # Convert the file back to binary
    uesave_run = subprocess.run(
        [uesave_exe, "from-json", "--input", json_path, "--output", gvas_path]  # noqa: S603
    )
    if uesave_run.returncode != 0:
        print(f"uesave.exe failed to convert {json_path} (return {uesave_run.returncode})")
        exit(1)

    # Open the old sav file to get type
    with open(sav_path, "rb") as f:
        data = f.read()
        save_type = data[11]

    # Open the binary file
    with open(gvas_path, "rb") as f:
        # Read the file
        data = f.read()
        uncompressed_len = len(data)
        compressed_data = zlib.compress(data)
        compressed_len = len(compressed_data)
        if save_type == 0x32:
            compressed_data = zlib.compress(compressed_data)
        shutil.move(sav_path, sav_path.parent / f"{sav_path.name}.old")
        with open(sav_path, "wb") as f:
            f.write(uncompressed_len.to_bytes(4, byteorder="little"))
            f.write(compressed_len.to_bytes(4, byteorder="little"))
            f.write(b"PlZ")
            f.write(bytes([save_type]))
            f.write(bytes(compressed_data))


def join_json_files(json_with_appearance: Path, json_with_progression: Path):
    input_dict = json.loads(json_with_appearance.read_text())
    app = input_dict["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "PlayerCharacterMakeData"
    ]

    output_dict = json.loads(json_with_progression.read_text())
    output_dict["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "PlayerCharacterMakeData"
    ] = app

    shutil.move(
        json_with_progression,
        json_with_progression.parent / f"{json_with_progression.name}.old",
    )
    with open(json_with_progression, "w") as f:
        json.dump(output_dict, f, indent=2)

    return json_with_progression


def main():
    if len(sys.argv) < 3:
        print("Wrong number of arguments. Usage:")
        print(
            "> python palworld_change_appearance.py <sav_with_desired_appeareance> <sav_with_desired_progression>"
        )
        exit(1)

    orig_sav_app_path = Path(sys.argv[1])
    orig_sav_prog_path = Path(sys.argv[2])
    if not orig_sav_app_path.exists():
        print(f"{orig_sav_app_path} file does not exist")
        exit(1)
    if not orig_sav_prog_path.exists():
        print(f"{orig_sav_app_path} file does not exist")
        exit(1)

    tmp_folder = Path(__file__).parent / "tmp"
    tmp_folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(orig_sav_app_path, tmp_folder / f"app_{orig_sav_app_path.name}")
    shutil.copy(orig_sav_prog_path, tmp_folder / f"prog_{orig_sav_prog_path.name}")
    sav_app_path = tmp_folder / f"app_{orig_sav_app_path.name}"
    sav_prog_path = tmp_folder / f"prog_{orig_sav_prog_path.name}"

    uesave_download_url = (
        "https://github.com/trumank/uesave-rs/releases/latest"
        "/download/uesave-x86_64-pc-windows-msvc.zip"
    )
    download_file(uesave_download_url, tmp_folder / "uesave.zip")
    unzip_file(tmp_folder / "uesave.zip", tmp_folder)

    app_json, _ = deserialize_sav(
        sav_app_path,
        output_folder=tmp_folder,
        uesave_exe=tmp_folder / "uesave.exe",
    )
    prog_json, prog_gvas = deserialize_sav(
        sav_prog_path,
        output_folder=tmp_folder,
        uesave_exe=tmp_folder / "uesave.exe",
    )
    final_json = join_json_files(app_json, prog_json)

    generate_sav(
        final_json,
        prog_gvas,
        sav_path=tmp_folder / sav_prog_path.name,
        uesave_exe=tmp_folder / "uesave.exe",
    )

    shutil.move(orig_sav_prog_path, f"{orig_sav_prog_path}.old")
    shutil.move(tmp_folder / sav_prog_path.name, orig_sav_prog_path)
    shutil.rmtree(tmp_folder)
    print("Conversion successful!")
    print(f"New character saved to: {orig_sav_prog_path}")
    print(f"Old character backup in: {orig_sav_prog_path}.old")


if __name__ == "__main__":
    main()
