FROM python:3.12
WORKDIR /usr/local/app
ENV CI=true
ENV DOCKER_RUN=true

RUN pip install pytest

COPY src ./src
EXPOSE 5000

RUN useradd app
USER app

RUN pytest -k test_is_docker ./
