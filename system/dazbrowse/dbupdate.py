
import datetime
import os
import glob
import gzip
from PIL import Image
import json
import urllib.parse
from dateutil import parser
from googletrans import Translator
from sdwebui_utils import SDWebUI
import pickle
from peewee import *


db = SqliteDatabase('duf.db')


class DufModel(Model):
    duf = CharField(primary_key=True, unique=True)
    duf_path = CharField()
    id = CharField()
    png_path = CharField()
    tip_png_path = CharField()
    author = CharField()
    asset_type = CharField()
    clip = CharField()
    deepdanbooru = CharField()
    category = CharField()
    model = CharField()
    sub_type = CharField()
    name = CharField()
    product = CharField()
    product_detail = CharField()
    update_date = DateTimeField(default=datetime.datetime.now)
    product_date = DateTimeField(default=datetime.datetime.now)
    file_date = DateTimeField(default=datetime.datetime.now)
    class Meta:
        database = db


class CategoryModel(Model):
    category = CharField(primary_key=True, unique=True)
    category_jp = CharField()
    class Meta:
        database = db


class ModelModel(Model):
    model = CharField(primary_key=True, unique=True)
    model_jp = CharField()
    class Meta:
        database = db


class AssetTypeModel(Model):
    asset_type = CharField(primary_key=True, unique=True)
    asset_type_jp = CharField()
    class Meta:
        database = db


class SubTypeModel(Model):
    sub_type = CharField(primary_key=True, unique=True)
    sub_type_jp = CharField()
    class Meta:
        database = db


class ProductModel(Model):
    product = CharField(primary_key=True, unique=True)
    product_jp = CharField()
    class Meta:
        database = db


    
def analyze_duf(base_dir, duf) -> str:
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
        #extra_image(png_path)
        print("extra_image:", png_path)
    
    clip = ''
    deepdanbooru = ''
    if os.path.exists(tip_png_path):
        #clip = api.interrogate(image=Image.open(tip_png_path), model="clip").info
        #deepdanbooru = api.interrogate(image=Image.open(tip_png_path), model="deepdanbooru").info
        print("clip:", clip)
    else:
        print("Not found:", tip_png_path)

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
    

def extra_images(sdwebui, directory):
    for filename in os.listdir(directory):
        if filename.endswith(".png") and not filename.endswith(".tip.png"):
            base_filename = os.path.splitext(filename)[0]
            tip_filename = base_filename + ".tip.png"
            if os.path.exists(os.path.join(directory, tip_filename)):
                continue

            extra_image(sdwebui, os.path.join(directory, filename))


def extra_image(sdwebui, filename):
    directory = os.path.dirname(filename)
    base_filename = os.path.splitext(filename)[0]
    tip_filename = base_filename + ".tip.png"
    dst = os.path.join(directory, tip_filename)

    src_img = Image.open(filename)
    result = sdwebui.api.extra_single_image(image=src_img, upscaler_1="SwinIR_4x", upscaling_resize=4)
    result.image.save(dst)


def save_memory(key, val):
    pickle_file = 'memory.pkl'
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as f:
            memory = pickle.load(f)
    else:
        memory = {}
    memory[key] = val
    with open(pickle_file, 'wb') as f:
        pickle.dump(memory, f)


def load_memory(key, defval=None):
    pickle_file = 'memory.pkl'
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as f:
            memory = pickle.load(f)
    else:
        memory = {}
    return memory.get(key, defval)


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


def start_sdwebui():
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
    p = sdwebui.start()
    print("wait_for_api")
    sdwebui.wait_for_api()

    return sdwebui, p

    
def main():
    print("Starting...")
    sdwebui, p = start_sdwebui()

    print("analyze")
    db.connect()
    db.create_tables([DufModel, CategoryModel, ModelModel, AssetTypeModel, SubTypeModel, ProductModel])

    try:
        #duf_analyze("D:\destdaz")

        result = DufModel.select().where(DufModel.clip == '' or DufModel.deepdanbooru == '').execute()

        count = 0
        for r in result:

            print(f"[{count}/{len(result)}]")
            count += 1

            print(r.png_path)
            
            if os.path.exists(r.png_path) and not os.path.exists(r.tip_png_path):
                extra_image(sdwebui, r.png_path)
                print("extra_image:", r.png_path)
            
            clip = ''
            deepdanbooru = ''
            if os.path.exists(r.tip_png_path):
                tip_image = Image.open(r.tip_png_path)
                clip = sdwebui.api.interrogate(image=tip_image, model="clip").info
                deepdanbooru = sdwebui.api.interrogate(image=tip_image, model="deepdanbooru").info
                
                print("clip:", clip)
                print("deepdanbooru:", deepdanbooru)

                r.clip = clip
                r.deepdanbooru = deepdanbooru
                r.save()

            else:
                print("Not found:", r.tip_png_path)

        #update_category()
    except Exception as e:
        print(e)

    finally:
        db.close()

    print("terminate")

    p.join()


if __name__ == '__main__':
    main()
