""" functions for logging and printing info """
import json
import logging
import logging.config
import os
import time
from . import const
from . import error

# - lookup table for internal strings to logging levels
LEVELS = {
    'CRITICAL' : logging.CRITICAL,
    'ERROR'    : logging.ERROR,
    'WARNING'  : logging.WARNING,
    'INFO'     : logging.INFO,
    'DEBUG'    : logging.DEBUG,
    'NOTSET'   : logging.NOTSET
}

def start_logger(options):
    """ start the logger """
    # - default configuration
    config = {
        'version'                  : 1,
        'disable_existing_loggers' : False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            },
            'mimimal': {
                'format': '%(message)s'
            }
        },
        'handlers': {
            'log_file_handler': {
                'class'        : 'logging.FileHandler',
                'level'        : 'DEBUG',
                'formatter'    : 'detailed',
                'filename'     : options['panzer']['debug'] + '.log',
                'encoding'     : const.ENCODING
            },
            'console': {
                'class'      : 'logging.StreamHandler',
                'level'      : 'INFO',
                'formatter'  : 'mimimal',
                'stream'     : 'ext://sys.stderr'
            }
        },
        'loggers': {
            __name__: {
                'handlers'   : ['console', 'log_file_handler'],
                'level'      : 'DEBUG',
                'propagate'  : True
            }
        }
    }
    # - set 'debug' mode if requested
    if not options['panzer']['debug']:
        config['loggers'][__name__]['handlers'].remove('log_file_handler')
        del config['handlers']['log_file_handler']
    else:
        # - delete old log file if it exists
        # - don't see value in keeping old logs here...
        filename = config['handlers']['log_file_handler']['filename']
        if os.path.exists(filename):
            os.remove(filename)
    # - set 'quiet' mode if requested
    if options['panzer']['quiet']:
        verbosity_level = 'WARNING'
    else:
        verbosity_level = 'INFO'
    config['handlers']['console']['level'] = verbosity_level
    # - set 'strict' mode if requested
    if options['panzer']['strict']:
        log.strict_mode = True
    # - send configuration to logger
    logging.config.dictConfig(config)
    log('DEBUG', 'panzer', pretty_start_log('panzer starts'))
    log('DEBUG', 'panzer', pretty_title('OPTIONS'))
    log('DEBUG', 'panzer', pretty_json_repr(options))

def log(level_str, sender, message):
    """ send a log message """
    my_logger = logging.getLogger(__name__)
    # set strict_mode to default value, if not already set
    if not hasattr(log, "strict_mode"):
        log.strict_mode = False
    # - lookup table for internal strings to pretty output strings
    pretty_levels = {
        'CRITICAL' : 'FATAL:   ',
        'ERROR'    : 'ERROR:   ',
        'WARNING'  : 'WARNING: ',
        'INFO'     : '         ',
        'DEBUG'    : '         ',
        'NOTSET'   : '         '
    }
    message = str(message)
    sender_str = ''
    message_str = ''
    level = LEVELS.get(level_str, LEVELS['ERROR'])
    # -- level
    pretty_level_str = pretty_levels.get(level_str, pretty_levels['ERROR'])
    # -- sender
    if sender != 'panzer':
        # sender_str = '  ' + sender + ': '
        sender_str = '  '
    # -- message
    message_str = message
    output = ''
    output += pretty_level_str
    output += sender_str
    output += message_str
    my_logger.log(level, output)
    # - if 'strict' mode and error logged, raise exception to exit panzer
    if log.strict_mode and (level_str == 'ERROR' or level_str == 'CRITICAL'):
        log.strict_mode = False
        raise error.StrictModeError

def go_quiet():
    """ force logging level to be --quiet """
    my_logger = logging.getLogger(__name__)
    my_logger.setLevel(LEVELS['WARNING'])

def go_loud(options):
    """ return logging level to that set in options """
    my_logger = logging.getLogger(__name__)
    if options['panzer']['quiet']:
        verbosity_level = 'WARNING'
    else:
        verbosity_level = 'INFO'
    my_logger.setLevel(LEVELS[verbosity_level])

def decode_stderr_json(stderr):
    """ return a list of decoded json messages in stderr """
    # - check for blank input
    if not stderr:
        # - nothing to do
        return list()
    # - split the input (based on newlines) into list of json strings
    output = list()
    for line in stderr.split('\n'):
        if not line:
            # - skip blank lines: no valid json or message to decode
            continue
        json_message = list()
        try:
            json_message = json.loads(line)
        except ValueError:
            # - if json cannot be decoded, just log as ERROR prefixed by '!'
            json_message = {'level': 'ERROR', 'message': '!' + line}
        output.append(json_message)
    return output

def log_stderr(stderr, sender=str()):
    """ send a log from external executable """
    # 1. check for blank input
    if not stderr:
        # - nothing to do
        return
    # 2. get a string with sender's name
    if sender:
        # - remove file extension from sender's name if present
        sender = os.path.splitext(sender)[0]
    # 3. now handle the messages sent by sender
    json_message = decode_stderr_json(stderr)
    for item in json_message:
        level = item['level']
        message = item['message']
        log(level, sender, message)

def pretty_keys(dictionary):
    """ return pretty printed list of dictionary keys, num per line """
    if not dictionary:
        return []
    # - number of keys printed per line
    num = 5
    # - turn into sorted list
    keys = list(dictionary.keys())
    keys.sort()
    # - fill with blank elements to width num
    missing = (len(keys) % num)
    if missing != 0:
        to_add = num - missing
        keys.extend([''] * to_add)
    # - turn into 2D matrix
    matrix = [[keys[i+j] for i in range(0, num)]
              for j in range(0, len(keys), num)]
    # - calculate max width for each column
    len_matrix = [[len(col) for col in row] for row in matrix]
    max_len_col = [max([row[j] for row in len_matrix])
                   for j in range(0, num)]
    # - pad with spaces
    matrix = [[row[j].ljust(max_len_col[j]) for j in range(0, num)]
              for row in matrix]
    # - return list of lines to print
    matrix = ['  '.join(row) for row in matrix]
    return matrix

def pretty_list(input_list, separator=', '):
    """ return pretty printed list """
    if input_list:
        output = '  %s' % separator.join(input_list)
    else:
        output = '  empty'
    return output

def pretty_json_repr(data):
    """ return pretty printed data as a json """
    return json.dumps(data, sort_keys=True, indent=2)

def pretty_title(title):
    """ return pretty printed section title """
    output = '-' * 5 + ' ' + title.lower() + ' ' + '-' * 5
    return output

def pretty_start_log(title):
    """ return pretty printed title for starting log """
    output = '>' * 10 + ' ' + title + ' ' + '<' * 10
    return output

def pretty_end_log(title):
    """ return pretty printed title for ending log """
    output = '>' * 10 + ' ' + title + ' ' + '<' * 10 + '\n\n'
    return output

def pretty_path(input_path):
    """ return path string replacing '~' for home directory """
    home_path = os.path.expanduser('~')
    cwd_path = os.getcwd()
    output_path = input_path.replace(home_path, '~').replace(cwd_path, './')
    return output_path

def pretty_runlist(runlist):
    """ return pretty printed runlist """
    if not runlist:
        return ['  empty']
    output = list()
    current_kind = str()
    for i, entry in enumerate(runlist):
        if current_kind != entry['kind']:
            output.append(entry['kind'] + ':')
            current_kind = entry['kind']
        basename = pretty_path(entry['command'])
        if entry['arguments']:
            basename += ' '
            basename += ' '.join(entry['arguments'])
        line = '%d' % (i+1)
        line = line.rjust(3, ' ')
        line += ' %s' % basename
        output.append(line)
    return output

def pretty_runlist_entry(num, max_num, command, arguments):
    """ return pretty printed run list entry """
    basename = command
    if arguments:
        basename += ' '
        basename += ' '.join(arguments)
    cur = '%d' % (num+1)
    cur = cur.rjust(len(str(max_num)), ' ')
    line = ' [%s/%d] %s' % (cur, max_num, basename)
    return line

def time_stamp(text):
    """
    print time since first & previous time_stamp call
    """
    if not const.DEBUG_TIMING:
        return
    try:
        now = time.time() - time_stamp.start
    except AttributeError:
        time_stamp.start = time.time()
        now = 0
    try:
        elapsed = now - time_stamp.last
    except AttributeError:
        elapsed = 0
    now_str = str(round(now * 1000)).rjust(7)
    now_str += ' msec'
    now_str += '    '
    now_str += text.ljust(30)
    if elapsed * 1000 > 1:
        now_str += str(round(elapsed * 1000)).rjust(7)
        now_str += ' msec'
    else:
        now_str += ' ' * 12
    time_stamp.last = now
    print(now_str)

