from flask import Flask, render_template
from sdwebui_utils import SDWebUI
import os


sdwebui = SDWebUI()

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html', image_url='/static/images/test.jpg')


def main():
    sdwebui.download()
    sdwebui.update()
    sdwebui.change_config()
    p = sdwebui.start()

    app.run(debug=True, use_reloader=False)

    p.terminate()
    p.join()


if __name__ == '__main__':
    main()

