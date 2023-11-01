
import datetime
import os
import glob
import gzip
from PIL import Image, ImageFile
import json
import time
import queue
import threading
from collections import deque
from datetime import timedelta
import hashlib
import urllib.parse
from dateutil import parser
from googletrans import Translator
from sdwebui_utils import SDWebUI
import pickle
from peewee import *
from mydb import *

ImageFile.LOAD_TRUNCATED_IMAGES = True

    
def analyze_duf(api, base_dir, duf) -> str:
    json_data = None
    
    if json_data is None:
        try:
            with open(duf, "r", encoding='utf-8') as f:
                json_data = json.load(f)
                print("plain text")
        except Exception as e:
            pass
    
    if json_data is None:
        try:
            with gzip.open(duf, 'rt', encoding='utf-8') as f:
                json_data = json.load(f)
                print("gzip data")
        except Exception as e:
            pass
    
    if json_data is None:
        print("cannot read json:", duf)
        return

    id = urllib.parse.unquote(json_data['asset_info']['id']).strip()
    duf_path = os.path.abspath(base_dir + id)
    author = json_data['asset_info']['contributor']['author']
    asset_type = json_data['asset_info']['type']
    product_date = json_data['asset_info']['modified']

    png_path = os.path.splitext(duf)[0] + ".png"    
    tip_png_path = os.path.splitext(duf)[0] + ".tip.png"
    if os.path.exists(png_path) and not os.path.exists(tip_png_path):
        extra_image(api, png_path)
        print("extra_image:", png_path)
    
    clip = ''
    deepdanbooru = ''
    if os.path.exists(tip_png_path):
        clip = api.interrogate(image=Image.open(tip_png_path), model="clip").info
        deepdanbooru = api.interrogate(image=Image.open(tip_png_path), model="deepdanbooru").info
        print("clip:", clip)
    else:
        print("Not found:", tip_png_path)
        tip_png_path = ""
    
    if not os.path.exists(png_path):
        png_path = ""

    path_parts = os.path.abspath(duf).replace(os.path.abspath(base_dir), '').replace('\\', '/').split('/')
    category = path_parts[1] if len(path_parts) > 1 else ''
    model = path_parts[2] if len(path_parts) > 2 else ''
    sub_type = path_parts[3] if len(path_parts) > 3 else ''
    name = path_parts[-1].replace('.duf', '') if len(path_parts) > 4 else ''
    product = name
    product_detail = ''
    if len(path_parts) > 5:
        product = path_parts[4]
        product_detail = '/'.join(path_parts[5:-1])

    if DufModel.select().where(DufModel.duf == duf).count() >= 1:
        DufModel.delete().where(DufModel.duf == duf).execute()
        print("update")
    else:
        print("insert")

    DufModel.create(
        duf=duf,
        hash = hashlib.sha256(duf.encode()).hexdigest(),
        duf_path=duf_path,
        id=id,
        png_path=png_path,
        tip_png_path=tip_png_path,
        author=author,
        asset_type=asset_type,
        clip=clip,
        deepdanbooru=deepdanbooru,
        category=category,
        model=model,
        sub_type=sub_type,
        name=name,
        product=product,
        product_detail=product_detail,
        update_date=datetime.datetime.now(),
        product_date=parser.parse(product_date),
        file_date=datetime.datetime.fromtimestamp(os.path.getmtime(duf))
    )

    return duf_path
    

def extra_images(api, directory):
    for filename in os.listdir(directory):
        if filename.endswith(".png") and not filename.endswith(".tip.png"):
            base_filename = os.path.splitext(filename)[0]
            tip_filename = base_filename + ".tip.png"
            if os.path.exists(os.path.join(directory, tip_filename)):
                continue

            extra_image(api, os.path.join(directory, filename))


def extra_image(api, filename):
    directory = os.path.dirname(filename)
    base_filename = os.path.splitext(filename)[0]
    tip_filename = base_filename + ".tip.png"
    dst = os.path.join(directory, tip_filename)

    src_img = Image.open(filename)
    result = api.extra_single_image(image=src_img, upscaler_1="SwinIR_4x", upscaling_resize=4)
    result.image.save(dst)


def insert_space_before_capital(s):
    if not s:
        return ""
    result = [s[0]]
    all_upper = s.isupper()
    for char in s[1:]:
        if char.isupper() and not all_upper and result[-1] != ' ':
            result.append(' ')
        result.append(char)
    return ''.join(result)


def update_category():
    
    tr = Translator()

    tableset = {
        'model': ModelModel,
        'category': CategoryModel,
        'asset_type': AssetTypeModel,
        'sub_type': SubTypeModel,
        'product': ProductModel,
    }

    for key, val in tableset.items():
        data = eval(f"DufModel.select(DufModel.{key}.distinct()).execute()")
        print(key)
        print(val.delete().execute())
        for d in data:
            result = eval(f"d.{key}")
            result_convert = result.replace('_', ' ').strip().replace('-', ' ').strip().replace('!', '').strip().replace('@', '').strip()
            result_convert = insert_space_before_capital(result_convert)
            try:
                result_jp = load_memory(result_convert)
                if result_jp is None:
                    result_jp = tr.translate(result_convert, dest='ja').text
                    save_memory(result_convert, result_jp)
            except Exception as e:
                result_jp = result
                save_memory(result_convert, result_jp)
            print(eval(f"val.create({key}=result, {key}_jp=result_jp)"))


def duf_analyze(base_dir):
    people = os.path.join(base_dir, 'People')

    dufs = glob.glob(os.path.join(people, '**', '*.duf'), recursive=True)
    for duf in dufs:
        if DufModel.select().where(DufModel.duf == duf).count() >= 1:
            continue

        print(duf)
        try:
            print(analyze_duf(base_dir, duf))
        except Exception as e:
            print(e)


def start_sdwebui(devices=[0]):
    sdwebui = SDWebUI()
    print("download")
    sdwebui.download()
    print("update")
    sdwebui.update()
    print("change_config")
    sdwebui.change_config()
    print("install_cn")
    sdwebui.install_cn()
    print("start")
    p = sdwebui.start(devices=devices)
    print("wait_for_api")
    sdwebui.wait_for_api()

    return sdwebui, p

    
def main():
    cuda_devices = [0, 1]

    db.connect()
    db.create_tables([DufModel, CategoryModel, ModelModel, AssetTypeModel, SubTypeModel, ProductModel])

    """
    for r in DufModel.select().execute():
        if not os.path.exists(r.tip_png_path):
            r.tip_png_path = ""

            r.save()

    return
    """

    print("Starting...")
    sdwebui, p = start_sdwebui(cuda_devices)

    print("analyze")

    try:
        #duf_analyze("D:\destdaz")

        result = DufModel.select().where(DufModel.clip == '' or DufModel.deepdanbooru == '').execute()

        task_queue = queue.Queue()

        def worker(i):
            while True:
                r = task_queue.get()
                print(r.png_path)
                if os.path.exists(r.png_path) and not os.path.exists(r.tip_png_path):
                    extra_image(sdwebui.apis[i], r.png_path)
                    print("extra_image:", r.png_path)
                
                if os.path.exists(r.tip_png_path):
                    try:
                        tip_image = Image.open(r.tip_png_path)
                    except Exception as ex:
                        print(ex)
                        continue
                    clip = sdwebui.apis[i].interrogate(image=tip_image, model="clip").info
                    deepdanbooru = sdwebui.apis[i].interrogate(image=tip_image, model="deepdanbooru").info

                    print("clip:", clip)
                    print("deepdanbooru:", deepdanbooru)

                    r.clip = clip
                    r.deepdanbooru = deepdanbooru
                    r.save()

                else:
                    print("Not found:", r.tip_png_path)
        
        count_thread = len(cuda_devices)

        for i in range(count_thread):
            p = threading.Thread(target=worker, args=(i,))
            p.start()
        
        recent_durations = deque(maxlen=30)
        total_record = len(result)
        count = 0
        start_time = time.time()

        for r in result:
            if not os.path.exists(r.png_path):
                continue

            if task_queue.qsize() < count_thread:
                print("add queue", r)
                task_queue.put(r)

                duration = time.time() - start_time
                recent_durations.append(duration)
                count = count + 1 
                remaining_data = total_record - count
                avg_duration = sum(recent_durations) / len(recent_durations)
                remaining_time = avg_duration * remaining_data
                remaining_time_str = str(timedelta(seconds=int(remaining_time)))
                
                print(f"Processed: {count}/{total_record}, Remaining Time: {remaining_time_str}")

                start_time = time.time()

            time.sleep(0.1)


        #update_category()
    except Exception as e:
        print(e)

    finally:
        db.close()

    print("terminate")

    p.join()


if __name__ == '__main__':
    main()
