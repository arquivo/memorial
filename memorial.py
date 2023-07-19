from __future__ import unicode_literals
import os

import requests
from bs4 import BeautifulSoup
from flask import Flask
from flask import render_template
from flask import request, send_from_directory

app = Flask(__name__)
app.config.from_object('config')

if 'MEMORIAL_CONFIGURATION' in os.environ:
    app.config.from_envvar('MEMORIAL_CONFIGURATION')

# for instance, this happen with gridcomputing.pt.
def fix_not_closed_metatags(tag):
    fix_tag = str(tag).split(">")[0]
    if not fix_tag.endswith('/'):
        fix_tag += "/>"
    else:
        fix_tag += ">"
    return fix_tag


def fetch_redirect_url_content(redirect_url_home, redirect_url_path):
    s = requests.Session()
    timeout_value = 3
    try:
        redirect_url_path_head = s.head(redirect_url_path, allow_redirects=True, timeout=(None, timeout_value))
        if redirect_url_path_head.ok and 'content-type' in redirect_url_path_head.headers and redirect_url_path_head.headers['content-type'].startswith('text/html'):
            return s.get(redirect_url_path, timeout=(None, timeout_value))
        else:
            return s.get(redirect_url_home, timeout=(None, timeout_value))
    except requests.exceptions.Timeout as e:
        raise e
    except Exception as e:
        return s.get(redirect_url_home, timeout=(None, timeout_value))

def extract_metadata(redirect_url_home, redirect_url_path):
    try:
        meta_list = []

        r = fetch_redirect_url_content(redirect_url_home, redirect_url_path)

        html = r.content
        soup = BeautifulSoup(html, "html.parser")
        
        valid_meta_names = ['description', 'keywords', 'author']
        for name in valid_meta_names:
            for tag in soup.find_all('meta', {'name': name}):
                meta_list.append(fix_not_closed_metatags(tag))

        valid_link_rels = ['author', 'home', 'shortcut icon', 'alternate']
        for rel_value in valid_link_rels:
            for tag in soup.find('head').find_all('link', attrs={'rel': rel_value}):
                meta_list.append(fix_not_closed_metatags(tag))

        title = soup.find('title')

        return title, meta_list
    except Exception as e:
        print('Failed to extract metadata for redirect url: '+ redirect_url_home + ' with exception: '+ str(e))
        return None, meta_list


@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect(path):
    origin_host = request.host
    host_without_www = origin_host.replace('www.','')
    wayback_server_url = app.config.get('WAYBACK_SERVER', 'https://arquivo.pt/wayback/')
    wayback_noframe_server_url = app.config.get('WAYBACK_NOFRAME_SERVER', 'https://arquivo.pt/noFrame/replay/')
    template = 'redirect_default.html'
    default_language = 'pt'
    message_pt = None
    message_en = None
    version = None
    button_color = None
    logo = None
    link_pt = None
    link_en = None

    host_config = app.config['ARCHIVE_CONFIG'].get(host_without_www, None)
    if host_config:
        template = host_config.get('template', template)
        default_language = host_config.get('default_language', default_language)
        message_pt = host_config.get('message_pt', message_pt)
        message_en = host_config.get('message_en', message_en)
        version = host_config.get('version', version)
        button_color = host_config.get('button_color', button_color)
        logo = host_config.get('logo', logo)
        link_pt = host_config.get('link_pt', link_pt)
        link_en = host_config.get('link_en', link_en)

    if version:
        redirect_url = "{}{}/{}".format(wayback_server_url, version, request.base_url)
        redirect_url_path = "{}{}/{}".format(wayback_noframe_server_url, version, request.base_url)
        redirect_url_home = "{}{}/{}".format(wayback_noframe_server_url, version, host_without_www)
    else:
        redirect_url = "{}{}".format(wayback_server_url, request.base_url)
        redirect_url_path = "{}{}".format(wayback_noframe_server_url, request.base_url)
        redirect_url_home = "{}{}".format(wayback_noframe_server_url, host_without_www)

    if template == 'redirect_default.html':
        title, metadata = extract_metadata(redirect_url_home, redirect_url_path)
        return render_template(template,
            title = title,
            metatags = metadata,
            origin_host = origin_host,
            origin_url = request.url,
            redirect_url = redirect_url,
            default_language = default_language,
            message_pt = message_pt,
            message_en = message_en,
            button_color = button_color,
            logo = logo,
            link_pt = link_pt,
            link_en = link_en,
            args = request.args.items()
        )
    else:
        return render_template(template,
            origin_host = origin_host,
            origin_url = request.url,
            redirect_url = redirect_url)

if __name__ == '__main__':
    app.run()