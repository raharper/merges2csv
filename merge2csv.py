#   Copyright (C) 2013 Canonical Ltd.
#
#   Author: Ryan Harper <ryan.harper@canonical.com>
#
#   Curtin is free software: you can redistribute it and/or modify it under
#   the terms of the GNU Affero General Public License as published by the
#   Free Software Foundation, either version 3 of the License, or (at your
#   option) any later version.
#
#   Curtin is distributed in the hope that it will be useful, but WITHOUT ANY
#   WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#   FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
#   more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with Curtin.  If not, see <http://www.gnu.org/licenses/>.


import csv
import json
import subprocess
import sys
import urllib3


POCKET = sys.argv[1]
URL = 'https://merges.ubuntu.com/%s.json' % POCKET

# download json from merges
http = urllib3.PoolManager()
print('Downloading merge data from ' + URL)
r = http.request('GET', URL)
if r.status != 200:
    print('Failed to fetch: ' + URL)
    sys.exit(1)

def dpkg_compare_versions(upkg, dpkg):
    if "-" in upkg:
        uver = upkg.split("-")[0]
        dver = dpkg.split("-")[0]
    else:
        uver = upkg
        dver = dpkg

    result=""
    if uver == dver:
        result = "="
        return result

    ge = subprocess.call(['dpkg', '--compare-versions', upkg, 'ge', dpkg])
    if ge == 0:
        return ">"
    else:
        return "<"

KEY_TO_HEADING = {
    'user': 'Last Uploader',
    'age' : 'Days since last merge',
    'left_version': 'Ubuntu Version',
    'base_version': 'Upstream Version',
    'right_version': 'Debian Version'
}
def heading(key):
    return KEY_TO_HEADING.get(key, key)

merges = json.loads(r.data.decode('utf-8'))
#merges = json.loads(open("%s.json" % pocket, "r").read())

with open('merges-%s.csv' % POCKET , 'w') as f:
    writer = csv.writer(f)
    header_order = [
            heading('source_package'),
            heading('Responsibility'),
            heading('Status'),
            heading('Progress'),
            heading('left_version'),
            heading('right_version'),
            heading('vs debian'),
            heading('base_version'),
            heading('age'),
            heading('user'),
            heading('link'),
            heading('uploader'),
            heading('binaries'),
            heading('short_description'),
            heading('uploaded'),
    ]
    key_order = [
            ('source_package'),
            ('responsibility'),
            ('status'),
            ('progress'),
            ('left_version'),
            ('right_version'),
            ('vs debian'),
            ('base_version'),
            ('age'),
            ('user'),
            ('link'),
            ('uploader'),
            ('binaries'),
            ('short_description'),
            ('uploaded'),
    ]
    writer.writerow(header_order)

    for package in merges:
        #print('{}:'.format(package['source_package']))
        dataline = []
        for key in key_order:
            if key == 'vs debian':
                value = dpkg_compare_versions(package['left_version'],
                                              package['right_version'])
                # google sheets requires leading tick to indicate field
                # is not a formula
                if value == '=':
                    value = "'="
            else:
                value = package.get(key, '')
            #print('  {}: {}'.format(key, value))
            dataline.append(value)

        #print(dataline)
        writer.writerow(dataline)

print('Wrote merges-%s.csv' % POCKET)
