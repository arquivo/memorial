from collections import defaultdict

from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
app.config.from_object('config')

# TODO change this and use the flask.g store
global versions_dict
versions_dict = defaultdict()
versions_dict["www.umic.pt"] = "20170822151328"
versions_dict["www.english.umic.pt"] = "20170831175908"


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect(path):
    if versions_dict.get(request.host, None):
        redirect_url = "{}{}/{}".format(app.config['WAYBACK_SERVER'], versions_dict[request.host], request.url)
    else:
        redirect_url = "{}{}".format(app.config['WAYBACK_SERVER'], request.url)
    return render_template('redirect.html', context=redirect_url)


if __name__ == '__main__':
    app.run(debug=True)
