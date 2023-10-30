from flask import Flask, render_template


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html', image_url='/static/images/test.jpg')


def main():
    print("run")
    app.run(debug=True, use_reloader=False)


if __name__ == '__main__':
    main()

