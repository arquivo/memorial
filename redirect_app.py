from flask import Flask
from flask import render_template

app = Flask(__name__)
app.config.from_object('config')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect(path):
    return render_template('redirect.html', context="{}{}".format(app.config['WAYBACK_SERVER'], path))


if __name__ == '__main__':
    app.run()
