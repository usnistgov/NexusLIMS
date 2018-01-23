import pika
import requests
import sys
import logging
import time
import json
import subprocess
import tempfile
import os
#import thread
import threading
import zipfile

_registeredClowder=list()

def setup(extractorName, messageType, rabbitmqExchange, rabbitmqURL,  sslVerify=False):
    """Connect to message bus and wait for messages"""
    global _extractorName, _messageType, _rabbitmqExchange, _sslVerify, _logger

    # start the logging system if not started before
    logging.basicConfig()
    _logger = logging.getLogger(__name__)

    #set the global variables
    _extractorName=extractorName # the name of the extractor
    _messageType=messageType # the type of messages the extractor will work on
    _rabbitmqExchange=rabbitmqExchange # what it the name of the rabbitmq exchange to be used
    _sslVerify=sslVerify

# ----------------------------------------------------------------------
# setup connection to server and wait for messages
def connect_message_bus(extractorName, messageType, processFileFunction, rabbitmqExchange, rabbitmqURL, checkMessageFunction=None, sslVerify=False):
    """Connect to message bus and wait for messages"""
    global _extractorName, _messageType, _checkMessageFunction, _processFileFunction, _rabbitmqExchange, _logger

    _checkMessageFunction=checkMessageFunction # the function that should be used to check whether ot not to proceed to process the file
    _processFileFunction=processFileFunction # the function which should be used to process the input file

    # check if setup has been called
    if '_extractorName' not in globals():
        setup(extractorName, messageType, rabbitmqExchange, rabbitmqURL,  sslVerify)

    # connect to rabbitmq using URL parameters
    parameters = pika.URLParameters(rabbitmqURL)
    connection = pika.BlockingConnection(parameters)
    
    # connect to channel
    channel = connection.channel()
    
    # declare the rabbitmqExchange in case it does not exist
    channel.exchange_declare(exchange=_rabbitmqExchange, exchange_type='topic', durable=True)
    
    # declare the queue in case it does not exist
    channel.queue_declare(queue=_extractorName, durable=True)

    # connect queue and rabbitmqExchange
    if isinstance(_messageType, str):
        channel.queue_bind(queue=_extractorName, exchange=_rabbitmqExchange, routing_key=_messageType)
    else:
        [channel.queue_bind(queue=_extractorName, exchange=_rabbitmqExchange, routing_key=x) for x in _messageType]
    channel.queue_bind(queue=_extractorName, exchange=_rabbitmqExchange, routing_key="extractors." + _extractorName)

    # setting prefetch count to 1 so we only take 1 message of the bus at a time, so other extractors of the same type can take the next message.
    channel.basic_qos(prefetch_count=1)

    # start listening
    _logger.info("Waiting for messages. To exit press CTRL+C")

    # create listener
    channel.basic_consume(on_message, queue=_extractorName, no_ack=False)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    # close connection
    connection.close()
 
# ----------------------------------------------------------------------
# Process any incoming message
def on_message(channel, method, header, body):
    """When message is received do the following steps:
    1. download the file
    2. launch extractor function"""

    global _logger, _extractorName, _checkMessageFunction, _processFileFunction
    fileid=0

    try:
        # parse body back from json
        jbody=json.loads(body)

        fileid=jbody['id']
        jbody['fileid']=fileid
        jbody['channel']=channel
        jbody['header']=header
        jbody['method']=method

        # INDIVIDUAL FILE MESSAGE
        if 'filename' in jbody:
            filename=jbody['filename']
            ext=os.path.splitext(filename)[1]

            # tell everybody we are starting to process the file
            status_update(channel=channel, header=header, fileid=fileid, status="Started processing file")

            # register extractor
            if jbody['host'] not in _registeredClowder:
                _registeredClowder.append(jbody['host'])
                url = "%s/api/extractors?key=%s" % (jbody['host'], jbody['secretKey'])
                register_extractor(url)

            # checks whether to process the file in this message or not
            checkResult = None if _checkMessageFunction is None else _checkMessageFunction(jbody)
            if _checkMessageFunction is None or checkResult:
                # if checkMessage returned correct flag, skip downloading file for process_file
                downloadFile = True
                if checkResult=="bypass" or (type(checkResult)==dict and "bypass" in checkResult):
                    downloadFile = False

                try:
                    # call actual extractor function
                    _logger.info("Starting a New Thread for Process File")
                    threading.Thread(target=thread_function, args=(channel, method, header, jbody, ext, downloadFile)).start()
                except:
                    _logger.exception("Error: unable to start new thread for processing")
                    status_update(channel=channel, header=header, fileid=fileid, status="Error processing")
                    status_update(channel=channel, header=header, fileid=fileid, status="Done")
            else:
                channel.basic_ack(method.delivery_tag)

        # DATASET MESSAGE
        elif 'datasetId' in jbody:
            # Prepare params object for fetching data from API
            params={
                'host': jbody['host'],
                'secretKey': jbody['secretKey']
            }

            # add dataset details
            datasetid=jbody['datasetId']
            jbody['datasetInfo']=get_dataset_info(datasetid, params)

            # add most recently added file details
            flist = get_dataset_file_list(datasetid, params)
            jbody['filelist']=flist
            for f in flist:
                if f['id'] == fileid:
                    jbody['filename']=f['filename']

            # tell everybody we are starting to process the file
            status_update(channel=channel, header=header, fileid=fileid, status="Started processing dataset from this file")

            # register extractor
            if jbody['host'] not in _registeredClowder:
                _registeredClowder.append(jbody['host'])
                url = "%s/api/extractors?key=%s" % (jbody['host'], jbody['secretKey'])
                register_extractor(url)

            # checks whether to process the file in this message or not
            checkResult = None if _checkMessageFunction is None else _checkMessageFunction(jbody)
            if _checkMessageFunction is None or checkResult:
                # if checkMessage returned correct flag, skip downloading file for process_file
                downloadFile = True
                if checkResult=="bypass" or (type(checkResult)==dict and "bypass" in checkResult):
                    downloadFile = False

                try:
                    # call actual extractor function
                    _logger.info("Starting a New Thread for Process Dataset")
                    threading.Thread(target=thread_function_dataset, args=(channel, method, header, jbody, downloadFile)).start()
                except:
                    _logger.exception("Error: unable to start new thread for processing")
                    status_update(channel=channel, header=header, fileid=fileid, status="Error processing")
                    status_update(channel=channel, header=header, fileid=fileid, status="Done")
            else:
                channel.basic_ack(method.delivery_tag)

    except subprocess.CalledProcessError as e:
        msg = str.format("Error processing [exit code={}]\n{}", e.returncode, e.output)
        _logger.exception("[%s] %s", fileid, msg)
        status_update(channel=channel, header=header, fileid=fileid, status=msg)
        status_update(channel=channel, header=header, fileid=fileid, status="Done")
        channel.basic_ack(method.delivery_tag)
    except:
        _logger.exception("[%s] error processing", fileid)
        status_update(channel=channel, header=header, fileid=fileid, status="Error processing")
        status_update(channel=channel, header=header, fileid=fileid, status="Done")
        channel.basic_ack(method.delivery_tag)

# ----------------------------------------------------------------------
def thread_function(channel, method, header, jbody, ext, downloadFile=True):
    global _processFileFunction 
    inputfile = None    
    
    host = jbody['host']
    fileid = jbody['id']
    secretKey = jbody['secretKey']
    intermediatefileid = jbody['intermediateId']
    
    if not (host.endswith('/')):
            host += '/'
    
    try:
        # download file
        if downloadFile:
            inputfile = download_file(channel, header, host, secretKey, fileid, intermediatefileid, ext)
        else:
            inputfile = None
            jbody['download_bypassed'] = True

        # add more information necessary to process the file to the dict
        jbody['channel'] = channel
        jbody['header'] = header
        jbody['inputfile'] = inputfile
    
        if _processFileFunction:
            _processFileFunction(jbody)
             
    finally:
        status_update(channel=channel, header=header, fileid=fileid, status="Done")
        channel.basic_ack(method.delivery_tag)
        if inputfile is not None:
            try:
                os.remove(inputfile)
            except OSError:
                pass
            except UnboundLocalError:
                pass

def thread_function_dataset(channel, method, header, jbody, downloadFile=True):
    global _processFileFunction
    inputfile = None

    host = jbody['host']
    fileid = jbody['fileid']
    datasetid = jbody['datasetId']
    secretKey = jbody['secretKey']
    intermediatefileid = jbody['intermediateId']

    if not (host.endswith('/')):
        host += '/'

    try:
        # download file
        if downloadFile:
            dszip = download_dataset_zip(channel, header, host, secretKey, datasetid)
            fileset = extract_zip_contents(dszip)
        else:
            fileset = []
            jbody['download_bypassed'] = True

        # add more information necessary to process the file to the dict
        jbody['channel'] = channel
        jbody['header'] = header
        jbody['files'] = fileset

        if _processFileFunction:
            _processFileFunction(jbody)

    finally:
        status_update(channel=channel, header=header, fileid=fileid, status="Done")
        channel.basic_ack(method.delivery_tag)
        if inputfile is not None:
            try:
                os.remove(inputfile)
            except OSError:
                pass
            except UnboundLocalError:
                pass

# ------------------
# Send updates about status of processing file
def status_update(status, fileid, channel, header):
    """Send notification on message bus with update"""

    # print status

    global _extractorName, _rabbitmqExchange, _logger

    _logger.debug("[%s] : %s", fileid, status)

    statusreport = {}
    statusreport['file_id'] = fileid
    statusreport['extractor_id'] = _extractorName
    statusreport['status'] = status
    statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    channel.basic_publish(exchange='',
                          routing_key=header.reply_to,
                          properties=pika.BasicProperties(correlation_id = header.correlation_id),
                          body=json.dumps(statusreport))


#def status_update(status, parameters):
#   """Send notification on message bus with update"""

#   _status_update(status=status, fileid=parameters['fileid'], channel=parameters['channel'], header=parameters['header'])

# ------------------
# Send updates about status of processing file - JSON version
def status_update_json(jsonstatus, fileid, channel, header):
    """Send status update to Clowder via RabbitMQ"""

    # print status

    global _extractorName, _rabbitmqExchange, _logger

    _logger.debug("[%s] : %s", fileid, jsonstatus['status'])

    channel.basic_publish(exchange='',
                          routing_key=header.reply_to,
                          properties=pika.BasicProperties(correlation_id=header.correlation_id),
                          body=json.dumps(jsonstatus))

# ----------------------------------------------------------------------
# Upload file metadata to Clowder
def _upload_file_metadata(fileid, mdata, channel, header, host, key):
    """Upload file metadata to Clowder"""

    global _sslVerify

    status_update(channel=channel, header=header, fileid=fileid, status="Uploading file metadata.")

    headers={'Content-Type': 'application/json'}

    if(not host.endswith("/")):
        host = host+"/"

    url=host+'api/files/'+ fileid +'/metadata?key=' + key
    
    r = requests.post(url, headers=headers, data=json.dumps(mdata), verify=_sslVerify)
    r.raise_for_status()

def upload_file_metadata(mdata, parameters):
    """Upload file metadata to Clowder"""

    return _upload_file_metadata(fileid=parameters['fileid'], mdata=mdata, channel=parameters['channel'], 
        header=parameters['header'], host=parameters['host'], key=parameters['secretKey'])

# Upload dataset metadata to Clowder
def _upload_dataset_metadata(dsid, mdata, channel, header, host, key):
    """Upload dataset metadata to Clowder"""

    global _sslVerify

    status_update(channel=channel, header=header, fileid=dsid, status="Uploading dataset metadata.")

    headers={'Content-Type': 'application/json'}

    if(not host.endswith("/")):
        host = host+"/"

    url=host+'api/datasets/'+ dsid +'/metadata?key=' + key

    r = requests.post(url, headers=headers, data=json.dumps(mdata), verify=_sslVerify)
    r.raise_for_status()

def upload_dataset_metadata(mdata, parameters):
    """Upload dataset metadata to Clowder"""

    return _upload_dataset_metadata(dsid=parameters['datasetId'], mdata=mdata, channel=parameters['channel'],
                                 header=parameters['header'], host=parameters['host'], key=parameters['secretKey'])

# UPLOADING METADATA - JSON LD
def _upload_file_metadata_jsonld(fileid, mdata, channel, header, host, key):
    """Upload file metadata to Clowder"""

    global _sslVerify
    status_update(channel=channel, header=header, fileid=fileid, status="Uploading file metadata.")
    headers={'Content-Type': 'application/json'}
    if(not host.endswith("/")):
        host = host+"/"
    url=host+'api/files/'+ fileid +'/metadata.jsonld?key=' + key
    r = requests.post(url, headers=headers, data=json.dumps(mdata), verify=_sslVerify)
    r.raise_for_status()

def upload_file_metadata_jsonld(mdata, parameters):
    """Upload file metadata to Clowder"""

    return _upload_file_metadata_jsonld(fileid=parameters['fileid'], mdata=mdata, channel=parameters['channel'],
                                 header=parameters['header'], host=parameters['host'], key=parameters['secretKey'])

def _upload_dataset_metadata_jsonld(dsid, mdata, channel, header, host, key):
    """Upload dataset metadata to Clowder"""

    global _sslVerify

    if channel:
        status_update(channel=channel, header=header, fileid=dsid, status="Uploading dataset metadata.")

    headers={'Content-Type': 'application/json'}

    if(not host.endswith("/")):
        host = host+"/"

    url=host+'api/datasets/'+ dsid +'/metadata.jsonld?key=' + key

    r = requests.post(url, headers=headers, data=json.dumps(mdata), verify=_sslVerify)
    print(r.text)
    r.raise_for_status()

def upload_dataset_metadata_jsonld(mdata, parameters):
    """Upload dataset metadata to Clowder"""

    return _upload_dataset_metadata_jsonld(dsid=parameters['datasetId'], mdata=mdata, channel=parameters['channel'],
                                    header=parameters['header'], host=parameters['host'], key=parameters['secretKey'])

# ----------------------------------------------------------------------
# Upload file tags to Clowder
def _upload_file_tags(fileid, tags, channel, header, host, key):
    """Upload file tags to Clowder"""

    global _sslVerify

    status_update(channel=channel, header=header, fileid=fileid, status="Uploading file tags.")

    headers={'Content-Type': 'application/json'}
    if(not host.endswith("/")):
        host = host+"/"

    url=host+'api/files/'+ fileid+'/tags?key=' + key

    r = requests.post(url, headers=headers, data=json.dumps(tags), verify=_sslVerify)
    r.raise_for_status()

def upload_file_tags(tags, parameters):
    """Upload file tags to Clowder"""

    return _upload_file_tags(tags=tags, channel=parameters['channel'], header=parameters['header'], 
        host=parameters['host'], key=parameters['secretKey'], fileid=parameters['fileid'])

# ----------------------------------------------------------------------
# Upload section tags to Clowder
def _upload_section_tags(sectionid, tags, channel, header, host, key):
    """Upload section tags to Clowder"""

    global _sslVerify

    headers={'Content-Type': 'application/json'}
    if(not host.endswith("/")):
        host = host+"/"

    url=host+'api/sections/'+ sectionid+'/tags?key=' + key

    r = requests.post(url, headers=headers, data=json.dumps(tags), verify=_sslVerify)
    r.raise_for_status()

def upload_section_tags(sectionid, tags, parameters):
    """Upload section tags to Clowder"""

    return _upload_section_tags(sectionid=sectionid, tags=tags, channel=parameters['channel'], header=parameters['header'], 
        host=parameters['host'], key=parameters['secretKey'])

# ----------------------------------------------------------------------
# Upload a preview to Clowder
def upload_preview(previewfile, parameters, previewdata=None):
    """Upload preview to Clowder
       previewfile: the file containing the preview
       parameters: parameters given by pyClowder
       previewdata: any metadata to be associated with preview,
                    this can contain a section_id to indicate the
                    section this preview should be associated with.
    """
    global _sslVerify, _logger

    key = parameters['secretKey']
    host = parameters['host']
    if(not host.endswith("/")):
        host = host+"/"
    url = host + 'api/previews?key=' + key
    
    # upload preview
    with open(previewfile, 'rb') as f:
        files={"File" : f}
        r = requests.post(url, files=files, verify=_sslVerify)
        r.raise_for_status()
    previewid=r.json()['id']
    _logger.debug("preview id = [%s]", previewid)

    # associate uploaded preview with orginal file/dataset
    headers={'Content-Type': 'application/json'}
    url = None
    if previewdata and 'section_id' in previewdata:
        url=None
    elif parameters['fileid']:
        url=host + 'api/files/' + parameters['fileid'] + '/previews/' + previewid + '?key=' + key
    elif parameters['collectionid']:
        url=host + 'api/collections/' + parameters['collectionid'] + '/previews/' + previewid + '?key=' + key
    if url:
        r = requests.post(url, headers=headers, data=json.dumps({}), verify=_sslVerify);
        r.raise_for_status()

    # associate metadata with preview
    if previewdata is not None:
        url = host + 'api/previews/' + previewid + '/metadata?key=' + key
        r = requests.post(url, headers=headers, data=json.dumps(previewdata), verify=_sslVerify);
        r.raise_for_status()

    return previewid

# ----------------------------------------------------------------------
# Upload a thumbnail to Clowder
def upload_thumbnail(thumbnail, parameters):
    """Upload thumbnail to Clowder, currently only files are supported.
       thumbnail: the file containing the thumbnail
       parameters: parameters given by pyClowder
    """
    global _sslVerify, _logger

    key = parameters['secretKey']
    host = parameters['host']
    if(not host.endswith("/")):
        host = host+"/"
    url = host + 'api/fileThumbnail?key=' + key
    
    # upload preview
    with open(thumbnail, 'rb') as f:
        files={"File" : f}
        r = requests.post(url, files=files, verify=_sslVerify)
        r.raise_for_status()
    id=r.json()['id']
    _logger.debug("preview id = [%s]", id)

    # associate uploaded preview with orginal file/dataset
    headers={'Content-Type': 'application/json'}
    url = None
    if parameters['fileid']:
        url=host + 'api/files/' + parameters['fileid'] + '/thumbnails/' + id + '?key=' + key
    if url:
        r = requests.post(url, headers=headers, data=json.dumps({}), verify=_sslVerify);
        r.raise_for_status()
    else:
        raise("")

    return id

# ----------------------------------------------------------------------
# Upload a section to Clowder
def _upload_section(sectiondata, channel, header, host, key):
    """Upload file preview to Clowder"""

    global _sslVerify, _logger

    sectionid=None

    # status_update(channel=channel, header=header, fileid=fileid, status="Uploading section.")
                
    if(not host.endswith("/")):
        host = host+"/"
                
    url=host + 'api/sections?key=' + key
    
    headers={'Content-Type': 'application/json'}
   
    r = requests.post(url,headers=headers, data=json.dumps(sectiondata), verify=_sslVerify)
    r.raise_for_status()
    
    sectionid=r.json()['id']
    _logger.debug("section id = [%s]",sectionid)

    return sectionid

def upload_section(sectiondata, parameters):
    """Upload file preview to Clowder"""

    return _upload_section(sectiondata=sectiondata, channel=parameters['channel'], 
        header=parameters['header'], host=parameters['host'], key=parameters['secretKey'])

# ----------------------------------------------------------------------
# Upload a file to dataset in Clowder
def _upload_file_to_dataset(filepath, datasetid, channel, header, host, key):
    """Upload file preview to Clowder"""

    global _sslVerify, _logger

    uploadedfileid=None

    if(not host.endswith("/")):
        host = host+"/"    

    url=host+'api/uploadToDataset/'+datasetid+'?key=' + key

    r = requests.post(url, files={"File" : open(filepath, 'rb')}, verify=_sslVerify)
    r.raise_for_status()
    

    uploadedfileid = r.json()['id']
    _logger.debug("uploaded file id = [%s]",uploadedfileid)

    return uploadedfileid

def upload_file_to_dataset(filepath, parameters):
    """Upload file to Clowder dataset"""

    return _upload_file_to_dataset(filepath=filepath, datasetid=parameters['datasetId'], channel=parameters['channel'], 
        header=parameters['header'], host=parameters['host'], key=parameters['secretKey'])

# ----------------------------------------------------------------------
# Download file from Clowder to a temporary location
def download_file(channel, header, host, key, fileid, intermediatefileid, ext):
    """Download file to be processed from Clowder"""

    global _sslVerify

    status_update(channel=channel, header=header, fileid=fileid, status="Downloading file.")

    # fetch data
    if(not host.endswith("/")):
        host = host+"/"

    r=requests.get('%sapi/files/%s?key=%s' % (host, intermediatefileid, key),
                   stream=True, verify=_sslVerify)
    r.raise_for_status()
    (fd, inputfile)=tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        for chunk in r.iter_content(chunk_size=10*1024):
            f.write(chunk)
    return inputfile

# Download dataset zipfile from Clowder to a temporary location
def download_dataset_zip(channel, header, host, key, datasetid):
    """Download dataset to be processed from Clowder"""

    global _sslVerify

    status_update(channel=channel, header=header, fileid=datasetid, status="Downloading dataset.")

    # fetch data
    if(not host.endswith("/")):
        host = host+"/"

    r=requests.get('%sapi/datasets/%s/download?key=%s' % (host, datasetid, key),
                   stream=True, verify=_sslVerify)
    r.raise_for_status()
    (fd, inputfile)=tempfile.mkstemp(suffix=".zip")

    with os.fdopen(fd, "wb") as f:
        for chunk in r.iter_content(chunk_size=10*1024):
            f.write(chunk)
    return inputfile

# Extract contents of a zipfile and return list of file paths
def extract_zip_contents(zfile):
    zip = zipfile.ZipFile(zfile)
    outDir = zfile.replace(".zip", "")
    zip.extractall(outDir)

    flist = []
    for root, subdirs, files in os.walk(outDir):
        for f in files:
            flist.append(os.path.join(root, f))

    return flist

# Download file metadata from Clowder (JSON-LD)
def download_file_metadata_jsonld(host, key, fileid, extractor=None):
    """Download file metadata from Clowder"""
    global _sslVerify

    # fetch data
    if(not host.endswith("/")):
        host = host+"/"
    extFilter = "" if extractor is None else "?extractor=%s" % extractor

    r=requests.get('%sapi/files/%s/metadata.jsonld?key=%s%s' % (host, fileid, key, extFilter),
                   stream=True, verify=_sslVerify)
    r.raise_for_status()
    return r.json()

# Download dataset metadata from Clowder (JSON-LD)
def download_dataset_metadata_jsonld(host, key, dsid, extractor=None):
    """Download dataset metadata from Clowder"""
    global _sslVerify

    # fetch data
    if(not host.endswith("/")):
        host = host+"/"
    extFilter = "" if extractor is None else "&extractor=%s" % extractor

    r=requests.get('%sapi/datasets/%s/metadata.jsonld?key=%s%s' % (host, dsid, key, extFilter),
                   stream=True, verify=_sslVerify)
    r.raise_for_status()
    return r.json()

# Remove dataset metadata from Clowder (JSON-LD)
def remove_dataset_metadata_jsonld(host, key, dsid, extractor=None):
    """Delete dataset metadata from Clowder"""
    global _sslVerify

    # fetch data
    if(not host.endswith("/")):
        host = host+"/"
    extFilter = "" if extractor is None else "&extractor=%s" % extractor

    r=requests.delete('%sapi/datasets/%s/metadata.jsonld?key=%s%s' % (host, dsid, key, extFilter),
                   stream=True, verify=_sslVerify)
    r.raise_for_status()

# ----------------------------------------------------------------------
# Get Clowder file URL
def get_file_URL(fileid, parameters):
    host=parameters['host']
    if(not host.endswith("/")):
        host = host+"/"    
    return host+"files/"+fileid

# Get list of files in a particular dataset, and return name of fileid if given
def get_dataset_file_list(datasetid, parameters):
    host=parameters['host']
    if(not host.endswith("/")):
        host = host+"/"

    r = requests.get("%sapi/datasets/%s/listFiles?key=%s" % (host, datasetid, parameters['secretKey']),
                     verify=_sslVerify)
    r.raise_for_status()
    jsonData = json.loads(r.text)
    return jsonData

# Get list of files in a particular dataset, and return name of fileid if given
def get_dataset_info(datasetid, parameters):
    host=parameters['host']
    if(not host.endswith("/")):
        host = host+"/"

    r = requests.get(host+"api/datasets/%s?key=%s" % (datasetid, parameters['secretKey']),
                     verify=_sslVerify)
    r.raise_for_status()

    jsonData = json.loads(r.text)
    return jsonData

def register_extractor(registrationEndpoints):
    """Register extractor info with Clowder. This assumes a file called extractor_info.json to be
    located in the current working folder."""

    global _extractorName, _sslVerify, _logger

    pathname = os.path.abspath(os.path.dirname(sys.argv[0]))

    _logger.info("Registering extractor...")
    headers = {'Content-Type': 'application/json'}
    try:
        with open(os.path.join(pathname, 'extractor_info.json')) as info_file:
            info = json.load(info_file)
            # This makes it consistent: we only need to change the name at one place: config.py.
            info["name"] = _extractorName
            for url in registrationEndpoints.split(','):
                # Trim the URL in case there are spaces in the config.py string.
                r = requests.post(url.strip(), headers=headers, data=json.dumps(info), verify=_sslVerify)
                _logger.debug("Registering extractor with " +  url + " : " + r.text)
    except Exception as e:
        _logger.error('Error in registering extractor: ' + str(e))
