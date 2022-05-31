FROM python:3.10-bullseye

WORKDIR /usr/app

RUN apt-get update && \
    apt-get -y install pipenv

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN pipenv install --dev --system

COPY app.py app.py

ENTRYPOINT ["python3", "app.py"]