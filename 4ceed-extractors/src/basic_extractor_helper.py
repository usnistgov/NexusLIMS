import matplotlib
matplotlib.use('Agg')
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import hyperspy.api as hs
import numpy as np
import shutil

def getdm3(input_file):
    metadata = dict()
    f = hs.load(input_file)
    # Name
    if ((hasattr(f.original_metadata.ImageList.TagGroup0, 'Name')) == True):
        metadata['Name'] = f.original_metadata.ImageList.TagGroup0.Name
    # DataBar.AcquisitionDate    AcqTime     ExposureNumber
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'DataBar')) == True):
        metadata['AcquisitionDate'] = f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Acquisition_Date
        metadata['AcquisitionTime'] = f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Acquisition_Time
        metadata['ExposureNumber'] = f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Exposure_Number
        if (hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar, 'Exposure_Time_s')) == True:
            metadata['ExposureTime(s)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Exposure_Time_s
    ImageTags_metadata = dict()
    # ImageTags.DataBar.DeviceName,
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'DataBar')) == True):
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar, 'Device_Name')) == True):
            ImageTags_metadata['DeviceName'] = f.original_metadata.ImageList.TagGroup0.ImageTags.DataBar.Device_Name

    # ImageTags.MicroscopeInfo
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'Microscope_Info')) == True):
        ImageTags_MicroscopeInfo = dict()
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info,
                     'Actual_Magnification')) == True):
            ImageTags_MicroscopeInfo[
                'ActualMagnification'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Actual_Magnification
        try:
            ImageTags_MicroscopeInfo['Cs(mm)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Csmm
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'EmissionCurrent(uA)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Emission_Current_A
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'IlluminationMode'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Illumination_Mode
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'ImagingMode'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Imaging_Mode
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'IndicatedMagnification'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Indicated_Magnification
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'Microscope'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Microscope
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'DetectorName?'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Name
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'OperationMode'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Operation_Mode
        except:
            pass
        try:
            ImageTags_MicroscopeInfo[
                'Operator'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Operator
        except:
            pass
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Probe_Current_nA')) == True):
            ImageTags_MicroscopeInfo[
                'ProbeCurrent(nA)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Probe_Current_nA
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'Probe_Size_nm')) == True):
            ImageTags_MicroscopeInfo[
                'ProbeSize(nm)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Probe_Size_nm
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info, 'STEM_Camera_Length')) == True):
            ImageTags_MicroscopeInfo[
                'STEMCameraLength'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.STEM_Camera_Length
        try:
            ImageTags_MicroscopeInfo['Voltage'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Voltage
        except:
            pass
        metadata['MicroscopeInfo'] = ImageTags_MicroscopeInfo
    # X&Y-DimScaling
    ImageData_metadata = dict()
    # ImageData.Calibrations
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData, 'Calibrations')) == True):
        ImageData_Calibrations_metadata = dict()
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations, 'Dimension')) == True):
            if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension,
                         'TagGroup0')) == True):
                ImageData_Calibrations_metadata[
                    'X-DimensionScaling'] = f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup0.as_dictionary()
            if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension,
                         'TagGroup1')) == True):
                ImageData_Calibrations_metadata[
                    'Y-DimensionScaling'] = f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup1.as_dictionary()
            if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations, 'Brightness')) == True):
                ImageData_Calibrations_metadata[
                    'Brightness'] = f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Brightness.as_dictionary()
            ImageData_metadata['Calibrations'] = ImageData_Calibrations_metadata
    # ImageData.Dimensions
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData, 'Dimensions')) == True):
        ImageData_metadata[
            'ImageDimensions'] = f.original_metadata.ImageList.TagGroup0.ImageData.Dimensions.as_dictionary()
    # ImageData.DataType
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageData, 'DataType')) == True):
        ImageData_metadata['DataType'] = f.original_metadata.ImageList.TagGroup0.ImageData.DataType
    # ImageData.PixelDepth
    try:
        ImageData_metadata['ImagePixelDepth'] = f.original_metadata.ImageList.TagGroup0.ImageData.PixelDepth
    except:
        pass
    metadata['ImageData'] = ImageData_metadata
    # ImageTags.Device
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'Tecnai')) == True):
        try:
            tecnai_metadata = f.original_metadata.ImageList.TagGroup0.ImageTags.Tecnai.Microscope_Info
            tecnai_clean = dict()
            tecnai_clean = tecnai_metadata.replace('\u2028', '\n').splitlines()
            # String Find User and take argument following:
            ImageTags_metadata['Tecnai'] = tecnai_clean
        except:
            pass
    # EELS Detector
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'EELS')) == True):
        eels_metadata = dict()
        try:
            eels_metadata[
                'NumberOfFrames'] = f.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Number_of_frames
        except:
            pass
        try:
            eels_metadata[
                'Spectrometer'] = f.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Acquisition.Spectrometer.as_dictionary()
        except:
            pass
        try:
            eels_metadata[
                'ExperimentalConditions'] = f.original_metadata.ImageList.TagGroup0.ImageTags.EELS.Experimental_Conditions.as_dictionary()
        except:
            pass
        ImageTags_metadata['EELS'] = eels_metadata
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'Meta_Data')) == True):
        ImageTags_metadata['Meta Data'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Meta_Data.as_dictionary()
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'Acquisition')) == True):
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition, 'Device')) == True):
            ImageTags_metadata[
                'Device'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Device.as_dictionary()
        # ImageTags.Acquisition.Frame.Area.Transform.TransformList.TagGroup0
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Area.Transform.Transform_List,
                     'TagGroup0')) == True):
            ImageTags_transform = dict()
            try:
                ImageTags_transform[
                    'Binning'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Area.Transform.Transform_List.TagGroup0.Binning
            except:
                pass
            try:
                ImageTags_transform[
                    'SubAreaAdjust'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Area.Transform.Transform_List.TagGroup0.Sub_Area_Adjust
            except:
                pass
            ImageTags_metadata['Transform'] = ImageTags_transform
        # ImageTags.Acquisition.Frame.Intensity
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame, 'Intensity')) == True):
            if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity,
                         'Range')) == True):
                ImageTags_metadata[
                    'Intensity'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Intensity.Range.as_dictionary()
        # ImageTags.Acquisition.Frame.ReferenceImages
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame, 'Reference_Images')) == True):
            ImageTags_metadata[
                'ReferenceImages'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Reference_Images.as_dictionary()
        # ImageTags.Acquisition.Frame.Sequence
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame, 'Sequence')) == True):
            ImageTags_metadata[
                'Sequence'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Frame.Sequence.as_dictionary()
        # ImageTags.Acquisition.Parameters.Detector
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters, 'Detector')) == True):
            if ((
                        hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector,
                                'Do_Continuous_Readout')) == True):
                ImageTags_metadata[
                    'Detector Readout Continuous'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Detector.Do_Continuous_Readout
        # ImageTags.Acquisition.Parameters.Environment
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters, 'Environment')) == True):
            ImageTags_metadata[
                'ModeName'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.Environment.Mode_Name
        # ImageTags.Acquisition.Parameters.High_Level
        if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters, 'High_Level')) == True):
            ImageTags_HighLevel = dict()
            try:
                ImageTags_HighLevel[
                    'Antiblooming'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Antiblooming
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'CCDReadArea'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.CCD_Read_Area
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'Exposure(s)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Exposure_s
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'NumberOfFrameShutters'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Number_Of_Frame_Shutters
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'Processing'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Processing
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'SecondaryShutterPostExposureCompensations(s)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Secondary_Shutter_Post_Exposure_Compensation_s
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'SecondaryShutterPretExposureCompensations(s)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Secondary_Shutter_Pre_Exposure_Compensation_s
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'Shutter'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Shutter.as_dictionary()
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'ShutterPostExposureCompensations(s)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Shutter_Post_Exposure_Compensation_s
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'ShutterPreExposureCompensations(s)'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Shutter_Pre_Exposure_Compensation_s
            except:
                pass
            try:
                ImageTags_HighLevel[
                    'Transform'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Acquisition.Parameters.High_Level.Transform.as_dictionary()
            except:
                pass
            ImageTags_metadata['HighLevel'] = ImageTags_HighLevel
    # DigiScan Detector
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'DigiScan')) == True):
        ImageTags_metadata['DigiScan'] = f.original_metadata.ImageList.TagGroup0.ImageTags.DigiScan.as_dictionary()
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'SI')) == True):
        ImageTags_metadata['SI'] = f.original_metadata.ImageList.TagGroup0.ImageTags.SI.as_dictionary()
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'Private')) == True):
        private_metadata = f.original_metadata.ImageList.TagGroup0.ImageTags.Private.as_dictionary()
        ImageTags_metadata['Private'] = private_metadata
    if ((hasattr(f.original_metadata.ImageList.TagGroup0.ImageTags, 'Source')) == True):
        ImageTags_metadata['Source'] = f.original_metadata.ImageList.TagGroup0.ImageTags.Source
    metadata['ImageTags'] = ImageTags_metadata
    # AnnotationGroupList
    if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.AnnotationGroupList, 'TagGroup0')) == True):
        # Count number of TagGroups to see how many user input annotations were added
        AnnotationGroupList_metadata = dict()
        try:
            AnnotationGroupList_metadata[
                'AnnotationType'] = f.original_metadata.DocumentObjectList.TagGroup0.AnnotationGroupList.TagGroup0.AnnotationType
        except:
            pass
        try:
            AnnotationGroupList_metadata['AnnotationKey'] = "2=line, 5=rectangle, 6=oval, 13=text, 20=?, 31=scale bar"
        except:
            pass
        try:
            AnnotationGroupList_metadata[
                'Rectangle'] = f.original_metadata.DocumentObjectList.TagGroup0.AnnotationGroupList.TagGroup0.Rectangle
        except:
            pass
        metadata['AnnotationGroupList'] = AnnotationGroupList_metadata
    # ImageDisplayInfo
    if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0, 'ImageDisplayInfo')) == True):
        ImageDisplayInfo_metadata = dict()
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'CLUTName')) == True):
            ImageDisplayInfo_metadata[
                'CLUTName'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.CLUTName
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'DoAutoSurvey')) == True):
            ImageDisplayInfo_metadata[
                'DoAutoSurvey'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.DoAutoSurvey
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'EstimatedMax')) == True):
            ImageDisplayInfo_metadata[
                'EstimatedMax'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.EstimatedMax
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'EstimatedMin')) == True):
            ImageDisplayInfo_metadata[
                'EstimatedMin'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.EstimatedMin
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'HighLimit')) == True):
            ImageDisplayInfo_metadata[
                'HighLimit'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.HighLimit
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'LowLimit')) == True):
            ImageDisplayInfo_metadata[
                'LowLimit'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.LowLimit
        if ((hasattr(f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo, 'IsInverted')) == True):
            ImageDisplayInfo_metadata[
                'IsInverted'] = f.original_metadata.DocumentObjectList.TagGroup0.ImageDisplayInfo.IsInverted
        metadata['ImageDisplayInfo'] = ImageDisplayInfo_metadata
        return metadata
#Reads in and parses bytes from .emi files, needs to have error handling implemented in the future
def getemi(file_name):
    with open(file_name, 'rb') as f:
        text = f.read()
        metadata = dict()
        # Parse MD from XML
        textstring = str(text)
        object_info_start = textstring.split("<ObjectInfo>")
        object_info = object_info_start[1].split("</ObjectInfo>")
        root_start = object_info[0].split("<ExperimentalDescription>")
        root_obj = root_start[1].split("</ExperimentalDescription>")
        root_obj_2 = root_obj[0].split("\\r\\n\\t")
        # UUID
        uuid_start = object_info[0].split("<Uuid>")
        uuid_end = uuid_start[1].split("</Uuid>")
        uuid_contents = str("UUID: " + uuid_end[0])
        metadata['UUID'] = uuid_contents
        # ExperimentalConditions
        ExperimentalConditions_dic = dict()
        # MicroscopeConditions
        miccond_dic = dict()
        # AcceleratingVoltage
        accelv_start = object_info[0].split("<AcceleratingVoltage>")
        accelv_end = accelv_start[1].split("</AcceleratingVoltage>")
        accelv_contents = str("AcceleratingVoltage: " + accelv_end[0])
        miccond_dic['AcceleratingVoltage'] = accelv_contents
        # Tilt1
        tilt1_start = object_info[0].split("<Tilt1>")
        tilt1_end = tilt1_start[1].split("</Tilt1>")
        tilt1_contents = str("Tilt1: " + tilt1_end[0])
        miccond_dic['Tilt1'] = tilt1_contents
        # Tilt2
        tilt2_start = object_info[0].split("<Tilt2>")
        tilt2_end = tilt2_start[1].split("</Tilt2>")
        tilt2_contents = str("Tilt2: " + tilt2_end[0])
        miccond_dic['Tilt2'] = tilt2_contents
        ExperimentalConditions_dic['MicroscopeConditions'] = miccond_dic
        metadata['ExperimentalConditions'] = ExperimentalConditions_dic
        # Begin ExperimentalDescription subsection
        root = ET.fromstring(root_obj_2[0])
        label_list = []
        value_list = []
        unit_list = []
        x = 0
        for item in root:
            label_name = root[x][0].text
            value = root[x][1].text
            units = root[x][2].text
            label_list.append(label_name)
            value_list.append(value)
            unit_list.append(units)
            x = x + 1
        # Combine ExpDesc. metadata label, value and units
        y = 0
        expdesc_dic = dict()
        for items in label_list:
            label = ": " + (str(value_list[y])) + " (units:" + str(unit_list[y]) + ")\n"
            expdesc_dic[label_list[y]] = label
            y = y + 1
        metadata['ExperimentalDescription'] = expdesc_dic
        # AcquisitionDate
        acqdate_start = object_info[0].split("<AcquireDate>")
        acqdate_end = acqdate_start[1].split("</AcquireDate>")
        acqdate_contents = str("AcquisitionDate: " + acqdate_end[0])
        metadata['AcquisitionDate'] = acqdate_contents
        # StartAcquisitionInfo
        acqinfo_dic = dict()
        root_start1 = object_info[0].split("</AcquireDate>")
        root_obj1 = root_start1[1].split("<Manufacturer>")
        root1 = ET.fromstring(root_obj1[0])
        acqinfo_label_list = []
        acqinfo_value_list = []
        x = 0
        for item in root1:
            label_name = root1[x].tag
            value = root1[x].text
            acqinfo_label_list.append(label_name)
            acqinfo_value_list.append(value)
            x = x + 1
        # Combine metadata label, value
        y = 0
        acqinfo_contents = str()
        for items in acqinfo_label_list:
            label = ": " + (str(acqinfo_value_list[y])) + "\n"
            acqinfo_dic[acqinfo_label_list[y]] = label
            y = y + 1
        metadata['AcquisitionInfo'] = acqinfo_dic
        # Begin Manufacturer portion
        root_start2 = object_info[0].split("</AcquireInfo>")
        root_end2 = root_start2[1].split("<DetectorRange>")
        fix = "<root>" + root_end2[0] + "</root>"
        root2 = ET.fromstring(fix)
        last_label_list = []
        last_value_list = []
        x = 0
        for item in root2:
            label_name = root2[x].tag
            value = root2[x].text
            last_label_list.append(label_name)
            last_value_list.append(value)
            label = ": " + (str(last_value_list[x])) + "\n"
            metadata[last_label_list[x]] = label
            x = x + 1
            # begindetectorrange
        fix2 = "<root>" + "<DetectorRange>" + root_end2[1] + "</root>"
        root3 = ET.fromstring(fix2)
        lab_list = []
        val_list = []
        finstr = str()
        detectorrange_dic = dict()
        x = 0
        for item in root3[0]:
            label_name = root3[0][x].tag
            value = root3[0][x].text
            lab_list.append(label_name)
            val_list.append(value)
            cont = ": " + str(val_list[x]) + "\n"
            detectorrange_dic[lab_list[x]] = cont
            x = x + 1
        metadata['DetectorRange'] = detectorrange_dic
        return metadata
#The getTif function is incomplete at the moment, this code works, but the curator forces tif files to be handled by their own extractors, so Tif's cannot be processed by HyperSpy
def getTif(input_file):
    metadata=dict()
    f=hs.load(input_file)
    if ((hasattr(f.original_metadata, 'fei_metadata'))==True):
        metadata['FEI_metadata']=f.original_metadata.fei_metadata.as_dictionary()
    return metadata

def getMetadata(input_file):
    metadata=dict()
    ftype=str(input_file)
    if ftype.endswith(".dm3", -4):
        metadata=getdm3(input_file)
        return metadata
    if ftype.endswith(".emi",-4):
        metadata[
            'Warning'] = "Warning, this file is associated with files starting with the same prefix. Don't change filename"
        metadata=getemi(input_file)
        return metadata
    if ftype.endswith(".ser",-4):
        metadata['Warning']="Warning, this file is associated with files starting with the same prefix. Don't change filename. The corresponding metadata for this file can be found in the emi file with the same prefix"
        return metadata
    if ftype.endswith(".tif", -4):
        metadata=getTif(input_file)
        print(metadata)
    
    else:
        return metadata

def makePreview(input_file, target):
    ftype = str(input_file)
    if ftype.endswith(".dm3", -4):
        f=hs.load(input_file)
        #if f.data.ndim < 2:
            #print("signal is 1D")
            #y_data=f.data
            #signal_name = f.original_metadata.ImageList.TagGroup0.Name
            #x_step = float(f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup0.Scale)
            #x_origin = float(f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup0.Origin)
            #x_units = f.original_metadata.ImageList.TagGroup0.ImageData.Calibrations.Dimension.TagGroup0.Units
            #x_data = np.arange(x_origin, (len(y_data) * x_step), x_step)
            #plt.plot(x_data, y_data, 'bo')
            #plt.grid(True)
            #plt.title("%s Signal" %signal_name)
            #plt.xlabel("x axis (%s)" %x_units)
            #plt.ylabel("Intensity")
            #plt.savefig(target)
        if (f.data.ndim == 2)==True:
            if (f.data.shape[0] == f.data.shape[1]) == True:
                spec_img=hs.plot.plot_images(f)
                spec_img_fig = spec_img.get_figure()
                spec_img_fig.savefig(target)
            if (f.data.shape[0] != f.data.shape[1]) == True:
                spec_plot_img=hs.plot.plot_spectra(f, style='heatmap')
                spec_plot_fig=spec_plot_img.get_figure()
                spec_plot_fig.savefig(target, overwrite=True)
        #Makes previews for 3D data such as Spectrum Images
        if (f.data.ndim == 3) == True: 
            x_dim= int((eels.data[:,0,0].shape)[0])
            y_dim= int((eels.data[0,:,0].shape)[0])
            pix_arr = np.zeros(shape=(x_dim,y_dim))
            cntx=0
            while cntx < x_dim:
                cnty=0
                while cnty < y_dim:
                    pix_arr[cntx][cnty]+=np.sum(f.data[cntx][cnty])
                    cnty=cnty+1
                cntx=cntx+1
            title=f.metadata.General.original_filename
            image=hs.signals.Signal1D(pix_arr)
            image.metadata.General.title = title
            thrD_img=hs.plot.plot_spectra(image, style='heatmap')
            fig=thrD_img.get_figure()
            fig.savefig(target, overwrite=True)
        else:
            f.save(target, overwrite=True)

    if ftype.endswith(".ser", -4):
        f = hs.load(input_file)
        if (f.data.shape[0] != f.data.shape[1]):
                img = hs.plot.plot_spectra(f, style='heatmap')
                fig = img.get_figure()
                fig.savefig(target, overwrite=True)
        else:
            f.save(target, overwrite=True)
