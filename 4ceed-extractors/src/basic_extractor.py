import sys
import json
import logging
import os
import tempfile
import requests
import basic_extractor_config
from basic_extractor_config import *
import basic_extractor_helper
from basic_extractor_helper import *
import extractors
import hyperspy.api as hsapi

def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL, registrationEndpoints,logger

    receiver = 'new.basic.extractorPython3'
    extractorName = extractorName
    messageType = basic_extractor_config.messageType
    rabbitmqExchange = basic_extractor_config.rabbitmqExchange
    rabbitmqURL = basic_extractor_config.rabbitmqURL
    playserverKey = basic_extractor_config.playserverKey


    logging.basicConfig(format='%(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pyclowder.extractors').setLevel(logging.INFO)

    logger = logging.getLogger(receiver)
    logger.setLevel(logging.DEBUG)

    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=processFile,
        checkMessageFunction=check_message, rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)

def check_message(parameters):
    return True

def processFile(parameters):
    input_file = parameters['inputfile']
    logger.info('processing file with name ' + str(parameters['filename']))
    metadata_dictionary = basic_extractor_helper.getMetadata(input_file)
    #get metadata as a python dictionary and then upload with this method
    extractors.upload_file_metadata(metadata_dictionary, parameters)
    logger.info('successfully uploaded metadata')
    #create a tempfile of type png, for the image preview
    (fd, tn_file) = tempfile.mkstemp(suffix=".png")
    try:
        basic_extractor_helper.makePreview(tn_file)
        #the above method saves a preview to the temporary file
        #the below method will upload the preview
        preview_id = extractors.upload_preview(tn_file, parameters, None)
        upload_preview_title(preview_id, 'preview', parameters)
        logger.info('successfully uploaded preview')
    except:
        logger.error("error with image preview " + input_file)
    try:
        os.remove(tn_file)
    except:
        logger.error("Could not remove temporary file")

#this method adds a title to the preview. it was not included with pyclowder
def upload_preview_title(previewid, title_name,parameters):
    key = parameters['secretKey']
    title = dict()
    title['title'] = title_name
    host = parameters['host']
    if (not host.endswith("/")):
        host = host + "/"
    url = host + 'api/previews/'+previewid+'/title?key='+key

    headers = {'Content-Type': 'application/json'}

    if url:
        r = requests.post(url, headers=headers, data=json.dumps(title), verify=False);
        r.raise_for_status()
    return r

if __name__ == "__main__":
    main()
