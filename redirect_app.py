from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
app.config.from_object('config')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect(path):
    redirect_url = "{}{}".format(app.config['WAYBACK_SERVER'], request.url)
    return render_template('redirect.html', context=redirect_url)


if __name__ == '__main__':
    app.run()
