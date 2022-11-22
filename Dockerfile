# Stage 1 - Compile Python dependencies
FROM amsterdam/python AS compile-image

# create and use virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Add and install build dependencies
COPY requirements .
RUN pip install --upgrade pip pip-tools

# Sync virtual env with app's dependencies
RUN pip-sync base.txt production.txt

# Stage 2 - Build docker image suitable for deployment
FROM amsterdam/python:3.7-slim-buster AS runtime-image

# copy python dependencies
COPY --from=compile-image /opt/venv /opt/venv

WORKDIR /app

# add application
RUN mkdir /app/log
COPY . /app

# configure entrypoint
EXPOSE 8000
RUN chmod u+x /app/start_app.sh

## set environment variables
ENV PATH="/opt/venv/bin:$PATH"

## start the application
ENTRYPOINT ["/app/start_app.sh"]
