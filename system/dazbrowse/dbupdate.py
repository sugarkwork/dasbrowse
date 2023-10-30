
import datetime
import os
import glob
import gzip
import webuiapi
from PIL import Image
import json
import urllib.parse
from sdwebui_utils import SDWebUI
from peewee import *


db = SqliteDatabase('duf.db')
api = webuiapi.WebUIApi()


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

    png_path = os.path.splitext(duf_path)[0] + ".png"    
    tip_png_path = os.path.splitext(duf_path)[0] + ".tip.png"
    if os.path.exists(png_path) and not os.path.exists(tip_png_path):
        extra_image(png_path)
    
    clip = ''
    deepdanbooru = ''
    if os.path.exists(tip_png_path):
        clip = api.interrogate(image=Image.open(tip_png_path), model="clip").info
        deepdanbooru = api.interrogate(image=Image.open(tip_png_path), model="deepdanbooru").info
        print("clip:", clip)
    else:
        print("Not found:", tip_png_path)

    path_parts = id.split('/')
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
        product_date=datetime.datetime.strptime(product_date, "%Y-%m-%dT%H:%M:%SZ"),
        file_date=datetime.datetime.fromtimestamp(os.path.getmtime(duf))
    )

    return duf_path
    

def extra_images(directory):
    for filename in os.listdir(directory):
        if filename.endswith(".png") and not filename.endswith(".tip.png"):
            base_filename = os.path.splitext(filename)[0]
            tip_filename = base_filename + ".tip.png"
            if os.path.exists(os.path.join(directory, tip_filename)):
                continue

            extra_image(os.path.join(directory, filename))


def extra_image(filename):
    directory = os.path.dirname(filename)
    base_filename = os.path.splitext(filename)[0]
    tip_filename = base_filename + ".tip.png"
    dst = os.path.join(directory, tip_filename)

    src_img = Image.open(filename)
    result = api.extra_single_image(image=src_img, upscaler_1="SwinIR 4x", upscaling_resize=4)
    result.image.save(dst)

    
def main():
    print("Starting...")
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

    db.connect()
    db.create_tables([DufModel])

    base_dir = "D:\destdaz\\"

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

    for dufdata in DufModel.select():
        print(dufdata.duf_path)
        print(dufdata.clip)

    db.close()

    print("terminate")
    p.terminate()
    p.join()


if __name__ == '__main__':
    main()
