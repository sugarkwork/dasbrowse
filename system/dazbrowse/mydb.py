import os
import datetime
import pickle
from peewee import *


db = SqliteDatabase('duf.db')


class DufModel(Model):
    duf = CharField(primary_key=True, unique=True)
    hash = CharField()
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
