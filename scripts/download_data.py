"""
scripts/download_data.py
Automated downloader for the UCI Online Retail II dataset.
"""

import os
import sys
import urllib.request
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATASET_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
ZIP_TARGET = os.path.join(RAW_DIR, "online_retail_ii.zip")


def download_dataset():
    os.makedirs(RAW_DIR, exist_ok=True)

    print(f"[*] Downloading UCI Online Retail II from:\n    {DATASET_URL}")
    print(f"[*] Destination: {ZIP_TARGET}")

    try:
        urllib.request.urlretrieve(DATASET_URL, ZIP_TARGET)
        print("[+] Download complete. Extracting files...")
        with zipfile.ZipFile(ZIP_TARGET, "r") as zip_ref:
            zip_ref.extractall(RAW_DIR)
        print(f"[+] Extraction complete. Raw files stored in: {RAW_DIR}")
    except Exception as e:
        print(f"[-] Automated download failed: {e}")
        print("    You can manually download the dataset from:")
        print("    https://archive.ics.uci.edu/dataset/502/online+retail+ii")
        print(f"    and place the CSV or Excel file into: {RAW_DIR}")


if __name__ == "__main__":
    download_dataset()
