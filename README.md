# RedirectApp

virtualenv venv --python=python3.6
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo apt install python3-dev

## For development use
uwsgi --ini uwsgi.ini --py-autoreload 1
