#!/usr/bin/python

# Script to process buildfaster jobs
# (much of this gratuitously copied from: http://hg.mozilla.org/automation/orangefactor/file/5894e67315f8/woo_mailer.py)

import pickle
import isthisbuildfaster
import tempita
import ConfigParser
from sendemail import SendEmail
import queue
import os

email_tmpl = '''We compared '{{revision}}' against the following revisions of mozilla-central:
{{for r in compare_revisions}}
{{r}}
{{endfor}}

{{resultbody}}

Visit the gofaster dashboard at {{exturl}}/

Brought to you by the Mozilla A-Team.

https://wiki.mozilla.org/Auto-tools
IRC channel #ateam
'''

DEFAULT_CONF_FILE = os.path.dirname(os.path.realpath(__file__)) + '/../settings.cfg'

def main():
    import errno, sys
    from optparse import OptionParser
    
    parser = OptionParser()
    parser.add_option('-c', '--config', action='store', type='string',
                      dest='config_file', default=DEFAULT_CONF_FILE, help='specify config file')
    parser.add_option('-t', '--test', action='store_true', dest='test_mode',
                      help='test mode, check options and print email to screen but do not send')
    (options, args) = parser.parse_args()
    
    cfg = ConfigParser.ConfigParser()
    cfg.read(options.config_file)

    try:
        local_server_url = cfg.get('gofaster', 'local_server_url')
        external_server_url = cfg.get('gofaster', 'external_server_url')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        sys.stderr.write('"local_server_url" and "external_server_url" options not found in\n"gofaster" section in file "%s".\n' % options.config_file)
        sys.exit(errno.EINVAL)

    try:
        mail_username = cfg.get('email', 'username')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        sys.stderr.write('No "username" option defined in "email" section of file "%s".' % options.config_file)
        sys.exit(errno.EINVAL)
    
    try:
        mail_password = cfg.get('email', 'password')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_password = None
        
    try:
        mail_server = cfg.get('email', 'server')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_server = 'mail.mozilla.com'
    
    try:
        mail_port = cfg.getint('email', 'port')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_port = 465
        
    try:
        mail_ssl = cfg.getboolean('email', 'ssl')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        mail_ssl = True

    # Get the next job from the queue
    job = queue.pop_job()
    if not job:
        print "No pending jobs"
        exit(0)

    data = isthisbuildfaster.compare_test_durations('mozilla-central', None,
                                                    job['tree'], 
                                                    job['revision'], 
                                                    job['submitter'])
    #import json
    #data = json.loads(open('/home/wlach/src/gofaster/isthisbuildfaster2.json', 'r').read())

    revision = '%s %s' % (job['tree'], job['revision'])
    mozilla_central_revisions = data['revisions'][0]['revision']

    notable_results = []
    resultbody = ""

    for (platform_name, platform) in data["durations"].iteritems():
        resultlines = []
        for (test_name, test) in sorted(platform.iteritems(), key=lambda t: t[0]):
            diff = test['mean'] - test['testtime']
            resultlines.append(", ".join(str(i) for i in ([test_name, test['mean'], test['testtime'], diff])))
            if abs(test['testtime']-test['mean']) > 2*test['stdev']:
                notable_results.append({ 'platform': platform_name, 
                                         'test': test_name, 
                                         'testtime': test['testtime'],
                                         'mean': test['mean'],
                                         'stdev': test['stdev'],
                                         'diff': diff })
                               
        resultbody += "Results for %s\n" % platform_name
        resultbody += "Suite, Mean result, %s, diff (seconds)\n" % revision
        resultbody += "\n".join(resultlines) + "\n\n"

    if len(notable_results) > 0:
        notable_text = "Notable results (> 2* faster/slower than standard deviation)\n"
        notable_text += "Platform, Suite, %s, Mean, stdev, diff (seconds)\n" % revision
        for notable_result in sorted(notable_results, key=lambda r: r['test'] + (r['platform']*10)):
            notable_text += ', '.join( str(i) for i in [ notable_result['platform'], 
                                                         notable_result['test'], 
                                                         notable_result['testtime'], 
                                                         notable_result['mean'], 
                                                         notable_result['stdev'],
                                                         notable_result['diff'] ])
            notable_text += '\n'
    resultbody = notable_text + '\n' + resultbody

    subject = 'Is this build faster? Results for %s' % revision
    tmpl = tempita.Template(email_tmpl)
    text = tmpl.substitute({'subject': subject,
                            'revision': revision,
                            'compare_revisions': mozilla_central_revisions,
                            'exturl': external_server_url,
                            'resultbody': resultbody})
    to = [ job['return_email'] ]

    if options.test_mode:
        print 'From: %s' % mail_username
        print 'To: %s' % " ".join(to)
        print 'Subject: %s' % subject
        print
        print text
    else:
        print 'Sending email to %s...' % ', '.join(to)
        SendEmail(From=mail_username, To=to, Subject=subject,
                  Username=mail_username, Password=mail_password, TextData=text,
                  Server=mail_server, Port=mail_port, UseSsl=mail_ssl)
        print 'Done!'

if __name__ == '__main__':
    main()