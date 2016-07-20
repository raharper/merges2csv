#   Copyright (C) 2015 Canonical Ltd.
#
#   Author: Ryan Harper <ryan.harper@canonical.com>
#   Author: Jon Grimm <jon.grimm@canonical.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

import argparse
import csv
import json
import subprocess
import sys
import urllib3

KEY_TO_HEADING = {
    'user': 'Last Uploader',
    'age': 'Days since last merge',
    'left_version': 'Ubuntu Version',
    'base_version': 'Upstream Version',
    'right_version': 'Debian Version'
}


def heading(key):
    return KEY_TO_HEADING.get(key, key)

# Prettify team names for output.
TEAM_TO_NAME = {
    'kubuntu-bugs': 'kubuntu',
    'desktop-packages': 'Desktop',
    'lubuntu-packaging': 'lubuntu',
    'ubuntuone-hackers': 'UbuntuOne',
    'ubuntu-sdk-bugs': 'SDK',
    'snappy-dev': 'Snappy-Dev',
    'edubuntu-bugs': 'edubuntu',
    'dx-packages': 'Desktop-DX',
    'mir-team': 'MIR Team',
    'ubuntu-security-bugs': 'Security',
    'translators-packages': 'Translators',
    'ubuntu-apps-bugs': 'Unity-Apps',
    'unsubscribed': '',
    'ubuntu-printing': 'Print',
    'ubuntu-server': 'Server',
    'kernel-packages': 'Kernel',
    'ubuntu-phonedations-bugs': 'Phone',
    'checkbox-bugs': 'Checkbox',
    'pkg-ime': 'IME',
    'ubuntu-openstack': 'OpenStack',
    'unity-api-bugs': 'Unity-API',
    'libertine-team': 'Libertine',
    'unity-ui-bugs': 'Unity-UI',
    'ubuntu-webapps-bugs': 'WebApps',
    'xubuntu-bugs': 'xubuntu',
    'maas-maintainers': 'MAAS',
    'documentation-packages': 'Docs',
    'foundations-bugs': 'Foundations',
}

# Parse command line args.
parser = argparse.ArgumentParser(
    description="""Helper to convert merges.ubuntu.com to CSV file.""")
parser.add_argument('COMPONENT', help="""E.g. main, universe, or multiverse""")
parser.add_argument('--exclude-same-upstream', default=True,
                    dest='exclude_same',
                    action='store_true',
                    help="""Only output packages where Debian upstream
                    version is greater than the Ubuntu upstream.""")
parser.add_argument('--team', default=None,
                    help="""Only output packages
                    belonging to specificified team,
                    for example 'ubuntu-server'""")
parser.add_argument('--outfilename', default=None,
                    help="""Override the default output filename of
                    merges-<COMPONENT>.csv""")
args = parser.parse_args()

URL = 'https://merges.ubuntu.com/%s.json' % args.COMPONENT
MAP = 'http://people.canonical.com/~ubuntu-archive/package-team-mapping.json'

# Download json from merges
http = urllib3.PoolManager()
print('Downloading merge data from ' + URL)
mergereq = http.request('GET', URL)
if mergereq.status != 200:
    print('Failed to fetch: ' + URL)
    sys.exit(1)

print('Downloading team package map from ' + MAP)
mapreq = http.request('GET', MAP)
if mapreq.status != 200:
    print('Failed to fetch: ' + MAP)
    sys.exit(1)


def dpkg_compare_versions(upkg, dpkg):
    if "-" in upkg:
        uver = upkg.split("-")[0]
        dver = dpkg.split("-")[0]
    else:
        uver = upkg
        dver = dpkg

    result = ""
    if uver == dver:
        result = "="
        return result

    ge = subprocess.call(['dpkg', '--compare-versions', upkg, 'ge', dpkg])
    if ge == 0:
        return ">"
    else:
        return "<"


merges = json.loads(mergereq.data.decode('utf-8'))
team_pkgs = json.loads(mapreq.data.decode('utf-8'))

# List of teams we care about. Currently, all or one team
if args.team is not None:
    if args.team in team_pkgs:
        teams = [args.team]
    else:
        # Let's help the poor user with names that we know about.
        print("Error: The team '{}' does not exist".format(args.team))
        print("Here are the currently known teams: ")
        for key, _ in team_pkgs.items():
            print("  "+key)
        sys.exit(1)
else:
    teams = team_pkgs.keys()

if args.outfilename is not None:
    outfilename = args.outfilename
else:
    outfilename = 'merges-%s.csv' % args.COMPONENT

with open(outfilename, 'w') as f:
    writer = csv.writer(f, lineterminator="\n")
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
        skip = False
        dataline = []

        # Walk the CSV keys for special processing.
        for key in key_order:
            if key == 'vs debian':
                value = dpkg_compare_versions(package['left_version'],
                                              package['right_version'])

                # Limit to only showing where Ubuntu is downlevel at upstream
                if args.exclude_same:
                    if value != '<':
                        skip = True

                # google sheets requires leading tick to indicate field
                # is not a formula
                if value == '=':
                    value = "'="
            elif key == 'responsibility':
                for team in teams:
                    if package['source_package'] in team_pkgs[team]:
                        teamname = TEAM_TO_NAME.get(team, team)
                        if key in package:
                            package['responsibility'] += ", " + teamname
                        else:
                            package['responsibility'] = teamname
                        value = package.get(key, '')
                    else:
                        skip = True
            else:
                value = package.get(key, '')

            dataline.append(value)

        if not skip:
            writer.writerow(dataline)

print('Wrote %s' % outfilename)
