# memorial

## Local development
This requires python3, so on an ubuntu linux machine install this package, using:
```bash
sudo apt install python3-dev
```

## Activate virtual environment and install its dependencies
```bash
virtualenv venv --python=python3.6
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Run
```bash
uwsgi --ini uwsgi.ini --py-autoreload 1
```

## Docker


```bash
docker build . -t memorial
docker run -p 127.0.0.1:8080:8080 memorial
```
