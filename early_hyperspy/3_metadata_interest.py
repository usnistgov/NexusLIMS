#! /usr/bin/env python
import hyperspy.api as hs
import glob as glob
import numpy as np
import matplotlib.pyplot as plt
import string
import argparse
import codecs
import os

#Reads in the files that are input into the command line while running the script, can do 1+ at a time. 
parser = argparse.ArgumentParser()
parser.add_argument("file", nargs='+')   
args = vars(parser.parse_args())
for file_name in args['file']:
    s = hs.load(file_name)
    filename=s.metadata.General.get_item('title')
    #What June Wants
    #original_metadata.ImageList.TagGroup0
    #TagGroup0.Name
    if((hasattr(s.original_metadata.ImageList.TagGroup0, 'Name'))==True):
        img_name =s.original_metadata.ImageList.TagGroup0.Name
        txt=("Image Name: %s\r\n"%(img_name))  
    #ImageList.TagGroup0.ImageData        
    if ((hasattr(s.original_metadata.ImageList.TagGroup0, 'ImageData'))== True):
        txt+=(" -ImageData-\r\n")
        #ImageData.Calibrations
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageData, 'Calibrations'))== True):
            #Calibrations.Dimension
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations, 'Dimension'))== True):
                txt+=("   ---Calibration Dimensions\r\n")
                #Calibrated dimension scale
                calibrated_dimension_scale = s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup0.Scale
                #Calibrated dimension units
                calibrated_dimension_units = s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup0.Units
                #Data-size
                data_size = s.original_metadata.ImageList.TagGroup0.ImageData.Data.size
                #Data-size_bytes
                data_size_bytes = s.original_metadata.ImageList.TagGroup0.ImageData.Data.size_bytes
                #DataType
                data_type = s.original_metadata.ImageList.TagGroup0.ImageData.DataType
                txt+=("    Calibrated dimension scale: %s\r\n"%(calibrated_dimension_scale))
                txt+=("    Calibrated dimension units: %s\r\n"%(calibrated_dimension_units))
                txt+=("    Data size: %s\r\n"%(data_size))
                txt+=("    Data size bytes: %s\r\n"%(data_size_bytes))
                txt+=("    Data type: %s\r\n"%(data_type))                
                #Calibrations.Dimension.Data0
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageData.Dimensions, 'Data0'))==True):
                    #Dimensions Data0
                    txt+=("   ---Data0---\r\n")
                    dimensions_data0 = s.original_metadata.ImageList.TagGroup0.ImageData.Dimensions.Data0
                    txt+=("   Dimensions of Data0: %s\r\n"%(dimensions_data0))
                #Calibrations.Dimension.Data1
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageData.Dimensions, 'Data1'))==True):
                    #Dimensions Data1
                    txt+=("   ---Data1---\r\n")
                    dimensions_data1 = s.original_metadata.ImageList.TagGroup0.ImageData.Dimensions.Data1
                    txt+=("   Dimensions of Data1: %s\r\n"%(dimensions_data1))
            #Calibrations.Brightness                
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations, 'Brightness'))== True):
                txt+=("   ---Brightness--\r\n")
                #Brightness Origin
                bright_origin = s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Brightness.Origin
                #Brightness Scale
                bright_scale = s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Brightness.Scale
                #Brightness Units
                bright_units = s.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Brightness.Units
                txt+=("    Brighness Origin: %s\r\n"%(bright_origin))
                txt+=("    Brighness Scale: %s\r\n"%(bright_scale))
                txt+=("    Brighness units: %s\r\n"%(bright_units))               
        #ImageData.PixelDepth
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageData, 'PixelDepth'))== True):
            txt+=("  --Pixel Depth--\r\n")
            pixel_depth = s.original_metadata.ImageList.TagGroup0.ImageData.PixelDepth
            txt+=("   Pixel Depth: %s\r\n"%(pixel_depth)) 
    
    

    #TagGroup0.ImageTags
    if((hasattr(s.original_metadata.ImageList.TagGroup0, 'ImageTags'))==True):
        txt+=("\r\n -Image Tags-\r\n")
        #ImageList.TagGroup0.ImageTags.DataBar
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'DataBar'))==True):
            txt+=("  --DataBar\r\n")
            #Data Bar- Acquisition Date
            acquisition_date = s.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Acquisition_Date
            #Data Bar - Acquisition Time
            acquisition_time = s.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Acquisition_Time
            txt+=("   Acquisition date: %s\r\n"%(acquisition_date))
            txt+=("   Acquisition time: %s\r\n"%(acquisition_time))
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.DataBar, 'Exposure_Number'))==True):
                exp_num = s.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Exposure_Number 
                txt+=("   Exposure Number: %s\r\n"%(exp_num))   
        #ImageTags.Acquisition
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'Acquisition'))==True):
            txt+=("\r\n  --Acquisition--\r\n")
            #ImageTags.Acquisition.Device
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition, 'Device'))==True):
                txt+=("   ---Device---\r\n")
                #Active Size (pixels)
                active_size_pixels = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Device.Active_Size_pixels
                active_size_pixels = str(active_size_pixels)
                #CCD-Pixel Size (um)
                ccd_pixel_size = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Device.CCD
                #Camera Number
                camera_number = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Device.Camera_Number
                #Device Name
                device_name = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Device.Name
                #Device Source
                device_source = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Device.Source
                txt+=("    Active pixel size: %s\r\n"%(active_size_pixels))
                txt+=("    CCD pixel size: %s\r\n"%(ccd_pixel_size))
                txt+=("    Camera Number: %s\r\n"%(camera_number))
                txt+=("    Device Name: %s\r\n"%(device_name))
                txt+=("    Device source: %s\r\n"%(device_source))
            #Acquisition.Frame
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition, 'Frame'))==True):
                txt+=("   ---Frame---\r\n")
                #Image Display Frame- Binning
                image_frame_binning = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Area.Transform.Transform_List.TagGroup0.Binning
                image_frame_binning = str(image_frame_binning)
                #Image Frame- CCD Pixel Size
                image_frame_ccd_pixel_size = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.CCD.Pixel_Size_um
                image_frame_ccd_pixel_size = str(image_frame_ccd_pixel_size)
                txt+=("    Image display frame: binning: %s\r\n"%(image_frame_binning))
                txt+=("    Image frame: CCD pixel size: %s\r\n"%(image_frame_ccd_pixel_size))           
                #Frame.Intensity
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame, 'Intensity'))==True):
                    txt+=("    ----Intensity----\r\n")
                    #Intensity.Range
                    if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity, 'Range'))==True):
                        txt+=("     -----Range-----\r\n")
                        #Intensity Bias (counts)
                        intensity_bias = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Bias_counts
                        #Intensity Dark Current (counts/s)
                        intensity_dark_current = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Dark_Current_countss
                        #Intensity Dark Level (counts)
                        intensity_dark_level = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Dark_Level_countsintensity_max_value = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Maximum_Value_counts
                        #Intensity Max Value (counts)
                        intensity_max_value=s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Maximum_Value_counts
                        #Intensity Min Value (counts)
                        intensity_min_value = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Minimum_Value_counts
                        #Intensity Saturation level (counts)
                        intensity_saturation_level = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.Saturation_Level_counts
                        txt+=("      Intensity bias: %s\r\n"%(intensity_bias))
                        txt+=("      Intensity dark current: %s\r\n"%(intensity_dark_current) )
                        txt+=("      Intensity dark level: %s\r\n"%(intensity_dark_level))
                        txt+=("      Intensity minimum value: %s\r\n"%(intensity_min_value))
                        txt+=("      Intensity maximum value: %s\r\n"%(intensity_max_value))
                        txt+=("      Intensity saturation level: %s\r\n"%(intensity_saturation_level))
                    #Intensity.Transform
                    if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity, 'Transform'))==True):
                        #.Frame.Intensity.Transform.Transform_List
                        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Transform, 'Transform_List'))==True):
                            #.Frame.Intensity.Transform.Transform_List.TagGroup2
                            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Transform.Transform_List, 'TagGroup2')) == True):
                                txt+=("     -----Transform\r\n")
                                txt+=("      TagGroup2\r\n")
                                #TagGroup2 ADCMinandMax
                                ADCMax = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Transform.Transform_List.TagGroup2.ADC_Max
                                ADCMin = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Transform.Transform_List.TagGroup2.ADC_Min
                                txt+=("       ACD Max: %s\r\n"%(ADCMax))
                                txt+=("       ADC Min: %s\r\n"%(ADCMin))                               
                #Acq.Frame.Reference_Images
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame, 'Reference_Images'))==True):
                    txt+=("    ----Reference Images----\r\n")
                    #Reference Images-Dark-Std Dev. (counts)
                    reference_images_dark_std_dev=s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Reference_Images.Dark.Standard_Deviation_counts
                    #Reference Images-Dark Mean (counts)
                    reference_images_dark_mean = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Reference_Images.Dark.Mean_countsreference_images_dark_std_dev = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Reference_Images.Dark.Standard_Deviation_counts
                    txt+=("     Reference images- dark mean: %s\r\n"%(reference_images_dark_mean))
                    txt+=("     Reference images- dark std dev: %s\r\n"%(reference_images_dark_std_dev))
                    
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition, 'Parameters'))==True):
                txt+=("   ---Parameters---\r\n") 
                #Parameters.Environment
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters, 'Environment'))==True):
                    txt+=("    ----Environment----\r\n")
                    #Environment Mode Name 
                    environment_mode_name = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Environment.Mode_Name
                    txt+=("     Environment Mode Name: %s\r\n"%(environment_mode_name))   
                #Parameters.Detector
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters, 'Detector'))==True):
                    txt+=("    ----Detector----\r\n")
                    #Parameters.Detector.PICM_Parameters
                    if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector, 'PICM_Parameters'))==True):
                        txt+=("     -----PICM Parameters-----\r\n")
                        CollectionMode = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector.PICM_Parameters.Collection_Mode
                        Exposures = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector.PICM_Parameters.Exposure_s
                        ShutterMode = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector.PICM_Parameters.Shutter_Mode
                        ShutterType = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector.PICM_Parameters.Shutter_Type
                        txt+=("      Collection Mode: %s\r\n"%(CollectionMode))
                        txt+=("      Exposures: %s\r\n"%(Exposures))
                        txt+=("      Shutter Mode: %s\r\n"%(ShutterMode))
                        txt+=("      Shutter Type: %s\r\n"%(ShutterType))        
                #Parameters.High_Level
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters, 'High_Level'))==True):
                    txt+=("    ----High-Level----\r\n")
                    #High Level - Binning
                    hgh_binning = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Binning
                    hgh_binning = str(hgh_binning)
                    #High Level- Antiblooming
                    hgh_antibloom = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Antiblooming
                    #High Level CCD Read Area
                    high_level_ccd_read_area = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.CCD_Read_Area
                    high_level_ccd_read_area =str(high_level_ccd_read_area)
                    #Parameters.High_Level.ChooseNumberOfFrameShuttersAuto
                    Choose_Auto = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Choose_Number_Of_Frame_Shutters_Automatically
                    txt+=("     Choose Number of Frame Shutters Automatically: %s\r\n"%(Choose_Auto))   
                    #High Level Exposure (s)
                    high_level_exposure = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Exposure_s
                    #High Level Processing
                    high_level_processing = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Processing
                    #Number of Frame Shutters
                    numFrameShut = s.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Number_Of_Frame_Shutters
                    txt+=("     High Level- Binning: %s\r\n"%(hgh_binning))
                    txt+=("     High Level- Antiblooming: %s\r\n"%(hgh_antibloom))
                    txt+=("     High-Level- CCD Read Area: %s\r\n"%(high_level_ccd_read_area))
                    txt+=("     High-Level- Exposure (s): %s\r\n"%(high_level_exposure))
                    txt+=("     High-Level- Processing: %s\r\n"%(high_level_processing))
                    txt+=("     High-Level- Number of Frame Shutters: %s\r\n"%(numFrameShut))
    
    
        
        #ImageTags.DigiScan
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'DigiScan'))==True):
            txt+=("--DigiScan--\r\n")
            horiz_DS_offset = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Horizontal_DS_Offset
            horiz_img_cent = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Horizontal_Image_Center
            horiz_pixel_perp_step = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Horizontal_Perpendicular_Pixel_Step
            horiz_pixel_step = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Horizontal_Pixel_Step
            horiz_spacing = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Horizontal_Spacing

            vert_DS_offset = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Vertical_DS_Offset
            vert_img_cent = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Vertical_Image_Center
            vert_pixel_perp_step = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Vertical_Perpendicular_Pixel_Step
            vert_pixel_step = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Vertical_Pixel_Step
            vert_spacing = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Vertical_Spacing
            zoom_fact = s.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.Zoom_factor   
            txt+=("   Horizontal DS offset: %s\r\n"%(horiz_DS_offset))
            txt+=("   Horizontal Image Center: %s\r\n"%(horiz_img_cent))
            txt+=("   Horizontal Perpendicular Pixel Step: %s\r\n"%(horiz_pixel_perp_step))
            txt+=("   Horizontal Pixel Step: %s\r\n"%(horiz_pixel_step))
            txt+=("   Horizontal Spacing: %s\r\n"%(horiz_spacing))
            txt+=("   Vertical DS offset: %s\r\n"%(vert_DS_offset))
            txt+=("   Vertical Image Center: %s\r\n"%(vert_img_cent))
            txt+=("  Vertical Perpendicular Pixel Step: %s\r\n"%(vert_pixel_perp_step))
            txt+=("   Vertical Pixel Step: %s\r\n"%(vert_pixel_step))
            txt+=("   Vertical Spacing: %s\r\n"%(vert_spacing))
            txt+=("   Zoom factor: %s\r\n"%(zoom_fact))   
        
        #ImageTags.Microscope_Info
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'Microscope_Info'))==True):
            txt+=("\r\n  --Microscope Info--\r\n")
            #Microscope_Info.ActualMag
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Actual_Magnification'))==True):
                actual_mag = s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Actual_Magnification
                txt+=("   Actual Magnification: %s\r\n"%(actual_mag))
            #Microscope_Info.Cs(mm)
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Csmm'))==True):
                cs_mm = s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Csmm
                txt+=("   Cs mm: %s\r\n"%(cs_mm))
            #Microscope_Info.Illumination Mode
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Illumination_Mode'))==True):
                illumination_mode = s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Illumination_Mode
                txt+=("   Illumination mode: %s\r\n"%(illumination_mode))
            #Microscope_Info.Imaging Mode
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Imaging_Mode'))==True):
                imaging_mode = s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Imaging_Mode
                txt+=("   Imaging Mode: %s\r\n"%(imaging_mode))
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Indicated_Magnification'))==True):
            #Microscope_Info.Indicated Magnification
                indicated_magnification = s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Indicated_Magnification
                txt+=("   Indicated magnification: %s\r\n"%(indicated_magnification))
            #Microscope_Info.Microscope
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Microscope'))==True):
                microscope = s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Microscope
                txt+=("   Microscope: %s\r\n"%(microscope))
            #Microscope Operation Mode
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Operation_Mode'))==True):
                micro_op_mode=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Operation_Mode
                txt+=("   Microscope Operation Mode: %s\r\n"%(micro_op_mode))   
            #Microscope Voltage
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Voltage'))==True):
                micro_voltage=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Voltage
                txt+=("   Microscope Voltage: %s\r\n"%(micro_voltage))
            #Detector Name
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Name'))==True):
                detect_name=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Name
                txt+=("   Microscope Detector Name: %s\r\n"%(detect_name))
            #Microscope Specimen
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Items'))==True):
                if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Items, 'TagGroup0'))==True):
                    if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Items.TagGroup0, 'Label'))==True):
                        specimen_value=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Items.TagGroup0.Value
                        txt+=("   Specimen: %s\r\n"%(specimen_value))
            #Probe Current
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Probe_Current_nA'))==True):
                probe_current=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Probe_Current_nA
                txt+=("   Probe Current (n/A): %s\r\n"%(probe_current))
            #Probe Size
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Probe_Size_nm'))==True):
                probe_size=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Probe_Size_nm
                txt+=("   Probe Size (nm): %s\r\n"%(probe_size))
            #STEM Cam Length
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'STEM_Camera_Length'))==True):
                stem_cam_length=s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.STEM_Camera_Length
                txt+=("   STEM Camera Length: %s\r\n"%(stem_cam_length))
        
        #ImageTags.SI
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'SI'))== True):
            txt+=("\r\n  --SI--\r\n")
            #SI.Acquisition
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.SI, 'Acquisition'))==True):
                txt+=("   ---SI Acquisition---\r\n")
                SI_date = s.original_metadata.ImageList.TagGroup0.ImageTags.SI.Acquisition.Date
                endtime = s.original_metadata.ImageList.TagGroup0.ImageTags.SI.Acquisition.End_time
                num_cycles = s.original_metadata.ImageList.TagGroup0.ImageTags.SI.Acquisition.Number_of_cycles
                pixel_time = s.original_metadata.ImageList.TagGroup0.ImageTags.SI.Acquisition.Pixel_time_s
                start_time = s.original_metadata.ImageList.TagGroup0.ImageTags.SI.Acquisition.Start_time
                survey_image = s.original_metadata.ImageList.TagGroup0.ImageTags.SI.Acquisition.Survey_Image
                txt+=("    SI Acquisition Date: %s\r\n"%(SI_date))
                txt+=("    Start time: %s\r\n"%(start_time))
                txt+=("    End time: %s\r\n"%(endtime))
                txt+=("    Number of cycles: %s\r\n"%(num_cycles))
                txt+=("    Pixel time (s): %s\r\n"%(pixel_time))
                txt+=("    Survey Image: %s\r\n"%(survey_image))

        #ImageTags.EELS        
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'EELS'))==True):
            txt+=("\r\n  --EELS--\r\n")
            eels_exposures = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Exposure_s
            num_frame = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Number_of_frames
            txt+=("   EELS- Exposures (s): %s\r\n"%(eels_exposures))
            txt+=("   EELS- Number of frames: %s\r\n"%(num_frame))
            #TagGroup0.ImageTags.EELS.Spectrometer
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition, 'Spectrometer'))==True):
                txt+=("   ---EELS Spectrometer---\r\n")
                apt_index = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Aperture_index
                apt_label = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Aperture_label
                disp_evch = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Dispersion_eVch
                disp_index = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Dispersion_index
                drift_enabled = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Drift_tube_enabled
                drift_voltage = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Drift_tube_voltage_V
                energy_loss = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Energy_loss_eV
                ht_offset = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.HT_offset_V
                ht_offset_enabled = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.HT_offset_enabled
                instr_id = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Instrument_ID
                instr_name = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Instrument_name
                spec_mode = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Mode
                spec_prism_offset = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Prism_offset_V
                spec_prism_offset_enabled = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.Prism_offset_enabled
                txt+=("    Spectrometer- Aperture index: %s\r\n"%(apt_index))
                txt+=("    Spectrometer- Aperture label: %s\r\n"%(apt_label))
                txt+=("    Spectrometer- Dispersion (eV/ch): %s\r\n"%(disp_evch))
                txt+=("    Spectrometer- Dispersion index: %s\r\n"%(disp_index))
                txt+=("    Spectrometer- Drift tube enabled: %s\r\n"%(drift_enabled))
                txt+=("    Spectrometer- Drift tube voltage (V): %s\r\n"%(drift_voltage))
                txt+=("    Spectrometer- Energy loss (eV): %s\r\n"%(energy_loss))
                txt+=("    Spectrometer- HT offset (V): %s\r\n"%(ht_offset))
                txt+=("    Spectrometer- HT offset enabled: %s\r\n"%(ht_offset_enabled))
                txt+=("    Spectrometer- Instrument ID: %s\r\n"%(instr_id))
                txt+=("    Spectrometer- Instrument name: %s\r\n"%(instr_name))
                txt+=("    Spectrometer- Dispersion (eV/ch): %s\r\n"%(disp_evch))
                txt+=("    Spectrometer- Mode: %s\r\n"%(spec_mode))
                txt+=("    Spectrometer- Prism offset (V): %s\r\n"%(spec_prism_offset))
                txt+=("    Spectrometer- Prism offset enabled: %s\r\n"%(spec_prism_offset_enabled))
            #TagGroup0.ImageTags.EELS.Experimental_Conditions
            if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags.EELS, 'Experimental_Conditions'))==True):
                txt+=("   ---Experimental Conditions---\r\n")
                collect_semiangle = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Experimental_Conditions.Collection_semiangle_mrad
                converg_semiangle = s.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Experimental_Conditions.Convergence_semiangle_mrad
                txt+=("    EELS Experimental Conditions- Collection semi-angle (mrad): %s\r\n"%(collect_semiangle))
                txt+=("    EELS Experimental Conditions- Convergence semi-angle (mrad): %s\r\n"%(converg_semiangle))                
        
        #ImageTags.Meta_Data
        if((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'Meta_Data'))==True):
            txt+=("\r\n  --Meta Data--\r\n")
            md_acq_mode = s.original_metadata.ImageList.TagGroup0.ImageTags.Meta_Data.Acquisition_Mode
            md_format = s.original_metadata.ImageList.TagGroup0.ImageTags.Meta_Data.Format
            md_signal = s.original_metadata.ImageList.TagGroup0.ImageTags.Meta_Data.Signal  
            txt+=("  Metadata- Acquisition Mode: %s\r\n"%(md_acq_mode))
            txt+=("  Metadata- Format: %s\r\n"%(md_format))
            txt+=("  Metadata-  Signal: %s\r\n"%(md_signal))    
    
    #If the ImageList.TagGroup0.ImageTags.Tecnai metadata category exists, 
    #then retrieve everything from Technai.Microscope_Info 
    if ((hasattr(s.original_metadata.ImageList.TagGroup0.ImageTags, 'Tecnai')) == True):
        txt+=("\r\n  --Technai Detector\r\n")
        
        #String parsing of all contents of Technai.Microscope_Info begins 
        p = s.original_metadata.ImageList.TagGroup0.ImageTags.Tecnai.Microscope_Info
        #Microscope Info
        microsplit = p.split('User', maxsplit=1)    #Parses the string, stopping @ the word 'User'
        microscope_info = (microsplit[0])
        #Microscope User
        user_split = microsplit[1].split('Gun', maxsplit=1)      #Parses the string, stopping @ the word 'Gun'
        user = (user_split[0])

        #Gun Info
        gun_split = user_split[1].split('Extr volt ', maxsplit=1)       #Parses the string, stopping @ the word 'Mode'
        gun_info =(gun_split[0])

        #Extraction Voltage
        extr_split = gun_split[1].split('Gun Lens 1 Emission', maxsplit=1)
        extract_volt = (extr_split[0])

        #Gun Lens Emission Current
        g_lens_split = extr_split[1].split('Mode', maxsplit=1)
        g_lens_emission = (g_lens_split[0])

        #Microscope Mode
        modesplit = g_lens_split[1].split('Image Defocus (um)', maxsplit=1)
        micmode = (modesplit[0])

        #Image Defocus (um)
        defoc_split = modesplit[1].split('Magn', maxsplit=1)
        defocus = defoc_split[0]

        #Magnification 
        m_split = defoc_split[1].split('Spot', maxsplit=1)
        magn = m_split[0]
        
        #Microscope spot
        spotsplit = m_split[1].split('C2', maxsplit=1)        #Parses the string, stopping @ the word 'C2'
        spot_info = spotsplit[0]
        #C2
        c2split = spotsplit[1].split('C3', maxsplit=1)          #Parses the string, stopping @ the word 'C3'
        c2 = c2split[0]
        #C3
        c3split = c2split[1].split('Obj', maxsplit=1)           #Parses the string, stopping @ the word 'Obj'
        c3 = c3split[0]
        #Obj
        objsplit = c3split[1].split('Dif', maxsplit=1)          #Parses the string, stopping @ the word 'Dif'
        obj = objsplit[0]
        #Dif
        difsplit = objsplit[1].split('Image shift', maxsplit=1) #Parses the string, stopping @ the word 'Image shift'
        dif = difsplit[0]
        #Image shift
        imgshiftsplit = difsplit[1].split('Stage', maxsplit=1)  #Parses the string, stopping @ the word 'Stage'
        img_shift = imgshiftsplit[0]
        #Stage
        stagesplit = imgshiftsplit[1].split('C1 Aperture:', maxsplit=1) #Parses the string, stopping @ the word 'C1 Aperture'
        stage = stagesplit[0]
        #Condenser Aperture 1
        c1_ap_split = stagesplit[1].split('C2 Aperture:', maxsplit=1)   #Parses the string, stopping @ the word 'C2 Aperture'
        c1_aperture = c1_ap_split[0]
        #Condenser Aperture 2
        c2_ap_split = c1_ap_split[1].split('OBJ Aperture:', maxsplit=1) #Parses the string, stopping @ the word 'OBJ Aperture'
        c2_aperture = c2_ap_split[0]
        #Objective Aperture
        obj_ap_split = c2_ap_split[1].split('SA Aperture:', maxsplit =1)    #Parses the string, stopping @ the word 'SA Aperture'
        obj_aperture = obj_ap_split[0]
        #Selected Area Aperture
        sa_ap_split = obj_ap_split[1].split('Filter related settings:', maxsplit=1) #Parses the string, stopping @ the word 'Filter related settings:'
        sa_aperture = sa_ap_split[0]
        #Filter Related Settings
        filter_settings_split = sa_ap_split[1].split('Mode:', maxsplit=1)   #Parses the string, stopping @ the word 'Mode:'
        filter_related_settings = filter_settings_split[0]
        #Mode
        modesplit = filter_settings_split[1].split('Selected dispersion:', maxsplit=1)  #Parses the string, stopping @ the word 'Selected dispersion'
        mode = modesplit[0]
        #Selected dispersion
        sel_disp_split = modesplit[1].split('Selected aperture:', maxsplit=1)   #Parses the string, stopping @ the word 'Selected aperture:'
        selected_dispersion = sel_disp_split[0]
        #Selected Aperture
        sel_ap_split = sel_disp_split[1].split('Prism shift:', maxsplit=1)      #Parses the string, stopping @ the word 'Prism shift:'
        selected_aperture = sel_ap_split[0]
        #Prism Shift
        prismsplit = sel_ap_split[1].split('Drift tube:', maxsplit=1)           #Parses the string, stopping @ the word 'Drift tube:'
        prism_shift=prismsplit[0]
        #Drift Tube
        driftsplit = sel_ap_split[1].split('Total energy loss: ', maxsplit=1)   #Parses the string, stopping @ the word 'Total energy loss:'
        drift_tube = driftsplit[0]
        #Total Energy Loss
        energylosssplit = driftsplit[1].split(' ', maxsplit=1)          
        total_energy_loss = energylosssplit[0]
        txt+=("   %s\r\n"%(microscope_info))
        txt+=("   User: %s\r\n"%(user))
        txt+=("   Gun info: %s\r\n"%(gun_info))
        txt+=("   Extraction Voltage: %s\r\n"%(extract_volt))
        txt+=("   Gun lens emission: %s\r\n"%(g_lens_emission))
        txt+=("   Microscope Mode: %s\r\n"%(micmode))
        txt+=("   Image Defocus (um): %s\r\n"%(defocus))
        txt+=("   Magnification: %s\r\n"%(magn))
        txt+=("   Spot: %s\r\n"%(spot_info))
        txt+=("   C2: %s\r\n"%(c2))
        txt+=("   C3: %s\r\n"%(c3))
        txt+=("   Stage: %s\r\n"%(stage))
        txt+=("   Condenser Aperture 1: %s\r\n"%(c1_aperture))
        txt+=("   Condenser Aperture 2: %s\r\n"%(c2_aperture))
        txt+=("   Objective Aperture: %s\r\n"%(obj_aperture))
        txt+=("   Selected Area Aperture: %s\r\n"%(sa_aperture))
        txt+=("   Filter related settings: %s\r\n"%(filter_related_settings))
        txt+=("   Mode: %s\r\n"%(mode))
        txt+=("   Selected Dispersion: %s\r\n"%(selected_dispersion))
        txt+=("   Selected Aperture: %s\r\n"%(selected_aperture))
        txt+=("   Prism shift: %s\r\n"%(prism_shift))
        txt+=("   Drift tube: %s\r\n"%(drift_tube))
        txt+=("   Total energy loss: %s\r\n"%(total_energy_loss))
        f = codecs.open('%s_WJW.txt'%(filename),encoding='utf-8',mode='w+')
        f.write(txt)
        f.close()
        print('%s_WJW.txt metadata file has been produced'%(filename))
    else:
        f = codecs.open('%s_WJW.txt'%(filename),encoding='utf-8',mode='w+')
        f.write(txt)
        f.close()
        print('%s_WJW.txt metadata file has been produced'%(filename))
    

  



