from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
app.config.from_object('config')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect(path):
    if app.config['ARCHIVE_VERSIONS'].get(request.host, None):
        redirect_url = "{}{}/{}".format(app.config['WAYBACK_SERVER'], app.config['ARCHIVE_VERSIONS'][request.host],
                                        request.url)
    else:
        redirect_url = "{}{}".format(app.config['WAYBACK_SERVER'], request.url)

    if app.config['TEMPLATES'].get(request.host, None):
        template = app.config['TEMPLATES'][request.host]
    else:
        template = 'redirect.html'
    return render_template(template, origin_url=request.url, redirect_url=redirect_url)


if __name__ == '__main__':
    app.run(debug=True)
