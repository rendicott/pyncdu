#!/usr/bin/env python

import logging
import sys
import inspect
import gc
import os
import nagpy
import subprocess
import re
from nagpy import NagiosReturn
from nagpy import PerfChunk
from nagpy import NagiosReturnCode
from optparse import OptionParser, OptionGroup

sversion = 'v0.1'
scriptfilename = os.path.basename(sys.argv[0])
defaultlogfilename = scriptfilename + '.log'

helptext = """
This script checks the output of the local
'zcat NCDUREPORT.gz | NCDUPARSERSCRIPT' command and reports 
the total size of the path that the report represents. 

It compares that size to warn_size and crit_size and acts 
accordingly. Additionally the check will go critical if the 
timestamp of the report is older than max_age

Designed to be used in conjunction with the 'ncdu_summary.py'
parser that spits out json details about the NCDU report file.

Usage Examples: 
python check_ncdu_gzip.py --filename /root/ncdu-archives/ncdu-output-digital-LATEST.gz --display_units gb
OK parsed file /root/ncdu-archives/ncdu-output-digital-LATEST.gz and got size '127324.5097 gb' with total number of files '3019290' in parse_time '11.2743' sec  ; | 'total_size'=127324.5097GB;400000;500000;; 'total_files'=3019290;;;; 'parse_time'=11.2743s;;;;

python check_ncdu_gzip.py --filename ../ncdu-archives/ncdu-output-digital-20160617.134228.gz --display_units gb
WARNING parsed file ../ncdu-archives/ncdu-output-digital-20160617.134228.gz (35.281 hours old) and got size '128796.4786 gb' with total number of files '3064285' in parse_time '10.9055' sec  ; | 'total_size'=128796.4786GB;400000;500000;; 'total_files'=3064285;;;; 'file_age'=127011.6s;86400.0;;; 'parse_time'=10.9055s;;;;

python check_ncdu_gzip.py --filename ../ncdu-archives/ncdu-output-digital-20160617.134228.gz --display_units gb --max_age 44
OK parsed file ../ncdu-archives/ncdu-output-digital-20160617.134228.gz (35.290 hours old) and got size '128796.4786 gb' with total number of files '3064285' in parse_time '10.4379' sec  ; | 'total_size'=128796.4786GB;400000;500000;; 'total_files'=3064285;;;; 'file_age'=127044.0s;158400.0;;; 'parse_time'=10.4379s;;;;

python check_ncdu_gzip.py --filename ../ncdu-archives/ncdu-output-digital-LATEST.gz --display_units tb --max_age 1
OK parsed file ../ncdu-archives/ncdu-output-digital-LATEST.gz (0.543 hours old) and got size '124.3403 tb' with total number of files '3019427' in parse_time '11.3879' sec  ; | 'total_size'=124.3403TB;400000;500000;; 'total_files'=3019427;;;; 'file_age'=1954.8s;3600.0;;; 'parse_time'=11.3879s;;;;


Requires: NagPy library (https://github.com/rendicott/nagpy)
Requires: ncdu_parser.py 
"""


def setuplogging(loglevel,printtostdout,logfile):
    #pretty self explanatory. Takes options and sets up logging.
    #print "starting up with loglevel",loglevel,logging.getLevelName(loglevel)
    logging.basicConfig(filename=logfile,
                        filemode='w',level=loglevel, 
                        format='%(asctime)s:%(levelname)s:%(message)s')
    if printtostdout:
        soh = logging.StreamHandler(sys.stdout)
        soh.setLevel(loglevel)
        logger = logging.getLogger()
        logger.addHandler(soh)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def execute_command(commandstring):
    try:
        output = subprocess.Popen(commandstring,stdout=subprocess.PIPE)
        return(output)
    except Exception as e:
        msg = "Exception calling command: '%s' , Exception: %s" % (commandstring,str(e))
        logging.debug(msg)
        return(msg)


def runoscommand(commandstringraw,subool=None):
    funcname = 'runoscommand'
    if subool == None:
        subool = False
    logging.info(funcname + '\t' + commandstringraw)
    if subool:
        commandlist = commandstringraw.split(' ')
        command = subprocess.Popen(commandlist,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
        outputstr, errors = command.communicate()
        logging.debug(funcname + '\t' +
            "Done running command, now list interpretation...")
        outputlis = [x for x in outputstr.split('\n')]
        return outputlis
    else:
        # make sure we're returning a list
        return os.popen(commandstringraw).readlines()

def check_file_time(filename, maxage):
    import os.path, time, datetime
    # last_mod = time.time(os.path.getmtime(filename))
    # created = time.time(os.path.getctime(filename))
    try:
        maxage_f = float(maxage)
    except Exception as ir:
        message = "Exception casting max_age '%s' as float: %s" % (str(maxage),str(ir))
        logging.debug(message)
        print(message)
        sys.exit(1)
    last_mod = os.path.getmtime(filename)
    created = os.path.getctime(filename)
    logging.debug("last modified: %s" % last_mod)
    logging.debug("created: %s" % created)
    now = time.time()
    logging.debug("Now time: " + str(now))
    sec_diff = float(now) - float(last_mod)
    logging.debug("seconds difference from now : " + str(sec_diff))
    hour_diff = sec_diff / float(3600)
    logging.debug("hours difference from now : " + str(hour_diff))
    alarm = False
    if hour_diff > maxage_f:
        alarm = True
        logging.debug("File has exceeded max_age of %s" % maxage_f)
    return(alarm, hour_diff)

def parse_file(options):
    # sample command:
    # 'zcat ../ncdu-archives/ncdu-output-digital-LATEST.gz | python ncdu_summary.py'
    cl = []
    cl.append('/usr/bin/zcat')
    cl.append(options.filename)
    cl.append('|')
    parser_command = options.parser_command.split(' ')
    for block in parser_command:
        cl.append(block)
    commandstring = ' '.join(cl)
    # print(commandstring)
    results = runoscommand(commandstring)
    logging.debug("command results: %s" % (str(results)))
    import json
    total_lines = long(0)
    total_size = long(0)
    parse_time = float(0)
    try:
        j = json.loads(results[0])
        total_lines = long(j.get('total_lines'))
        total_size = long(j.get('total_size'))
        parse_time = float(j.get('parse_time'))
    except Exception as rr:
        msg = "Exception parsing command results. ZEROING VALUES...: " + str(rr)
        logging.debug(msg)
        print(msg)
    logging.debug("TOTAL_LINES: " + str(total_lines))
    logging.debug("TOTAL_SIZE: " + str(total_size))
    logging.debug("PARSE_TIME: " + str(parse_time))
    return(total_lines, total_size, parse_time)

def convert_size(size, units):
    """
    Converts data size to given units.
    Valide units: kb, mb, gb, tb
    returns size, units
    """
    dividers = {
            'kb': long(1024),
            'mb': long(1048576),
            'gb': long(1073741824),
            'tb': long(1099511627776),
    }
    logging.debug("Type of incoming size is '%s' " % str(type(size)))
    try:
        lsize = long(size)
    except Exception as er:
        msg = "Exception casting total_size as long: " + str(er)
        logging.debug(msg)
        print(msg)
        sys.exit(1)
    try:
        d = dividers[units.lower()]
    except Exception as err:
        msg = "Exception looking up units. Valid units are kb,mb,gb,tb: " + str(err)
        logging.debug(msg)
        print(msg)
        sys.exit(1)
    try:
        msize = float(lsize) / float(d)
    except Exception as orr:
        msg = "Exception dividing total_size '%s' by divider '%s' for unit '%s' : " % (str(lsize), str(d), str(units))
        logging.debug(msg)
        print(msg)
        sys.exit(1)
    return msize, units

def main(options):
    ''' The main() method. Program starts here.
    '''
    #output = execute_command(['/bin/df','-P'])
    # sample command "zcat /tmp/ncdu-output-logs-LATEST.gz | timeout 10s ncdu -1f- 2>&1"
    (age_alarm, hour_diff) = check_file_time(options.filename, options.max_age)
    (total_lines, total_size, parse_time) = parse_file(options)
    (converted_size, units) = convert_size(total_size, options.display_units)
    # alter float precision
    converted_size = "{:.4f}".format(converted_size)
    parse_time = "{:.4f}".format(parse_time)
    hour_diff = "{:.3f}".format(hour_diff)
    logging.debug("CONVERTED_SIZE: " + str(converted_size) + ' ' + str(units))
    
    
    pc_size = PerfChunk(stringname='total_size',value=converted_size, unit=units.upper())
    pc_size.warn = str(options.warn_size)
    pc_size.crit = str(options.crit_size)
    

    if float(converted_size) >= float(options.crit_size):
        nrc = 2
    elif float(converted_size) >= float(options.warn_size):
        nrc = 1
    else:
        nrc = 0

    # now check to see if file is older than maxage and override size alarms
    if age_alarm:
        nrc = 1
    # build your nagios message and tell it to be warn,crit,ok, etc.
    # nrc = 1  # WARNING
    # nrc = 2  # CRITICAL
    
    try:
        msg =  ("parsed file %s (%s hours old) and got size '%s %s' with total number of files '%s' in parse_time '%s' sec" % (options.filename,
                                                                                                                str(hour_diff),
                                                                                                                str(converted_size),
                                                                                                                str(units),
                                                                                                                str(total_lines),
                                                                                                                str(parse_time)))
    except Exception as irr:
        message = "Exception building Nagios msg string: " + str(irr)
        logging.debug(message)
        print(message)
        sys.exit(1)
    nm = NagiosReturnCode(returncode=nrc,msgstring=msg)
    # append the primary performance counter that we care about
    nm.perfChunkList.append(pc_size)

    # build additional performance metrics  
    #print('SIZE:::::' + parse_size(selected_mount.size))
    #print('USED:::::' + parse_size(selected_mount.used))
    #print('AVAIL:::::' + parse_size(selected_mount.avail))
    
    
    try:
        pc_files = PerfChunk(stringname='total_files', value=total_lines)
        nm.perfChunkList.append(pc_files)
    except Exception as r:
        logging.debug("EXCEPTION files: " + str(r))
    try:
        seconds_diff = float(hour_diff) * float(3600)
        maxage_seconds = float(options.max_age) * float(3600)
        pc_age = PerfChunk(stringname='file_age', value=seconds_diff, unit='s', warn=maxage_seconds)
        nm.perfChunkList.append(pc_age)
    except Exception as r:
        logging.debug("EXCEPTION files: " + str(r))
    try:
        pc_parsetime = PerfChunk(stringname='parse_time', value=parse_time, unit='s')
        nm.perfChunkList.append(pc_parsetime)
    except Exception as r:
        print("EXCEPTION used: " + str(r))
    nm.genreturncode() # will raise a 'NagiosReturn' exception which is normal
    

if __name__ == '__main__':
    '''This main section is mostly for parsing arguments to the 
    script and setting up debugging'''
    from optparse import OptionParser
    '''set up an additional option group just for debugging parameters'''
    from optparse import OptionGroup
    usage = ("%prog [--debug] [--printtostdout] [--logfile] [--version] [--help] [--samplefileoption]" + '\n' + helptext)
    #set up the parser object
    parser = OptionParser(usage, version='%prog ' + sversion)
    parser.add_option('--warn_size',
                    type='string',
                    help=("Warning level for the path size represented by this NCDU report in GB. (Default=400000)"),default='400000')
    parser.add_option('--crit_size',
                    type='string',
                    help=("Critical level for the path size represented by this NCDU report in GB. (Default=500000)"),default='500000')
    parser.add_option('--max_age',
                    type='string',
                    help=("Max age of the NCDU report's timestamp in hours. (Default=24)"),default=24)
    parser.add_option('--parse_timeout',
                      type='string',
                      help=('Timeout value in seconds. This determines how long we wait for NCDU to ' +
                            'to process the report before grabbing the total size (Default=10)'), default=10)
    parser.add_option('--parser_command',
                      type='string',
                      help=("Path to parser application (Default='/usr/bin/python ncdu_summary.py'"), default='/usr/bin/python ncdu_summary.py')
    parser.add_option('--display_units',
                      type='string',
                      help=("Display units for parsed size. Valid units are kb,mb,gb,tb (Default='gb')"), default='gb')
    parser.add_option('--filename',
                      type='string',
                      help="The full path of the filename to check. (Default=None)",
                      default=None)
    parser_debug = OptionGroup(parser,'Debug Options')
    parser_debug.add_option('-d','--debug',type='string',
        help=('Available levels are CRITICAL (3), ERROR (2), '
            'WARNING (1), INFO (0), DEBUG (-1)'),
        default='CRITICAL')
    parser_debug.add_option('-p','--printtostdout',action='store_true',
        default=False,help='Print all log messages to stdout')
    parser_debug.add_option('-l','--logfile',type='string',metavar='FILE',
        help=('Desired filename of log file output. Default '
            'is "'+ defaultlogfilename +'"')
        ,default=defaultlogfilename)
    #officially adds the debuggin option group
    parser.add_option_group(parser_debug) 
    options,args = parser.parse_args() #here's where the options get parsed

    try: #now try and get the debugging options
        loglevel = getattr(logging,options.debug)
    except AttributeError: #set the log level
        loglevel = {3:logging.CRITICAL,
                    2:logging.ERROR,
                    1:logging.WARNING,
                    0:logging.INFO,
                    -1:logging.DEBUG,
                    }[int(options.debug)]

    try:
        open(options.logfile,'w') #try and open the default log file
    except:
        logging.debug("Unable to open log file '%s' for writing." % options.logfile)
        logging.debug(
            "Unable to open log file '%s' for writing." % options.logfile)

    setuplogging(loglevel,options.printtostdout,options.logfile)
    try:
        main(options)
    except NagiosReturn, e:
        print e.message
        sys.exit(e.code)
    