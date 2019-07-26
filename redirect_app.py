from __future__ import unicode_literals

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
    if not fix_tag.endswith('/'):
        fix_tag += "/>"
    else:
        fix_tag += ">"
    return fix_tag


def extract_metadata(redirect_url):
    try:
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
    except Exception:
        return None, meta_list


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect(path):
    origin_host = request.host
    host_without_www = origin_host.replace('www.','')
    wayback_server_url = app.config.get('WAYBACK_SERVER', 'https://arquivo.pt/wayback/')
    template = 'redirect_default.html'
    message = None
    version = None
    button_color = None

    host_config = app.config['ARCHIVE_CONFIG'].get(host_without_www, None)
    
    if host_config:
        template = host_config.get('template', template)
        message = host_config.get('message', message)
        version = host_config.get('version', version)
        button_color = host_config.get('button_color', button_color)

    if version:
        redirect_url = "{}{}/{}".format(wayback_server_url, version, request.url)
    else:
        redirect_url = "{}{}".format(wayback_server_url, request.url)

    if template == 'redirect_default.html':
        title, metadata = extract_metadata(redirect_url)
        return render_template(template, title=title, metatags=metadata, origin_host=origin_host,
                               origin_url=request.url, redirect_url=redirect_url, message=message, button_color=button_color)
    else:
        return render_template(template, origin_host=origin_host, origin_url=request.url, redirect_url=redirect_url)


if __name__ == '__main__':
    app.run()
