#! /usr/bin/env python
import os
import argparse
import hyperspy.api as hs
import glob as glob
import numpy as np
import matplotlib.pyplot as plt

   
    
for file_name in glob.glob('*.dm3'):
    print(file_name)
    img = hs.load(file_name)
    h = img.metadata.General.original_filename
    h2 = h[0:-4]
    img.metadata.General.title = h2
    filename=img.metadata.General.get_item('title')
    img.save('%s.hdf5'%(filename))
    print('%s'%(h), "--->", '%s.hdf5'%(filename))
   
   
for file_name in glob.glob('*.dm4'):
    print(file_name)
    img = hs.load(file_name)
    h = img.metadata.General.original_filename
    h2 = h[0:-4]
    img.metadata.General.title = h2
    filename=img.metadata.General.get_item('title')
    img.save('%s.hdf5'%(filename))
    print('%s'%(h), "--->", '%s.hdf5'%(filename)) 
    
for file_name in glob.glob('*.emi'):    #Must have the .ser file (usually w/same title) accompanied in the folder so that it could read
    print(file_name)
    img = hs.load(file_name)
    h = img.metadata.General.original_filename
    h2 = h[0:-4]
    img.metadata.General.title = h2
    filename=img.metadata.General.get_item('title')
    img.save('%s.hdf5'%(filename))
    print('%s'%(h), "--->", '%s.hdf5'%(filename))
    
for file_name in glob.glob('*.mrc'):
    print(file_name)
    img = hs.load(file_name)
    h = img.metadata.General.original_filename
    h2 = h[0:-4]
    img.metadata.General.title = h2
    filename=img.metadata.General.get_item('title')
    img.save('%s.hdf5'%(filename))
    print('%s'%(h), "--->", '%s.hdf5'%(filename)) 
    
