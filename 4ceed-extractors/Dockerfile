FROM python:3.6

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN pip install hyperspy
RUN pip install numpy
RUN pip install matplotlib
RUN pip install lxml
RUN pip install xmljson
RUN pip install xmltodict
ADD ./src /code
COPY extractor-start.sh /code/
WORKDIR /code

CMD ["/code/extractor-start.sh"] 
