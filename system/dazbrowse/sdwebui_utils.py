import os
import subprocess
import multiprocessing
import threading
import time
from utils import download_bigdata, download_and_unzip


def _print_log(log_queue, sdwebui):
    while True:
        while not log_queue.empty():
            log_data = str(log_queue.get()).strip()
            if 'Running on local URL' in log_data:
                sdwebui.set_running(True)
            print(log_data)
        time.sleep(0.5)


def print_output(stream, stdin, log_queue):
    for line in stream:
        log_queue.put(line)
        if '...' in line:
            stdin.write('\n')


class SDWebUI:
    def __init__(self):
        self.sdwebui_url = "https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/download/v1.0.0-pre/sd.webui.zip"
        self.model_url = "https://huggingface.co/sugarknight/test_real/resolve/main/bb_mix2.safetensors"
        self.default_model = "./temp/sdwebui/webui/models/Stable-diffusion/bb_mix2.safetensors"
        self.temp_dir = "./temp/sdwebui"
        self.api = None

        self._running = multiprocessing.Value('i', 0)

        self._log = multiprocessing.Queue()
        threading.Thread(target=_print_log, args=(self._log, self)).start()


    def is_running(self) -> bool:
        return self._running.value == 1
    
    def set_running(self, val: bool):
        print("set_running", val)
        self._running.value = 1 if val is True else 0
    
    def add_log(self, log: str):
        self._log.put(log)
    
    def get_log(self) -> str:
        if self._log.empty():
            return ""
        return self._log.get()

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


    def install_cn(self):
        print("install_cn")

        extension_dir = os.path.abspath(os.path.join(self.temp_dir, "webui", "extensions"))
        controlnet_model_dir = os.path.abspath(os.path.join(self.temp_dir, "webui", "models", "ControlNet"))
        
        repo_url = "https://github.com/Mikubill/sd-webui-controlnet"
        repo_dir = os.path.join(extension_dir, "sd-webui-controlnet")

        if os.path.exists(repo_dir):
            subprocess.run(["git", "pull"], check=True, cwd=repo_dir)
        else:
            subprocess.run(["git", "clone", repo_url], check=True, cwd=extension_dir)
        
        if not os.path.exists(controlnet_model_dir):
            os.makedirs(controlnet_model_dir)
        
        model_base_url = "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/"
        models = ["control_v11f1e_sd15_tile.pth", "control_v11f1e_sd15_tile.yaml"]
        for model in models:
            if not os.path.exists(os.path.join(controlnet_model_dir, model)):
                print("Downloading", model)
                download_bigdata(f"{model_base_url}{model}", os.path.join(controlnet_model_dir, model))
    
    def wait_for_api(self, timeout=100):
        for _ in range(timeout):
            if self.is_running():
                break
            time.sleep(1)

    def start_subprocess(self, path):
        print("start_subprocess", path)
        if not os.path.exists(path):
            print("Error: The specified path does not exist:", path)
            return
        
        directory, executable = os.path.split(path)
        os.environ["SD_WEBUI_RESTARTING"] = "1"
        process = subprocess.Popen(['cmd', '/C', executable], cwd=directory,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True, env=os.environ)

        stdout_thread = threading.Thread(target=print_output, args=(process.stdout, process.stdin, self._log))
        stderr_thread = threading.Thread(target=print_output, args=(process.stderr, process.stdin, self._log))
        print("Starting subprocess")
        stdout_thread.start()
        stderr_thread.start()
        print("Waiting for subprocess to finish")
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
        print("run: ", path)
        self.start_subprocess(path)

    def start(self):
        print("start", self.run)
        p = threading.Thread(target=self.run)
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

