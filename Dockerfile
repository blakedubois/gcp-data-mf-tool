FROM python:3.6
ADD . /app

RUN cd /app && \
python setup.py sdist bdist_wheel && \
python setup.py install

ENTRYPOINT ["mfutil"]
