VERY IMPORTANT: The 3 Python scripts must live in the same folder as your microscopy data

These files perform these functions:

1_data_2_hdf5.py: Converts dm3, dm4, emi, ser, mcr (so far) to hdf5.
2_hdf5_2_txt.py: Converts full original data (that got converted to hdf5) into a text file.
3_metadata_interest: these are (my) customized metadata of interest fields, this can be customized on a user basis. There is a switch where you can decide to batch convert an entire folder or one file at a time. Default is one file at a time.



To start:
1. Open up Git Bash, the change directory to where ever my data is (note Linux based)
2. Run Program in command line ( ex: "./1_data_2_hdf5.py" --> converts all data within current directory)
3. hdf5 or txt files are produced in current dir.