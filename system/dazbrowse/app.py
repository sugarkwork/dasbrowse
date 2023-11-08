import json
import subprocess
from mydb import *
from flask import Flask, render_template, request, send_file


app = Flask(__name__)


@app.route('/')
def home():
    category = CategoryModel.select().order_by(CategoryModel.category.asc()).execute()
    model = ModelModel.select().order_by(ModelModel.model.asc()).execute()
    asset_type = AssetTypeModel.select().order_by(AssetTypeModel.asset_type.asc()).execute()
    sub_type = SubTypeModel.select().order_by(SubTypeModel.sub_type.asc()).execute()
    product = ProductModel.select().order_by(ProductModel.product.asc()).execute()

    return render_template(
        'index.html', 
        image_url='/static/images/test.jpg', 
        category_len=len(category), category=category,
        model_len=len(model), model=model,
        asset_type_len=len(asset_type), asset_type=asset_type,
        sub_type_len=len(sub_type), sub_type=sub_type,
        product_len=len(product), product=product,
        )


@app.route('/dropdown/<dropdown_name>', methods=['GET', 'POST'])
def get_dropdown(dropdown_name):

    where = f".where(DufModel.{dropdown_name} == request.json[dropdown_name])"
    if len(request.json.get(dropdown_name, "")) <= 0:
        where = ""
    category_select = eval(f"DufModel.select(DufModel.category.distinct()){where}.order_by(DufModel.category.asc()).execute()")
    model_select = eval(f"DufModel.select(DufModel.model.distinct()){where}.order_by(DufModel.model.asc()).execute()")
    asset_type_select = eval(f"DufModel.select(DufModel.asset_type.distinct()){where}.order_by(DufModel.asset_type.asc()).execute()")
    sub_type_select = eval(f"DufModel.select(DufModel.sub_type.distinct()){where}.order_by(DufModel.sub_type.asc()).execute()")
    product_select = eval(f"DufModel.select(DufModel.product.distinct()){where}.order_by(DufModel.product.asc()).execute()")

    return json.dumps({
        'category': [c.category for c in category_select], 
        'model': [c.model for c in model_select],
        'asset_type': [c.asset_type for c in asset_type_select],
        'sub_type': [c.sub_type for c in sub_type_select],
        'product': [c.product for c in product_select],
        })


def cut_string(s):
    if len(s) > 13:
        return s[:13] + "..."
    else:
        return s


@app.route('/search', methods=['GET', 'POST'])
def get_result():
    print(request.json)

    query = ""
    if "query" in request.json:
        q = str(request.json['query']).strip().lower()
        query = f"& ( ( fn.LOWER(DufModel.clip).contains('{q}') ) | ( fn.LOWER(DufModel.deepdanbooru).contains('{q}') ) | ( fn.LOWER(DufModel.duf).contains('{q}') ) ) "

    category = f"& ( DufModel.category == '{request.json['category']}' ) " if 'category' in request.json and len(request.json['category']) > 0 else ''
    model = f"& ( DufModel.model == '{request.json['model']}' ) " if 'model' in request.json and len(request.json['model']) > 0 else ''
    asset_type = f"& ( DufModel.asset_type == '{request.json['asset_type']}' ) " if 'asset_type' in request.json and len(request.json['asset_type']) > 0 else ''
    sub_type = f"& ( DufModel.sub_type == '{request.json['sub_type']}' ) " if 'sub_type' in request.json and len(request.json['sub_type']) > 0 else ''
    product = f"& ( DufModel.product == '{request.json['product']}' ) " if 'product' in request.json and len(request.json['product']) > 0 else ''

    query = (
        "DufModel.select().where( ( DufModel.tip_png_path != '' ) "
        + category + model + asset_type + sub_type + product + query +
        ' ).order_by(DufModel.duf.asc()).limit(300).execute()')
    
    print(query)
    
    result = eval(query)
    return_data = []
    for r in result:
        return_data.append({'url': f'/open/{r.hash}', 'name_short': cut_string(r.name), 'name': r.name, 'img': f'/image/{r.hash}/image.png', 'duf': r.duf})

    return json.dumps(return_data)


@app.route('/image/<image_hash>/image.png')
def get_image(image_hash):
    result = DufModel.select(DufModel.tip_png_path, DufModel.hash).where(DufModel.hash == image_hash).get()
    return send_file(result.tip_png_path, mimetype='image/png')


@app.route('/open/<image_hash>')
def open_duf(image_hash):
    result = DufModel.select(DufModel.duf).where(DufModel.hash == image_hash).get()
    cmd = ["start", "", f'{result.duf}']
    print(cmd)
    subprocess.Popen(cmd, shell=True)
    return json.dumps({'start': cmd})


def main():
    app.run(debug=True, threaded=True)


if __name__ == '__main__':
    main()

