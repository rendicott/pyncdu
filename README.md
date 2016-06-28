
# pyNCDU
This is a collection of three scripts to be used as an NCDU granular disk usage reporting
orchestration tool for very large filesystems (>1PB). The goal is to run scheduled 
[NCDU](https://dev.yorhel.nl/ncdu) reports using `pyncdu.py` and store the results 
compressed and ship them off to an archive server. The archive server will then use
the `check_ncdu_gzip.py` and the `ncdu_summary.py` scripts to parse and report the 
sizes in Nagios return code format so overall fileystem growth can be graphed and alerted
on over time. 

## pyncdu.py
Copy this file down to the server that has access to the large filesystem. In this case
it is one of the Hadoop nodes. Also copy the `runningconfig.ini` file down to the same
directory as the `pyncdu.py` script. In my case I just copied the two files to the
`/root/pyncdu` directory.


The script is essentially a helper for running
the following sequence of commands:

`ncdu -1xo- /mapr/mapr.contoso.com/user | gzip /tmp/ncdu-output-user.gz`

then it takes that file and moves it off to an archive server of you choice by runnning

`scp -i /root/.ssl/dreamcatcher /tmp/ncdu-output-user.gz root@dodreamcatcher1.docl.nic:/root/ncdu-archives/ncdu-output-user.gz`

In addition to the timestamped file it transfers another file with the `-LATEST` moniker  overwriting the previous `-LATEST` file. 


Basic usage of the `pyncdu.py` scrpt. 
```
Usage: pyncdu.py [--debug] [--printtostdout] [--logfile] [--version] [--help] [--samplefileoption]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c FILE, --configfile=FILE
                        Path to the ini config file
                        (Default='runningconfig.ini')
  -j JOBNAME, --jobname=JOBNAME
                        Which job to run by name. This is the name: in the ini
                        file (Default=None)
  --fake                Boolean flag. If this option is present then no actual
                        ncdu commands will be run, just fake ones
                        (Default=False)

  Debug Options:
    -d DEBUG, --debug=DEBUG
                        Available levels are CRITICAL (3), ERROR (2), WARNING
                        (1), INFO (0), DEBUG (-1)
    -p, --printtostdout
                        Print all log messages to stdout
    -l FILE, --logfile=FILE
                        Desired filename of log file output. Default is
                        "pyncdu.py.log"
```

You can look at the provided `runningconfig.ini` for examples of how to set up jobs.
```
[global]
path_ncdu_executable: /usr/bin/ncdu

# location where temporary output files are stored
path_tempfile: /tmp/

# hostname IP of remote machine to SCP reports to
export_to_hostnameip: dodreamcatcher1.docl.nic

# username to use with scp to auth against the remote machine
export_to_username: root

# the private key identity file to use with the above username
export_to_identityfile_path: /root/.ssh/dreamcatcher

# the path on the remote machine in which to put report files
export_to_remotepath: /root/ncdu-archives/

# the prefix to use for all files
export_to_fileprefix: ncdu-output-

# every file will be named with a timestamp in this format (python datetime)
format_timestamp: %Y%m%d.%H%M%S


# now the list of 'jobs' which are paths that you want NCDU to scan and 
# provide a report for
# all path config sections must be prefixed with 'path_'

[path_01]
# the job name as a descriptor
name: user

# path that you want to want to scan with the ncdu command
path: /mapr/mapr.contoso.com/user


[path_02]
name: other
path: /mapr/mapr.contoso.com/

# excludes_list is optional. Each of these exclude paths
# will be used for the --exclude option with NCDU
excludes_list: [
        "/mapr/mapr.contoso.com/digital",
        "/mapr/mapr.contoso.com/datahub",
        "/mapr/mapr.contoso.com/stage",
        "/mapr/mapr.contoso.com/apps",
        "/mapr/mapr.contoso.com/apps",
        "/mapr/mapr.contoso.com/targetaudience"
    ]
```

Then you can schedule jobs with cron. See an example below of how you can schedule
all jobs to run with cron. 
```
0 * * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname trxnmatch >/dev/null 2>&1
10 * * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname user >/dev/null 2>&1
20 * * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname targetaudience >/dev/null 2>&1
25 * * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname logs >/dev/null 2>&1
35 * * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname apps >/dev/null 2>&1
40 * * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname stage >/dev/null 2>&1

# 45th minute of odd hours
45 1-23/2 * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname datahub >/dev/null 2>&1

# 30th minute of even hours
30 */2 * * * /usr/bin/python /root/pyncdu/pyncdu.py --jobname digital >/dev/null 2>&1
```

# check_ncdu_gzip.py and ncdu_summary.py
Put these files on the same server you're using to store the archives. In this example it's
`dodreamcatcher1.docl.nic`

Basic usage of the `check_ncdu_gzip.py` script is as follows:

```
Usage: check_ncdu_gzip.py [--debug] [--printtostdout] [--logfile] [--version] [--help] [--samplefileoption]

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


Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  --warn_size=WARN_SIZE
                        Warning level for the path size represented by this
                        NCDU report in GB. (Default=400000)
  --crit_size=CRIT_SIZE
                        Critical level for the path size represented by this
                        NCDU report in GB. (Default=500000)
  --max_age=MAX_AGE     Max age of the NCDU report's timestamp in hours.
                        (Default=24)
  --parse_timeout=PARSE_TIMEOUT
                        Timeout value in seconds. This determines how long we
                        wait for NCDU to to process the report before grabbing
                        the total size (Default=10)
  --parser_command=PARSER_COMMAND
                        Path to parser application (Default='/usr/bin/python
                        ncdu_summary.py'
  --display_units=DISPLAY_UNITS
                        Display units for parsed size. Valid units are
                        kb,mb,gb,tb (Default='gb')
  --filename=FILENAME   The full path of the filename to check. (Default=None)

  Debug Options:
    -d DEBUG, --debug=DEBUG
                        Available levels are CRITICAL (3), ERROR (2), WARNING
                        (1), INFO (0), DEBUG (-1)
    -p, --printtostdout
                        Print all log messages to stdout
    -l FILE, --logfile=FILE
                        Desired filename of log file output. Default is
                        "check_ncdu_gzip.py.log"

```

The `ncdu_summary.py` script is just a simple parser for the NCDU report files. I wrote it because
I couldn't figure out a way to get the `ncdu -1f-` command to give me a simple size summary to `STDOUT`.
The script is mildly speed optimized but I realize it's probably not perfect so I designed `check_ncdu_summary.py`
so that you could write your own parser as long as it spits out a JSON summary like this:

```
zcat ncdu-report.gz | python ncdu_summary.py
{"total_lines":424143,"total_size":359849564548,"parse_time":2.67200016975}
```

# Nagios Checks
On the same node you're using as your archive server (e.g., `dodreamcatcher1.docl.nic`) add a line in the local
`/etc/nrpe/npre.cfg` file that looks like this:

```
command[check_ncdu_gzip]=python /usr/lib64/nagios/plugins/check_ncdu_gzip.py --filename=$ARG1$ --warn_size=$ARG2$ --crit_size=$ARG3$ --max_age=$ARG4$ --parse_timeout=$ARG5$ --display_units=$ARG6$ --parser_command=$ARG7$
```

Define a new command in your Nagios config (e.g., `commands.cfg`) that looks like this:

```
define command {
    command_name    check_ncdu_gzip
######################################## filename | warn_size (gb) | crit_size (gb) | max_age (hrs) | parse_timeout (secs) | display_units (kb,mb,gb,tb) | parser_command
    command_line    /usr/lib/nagios/plugins/check_nrpe -H $HOSTADDRESS$ -t 20 -c check_ncdu_gzip -a $ARG1$ $ARG2$ $ARG3$ $ARG4$ $ARG5$ $ARG6$ /usr/lib64/nagios/plugins/ncdu_summary.py
}
```

Then you would define standard host and service checks to use the command like this. You would have one check for each job/path definition in the `runningconfig.ini` for `pyncdu.py` 

```
################ HOST: dodreamcatcher1.docl.nic #############
#################  Used for disk usage reporting ############
define host {
    use             TPL-hst-mapr-dev,TPL-host-pnp
    hostgroups      HG-mapr-dev
    host_name       DODREAMCATCHER1
    address         dodreamcatcher1.docl.nic
    check_command   check-host-alive
}
define service{
        use                             TPL-svc-mapr-dev,TPL-srv-pnp
        host_name                       DODREAMCATCHER1
        service_description             Disk Usage Report - maprN - USER 
        check_command                   check_ncdu_gzip!/root/ncdu-archives/ncdu-output-user-LATEST.gz!400000!500000!24!15!gb
        _graphitepostfix                nrpe_ncdu_user
        }

define service{
        use                             TPL-svc-mapr-dev,TPL-srv-pnp
        host_name                       DODREAMCATCHER1
        service_description             Disk Usage Report - maprN - DIGITAL 
        check_command                   check_ncdu_gzip!/root/ncdu-archives/ncdu-output-digital-LATEST.gz!400000!500000!24!15!gb
        _graphitepostfix                nrpe_ncdu_digital
        }

define service{
        use                             TPL-svc-mapr-dev,TPL-srv-pnp
        host_name                       DODREAMCATCHER1
        service_description             Disk Usage Report - maprN - TARGETAUDIENCE 
        check_command                   check_ncdu_gzip!/root/ncdu-archives/ncdu-output-targetaudience-LATEST.gz!400000!500000!24!15!gb
        _graphitepostfix                nrpe_ncdu_targetaudience
        }

define service{
        use                             TPL-svc-mapr-dev,TPL-srv-pnp
        host_name                       DODREAMCATCHER1
        service_description             Disk Usage Report - maprN - TRXNMATCH 
        check_command                   check_ncdu_gzip!/root/ncdu-archives/ncdu-output-trxnmatch-LATEST.gz!400000!500000!24!15!gb
        _graphitepostfix                nrpe_ncdu_trxnmatch
        }
```