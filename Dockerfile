FROM python:3-alpine

COPY . /app

WORKDIR /app

RUN pip install -e .[pg]

ENTRYPOINT ["synpurge"]
