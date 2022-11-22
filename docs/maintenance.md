# Maintenance

Het dockerfile `Dockerfile_python_deps` wordt gebruikt om Python dependencies te genereren en onderhouden.

## Build image
Als je nog geen lokaal image hebt, genereer eerst het Docker image:
```
$ cd backend
$ docker build -f Dockerfile_python_deps . -t ams-bereikbaarheid-generate-python-deps
```

## Genereer dependencies
Vanuit de root, draai het volgende commando voor het requirements file wat je wilt genereren.

Bijvoorbeeld voor productie dependencies:
```
$ cd backend
$ docker run --rm -v $(pwd)/requirements:/requirements ams-bereikbaarheid-generate-python-deps --dry-run production.in
```
De output kun je copy-pasten naar de bijhorende `txt` file.

## Update dependencies
Vanuit de root, draai het volgende commando voor het requirements file wat je wilt updaten.

Bijvoorbeeld voor productie dependencies:
```
$ cd backend
$ docker run --rm -v $(pwd)/requirements:/requirements ams-bereikbaarheid-generate-python-deps --dry-run --upgrade production.in
```
De output kun je copy-pasten naar de bijhorende `txt` file.
