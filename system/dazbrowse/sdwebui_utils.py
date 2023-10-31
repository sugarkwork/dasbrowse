import os
import subprocess
from threading import Thread, Lock, Event
import time
from utils import download_bigdata, download_and_unzip
import webuiapi


def _print_log(log_queue, sdwebui, exit_flag):
    while True:
        while len(log_queue) > 0:
            log_data = str(log_queue.pop(0)).strip()
            if 'Running on local URL' in log_data or 'Loading weights' in log_data:
                time.sleep(5)
                sdwebui.set_running(True)
            print(log_data)
        time.sleep(0.5)
        if exit_flag.is_set():
            break


def print_output(stream, stdin, log_queue, exit_flag):
    for line in stream:
        log_queue.append(line)
        if '.' in line:
            stdin.write('\n')
            stdin.flush()
        if exit_flag.is_set():
            break


class SDWebUI:
    def __init__(self):
        self.sdwebui_url = "https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/download/v1.0.0-pre/sd.webui.zip"
        self.model_url = "https://huggingface.co/sugarknight/test_real/resolve/main/bb_mix2.safetensors"
        self.default_model = "./temp/sdwebui/webui/models/Stable-diffusion/bb_mix2.safetensors"
        self.temp_dir = "./temp/sdwebui"
        self.api = webuiapi.WebUIApi()

        self._running = 0
        self._running_lock = Lock()
        self._log = []
        self._log_lock = Lock()

    def is_running(self) -> bool:
        with self._running_lock:
            return self._running == 1
    
    def set_running(self, val: bool):
        with self._running_lock:
            print("set_running", val)
            self._running = 1 if val is True else 0
    
    def add_log(self, log: str):
        with self._log_lock:
            self._log.append(log)
    
    def get_log(self) -> str:
        with self._log_lock:
            if len(self._log) == 0:
                return ""
            return self._log.pop(0)

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

        exit_flag = Event()

        directory, executable = os.path.split(path)
        os.environ["SD_WEBUI_RESTARTING"] = "1"
        process = subprocess.Popen(['cmd', '/C', executable], cwd=directory,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True, env=os.environ)

        stdout_thread = Thread(target=print_output, args=(process.stdout, process.stdin, self._log, exit_flag))
        stderr_thread = Thread(target=print_output, args=(process.stderr, process.stdin, self._log, exit_flag))
        logwatcher_thread = Thread(target=_print_log, args=(self._log, self, exit_flag))

        print("Starting subprocess")
        stdout_thread.start()
        stderr_thread.start()
        logwatcher_thread.start()

        print("Waiting for subprocess to finish")
        process.wait()
        exit_flag.set()

        print("Waiting for thread to finish")
        stdout_thread.join()
        stderr_thread.join()
        logwatcher_thread.join()

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
        p = Thread(target=self.run)
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

