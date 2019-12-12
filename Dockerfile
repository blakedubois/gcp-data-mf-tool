FROM python:3.6-slim
ADD . /app

ENV LC_ALL=C.UTF-8
ENV LOCAL=C.UTF-8

RUN cd /app && \
python setup.py install && \
rm -rf /app

ENTRYPOINT ["mfutil"]
