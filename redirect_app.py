import requests
from bs4 import BeautifulSoup
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
app.config.from_object('config')


# for instance, this happen with gridcomputing.pt.
def fix_not_closed_metatags(tag):
    fix_tag = str(tag).split(">")[0]
    if fix_tag.endswith('/'):
        fix_tag += ">"
    else:
        fix_tag += "/>"
    return fix_tag


def extract_metadata(redirect_url):
    r = requests.get(redirect_url)
    html = r.content

    soup = BeautifulSoup(html, "html.parser")

    meta_list = []

    valid_meta_names = ['description', 'keywords', 'author']

    for name in valid_meta_names:
        for tag in soup.find_all('meta', {'name': name}):
            meta_list.append(fix_not_closed_metatags(tag))

    title = soup.find('title')

    return title, meta_list


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

    if template == 'redirect_default.html':
        title, metadata = extract_metadata(redirect_url)

        return render_template(template, title=title, metatags=metadata, origin_host=request.host,
                               origin_url=request.url,
                               redirect_url=redirect_url)
    else:
        return render_template(template, origin_host=request.host, origin_url=request.url, redirect_url=redirect_url)


if __name__ == '__main__':
    app.run()
