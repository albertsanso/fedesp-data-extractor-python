import csv
from pathlib import Path
from common import rfetmcommons

def save_to_csv(data, filename):
    if not data:
        print("No data to save.")
        return

    # Create parent folders if they dont exist
    file_path = Path(filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    keys = data[0].keys()
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

def load_by_module_and_file(module, filename):
    filename_fullpath = rfetmcommons.RESOURCES_FOLDER + "/" + module + "/" + filename
    with open(filename_fullpath, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)