import asyncio
import multiprocessing
import subprocess
import requests
import zipfile
import os
from flask import Flask, render_template

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

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', image_url='/static/images/example.jpg')

def sdwebui_search_path(path):
    abspath = os.path.abspath(path)
    print(abspath)
    if os.path.exists(abspath):
        print("Found.")
        return abspath
    else:
        print("Not found.")

    print(path)
    if os.path.exists(path):
        print("Found.")
        return path
    else:
        print("Not found.")
    
    path = os.path.realpath(path)
    print(path)
    if os.path.exists(path):
        print("Found.")
        return path
    else:
        print("Not found.")

    return path

def start_subprocess(path):
    print("start_subprocess", path)
    if not os.path.exists(path):
        print("Error: The specified path does not exist:", path)
        return
    process = subprocess.Popen(f'cmd /C "{path}"', stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, shell=True)

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    stderr = process.stderr.read()
    if stderr:
        print("Error:", stderr.strip())
    return_code = process.poll()
    print("Return code:", return_code)

def sdwebui_update():
    path = sdwebui_search_path("./temp/sdwebui/update.bat")
    start_subprocess(path)

def sdwebui_download():
    url = "https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/download/v1.0.0-pre/sd.webui.zip"
    download_and_unzip(url, extract_to='./temp/sdwebui')

def sdwebui_run(options):
    path = sdwebui_search_path("./temp/sdwebui/run.bat")
    start_subprocess(path)

def sdwebui_start():
    p = multiprocessing.Process(target=sdwebui_run, args=("Hello, World!",))
    p.start()
    return p

def main():
    print("Downloading...")
    if not os.path.exists("temp/sdwebui"):
        sdwebui_download()
        print("Downloaded.")
    else:
        print("Already downloaded.")
    
    sdwebui_update()
    p = sdwebui_start()

    app.run(debug=True)

    p.terminate()
    p.join() 


if __name__ == '__main__':
    main()
