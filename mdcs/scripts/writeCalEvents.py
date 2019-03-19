#! /usr/bin/env python
import requests
from requests_ntlm import HttpNtlmAuth

def getEvents():
    #NIST Functional Acct Credentials (credentials don't work)
    #Note: 
    #10/12/18- Not sure why they don't work, Username is listed
    #as 'miclims Functional acct.' on the sheet from iTAC and I've tried 
    #this as well as 'miclims' and still receive 401 (unauthorized) errors.
    #I tried my own credentials today and that still works, so I'm not sure
    #what to do next. 
    username='miclims'
    pwd='############'
    
    domain='nist'
    path = domain+'\\'+username

    #Paths for other Nexus Instruments that can be booked through SP Cal
    titan_events = "FEITitanEvents"
    quanta_events = "FEIQuanta200Events"
    jeol_jsm_events = "JEOLJSM7100Events"
    hitachi_events = "HitachiS4700Events"
    jeol_jem_events = "JEOLJEM3010Events"
    cm30_events = "PhilipsCM30Events"
    em400_events = "PhilipsEM400Events"
    
    
    url='https://***REMOVED***/***REMOVED***/_vti_bin/ListData.svc/'

    instr_name=titan_events
    r=requests.get(url+"%s"%(instr_name), auth=HttpNtlmAuth(path, pwd))
    print(r.status_code)
    text = r.text
    return text
    
def writeEvents():
    with open('cal_events.xml', 'w') as f: 
        text = getEvents()
        f.write(text)

writeEvents()
