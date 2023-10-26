import requests
import zipfile
import os


def download_and_unzip(url, extract_to='.'):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    if not os.path.exists("temp"):
        os.makedirs("temp")
    with open('temp/temp.zip', 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    with zipfile.ZipFile('temp/temp.zip', 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove('temp/temp.zip')


def download_bigdata(url, path):
    with requests.get(url, stream=True) as r:
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
