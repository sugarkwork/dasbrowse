import json
from mydb import *
from flask import Flask, render_template, request


app = Flask(__name__)


@app.route('/')
def home():
    category = CategoryModel.select().execute()
    model = ModelModel.select().execute()
    asset_type = AssetTypeModel.select().execute()
    sub_type = SubTypeModel.select().execute()
    product = ProductModel.select().execute()

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
    category_select = eval(f"DufModel.select(DufModel.category.distinct()).where(DufModel.{dropdown_name} == request.json[dropdown_name]).execute()")
    model_select = eval(f"DufModel.select(DufModel.model.distinct()).where(DufModel.{dropdown_name} == request.json[dropdown_name]).execute()")


    return json.dumps({'category': category_select.values_list(), 'model': model_select.values_list()})


def main():
    app.run(debug=True)


if __name__ == '__main__':
    main()

