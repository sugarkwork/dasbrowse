
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
import cv2
import subprocess
from peewee import *
from mydb import *

ImageFile.LOAD_TRUNCATED_IMAGES = True

    
def analyze_duf(api, base_dir, duf) -> str:
    png_path = os.path.splitext(duf)[0] + ".png"    
    tip_png_path = os.path.splitext(duf)[0] + ".tip.png"
    if not os.path.exists(png_path) and not os.path.exists(tip_png_path):
        return

    json_data = open_data(duf)
    
    if json_data is None:
        print("cannot read json:", duf)
        return
    
    asset_info = json_data.get('asset_info',{})

    id = urllib.parse.unquote(asset_info.get('id', "")).strip()
    duf_path = os.path.abspath(base_dir + id)
    author = asset_info.get('contributor',{}).get('author',"")
    asset_type = asset_info.get('type',"")
    product_date = asset_info.get('modified',"")

    if os.path.exists(png_path) and not os.path.exists(tip_png_path):
        if api is not None:
            extra_image(api, png_path)
            print("extra_image:", png_path)
    
    clip = ''
    deepdanbooru = ''
    if os.path.exists(tip_png_path):
        if api is not None:
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
        pass
        print("insert")
    
    if len(product_date) <= 0:
        product_date = datetime.datetime.fromtimestamp(os.path.getmtime(duf))
    
    try:
        product_date = parser.parse(product_date)
    except:
        product_date = str(datetime.datetime.fromtimestamp(os.path.getmtime(duf)))

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
        product_date=product_date,
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

    print(f"extra_image {base_filename} -> {tip_filename} : {os.path.exists(dst)}")


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
        del_result = val.delete().execute()
        #print(del_result)
        for d in data:
            result = eval(f"d.{key}")
            if len(result) <= 0:
                continue
            result_convert = result.replace('_', ' ').strip().replace('-', ' ').strip().replace('!', '').strip().replace('@', '').strip()
            result_convert = insert_space_before_capital(result_convert)
            try:
                result_jp = load_memory(result_convert)

                if result_jp is None:
                    result_jp = tr.translate(result_convert, dest='ja').text
                    save_memory(result_convert, result_jp)
                    pass

                if result_jp is None or len(result_jp) <= 0:
                    result_jp = result_convert

            except Exception as e:
                result_jp = result
                save_memory(result_convert, result_jp)
            create_result = eval(f"val.create({key}=result, {key}_jp=result_jp)")
            #print(create_result)


def duf_analyze(api, base_dir):

    target_dir = ['People', 'Environments', 'Animals', 'Figures', 'Light Presets', 'Props', 'Render Presets', 'Render Settings', 'Shader Presets', 'Vehicles']

    for d in target_dir:
        people = os.path.join(base_dir, d)
        if not os.path.exists(people):
            continue

        dufs = glob.glob(os.path.join(people, '**', '*.duf'), recursive=True)
        db_dufs = [d.duf for d in DufModel.select(DufModel.duf).execute()]
        for duf in dufs:
            if duf in db_dufs:
                continue

            #print(duf)
            try:
                analyze_duf(api, base_dir, duf)
                #print()
            except Exception as e:
                print("duf_analyze error:", e)


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
    print("analyze")

    try:

        duf_analyze(None, "D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library")
        duf_analyze(None, "D:\destdaz")

        update_category()
            
        sdwebui, p = start_sdwebui(cuda_devices)

        result = DufModel.select().where( ( ( DufModel.clip == '' ) or ( DufModel.deepdanbooru == '' ) ) and ( DufModel.asset_type == 'preset_pose' ) ).execute()

        task_queue = queue.Queue()

        def worker(i):
            while True:
                r = task_queue.get()
                print(f"worker[{i}]: get queue: ", r.png_path)
                if os.path.exists(r.png_path) and not os.path.exists(r.tip_png_path):
                    extra_image(sdwebui.apis[i], r.png_path)
                
                if os.path.exists(r.tip_png_path):
                    try:
                        tip_image = Image.open(r.tip_png_path)
                    except Exception as ex:
                        try:
                            image_cv2 = cv2.imread(r.tip_png_path)
                            image_rgb = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB)
                            tip_image = Image.fromarray(image_rgb)
                        except Exception as ex:
                            print(f"worker[{i}]: load image error:", ex)
                            continue

                    clip = sdwebui.apis[i].interrogate(image=tip_image, model="clip").info
                    deepdanbooru = sdwebui.apis[i].interrogate(image=tip_image, model="deepdanbooru").info

                    print(f"worker[{i}]: clip:", clip)
                    print(f"worker[{i}]: deepdanbooru:", deepdanbooru)

                    r.clip = clip
                    r.deepdanbooru = deepdanbooru
                    r.save()

                else:
                    print(f"worker[{i}]: Not found:", r.tip_png_path)
        
        count_thread = len(cuda_devices)

        for i in range(count_thread):
            p = threading.Thread(target=worker, args=(i,))
            p.start()
        
        recent_durations = deque(maxlen=50)
        total_record = len(result)
        count = 0
        start_time = time.time()

        for r in result:
            if not os.path.exists(r.png_path):
                continue

            while task_queue.qsize() < count_thread + 1:
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

    except Exception as e:
        print(e)

    finally:
        db.close()

    print("terminate")

    p.join()


def extract_file(archive_path):
    command = [os.path.abspath(r"C:\Program Files\7-Zip\7z.exe"), "e", "-so", archive_path] 
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"Error: {result.stderr.decode('utf-8').strip()}")
    return result.stdout


def open_file(archive_path):
    with open(archive_path, 'rb') as f:
        return f.read()


def open_gzip(archive_path):
    with gzip.open(archive_path, 'rtb') as f:
        return f.read()


def open_data(archive_path):
    try_encoding = [
        'utf-8',
        'utf-8-sig',
        'latin-1',
    ]
    
    def json_loads(data):
        if data is None:
            return None
        
        for encoding in try_encoding:
            text_data = None

            try:
                text_data = data.decode(encoding)
            except:
                continue

            if text_data is not None and len(text_data) <= 0:
                print("dummy(empty))")
                return {}

            try:
                json_data = json.loads(text_data)
                return json_data
            except:
                pass

            if text_data is not None and 'dummy' in text_data.lower():
                print("dummy(text)")
                return {}
            
            try:
                json_data = eval(text_data)
                return json_data
            except:
                pass

        return None
    
    try:
        data = open_file(archive_path)
        
        json_result = json_loads(data)
        if json_result is not None:
            return json_result
        else:
            print("not json")
    except:
        print("not text file")

    try:
        data = open_gzip(archive_path)

        json_result = json_loads(data)
        if json_result is not None:
            return json_result
        else:
            print("not json (gzip)")
    except:
        print("not gzip")

    try:
        data = extract_file(archive_path)
        if len(data) <= 0:
            print("not archive")
        else:
            print("archive")
        
        json_result = json_loads(data)
        if json_result is not None:
            return json_result
    except:
        print("not archive")
    
    print("not json")
    
    return None


def test2(duf):
    print(duf)

    json_data = open_data(duf)
    
    if json_data is None:
        print("cannot read json:", duf)
        return False
    else:
        print("load ok")
        return True


def test():
    dufs = [
        r"D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library\People\Genesis 8 Female\Characters\Minto\Materials\MakeUps\Minto Face !Freckles.duf",
        r"D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library\People\Genesis 8 Female\Clothing\PoisenedLily\Comfy Short Set\Materials\Iray\All.duf",
        r"D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library\People\Genesis 8 Female\Clothing\Rare n Nirv\Shoes Collection\Materials\Casual Slippers\Colors A\RN !!CasualSlippers Color 00 A.duf",
        r"D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library\People\Genesis 8 Female\Poses\Warrior Queen Poses\Warrior Queen Hint.duf",
        r"D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library\People\Genesis 8 Female\Shapes\FMC Girl 8 Morph Kit\FMC Vol03 !Tips 01.duf",
        r"D:\daz3d\Applications\Data\DAZ 3D\My DAZ 3D Library\People\Genesis 8 Female\Clothing\Rare n Nirv\Shoes Collection\Materials\Garden Slippers\RN GardenSlippers Decos Color 00.duf"
    ]

    for duf in dufs:
        if not test2(duf):
            return


if __name__ == '__main__':
    #test()
    main()
