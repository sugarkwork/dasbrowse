import os
import subprocess
import multiprocessing
import threading
from utils import download_bigdata, download_and_unzip

class SDWebUI:
    def __init__(self):
        self.sdwebui_url = "https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/download/v1.0.0-pre/sd.webui.zip"
        self.model_url = "https://huggingface.co/sugarknight/test_illust/resolve/main/gg_mix.safetensors"
        self.default_model = "./temp/sdwebui/webui/models/Stable-diffusion/gg_mix.safetensors"
        self.temp_dir = "./temp/sdwebui"

    def search_path(self, path):
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


    def start_subprocess(self, path):
        print("start_subprocess", path)
        if not os.path.exists(path):
            print("Error: The specified path does not exist:", path)
            return
        
        directory, executable = os.path.split(path)
        os.environ["SD_WEBUI_RESTARTING"] = "1"
        process = subprocess.Popen(['cmd', '/C', executable], cwd=directory,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.DEVNULL,
                                stderr=subprocess.PIPE,
                                text=True, env=os.environ)

        def print_output(stream):
            for line in stream:
                if stream is process.stdout:
                    print(line.strip())
                else:
                    print("Error:", line.strip())

        stdout_thread = threading.Thread(target=print_output, args=(process.stdout,))
        stderr_thread = threading.Thread(target=print_output, args=(process.stderr,))
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()

        return_code = process.poll()
        print("Return code:", return_code)


    def update(self):
        path = self.search_path(f"{self.temp_dir}/update.bat")
        self.start_subprocess(path)

    def download(self):
        if not os.path.exists(self.temp_dir):
            download_and_unzip(self.sdwebui_url, extract_to=f"{self.temp_dir}")

        if not os.path.exists(self.default_model):
            download_bigdata(self.model_url, self.default_model)

    def run(self):
        path = self.search_path(f"{self.temp_dir}/run.bat")
        self.start_subprocess(path)

    def start(self):
        p = multiprocessing.Process(target=self.run)
        p.start()
        return p

    def change_config(self):
        file_path = f'{self.temp_dir}/webui/webui-user.bat'

        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        options = ['--api']
        update_file = False
        for i, line in enumerate(lines):
            print(line)
            if 'COMMANDLINE_ARGS' in line:
                for option in options:
                    if option in line:
                        print('追加済み:', option.strip())
                    else:
                        lines[i] = f'{lines[i].strip()} {option}\n'
                        update_file = True
                        print('追加:', option.strip())
        if update_file:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

