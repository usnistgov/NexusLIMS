#! /usr/bin/env python
import os
import io
import hyperspy.api as hs
import glob as glob
import codecs
import string



for files in glob.glob('*.hdf5'):       #Loop for all files within you're currently running from
    img = hs.load(files)                            #loading files into HyperSpy
    filename=img.metadata.General.get_item('title')     #Grabbing title stored in original file
    img.original_metadata.export('%s.txt'%(filename), encoding='utf-8')     #Exports the file to a utf-8 encoded txt file with the same name
  
    b = open('%s.txt'%(filename), 'r', encoding = 'utf-8')
    fileContents=b.read()
    fileContents = fileContents.replace('\n', '\r\n')
    b.close()
    f = codecs.open('%s.txt'%(filename),encoding='utf-8',mode='w+')
    f.write(fileContents)
    f.close()
    print('%s has been saved as a .txt file'%(filename))
    
    
