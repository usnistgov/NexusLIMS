This directory contains miscellaneous files for support the NEXUS lab
in MDCS.  In particular, it includes:

* `validate`, `validate.cmd` -- a script (for *nix, windows) for executing
  the JUNX XML validator.
* `schemaLocation4windows.txt` -- an example schemaLocation.txt file for
  indicating the location of XML schemas on Windows (used by validate).
* `schemaLocation4nix.txt` -- an example schemaLocation.txt file for
  indicating the location of XML schemas on Linux/Mac (used by validate).

## Executing validate

```
validate [ -qh ] [ -S schemaLocFile ] xmlfile ...
  -h      print this usage (ignore all other input)
  -q      print nothing to standard out; only set the exit code
  -s      print nothing to standard out or error; only set the exit code
  -S schemaLocFile  set the schema cache via a schema location file

Each line in a schemaLocFile gives a namespace, a space, and local file path.
The file path is the location of the Schema (.xsd) document for that namespace.
```
## About schemaLocation.txt files

The `validate` tool needs to know where to find schemas to check XML
documents against; schemaLocation files provide that information to
`validate`.  Each line in such a file maps a namespace URI to a file path on disk 
where the corresponding XSD schema file is located.  If there is a
file called `schemaLocation.txt` in the directory where validate is
run, that that file will be read automatically (unless `-S` is used).
The `-S` option allows a different file to be read. 

This directory contains 2 examples of schemaLocation files, one
appropriate for windows and one for Linux/Mac.  Edit one of these to
change the file paths to point to files in the `mdcs/schemas`
directory in your local `NexusMicroscopyNIMS` repository.  Next copy
it to the directory where your XML files are located, naming it
`schemaLocation.txt`.

## More about validate and JUNX

Find the validate tool attached to the NexusMicroscopyNIMS wiki.

For more about JUNX, see https://github.com/RayPlante/junx.

