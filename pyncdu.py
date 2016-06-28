'''
Runs ncdu in silent mode and outputs an ncdu file.
Then it takes the ncdu file and ships it to a remote
server for archiving/parsing. 

'''

import logging
import sys
import ConfigParser
import os
import json
import datetime
import subprocess

sversion = 'v0.1'
scriptfilename = os.path.basename(sys.argv[0])
defaultlogfilename = scriptfilename + '.log'
    

def setuplogging(loglevel, printtostdout, logfile):
    # pretty self explanatory. Takes options and sets up logging.
    print("starting up with loglevel", loglevel, logging.getLevelName(loglevel))
    logging.basicConfig(filename=logfile,
                        filemode='w', level=loglevel, 
                        format='%(asctime)s:%(levelname)s:%(message)s')
    if printtostdout:
        soh = logging.StreamHandler(sys.stdout)
        soh.setLevel(loglevel)
        logger = logging.getLogger()
        logger.addHandler(soh)

def get_timestamp_string(format=None):
    if format is None:
        format = '%Y%m%d.%H%M%S'
    return(datetime.datetime.strftime(datetime.datetime.now(),format))


def execute_command(commandstring,fake=None):
    if fake is None:
        fake = False
    if fake:
        f = []
        f.append("I would have run the following command if I wasn't faking it: ")
        f.append(commandstring)
        return f
    else:
        logging.debug("COMMAND RECEIVED WAS: " + str(commandstring))
        try:
            #output = subprocess.Popen(commandstring,stdout=subprocess.PIPE)
            output = subprocess.call(commandstring,shell=True)
            return(output)
        except Exception as e:
            msg = "Exception calling command: '%s' , Exception: %s" % (commandstring,str(e))
            logging.debug(msg)
            return(msg)

class Path:
    def __init__(self):
        self.name = ''
        self.path = ''
        self.exclude_list = []
        self.resultsfile = ''
        self.resultsfile_scp_command_list = []
        self.infofile_scp_command_list = []
        self.resultsfile_scp_command_string = ''
        self.infofile_scp_command_string = ''
        self.infofile_delete_command_list = []
        self.infofile_delete_command_string = ''
        self.resultsfile_delete_command_list = []
        self.resultsfile_delete_command_string = ''
        # latest placeholders
        self.resultsfile_latest = ''
        self.infofile_latest = ''
        self.resultsfile_latest_scp_command_list = []
        self.infofile_latest_scp_command_list = []
        self.resultsfile_latest_scp_command_string = ''
        self.infofile_latest_scp_command_string = ''
        #
        self.infofile = ''
        self.commandstring = ''
        self.commandlist = []
    def dumpself(self):
        msg = ''
        msg += '|\t----PATH----\n'
        msg += "|\tNAME: '%s'\n" % str(self.name)
        msg += "|\tPATH: '%s'\n" % str(self.path)
        msg += "|\tRESULTSFILE: '%s'\n" % str(self.resultsfile)
        msg += "|\tINFOFILE: '%s'\n" % str(self.infofile)
        msg += "|\tRESULTSFILE_LATEST: '%s'\n" % str(self.resultsfile_latest)
        msg += "|\tINFOFILE_LATEST: '%s'\n" % str(self.infofile_latest)
        msg += "|\tCOMMANDSTRING: '%s'\n" % str(self.commandstring)
        msg += "|\tCOMMANDLIST: '%s'\n" % str(self.commandlist)
        msg += "|\tRESULTSFILE_SCP_COMMAND_LIST: '%s'\n" % str(self.resultsfile_scp_command_list)
        msg += "|\tINFOFILE_SCP_COMMAND_LIST: '%s'\n" % str(self.infofile_scp_command_list)
        msg += "|\tRESULTSFILE_SCP_COMMAND_STRING: '%s'\n" % str(self.resultsfile_scp_command_string)
        msg += "|\tINFOFILE_SCP_COMMAND_STRING: '%s'\n" % str(self.infofile_scp_command_string)
        msg += "|\tRESULTSFILE_DELETE_COMMAND_LIST: '%s'\n" % str(self.resultsfile_delete_command_list)
        msg += "|\tINFOFILE_DELETE_COMMAND_LIST: '%s'\n" % str(self.infofile_delete_command_list)
        msg += "|\tRESULTSFILE_DELETE_COMMAND_STRING: '%s'\n" % str(self.resultsfile_delete_command_string)
        msg += "|\tINFOFILE_DELETE_COMMAND_STRING: '%s'\n" % str(self.infofile_delete_command_string)
        #LATEST
        msg += "|\tRESULTSFILE_LATEST_SCP_COMMAND_LIST: '%s'\n" % str(self.resultsfile_latest_scp_command_list)
        msg += "|\tINFOFILE_LATEST_SCP_COMMAND_LIST: '%s'\n" % str(self.infofile_latest_scp_command_list)
        msg += "|\tRESULTSFILE_LATEST_SCP_COMMAND_STRING: '%s'\n" % str(self.resultsfile_latest_scp_command_string)
        msg += "|\tINFOFILE_LATEST_SCP_COMMAND_STRING: '%s'\n" % str(self.infofile_latest_scp_command_string)
        #
        msg += "|\tEXCLUDE_LIST: \n"
        for p in self.exclude_list:
            msg += "|\t\tEXCLUDE: '%s'\n" % str(p)
        msg += "|\t------------\n"
        return msg


class Settings:
    def __init__(self):
        self.path_ncdu_executable = ''
        self.path_tempfile = ''
        self.export_to_hostnameip = ''
        self.export_to_username = ''
        self.export_to_identityfile_path = ''
        self.export_to_remotepath = ''
        self.export_to_fileprefix = ''
        self.format_timestamp = ''
        self.paths = []
    def dumpself(self):
        msg = ''
        msg += '----SETTINGS----\n'
        msg += "| path_ncdu_executable: '%s'\n" % str(self.path_ncdu_executable)
        msg += "| path_tempfile: '%s'\n" % str(self.path_tempfile)
        msg += "| export_to_hostnameip: '%s'\n" % str(self.export_to_hostnameip)
        msg += "| export_to_username: '%s'\n" % str(self.export_to_username)
        msg += "| export_to_identityfile_path: '%s'\n" % str(self.export_to_identityfile_path)
        msg += "| export_to_remotepath: '%s'\n" % str(self.export_to_remotepath)
        msg += "| export_to_fileprefix: '%s'\n" % str(self.export_to_fileprefix)
        msg += "| format_timestamp: '%s'\n" % str(self.format_timestamp)
        msg += "| PATHS: \n"
        for p in self.paths:
            msg += p.dumpself()
        msg += "| ---------------"
        return msg


def process_config(filename):
    """
    Processes the config INI file and returns a Settings
    object.
    :param filename:
    :return: settings
    """
    logging.debug('------- ENTERING FUNCTION: process_config() -------')
    try:
        cfg = ConfigParser.ConfigParser()
        cfg.read(filename)
        settings = Settings()
        settings.path_ncdu_executable = cfg.get('global', 'path_ncdu_executable')
        settings.path_tempfile = cfg.get('global', 'path_tempfile')
        settings.export_to_hostnameip = cfg.get('global', 'export_to_hostnameip')
        settings.export_to_username = cfg.get('global', 'export_to_username')
        settings.export_to_identityfile_path = cfg.get('global', 'export_to_identityfile_path')
        settings.export_to_remotepath = cfg.get('global', 'export_to_remotepath')
        settings.export_to_fileprefix = cfg.get('global', 'export_to_fileprefix')
        settings.format_timestamp = cfg.get('global', 'format_timestamp')       
        try:
            logging.debug('-_-_-_-_-_-_-_ Total number of sections = ' + str(len(cfg.sections())))
            for section in cfg.sections():
                logging.debug('-_-_-_-_-_-_-_ Looping through sections. Current Section = ' + str(section))
                if 'path_' in section:
                    path = Path()
                    path.name = cfg.get(section, 'name')
                    path.path = cfg.get(section,'path')
                    try:
                        jlist = json.loads(cfg.get(section,'excludes_list'))
                        slist = [str(x) for x in jlist]
                        path.exclude_list = slist
                    except Exception as jj:
                        #logging.debug("Exception loading excludes_list: " + str(jj))
                        pass
                    settings.paths.append(path)
        except Exception as err:
            message = "Exception processing configured paths: " + str(err)
            logging.debug(message)
    except Exception as orr:
        logging.critical("Exception processing config: " + str(orr))
        sys.exit(1)

    return settings

def build_ncdu_commands(settings):
    for path in settings.paths:
        # basic format is 'ncdu -1xo- /mapr/mapr.contoso.com/user | gzip >~/ncdu-output-user.gz'
        command_list = []
        command_list.append(settings.path_ncdu_executable)
        command_list.append('-1xo-')
        command_list.append(path.path)
        if len(path.exclude_list) > 0:
            for e in path.exclude_list:
                command_list.append('--exclude ' + e)
        command_list.append('|')
        command_list.append('gzip')
        genfile =   settings.path_tempfile + \
                    settings.export_to_fileprefix + \
                    path.name + '-' + \
                    get_timestamp_string(format=settings.format_timestamp)
        genfile_latest = settings.export_to_fileprefix + \
                         path.name + '-' + \
                         'LATEST'
        outfile = ">"
        outfile += genfile + ".gz"
        outfile_info = genfile + "-info.txt"
        outfile_info_latest = genfile_latest + '-info.txt'
        path.resultsfile_latest = genfile_latest + '.gz'
        path.resultsfile = genfile + ".gz"
        path.infofile = outfile_info
        path.infofile_latest = outfile_info_latest
        command_list.append(outfile)
        path.commandlist = command_list
        commandstring = ' '.join(command_list)
        path.commandstring = commandstring
        #logging.debug("Built command: '%s'" % commandstring)
    return settings


def build_delete_commands(settings):
    for path in settings.paths:
        cl = ['rm']
        cl.append('-f')
        path.infofile_delete_command_list = list(cl)
        path.resultsfile_delete_command_list = list(cl)
        path.infofile_delete_command_list.append(path.infofile)
        path.resultsfile_delete_command_list.append(path.resultsfile)
        path.infofile_delete_command_string = ' '.join(path.infofile_delete_command_list)
        path.resultsfile_delete_command_string = ' '.join(path.resultsfile_delete_command_list)
    return settings


def build_scp_commands(settings):
    for path in settings.paths:
        cl = []
        # basic format is 'scp -i /root/.ssh/dreamcatcher /tmp/ncdu-output-testing-20160617.122943-info.txt root@dodreamcatcher1.docl.nic:/root/ncdu-archives/ncdu-output-testing-20160617.122943-info.txt'
        cl.append('/usr/bin/scp')
        cl.append('-i')
        cl.append(settings.export_to_identityfile_path)
        path.resultsfile_scp_command_list = list(cl)
        path.infofile_scp_command_list = list(cl)
        path.resultsfile_latest_scp_command_list = list(cl)
        path.infofile_latest_scp_command_list = list(cl)        
        # now we split into two different commands
        path.resultsfile_scp_command_list.append(path.resultsfile)
        path.infofile_scp_command_list.append(path.infofile)
        path.resultsfile_latest_scp_command_list.append(path.resultsfile)
        path.infofile_latest_scp_command_list.append(path.infofile)
        logging.debug("CURRENT RESULTSFILE = '%s'" % str(path.resultsfile_scp_command_list))
        logging.debug("CURRENT INFOFILE = '%s'" % str(path.infofile_scp_command_list))
        logging.debug("CURRENT LATEST RESULTSFILE = '%s'" % str(path.resultsfile_latest_scp_command_list))
        logging.debug("CURRENT LATEST INFOFILE = '%s'" % str(path.infofile_latest_scp_command_list))        
        # strip the prefix from the file and only grab the file
        # example: /path/to/file/txt ==> file.txt
        justfile = path.resultsfile.split('/')[-1]
        path.resultsfile_scp_command_list.append(   settings.export_to_username + \
                                                    '@' + settings.export_to_hostnameip + \
                                                    ':' + settings.export_to_remotepath + \
                                                    '/' + justfile)
        path.resultsfile_latest_scp_command_list.append( settings.export_to_username + \
                                                         '@' + settings.export_to_hostnameip + \
                                                         ':' + settings.export_to_remotepath + \
                                                         '/' + path.resultsfile_latest)
        justfile = path.infofile.split('/')[-1]
        path.infofile_scp_command_list.append( settings.export_to_username + \
                                               '@' + settings.export_to_hostnameip + \
                                               ':' + settings.export_to_remotepath + \
                                               '/' + justfile)
        path.infofile_latest_scp_command_list.append( settings.export_to_username + \
                                                      '@' + settings.export_to_hostnameip + \
                                                      ':' + settings.export_to_remotepath + \
                                                      '/' + path.infofile_latest)
        path.resultsfile_scp_command_string = ' '.join(path.resultsfile_scp_command_list)
        path.infofile_scp_command_string = ' '.join(path.infofile_scp_command_list)
        path.resultsfile_latest_scp_command_string = ' '.join(path.resultsfile_latest_scp_command_list)
        path.infofile_latest_scp_command_string = ' '.join(path.infofile_latest_scp_command_list)
    return settings



def main(opts):
    """ The main() method. Program starts here.
    """
    settings = process_config(opts.configfile)
    settings = build_ncdu_commands(settings)
    settings = build_scp_commands(settings)
    settings = build_delete_commands(settings)
    logging.debug(settings.dumpself())
    if opts.jobname is None:
        msg = "Must provide a job name. Exiting..."
        logging.debug(msg)
        print(msg)
        sys.exit(1)
    else:
        found = False
        for path in settings.paths:
            if path.name == opts.jobname:
                found = True
                with open(path.infofile,'wt') as f:
                    msg = "Running job '%s' and outputting results to '%s'....." % (opts.jobname,path.infofile)
                    logging.debug(msg)
                    print(msg)
                    f.write(path.dumpself() + "\n")
                    start = datetime.datetime.now()
                    start_string = datetime.datetime.strftime(start,settings.format_timestamp)
                    f.write("JOB START TIME: " + str(start_string) + "\n")
                    results = execute_command(path.commandstring,fake=opts.fake)
                    f.write("JOB COMMAND RESULTS:" + "\n")
                    f.write("===========================" + "\n")
                    #for line in results:
                        #f.write(line + "\n")
                    #f.write("\n")
                    f.write("===========================" + "\n")
                    end = datetime.datetime.now()
                    end_string = datetime.datetime.strftime(end,settings.format_timestamp)
                    f.write("JOB END TIME: " + str(end_string) + "\n")
                    f.write("TOTAL RUNTIME: " + str(end - start) + "\n")
                # NOW SCP FILES
                results = execute_command(path.resultsfile_scp_command_string,fake=opts.fake)
                logging.debug("resultsfile_scp_command RESULTS: " + str(results))
                results2 = execute_command(path.infofile_scp_command_string,fake=opts.fake)
                logging.debug("infofile_scp_command RESULTS: " + str(results2))
                # now scp latest files
                results11 = execute_command(path.resultsfile_latest_scp_command_string,fake=opts.fake)
                logging.debug("resultsfile_latest_scp_command RESULTS: " + str(results11))
                results22 = execute_command(path.infofile_latest_scp_command_string,fake=opts.fake)
                logging.debug("infofile_latest_scp_command RESULTS: " + str(results22))
                # NOW DELETE
                results3 = execute_command(path.resultsfile_delete_command_string,fake=opts.fake)
                logging.debug("resultsfile_delete_command RESULTS: " + str(results3))
                results4 = execute_command(path.infofile_delete_command_string,fake=opts.fake)
                logging.debug("infofile_delete_command RESULTS: " + str(results4))
        if not found:
            msg = "No jobs found with name '%s'. Exiting..." % opts.jobname
            logging.debug(msg)
            print(msg)
            sys.exit(1)





if __name__ == '__main__':
    '''This main section is mostly for parsing arguments to the 
    script and setting up debugging'''
    from optparse import OptionParser
    '''set up an additional option group just for debugging parameters'''
    from optparse import OptionGroup
    usage = "%prog [--debug] [--printtostdout] [--logfile] [--version] [--help] [--samplefileoption]"
    # set up the parser object
    parser = OptionParser(usage, version='%prog ' + sversion)
    parser.add_option('-c', '--configfile', 
                      type='string',
                      metavar='FILE',
                      help="Path to the ini config file (Default='runningconfig.ini')", default='runningconfig.ini')
    parser.add_option('-j', '--jobname', 
                      type='string',
                      help="Which job to run by name. This is the name: in the ini file (Default=None)", default=None)
    parser.add_option('--fake',
                      action='store_true',
                      help="Boolean flag. If this option is present then no actual ncdu commands will be " + 
                           "run, just fake ones (Default=False)",
                      default=False)
    parser_debug = OptionGroup(parser, 'Debug Options')
    parser_debug.add_option('-d', '--debug', type='string',
                            help=('Available levels are CRITICAL (3), ERROR (2), '
                                  'WARNING (1), INFO (0), DEBUG (-1)'),
                            default='CRITICAL')
    parser_debug.add_option('-p', '--printtostdout', action='store_true',
                            default=False, help='Print all log messages to stdout')
    parser_debug.add_option('-l', '--logfile', type='string', metavar='FILE',
                            help=('Desired filename of log file output. Default '
                                  'is "' + defaultlogfilename + '"'),
                            default=defaultlogfilename)
    # officially adds the debugging option group
    parser.add_option_group(parser_debug) 
    options, args = parser.parse_args()  # here's where the options get parsed

    try: # now try and get the debugging options
        loglevel = getattr(logging, options.debug)
    except AttributeError:  # set the log level
        loglevel = {3: logging.CRITICAL,
                    2: logging.ERROR,
                    1: logging.WARNING,
                    0: logging.INFO,
                    -1: logging.DEBUG,
                    }[int(options.debug)]

    try:
        open(options.logfile, 'w')  # try and open the default log file
    except:
        print("Unable to open log file '%s' for writing." % options.logfile)
        logging.debug(
            "Unable to open log file '%s' for writing." % options.logfile)

    setuplogging(loglevel, options.printtostdout, options.logfile)
    try:
        if options.configfile == 'runningconfig.ini':
            # try to get the real directory of the running script
            currdir = os.path.dirname(os.path.realpath(__file__))
            options.configfile = currdir + "/" + "runningconfig.ini"
    except Exception as arrr:
        msg = "Exception processing config file location: " + str(arrr)
        logging.error(msg)
        print(msg)
        sys.exit(1)
    main(options)

