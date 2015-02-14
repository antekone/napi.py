#!/usr/bin/python -W ignore
# -*- coding: utf-8 -*-
# $Id$
#
# Windows support added by Grzegorz Antoniak (http://anadoxin.org/blog)
#

from __future__ import with_statement

__version__   = 'version 0.5-a1'
__author__    = 'Marcin ``MySZ`` Sztolcman <marcin@urzenia.net> (based od napi.py from http://hacking.apcoh.com/2008/01/napi_06.html - 0.15b)'
__copyright__ = '(r) 2008 - 2009'
__program__   = 'napi.py - find and download polish subtitles for films (from http://www.napiprojekt.pl/)'
__date__      = '2008-11-21'
__license__   = 'GPL v.2'

__desc__      = '''%(desc)s
%(author)s %(copyright)s
license: %(license)s
%(version)s (%(date)s)''' % {
  'desc': __program__,
  'author': __author__,
  'copyright': __copyright__,
  'license': __license__,
  'version': __version__,
  'date': __date__
}

import hashlib
import os, os.path
import re
import subprocess
import sys
import urllib
from distutils import spawn

def calculate_md5 (path):
    with open (path, 'rb') as fh:
        return hashlib.md5 (fh.read (10485760)).hexdigest ()

def calculate_f (md5digest):
    idx = ( 0xe, 0x3,  0x6, 0x8, 0x2 )
    mul = (   2,   2,    5,   4,   3 )
    add = (   0, 0xd, 0x10, 0xb, 0x5 )

    b = []
    for a, m, i in zip (add, mul, idx):
        t = a + int (md5digest[i], 16)
        v = int (md5digest[t:t+2], 16)
        b.append ( ('%x' % (v*m))[-1] )

    return ''.join (b)

def probe_for_7zip():
    # Try locations from %PATH% first. please note that this will
    # not support situations like this:
    #
    # set PATH=%PATH%;"c:\program files\7-zip"
    #
    # but it will handle this:
    #
    # set PATH=%PATH%:c:\program files\7-zip
    #
    # it seems to be a bug in find_executable(). This method will
    # search current directory as well.

    exepath = spawn.find_executable("7z.exe")
    if exepath is not None:
        return exepath

    # Try to use REG.EXE to read registry settings at:
    #
    # HKEY_CURRENT_USER\SOFTWARE\7-zip, value Path
    #
    # This key should contain 7-zip's install directory.

    proc = subprocess.Popen(["reg", "query", "hkcu\\software\\7-zip", "/v", "path"], stdout=subprocess.PIPE)

    stdout,stderr = proc.communicate()
    lines = str(stdout).split("\n")
    for line in lines:
        line = line.strip()
        m = re.match('^[Pp]ath[ ]*REG_SZ[ ]*(.*)$', line)
        if m:
            exepath = os.path.join(m.group(1), "7z.exe")
            if os.path.exists(exepath):
                return exepath

    # If above methods won't work, just try to use hardcoded
    # default install locations.

    for hdir in [ "c:\\program files\\7-zip",
            "c:\\program files (x86)\\7-zip" ]:
        exename = os.path.join(hdir, "7z.exe")
        if os.path.exists(exename):
            return exename

    return None

def extract_subtitles (data):
    # create temporary archive for 7zip
    fh_arch_path = os.tempnam (None, 'sub_')
    with open (fh_arch_path, 'wb') as fh:
        fh.write (data)

    if os.name == 'nt':
        path_to_7zip = probe_for_7zip()
        if path_to_7zip is None:
            print("Please install 7-Zip first, or at least put 7z.exe somewhere into your %PATH%.")
            sys.exit(1)
    else:
        path_to_7zip = '7za'

    # extract archive and write it to second temporary file
    cmd = (path_to_7zip, 'x', '-y', '-so', '-bd', '-piBlm8NTigvru0Jr0', fh_arch_path, )

    p = subprocess.Popen (cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate ()

    # remove temporary archive
    try:
        os.remove (fh_arch_path)
    except:
        pass

    if p.returncode != 0:
        return False

    # return content of subtitles
    return stdout

def get_subtitles (film, output=None):
    if not os.path.isfile (film):
        return False

    md5 = calculate_md5 (film)

    url = 'http://napiprojekt.pl/unit_napisy/dl.php?l=PL&f=%s&t=%s&v=other&kolejka=false&nick=&pass=&napios=%s'
    url %= (md5, calculate_f (md5), os.name)

    # download and extract subtitles if found
    data = urllib.urlopen (url).read ()
    data = extract_subtitles (data)
    if not data:
        return False

    # find output directory and correct subtitles filename
    dname, fname = os.path.split (film)
    if output and os.path.isdir (output):
        dname   = output
    elif not dname:
        dname   = os.getcwd ()

    # write subtitles file in right directory
    fname = os.path.splitext (fname)[0] + '.txt'
    with open (os.path.join (dname, fname), 'w') as fh:
        fh.write (data)

    return True

def has_subtitle (film):
    p = os.path.splitext (film)
    return os.path.isfile (p[0] + '.txt')

def is_film (path):
    if os.path.isfile (path) and re.search ('\.(?:avi|mpe?g|mp4|mkv|rmvb)$', path, re.I):
        return True
    return False

def find_films__recursive (path):
    ret = []
    for root, dirs, files in os.walk (path):
        for f in files:
            p = os.path.join (root, f)
            if is_film (p):
                ret.append (p)
    return ret

def find_films__nonrecursive (path):
    ret = []
    for fname in os.listdir (path):
        p = os.path.join (path, fname)
        if is_film (p):
            ret.append (p)
    return ret

def find_films (path, recursive=False):
    if not os.path.isdir (path):
        return

    if recursive:
        return find_films__recursive (path)
    else:
        return find_films__nonrecursive (path)


def main ():
    import getopt

    usage = __desc__ + "\n\n" + '''%s [-h|--help] [-v|--version] [-d|--directory] [-r|--recursive] [-o|--output output_dir] [-n|--no-validate] [-w|--overwrite] input1 input2 .. inputN
-h|--help           - this help message
-d|--directory      - if specified, scan every passed argument (input1 .. inputN) for files with extensions: avi, mpeg, mpg, mp4, mkv, rmvb
-r|--recursive      - if specified, every directory passed as input will be scanned recursively. Skipped when -d is not specified
-o|--output_dir     - specify directory when you want to save downloaded files. If not specified, try to save every subtitle in films directory
-n|--no-validate    - if given, specified list of films will not be validated for being movie files (work only without -d parameter)
-w|--overwrite      - if specified, existent subtitles will not be overwritten
input1 .. inputN    - if -d is not specified, this is treaten like films files, to which you want to download subtitles. In other case, this is list of directories whis are scanned for files''' % (os.path.basename (sys.argv[0]),)

    ## parsing getopt options
    opts_short  = 'hdo:rnw'
    opts_long   = ['help', 'directory', 'output=', 'recursive', 'no-validate', 'overwrite']
    try:
        opts, args = getopt.gnu_getopt (sys.argv[1:], opts_short, opts_long)
    except getopt.GetoptError, e:
        print e
        raise SystemExit (1)

    recursive       = False
    directory       = False
    output          = None
    validate        = True
    overwrite       = False
    for o, a in opts:
        if o in ('-h', '--help'):
            print usage
            raise SystemExit (0)
        elif o in ('-v', '--version'):
            print __version__
            raise SystemExit (0)
        elif o in ('-d', '--directory'):
            directory = True
        elif o in ('-r', '--recursive'):
            recursive = True
        elif o in ('-o', '--output'):
            output = a
        elif o in ('-n', '--no-validate'):
            validate = False
        elif o in ('-w', '--overwrite'):
            overwrite = True

    ## find all films
    fnames = []
    if directory:
        dirs = []
        if not args:
            dirs.append (os.getcwd ())
        else:
            dirs.extend (args)
        for d in dirs:
            f = find_films (d, recursive)
            if f:
                fnames.extend (f)

    ## all files from current dir
    elif not args:
        fnames.extend (find_films (os.getcwd ()))

    ## check files given by user
    elif validate:
        fnames.extend (f for f in args if is_film (f))

    ## don't check, every given file is a file (skip only nonfile)
    else:
        fnames.extend (f for f in args if os.path.isfile (f))

    ## skip searching for existent subtitles
    if not overwrite:
        fnames = [ f for f in fnames if not has_subtitle (f) ]

    if not fnames:
        print 'Cannot find any film.'
        raise SystemExit (2)

    # find longest filename
    length = max (map (len, fnames)) + 1

    ## download all subtitles
    for fname in fnames:
        r = get_subtitles (fname, output)
        if r:
            status = u'done'
        else:
            status = u'not found'
        fname += ' '
        print u'%s: %s' % (fname.ljust (length, '-'), status)


if __name__ == '__main__':
    main ()

# vim: ft=python:et:tw=0:
