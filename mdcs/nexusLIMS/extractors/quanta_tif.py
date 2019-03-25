def get_metadata(filename):
    """
    Returns the metadata (as a string) from a .tif file saved by the FEI Quanta
    SEM in the Nexus Microscopy Facility

    Parameters
    ----------
    filename : str
        path to a .tif file saved by the Quanta

    Returns
    -------
    metadata : str
        The metadata text extracted from the file
    """
    with open(filename, 'rb') as f:
        content = f.read()
    metadata_bytes = content[content.find(b'[User]'):]
    metadata = metadata_bytes.decode().replace('\r\n', '\n')

    return metadata


# if __name__ == '__main__':
#     """
#     These lines are just for testing. For real use, import the methods you
#     need and operate from there
#     """
#     meta = get_metadata('/mnt/***REMOVED***/Quanta/***REMOVED***/171218 - Evergreen '
#                         'Sprig - Quanta/quad1image_001.tif')
#
#     print(meta)
