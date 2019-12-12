FROM python:3.6-slim
ADD . /app

ENV LC_ALL = en_US.UTF-8
ENV LOCAL = en_US.UTF-8

RUN cd /app && \
python setup.py install && \
rm -rf /app

ENTRYPOINT ["mfutil"]
