#  NIST Public License - 2019
#
#  This software was developed by employees of the National Institute of
#  Standards and Technology (NIST), an agency of the Federal Government
#  and is being made available as a public service. Pursuant to title 17
#  United States Code Section 105, works of NIST employees are not subject
#  to copyright protection in the United States.  This software may be
#  subject to foreign copyright.  Permission in the United States and in
#  foreign countries, to the extent that NIST may hold copyright, to use,
#  copy, modify, create derivative works, and distribute this software and
#  its documentation without fee is hereby granted on a non-exclusive basis,
#  provided that this notice and disclaimer of warranty appears in all copies.
#
#  THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
#  EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
#  TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
#  IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
#  AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION
#  WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE
#  ERROR FREE.  IN NO EVENT SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING,
#  BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES,
#  ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE,
#  WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER
#  OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND
#  WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF,
#  OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.
#

"""
This script takes two paths as input, and will duplicate the folder structure
(without the files) contained in the input_path at the output_path's location.
"""

import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("input_path",
                    help="the path to the directory structure that should be "
                         "copied")
parser.add_argument("output_path",
                    help="the path to which the input directory structure "
                         "should be copied")
parser.add_argument("-v", "--verbose",
                    help="print directories to be copied",
                    action="store_true")
parser.add_argument("-n", "--dry-run",
                    help="do not actually do any directory creation "
                         "(use with -v to preview what will be done)",
                    action="store_true")

if __name__ == '__main__':
    args = parser.parse_args()

    if args.dry_run:
        print("*** DRY RUN SPECIFIED; NO DIRECTORIES ARE BEING CREATED ***\n")

    for p in args.input_path, args.output_path:
        if not os.path.isdir(p):
            raise NotADirectoryError(f''
                                     f'"{p}" is not a valid directory. Please '
                                     f'check the input and try again, making '
                                     f'sure to create the output directory '
                                     f'before running this script.')

    # Shamelessly stolen from https://stackoverflow.com/a/40829525/1435788:
    for dir_path, dir_names, _ in os.walk(args.input_path):

        rel_path = os.path.relpath(dir_path, start=args.input_path)

        # skip the first iteration, since the current directory always exists
        if rel_path == '.':
            continue

        structure = os.path.join(args.output_path,
                                 rel_path)
        if args.verbose:
            print(structure)
        if not os.path.isdir(structure):
            if not args.dry_run:
                os.mkdir(structure)
        else:
            if args.verbose:
                print(f"!! {structure} already exists !!")
