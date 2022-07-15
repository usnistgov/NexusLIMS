import requests
import os
from lxml import etree as et
import json
from typing import Union, Dict
from urllib.parse import unquote
from tqdm import tqdm

username = 'admin'
password = 'changeme'
url = 'https://nexuslims.url.com/'
fname = 'records.json'
root_path = os.environ.get('mmfnexus_path')


def get_all_docs(write_to_file: Union[bool, str] = False) -> Dict:
    r = requests.get(f'{url}rest/admin/data/', verify=False,
                     auth=(username, password))
    r.raise_for_status()

    if write_to_file:
        with open(write_to_file, 'w') as outfile:
            json.dump(r.json(), outfile)

    return r.json()


def parse_json_file(json_file: str) -> Dict:
    with open(json_file, 'r') as f:
        data = json.load(f)

    sizes = {}
    for d in tqdm(data):
        record_title = d['title']
        sizes[record_title] = 0
        doc = et.fromstring(d['xml_content'].encode())
        file_list = [unquote(t.text) for t in doc.xpath('//location')]
        for f in file_list:
            if f[0] == '/':
                f = f[1:]
            full_path = os.path.join(root_path, f)
            if os.path.isfile(full_path):
                sizes[record_title] += os.path.getsize(full_path)
            else:
                print(f"{f} was not found")

    return sizes


def sizeof_fmt(num, suffix="B"):
    # https://stackoverflow.com/a/1094933
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


if __name__ == "__main__":
    if not os.path.isfile(fname):
        get_all_docs(write_to_file=fname)
    sizes = parse_json_file(fname)
    total = 0
    for k, v in sizes.items():
        print(f"{sizeof_fmt(v)} : {k}")
        total += v
    print(f"total: {sizeof_fmt(total)}")