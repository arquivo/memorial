# RedirectApp

## Local development
This requires python3, so on an ubuntu linux machine install this package, using:
```
sudo apt install python3-dev
```

## Activate virtual environment and install its dependencies
```
virtualenv venv --python=python3.6
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Run
uwsgi --ini uwsgi.ini --py-autoreload 1
