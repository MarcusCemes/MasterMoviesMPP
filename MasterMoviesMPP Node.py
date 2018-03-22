'''

Copyright (c) 2018 Marcus Cemes

Licensing details for this software are availiable at http://www.binpress.com/license/view/l/726188b547b5721aef641f792c74170e
This program was designed for TurboThread.com by Marcus Cemes @ mastermovies.co.uk
'''

# Import modules
import sys
import argparse
import uuid
import os
import errno
import atexit
import time
import datetime
import pathlib
import subprocess
import json
import shutil
import logging
import configparser  # dependancy
import MySQLdb   # External dependancy "mysqlclient"
import colorama  # External dependancy


### CLASSES ###

class jobStatus:
    imported = 0
    ingesting = 1
    transcoding = 2
    transcoded = 3
    exporting = 4
    completed = 5
    error = 13


class smallJobStatus:
    ready = 0
    running = 1
    completed = 2
    error = 13


### METHODS ###

on_new_line = True
def verbose(msg="", persistent_line=True, color=colorama.Fore.RESET):
    global on_new_line
    line = datetime.datetime.now().strftime("%x %H:%M:%S")+': '+color+colorama.Style.BRIGHT+msg+colorama.Style.RESET_ALL
    if persistent_line:
        if on_new_line:
            sys.stdout.write(line+'\n')
        else:
            sys.stdout.write('\033[2K\r'+line+'\n')  # Clear line
            on_new_line = True
    else:
        if on_new_line:
            sys.stdout.write(line)
            on_new_line = False
        else:
            sys.stdout.write('\033[2K\r'+line)
    sys.stdout.flush()


def silent_print(msg='', colour=colorama.Fore.RESET):
    if not is_verbose:
        global first_silent_print
        if not first_silent_print:
            colour = colorama.Cursor.UP()+'\033[2K'+colour
        first_silent_print = False
        print(colour + colorama.Style.BRIGHT + msg + colorama.Style.RESET_ALL)


def quitFatally(errorMessage, exitCode=13, exception=False):
    print('')
    print(colorama.Fore.RED+colorama.Style.BRIGHT+('*** FATAL ERROR - CODE %d ***' % exitCode).center(terminal_width))
    if isinstance(errorMessage, str):
        print(errorMessage.center(terminal_width))
    else:
        for msg in errorMessage:
            print(msg.center(terminal_width))
    if exception:
        print('Error message to help you :)'.center(terminal_width))
        logger.error("The original exception:", exc_info=exception)
    try:
        if 'cursor' in globals():
            __unregister__()  # Attempt to unregister if the connection exists
    except Exception:
        sys.exc_clear()  # Ignore the error
    print(colorama.Style.RESET_ALL)
    os._exit(exitCode)


def silentRemove(path):
    try:
        os.remove(path)
    except Exception:
        return True


def get_smallest_output():
    # return the output with the smallest y
    if len(outputs) > 0:
        smallest = outputs[0]
        for output in outputs:
            if output['maxY'] < smallest['maxY']:
                smallest = output
        return smallest
    else:
        return None


def increasesleep_time():
    global sleep_time
    if sleep_time < maxsleep_time:
        sleep_time *= 2
        if sleep_time > maxsleep_time:
            sleep_time = maxsleep_time


def create_connection():
    global connection_open, connection, cursor, server, port, database, username, password
    if not connection_open:
        try:
            connection = MySQLdb.connect(host=server, port=port, db=database, user=username, passwd=password)
            cursor = connection.cursor(MySQLdb.cursors.DictCursor)
            connection.autocommit(False)
            connection_open = True
        except MySQLdb.InterfaceError:
            return False
    return True


def closeConnection():
    global connection, connection_open
    connection_open = False
    connection.close()


def new_unused_uuid():
    while True:
        id = uuid.uuid4()
        execute("SELECT jobUUID FROM job WHERE jobUUID = %s UNION SELECT nodeUUID FROM node WHERE nodeUUID = %s", id.bytes, id.bytes)
        if cursor.fetchone():
            continue
        return id


# Basic database maintenace to keep consistency. Shouldn't be necessary, but here just in case
def database_maintenance():
    global policies
    try:
        connection.autocommit(True)
        # Purge old nodes
        execute('DELETE FROM node WHERE TIMESTAMPDIFF(SECOND, lastAccess, CURRENT_TIMESTAMP) > %s', int(policies['nodeTimeout']))

        # Rollback jobs that are stuck in ingesting/exporting, without an asigned node
        connection.autocommit(False)
        # execute('UPDATE job LEFT JOIN node ON jobUUID = fk_jobUUID SET status = status-1 WHERE fk_jobUUID IS NULL AND STATUS IN (%s, %s)', jobStatus.ingesting, jobStatus.exporting) # TSQL
        execute("LOCK TABLES node READ, job WRITE;")  # Prevent deadlocks
        execute("UPDATE job SET status = status - 1 WHERE status IN (%s, %s) AND jobUUID NOT IN (SELECT fk_jobUUID FROM node WHERE fk_jobUUID IS NOT NULL);", jobStatus.ingesting, jobStatus.exporting);
        connection.commit()
        execute("UNLOCK TABLES;")
        connection.autocommit(True)

        # Remove this node from any jobs
        execute('UPDATE {}Job SET fk_nodeUUID = NULL, status = %s  WHERE fk_nodeUUID = %s AND status = %s'.format(node_type), smallJobStatus.ready, unique_id.bytes, smallJobStatus.running)
    except MySQLdb.Error:
        pass  # Tasks are not necessary and do not require high priority
    connection.autocommit(False)


def failjob(**kwargs):
    # Update the smallJob status and failure
    execute('UPDATE {}Job SET status = %s, failures = failures + 1 WHERE fk_nodeUUID = %s'.format(node_type), smallJobStatus.ready, unique_id.bytes)
    execute('SELECT failures, fk_jobUUID FROM {}Job WHERE fk_nodeUUID = %s'.format(node_type), unique_id.bytes)
    row = cursor.fetchone()
    if row['failures'] >= int(policies['failureTolerance']) or 'fatal' in kwargs and kwargs['fatal'] == True:
        # Update the job status to error if it passes the failure tolerancy, or it's a fatal error
        verbose("Job failed, exceeded maximum failure tolerance, or fatal job error occurred", True, colorama.Fore.RED)
        execute('UPDATE job SET status = %s, failed = 1 WHERE jobUUID = %s', jobStatus.error, row['fk_jobUUID'])
        execute('UPDATE {}Job SET status = %s WHERE fk_nodeUUID = %s'.format(node_type), smallJobStatus.error, unique_id.bytes)
        connection.commit()

        # Remove working files, don't need them
        shutil.rmtree(work_paths['ingest'] / job_uuid_hex, True)
        shutil.rmtree(work_paths['transcode'] / job_uuid_hex, True)
        shutil.rmtree(work_paths['export'] / job_uuid_hex, True)

        # Move the fiel to quarantine
        source_file = work_paths['source'] / job_data['sourceName']
        if source_file.is_file():
            quarantine = work_paths['root'] / 'quarantine'
            quarantine.mkdir(exist_ok=True)
            shutil.move(str(source_file), str(quarantine))
        return True

    connection.commit()
    return False


# Shutdown hook to unregister from the database
unregistered = False
def __unregister__():
    print('')
    print('*** DETECTED TERMINATION ***'.center(terminal_width))
    global unregistered
    if unregistered:
        print('Already unregistered from the database'.center(terminal_width))
    else:
        create_connection()
        connection.rollback() # Otherwise might conflict statements
        deauthorise() # Clean itself from the database (should not be necessary)
        execute("DELETE FROM node WHERE nodeUUID=%s", unique_id.bytes) # Unregister the node
        connection.commit()
        closeConnection()
        print('Successfully unregistered from the database'.center(terminal_width))


# In the case of an uncaught error, attempt to unregister from the database
def __panicUnregister__(exc_type, exc_value, exc_traceback):
    print('')
    print('*** HANDLING UNCAUGHT EXCEPTION ***'.center(terminal_width))
    print('Attempting to unregister from the database'.center(terminal_width))
    create_connection()
    connection.rollback()
    deauthorise()
    try:
        execute("DELETE FROM node WHERE nodeUUID = %s", unique_id.bytes)
        connection.commit()
    except Exception:
        print('Failed. Database may be temporarily inconsistent until next maintenance')
    else:
        global unregistered
        unregistered = True
        print('Unregistered. Panic over.'.center(terminal_width))
        print('')
        logger.error("The original exception:", exc_info=(exc_type, exc_value, exc_traceback))
        print('')
    closeConnection()

# The new SQL module requires parameters to be in a tuple, unlike pyodbc
def execute(sql, *params, **kwargs):
    global retry_count, retry_interval
    lostConnection = 0
    executemany = kwargs.get('executemany', False)
    while not create_connection() and lostConnection < retry_count:
        lostConnection += 1
        verbose("Lost connection to the database. Retrying...", False, colorama.Fore.RED)
        time.sleep(retry_interval)
    if lostConnection == retry_count and lostConnection > 0:
        quitFatally("Connection to the database was lost.")
    else:
        if lostConnection > 0:
            print(colorama.Cursor.UP()+'\033[2K')
        if not executemany:
            return cursor.execute(sql, params)
        else:
            return cursor.executemany(sql, params[0])


# Update polices from the database
def updatePolicies():
    try:
        # Update the policy table
        execute("SELECT policy, value FROM policy")
        rows = cursor.fetchall()
        for row in rows:
            policies[row['policy']] = row['value']  # Add to the policies dictionary as (policy: value)

        # Get node specific policies
        execute("SELECT terminate, authorise FROM node WHERE nodeUUID = %s", unique_id.bytes)
        row = cursor.fetchone()
        if not row:
            quitFatally('Node is no longer on the database. Shutting down to avoid conflict')
        node_policies['terminate'] = row['terminate']
        node_policies['authorise'] = row['authorise']

        # Refresh the outputs
        del outputs[:]  # Empty the list
        execute("SELECT * FROM output WHERE active = 1")
        rows = cursor.fetchall()
        for row in rows:
            outputs.append(row)

        # Update the node's last access
        execute('UPDATE node SET lastAccess = CURRENT_TIMESTAMP WHERE nodeUUID = %s', unique_id.bytes)  # Update last access
        connection.commit()  # update the node's last access

    except Exception as e:
        quitFatally('Could not update policies. The database might be down.', errno.ECONNRESET, e)  # Policies most be reachable

def authorise():
    global job_data, job_uuid, job_uuid_hex, authorised
    job_uuid = job_data['jobUUID']
    job_uuid_hex = uuid.UUID(bytes = job_uuid).hex
    authorised = True
    execute("UPDATE node SET isActive = 1, fk_jobUUID = %s WHERE nodeUUID = %s", job_uuid, unique_id.bytes)
    connection.commit()

    # Some things that need to happen at the start of each job
    verbose("", True)  # Create a space before the job in the terminal output
    sleep_time = 5  # Reset sleep timer, jobs are present
    print(colorama.Cursor.UP()+'\033[2K')


def deauthorise():
    global job_data, job_uuid, job_uuid_hex, authorised
    job_data = None
    job_uuid = None
    job_uuid_hex = None
    authorised = False
    execute("UPDATE node SET isActive = 0, fk_jobUUID = NULL WHERE nodeUUID = %s", unique_id.bytes)
    execute("UPDATE {}Job SET fk_nodeUUID = NULL WHERE fk_nodeUUID = %s".format(node_type), unique_id.bytes)
    connection.commit()


def debug(m):
    print(datetime.datetime.now().strftime("%S,%f") + ": " + m)


if not pathlib.Path('config.ini').is_file():
    print('config.ini file was not found.')
    os._exit(1)

# This is the command line argument parser
programDescription = "MasterMovies Media Processing Platform, designed for TurboThread.com\nCopyright (c) 2018 Marcus Cemes\n\nThis program must be launched in one of three modes: Ingest, Transcode or Export. At least one of each is required to run in parallel for a complete system.\nA database connection is also required, specified in the config file."
parser = argparse.ArgumentParser(description=programDescription, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("node_type", choices=("ingest", "transcode", "export"), help="the selected mode the program should start in.\nOptions available: 'ingest', 'transcode' or 'export'.", metavar="node_type")
args = parser.parse_args()

cfg = configparser.ConfigParser()
cfg.read('config.ini')

version = '1.3'  # The program version

node_type = args.node_type.lower()
is_verbose = cfg['Program'].getboolean('verbose', True)
server = cfg['Database'].get('server', 'localhost')
port = cfg['Database'].getint('port', 3306)
username = cfg['Database'].get('username')
password = cfg['Database'].get('password')
database = cfg['Database'].get('database', 'MasterMoviesMMP')
retry_count = cfg['Database'].getint('retry_count', 12)
retry_interval = cfg['Database'].getint('retry_interval', 5)
work_dir = cfg['Path'].get('work_dir')
source_dir = cfg['Path'].get('source_dir')
move_after_export = cfg['Path'].getboolean('move_after_export', False)
move_after_export_dir = cfg['Path'].get('move_after_export_dir')

# These are runtime global variables. Best not to touch.
node_types = {'ingest':0, 'transcode':1,'export':2, 'build':3}
work_paths = {}
unique_id = None
policies = {} # Global polices
node_policies = {} # Node specific policies
outputs = [] # Transcode outputs
job_data = None # The last job
job_uuid = None # same as job_data['jobUUID']
media_info = None
job_uuid_hex = None
authorised = False # Whether the job is authorised. Also an indicator of whether a job is active
node_authorised = True
connection_open = False
first_silent_print = True # used for silent_print()
required_policies = ['ingestEnabled', 'transcodeEnabled', 'exportEnabled', 'terminateAll', 'nodeTimeout', 'verifyDuringIngest', 'failureTolerance']

# THe only solution that I found to print the traceback of uncaught errors in __panicUnregister__()
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

# Customisable variables. Play around with them if you want
terminal_width = cfg['Program'].getint('terminal_width', 80) # For cantering text in the terminal window (the terminal width)
maxsleep_time = cfg['Program'].getint('default_sleep', 5) # The maximum sleep time upon several sleep cycles
sleep_time = cfg['Program'].getint('max_sleep', 10) # The initial sleep time, doubles every sleep cycle until maxsleep_time is reached


colorama.init() # For pretty colours on Windows...

# Roll the credits
print('')
print(colorama.Style.RESET_ALL+colorama.Style.BRIGHT + '-'*terminal_width)
print(('MasterMovies Media Processing Platform: {node} node v{version}'.format(node=node_type, version=version)).center(terminal_width))
print('Copyright (c) 2018 Marcus Cemes'.center(terminal_width))
print('Designed for TurboThread.com'.center(terminal_width))
print('-'*terminal_width)
print(colorama.Style.RESET_ALL)
print('Running in {} mode'.format(node_type).center(terminal_width))
print('')

sys.stdout.write("\x1b]2;MasterMovies Media Processing Platform\x07")
with open(os.devnull, 'w') as FNULL:
    subprocess.call("title MasterMovies Media Processing Platform", stdout=FNULL, stderr=FNULL, shell=True)

# Create the database connection
verbose('Connecting to database on {}:{} with username {}...'.format(server, port, username), False, colorama.Fore.YELLOW)
if not create_connection(): # Create the connection
    quitFatally('Could not create a connection to the database.', errno.EHOSTDOWN, sys.exc_info())
verbose('Connection to database on {}:{} successful'.format(server, port), True, colorama.Fore.GREEN)

unique_id = new_unused_uuid() # Give this node a UUID
verbose('This node\'s UUID is: {}'.format(unique_id), True)

# Create the regular and panic termination hooks
atexit.register(__unregister__)
sys.excepthook = __panicUnregister__

# Register the node with the DB
verbose('Registering this node on the database...', False, colorama.Fore.YELLOW)
try:
    execute("INSERT INTO node (nodeUUID, lastAccess, type) VALUES (%s, CURRENT_TIMESTAMP ,%s)", unique_id.bytes, node_types[node_type])
    connection.commit()
    verbose('Successfully registered this node on the database', True, colorama.Fore.GREEN)
except:
    quitFatally('Unable to register this node on the database', errno.ECONNRESET, sys.exc_info())

# Update policies
updatePolicies() # Needed for the work directories

# Check whether the working path exists
work_dir_path = pathlib.Path(work_dir)
work_paths['root'] = work_dir_path
work_paths['source'] = pathlib.Path(source_dir)
work_paths['ingest'] = work_dir_path / 'ingest'
work_paths['transcode'] = work_dir_path / 'transcode'
work_paths['export'] = work_dir_path / 'export'
for key, path in work_paths.items():
    if not path.is_dir():
        quitFatally('Unable to access {} directory at {}.\nFor safety reasons, we won\'t generate the directory, as it may be a configuration error.'.format(key, str(path)), errno.ENOENT)

if not is_verbose:
    print('Not in verbose mode. No further runtime information will be displayed.')


# The main program loop. Will be broken if time.sleep is interrupted, or when marked for termination
while True:

    if authorised:
        deauthorise()

    verbose('Node ready', False, colorama.Fore.MAGENTA)
    silent_print("Ready", colorama.Fore.GREEN)

    updatePolicies()  # Get the latest policies from the database
    database_maintenance()

    # Check for global scheduled termination
    if policies['terminateAll'].lower() in ('1', 'true', 'yes'):
        verbose('Global termination is scheduled (\'terminateAll is 1\')', False, colorama.Fore.CYAN)
        break
    if node_policies['terminate'] == bytes([1]):
        verbose('Node termination is scheduled (terminate is 1)', False, colorama.Fore.CYAN)
        break

    # Check whether this work type is authorised
    if policies[node_type+'Enabled'] not in ('1', 'true') or node_policies['authorise'] != bytes([1]):
        if node_authorised:
            node_authorised = False
        verbose('Not authorised for work', False, colorama.Fore.RED)
        silent_print('Disabled', colorama.Fore.RED)

    elif len(outputs) == 0:
        verbose('No active outputs. Disabled for security reasons.', False, colorama.Fore.RED)
        silent_print("Error: no outputs", colorama.Fore.RED)
    else:
        # Node is active, search for work
        node_authorised = True # Used to display the error message only once if not authorised

        if (node_type == "ingest"):

            # Register for a job
            execute("SELECT * FROM job WHERE status = %s LIMIT 1 FOR UPDATE", jobStatus.imported)
            job_data = cursor.fetchone()
            if not job_data:
                connection.rollback()
            else:
                # Update the job status, and add the jobUUID if needed (necessary for authorise() )
                execute("UPDATE job SET status = %s WHERE jobID = %s", jobStatus.ingesting, job_data['jobID'])
                if job_data['jobUUID'] == None:
                    job_data['jobUUID'] = new_unused_uuid().bytes
                    execute("UPDATE job SET jobUUID = %s WHERE jobID = %s LIMIT 1", job_data['jobUUID'], job_data['jobID'])
                authorise()  # This will also commit

                # Create the ingestJob entry, and add the date if needed
                connection.autocommit(True)
                execute("INSERT INTO ingestJob (fk_jobUUID, fk_nodeUUID, status) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE fk_nodeUUID = %s, status = %s", job_data['jobUUID'], unique_id.bytes, smallJobStatus.running, unique_id.bytes, smallJobStatus.running)
                if job_data['dateAdded'] == None:
                    job_data['dateAdded'] = datetime.datetime.now()
                    execute("UPDATE job SET dateAdded = %s WHERE jobID = %s LIMIT 1", job_data['dateAdded'], job_data['jobID'])
                connection.autocommit(False)

                # Start the ingest of the job
                silent_print("Ingesting...", colorama.Fore.CYAN)
                verbose('Authorised for ingest of jobID: {}'.format(job_data['jobID']), True, colorama.Fore.CYAN)

                sFile = work_paths['source'] / job_data['sourceName']
                if not sFile.is_file():
                    # Check the quarantine
                    qFile = work_paths['root'] / 'quarantine' / job_data['sourceName']
                    if not qFile.is_file():
                        verbose('Could not find the source file: {}'.format(str(sFile)), True, colorama.Fore.RED)
                        verbose('Ingest failed', True, colorama.Fore.RED)
                        failjob(fatal=True)
                        deauthorise()
                        continue
                    else:
                        verbose('Found the source file in quarantine. Moving to source.', True, colorama.Fore.YELLOW)
                        shutil.move(str(qFile), str(work_paths['source']))

                ingestLocation = work_paths['ingest'] / job_uuid_hex
                try:
                    ingestLocation.mkdir(parents=False, exist_ok=True) # Create the job ingest folder
                except Exception as e:
                    verbose('Could not create ingest folder {}'.format(str(ingestLocation)), True, colorama.Fore.RED)
                    verbose('Ingest failed', True, colorama.Fore.RED)
                    failjob() # Fatally fail the job
                    deauthorise()
                    continue # Next job
                else:
                    # Read media information
                    verbose('Reading media information...', False, colorama.Fore.YELLOW)
                    cmd = 'ffprobe -loglevel fatal -print_format json -show_format -show_streams "{}"'.format(sFile)
                    ingestMFile = ingestLocation / 'media_info.txt'
                    media_info = None
                    with open(ingestMFile, "w") as m:
                        subprocess.call(cmd, stdout=m, shell=True)
                    with open(ingestMFile, 'r') as m:
                        media_info = m.read()
                    media_info = json.loads(media_info)
                    execute("UPDATE job SET mediaInfo = %s WHERE jobUUID= %s", json.dumps(media_info), job_uuid)
                    connection.commit()
                    verbose('Media information updated', True, colorama.Fore.GREEN)

                    skip_verification = True
                    if policies['verifyDuringIngest'].lower() not in ('0', 'false', 'no'):
                        skip_verification = False

                        # Analyse the footage, writing to the log and error files
                        verbose('Verifying integrity of the video file...', False, colorama.Fore.YELLOW)
                        integrityFile = ingestLocation / 'integrity.log'
                        with open(integrityFile, 'w') as err:
                            cmd = 'ffmpeg -loglevel error -nostdin -i "{source}" -f null -'.format(source=str(sFile)) # Decode the video and check for errors
                            subprocess.call(cmd, stderr=err, shell=True)

                    # Read the size of the error log, make sure there were no errors
                    if not skip_verification and integrityFile.stat().st_size > 0:
                        verbose('Video verification failed. Refer to integrity.log in the ingest folder', True, colorama.Fore.RED)
                        verbose('Ingest failed', True, colorama.Fore.RED)
                        failjob()
                        deauthorise()
                        continue
                    else:
                        verbose('Video integrity verified', True, colorama.Fore.GREEN)

                    verbose('Splitting video...', False, colorama.Fore.YELLOW)
                    sourceFileSize = sFile.stat().st_size
                    segment_time = 0 # The length of split segments
                    if sourceFileSize > 100*(10**6):
                        segment_time = 10 # 10 sceonds for 100+ MB
                    elif sourceFileSize > 50*(10**6):
                        segment_time = 5 # 5 seconds for 50+ MB

                    # Segment the file into the ingest folder
                    splitFile = ingestLocation / 'split.log'
                    with open(splitFile, 'w') as err:
                        cmd = 'ffmpeg -loglevel error -y -nostdin -i "{source}" -vcodec copy -acodec copy -an -f segment -segment_time {segment_time} "{output}"'.format(source=str(sFile), segment_time=segment_time, output=ingestLocation / '%d.ts') # The last %d is an ffmpeg decorater, not python
                        subprocess.call(cmd, stderr=err, shell=True)
                    if (splitFile.stat().st_size > 0):
                        verbose("Error while splitting the file, refer to split.log in the ingest folder", True, colorama.Fore.RED)
                        failjob()
                        deauthorise()
                        continue
                    verbose('Video file split', True, colorama.Fore.GREEN)

                    # Create jobs for transcode
                    verbose('Submitting transcode jobs to database', False, colorama.Fore.YELLOW)
                    parts = []
                    for file in ingestLocation.glob('*.ts'):
                        t = (job_uuid, int(file.stem)) # Tuple with the job_uuid, and part number
                        parts.append(t) # Store the part number in parts

                    execute("DELETE FROM transcodeJob WHERE fk_jobUUID= %s", job_uuid) # Purge any transcode jobs
                    execute("INSERT INTO transcodeJob (fk_jobUUID, segmentPart) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status = 0, fk_nodeUUID = NULL", parts, executemany=True)
                    connection.commit()
                    verbose('Created transcode jobs in the database', True, colorama.Fore.GREEN)

                    # Mark the ingest as complete, and the job as in the transcode phase
                    execute('UPDATE job SET status = %s WHERE jobUUID = %s', jobStatus.transcoding, job_uuid)
                    execute('UPDATE ingestJob SET status = %s, fk_nodeUUID = NULL WHERE fk_jobUUID = %s', smallJobStatus.completed, job_uuid)
                    connection.commit()

                    verbose('Successful ingest: jobID %d is ready for transcoding.' % job_data['jobID'], True, colorama.Fore.CYAN)
                    deauthorise()
                    continue


        elif (node_type == "transcode"):
            # Update one row to match it's nodeUUID, and both job and transcodeJob have the right status
            execute('SELECT * FROM transcodeJob INNER JOIN job ON jobUUID = fk_jobUUID  WHERE job.status = %s AND transcodeJob.status = %s LIMIT 1 FOR UPDATE', jobStatus.transcoding, smallJobStatus.ready)

            if cursor.rowcount == 0:
                connection.rollback()
            else:
                # Start the job if the SQL gave it a job
                job_data = cursor.fetchone()
                execute('UPDATE transcodeJob SET fk_nodeUUID = %s, transcodeJob.status = %s WHERE transcodeJobID = %s', unique_id.bytes, smallJobStatus.running, job_data['transcodeJobID'])
                authorise() # This will also commit the changes

                # Start the transcode
                silent_print("Transcoding...", colorama.Fore.CYAN)
                verbose('Authorised for transcode of transcodeJobID {}'.format(job_data['transcodeJobID']), True, colorama.Fore.CYAN)

                try:
                    media_info = json.loads(job_data['mediaInfo']) # Created by the ingest process
                except (TypeError, json.decoder.JSONDecodeError):
                    verbose('Unable to load media information. Re-ingest is necessary.', True, colorama.Fore.RED)
                    failjob(fatal=True)
                    deauthorise()
                    continue
                ingestLocation = work_paths['ingest'] / job_uuid_hex
                transcodeLocation = work_paths['transcode'] / job_uuid_hex
                verbose('Searching for source file...', False, colorama.Fore.YELLOW)
                try:
                    transcodeLocation.mkdir(parents=False, exist_ok=True) # Create the job ingest folder
                except:
                    verbose('Unable to create transcode folder {}'.format(transcodeLocation), True, colorama.Fore.RED)
                    verbose('Transcode failed', True, colorama.Fore.RED)
                    failjob()
                    deauthorise()
                    continue

                tFile = ingestLocation / ('{}.ts'.format(job_data['segmentPart']))
                if not tFile.is_file():
                    # Source file can't be found
                    verbose('Could not find the part file: '+str(tFile), True, colorama.Fore.RED)
                    failjob()
                    deauthorise()
                    verbose('Transcode failed', True, colorama.Fore.RED)
                    continue # Start the next job

                else:
                    # File found, ready for transcode
                    verbose('Preparing for transcode...', False, colorama.Fore.YELLOW)

                    # Build the transcode command
                    cmd = 'ffmpeg -y -loglevel error -nostdin -i "{source}"'.format(source=str(tFile))
                    videoX = media_info['streams'][0]['width']
                    videoY = media_info['streams'][0]['height']
                    stream_framerate_fraction = media_info['streams'][0]['r_frame_rate'].split('/') # FFProbe gives a fraction...
                    stream_framerate = int(round(int(stream_framerate_fraction[0]) / int(stream_framerate_fraction[1])))
                    active_transcodes = 0
                    for resolution in outputs:
                        xReduction = resolution['maxX'] / videoX
                        yReduction = resolution['maxY'] / videoY
                        # Check if it would be an upscale, if so, skip
                        if xReduction <= 1 or yReduction <= 1:
                            newX = resolution['maxX']
                            newY = round(videoY * xReduction) # Scale down for the video width keeping the aspect ratio
                            if newY > resolution['maxY']:
                                newY = resolution['maxY'] # If it's still too high, shrink it down to fit the height (portrait based video)
                                newX = round(videoX * yReduction)
                            framerate = ""
                            if stream_framerate > resolution['maxFramerate']:
                                framerate = "-r "+str(resolution['maxFramerate'])
                            # Resolution must be even, especially the vertical resolution
                            if newX % 2 == 1:
                                newX += 1;
                            if newY % 2 == 1:
                                newY += 1;
                            cmd += ' -s {x}x{y} -vcodec libx264 -an -profile:v {profile} -preset {preset} -crf {crf} {framerate} "{output}"'.format(x=newX, y=newY, profile=resolution['profile'], preset=resolution['preset'], crf=resolution['CRF'], framerate=framerate, output=transcodeLocation / ('{part}_{res}.ts'.format(part=job_data['segmentPart'], res=resolution['maxY'])))
                            active_transcodes += 1
                    if active_transcodes == 0:
                        # If it's too small, transcode without scaling, and rename to lowest resolutions
                        resolution = get_smallest_output() # Only for file renaming purposes
                        framerate = ""
                        if stream_framerate > resolution['maxFramerate']:
                            framerate = "-r "+resolution['maxFramerate']
                        cmd += ' -vcodec libx264 -acodec aac -b:a {audio}k -profile:v {profile} -preset {preset} -crf {crf} {framerate} "{output}"'.format(profile=resolution['profile'], preset=resolution['preset'], crf=resolution['CRF'], framerate=framerate, output=transcodeLocation / ('{part}_{res}.ts'.format(part=job_data['segmentPart'], res=resolution['maxY'])))

                    verbose('Transcoding...', False, colorama.Fore.YELLOW)
                    result = subprocess.run(cmd, stderr=subprocess.PIPE, shell=True)
                    if len(result.stderr) > 0:
                        verbose('Transcode failed. Error: %s' % result.stderr.decode('utf-8'), True, colorama.Fore.RED)
                        failjob()
                        deauthorise()
                        continue
                    verbose('Transcode complete', True, colorama.Fore.GREEN)

                    # Set the transcode job as completed
                    execute("UPDATE transcodeJob SET status = %s, fk_nodeUUID = NULL WHERE fk_nodeUUID = %s", smallJobStatus.completed, unique_id.bytes)
                    # Update all jobs to export that have no more transcode jobs remaining
                    execute("LOCK TABLES job WRITE, transcodeJob READ;")
                    execute("UPDATE job SET job.status = %s WHERE job.status = %s AND job.jobUUID NOT IN (SELECT fk_jobUUID FROM transcodeJob WHERE transcodeJob.fk_jobUUID = job.jobUUID AND transcodeJob.status < %s)", jobStatus.transcoded, jobStatus.transcoding, smallJobStatus.completed)
                    connection.commit()
                    execute("UNLOCK TABLES;")
                    verbose('Database has been updated with transcode completion', True, colorama.Fore.CYAN)
                    deauthorise()
                    continue



        elif (node_type == "export"):
            # Export finished transcode segments
            execute("SELECT * FROM job WHERE status = %s LIMIT 1 FOR UPDATE", jobStatus.transcoded)

            job_data = cursor.fetchone()
            if not job_data:
                connection.rollback()
            else:
                execute('UPDATE job SET status = %s WHERE jobUUID = %s LIMIT 1', jobStatus.exporting, job_data['jobUUID'])
                authorise()  # This will also commit the changes

                execute("INSERT INTO exportJob (fk_jobUUID, fk_nodeUUID, status) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE status = %s, fk_nodeUUID = %s", job_data['jobUUID'], unique_id.bytes, smallJobStatus.running, smallJobStatus.running, unique_id.bytes)
                connection.commit()

                silent_print("Exporting...", colorama.Fore.CYAN)
                verbose('Authorised for export of jobID %d' % job_data['jobID'], True, colorama.Fore.CYAN)

                # Start the export
                sourceLocation = work_paths['source']
                transcodeLocation = work_paths['transcode'] / job_uuid_hex
                exportLocation = work_paths['export'] / job_uuid_hex
                try:
                    media_info = json.loads(job_data['mediaInfo'])
                except (TypeError, json.decoder.JSONDecodeError):
                    verbose('Unable to load media information. Re-ingest is necessary.', True, colorama.Fore.RED)
                    failjob(fatal=True)
                    deauthorise()
                    continue

                try:
                    exportLocation.mkdir(parents=False, exist_ok=True) # Create the job export folder
                except Exception as e:
                    verbose('Unable to create export folder %s' % str(exportLocation), True, colorama.Fore.RED)
                    verbose('Export failed', True, colorama.Fore.RED)
                    failjob()
                    deauthorise()
                    continue # Next job
                else:
                    # Check for all transcode job completion
                    verbose('Checking that all transcode jobs are complete...', False, colorama.Fore.YELLOW)

                    restartedTranscodeJobs = False # If some were restarted
                    stillInProgress = False # If some are still in progress
                    segments = [] # List of all the segments
                    toRestart = [] # List of all that need to be restarted
                    unfinished = [] # List of unfinished segments
                    jobFailed = False #

                    execute('SELECT transcodeJobID, status, segmentPart, failures FROM transcodeJob WHERE fk_jobUUID = %s ORDER BY segmentPart ASC', job_uuid)
                    while True:
                        row = cursor.fetchone()
                        if row == None:
                            break;
                        segments.append(row['segmentPart'])
                        # If the transcode job is in error, restart it, or fail the job if the failure tolerance is reached
                        if row['status'] == 13:
                            if row['failures'] < int(policies['failureTolerance']):
                                toRestart.append( row['segmentPart'] )
                                restartedTranscodeJobs = True
                                verbose('Segment %d failed. Marking for re-transcode', True, colorama.Fore.YELLOW)
                                verbose('Checking that all transcode jobs were successful...', False, colorama.Fore.YELLOW)
                            else:
                                jobFailed = True
                                verbose('Segment %d exceeded the maximum failure tolerance.' % row['segmentPart'], True, colorama.Fore.RED)
                                verbose('Checking that all transcode jobs were successful...', False, colorama.Fore.YELLOW)
                                break # Fatal job error
                        if row['status'] < 2:
                            stillInProgress = True # Don't continue the export, still in progress
                            verbose('Segment %d is not finished.' % row['segmentPart'], True, colorama.Fore.YELLOW)
                            verbose('Checking that all transcode jobs were successful...', False, colorama.Fore.YELLOW)
                            unfinished.append(row['segmentPart'])
                    if jobFailed:
                        # This shouldn't happen, it's old code, but here for redundancy
                        verbose('One or more transcode segments exceeded the maximum failure tolerance. Marking the job as a failure (Status 13). This is a fatal job error.', True, colorama.Fore.RED)
                        execute('UPDATE job SET status = %s, failed = 1 WHERE jobUUID = %s', jobStatus.error, job_uuid)
                        execute('UPDATE exportJob SET status = %s, fk_nodeUUID = NULL, failures = failures + 1 WHERE fk_jobUUID = %s', smallJobStatus.error, job_uuid)
                        connection.commit()
                        deauthorise()
                        continue # Next job

                    successColour = colorama.Fore.GREEN
                    if (len(toRestart) + len(unfinished)) > 0:
                        successColour = colorama.Fore.YELLOW
                    verbose('%d out of %d segments are reported as successfully transcoded' % (len(segments) - len(toRestart) - len(unfinished), len(segments)), True, successColour)

                    # If all the jobs are finished, the check the presence of all segments
                    verbose('Verifying the presence of all necessary transcoded video segments...', False, colorama.Fore.YELLOW)
                    if not restartedTranscodeJobs and not stillInProgress:
                        validResolution = [] # Not all resolutions will be present in the export, to avoid upscaling. Need to figure out which ones apply based on the source resolution
                        # Determine which resolutions apply to avoid upscaling
                        for resolution in outputs:
                            if (media_info['streams'][0]['width'] >= resolution['maxX'] or media_info['streams'][0]['width'] >= resolution['maxX']):
                                validResolution.append(resolution) # We're interested in the height, used for naming
                        if len(validResolution) == 0:
                            # If the video is too small, it was renamed to the smallest resolutions
                            validResolution.append(get_smallest_output())

                        # For each video segment
                        for segment in segments:
                            allSegmentsPresent = True
                            # For each resolution of the current segment
                            for res in validResolution:
                                if not (transcodeLocation / ("%d_%d.ts" % (segment, res['maxY']))).is_file():
                                    allSegmentsPresent = False # File is missing
                                    verbose('Segment %s is missing ' % '%d_%d.ts' % (segment, res['maxY']), True, colorama.Fore.YELLOW)
                                    verbose('Verifiying the presence of all necessary transcoded video segments...', False, colorama.Fore.YELLOW)
                            if not allSegmentsPresent:
                                restartedTranscodeJobs = True # Restart the segment transcode that is missing
                                if not segment in toRestart:
                                    toRestart.append(segment)

                    if restartedTranscodeJobs or stillInProgress:
                        if restartedTranscodeJobs:
                            verbose('Parts are missing, or the transcoded segments do not conform with the latest global and video output policies.', True, colorama.Fore.YELLOW)
                        else:
                            verbose('There are still transcode jobs running.', True, colorama.Fore.YELLOW)
                        # Restart any jobs.
                        if not failjob():
                            # Job failure isn't fatal yet, so restart the transcode jobs
                            toRestartTuples = []
                            for n in toRestart:
                                toRestartTuples.append( (smallJobStatus.ready, n, job_uuid) )
                            connection.autocommit(True)  # Transactions not required.... Don't want deadlocks.
                            if len(toRestartTuples) > 0:
                                execute("UPDATE transcodeJob SET status = %s, failures = failures + 1, fk_nodeUUID = NULL WHERE segmentPart=%s AND fk_jobUUID=%s", toRestartTuples, executemany=True)
                            execute("UPDATE job SET status = %s WHERE jobUUID = %s", jobStatus.transcoding, job_uuid) # Back into the transcode stage
                            execute("UPDATE exportJob SET failures = failures + 1, status = %s WHERE fk_jobUUID = %s", smallJobStatus.ready, job_uuid) # Remove the exportJob
                            connection.autocommit(False)

                            verbose('The export was halted, the appropriate segments have been resubmitted for transcoding.', True, colorama.Fore.CYAN)
                        deauthorise()
                        continue # Next job

                    # Start the export
                    # Create the concat list for ffmpeg for each resolution, and join the segments.
                    verbose('All parts are conform to global policies and resolution outputs. Starting transcode', True, colorama.Fore.GREEN)
                    exportLog = exportLocation / 'export.log'
                    for res in validResolution:
                        stream_framerate_fraction = media_info['streams'][0]['r_frame_rate'].split('/') # TODO get the correct framerate, accounting for reduction
                        stream_framerate = int(round(int(stream_framerate_fraction[0]) / int(stream_framerate_fraction[1])))

                        verbose('Exporting resolution {resolution}p{framerate}'.format(resolution=res['maxY'],framerate=min(stream_framerate, res['maxFramerate'])), False, colorama.Fore.YELLOW)
                        file_list = ""
                        first_print = True
                        for segment in segments:
                            if not first_print:
                                file_list += '|'
                            first_print = False

                            v = transcodeLocation / ('%d_%d.ts' % (segment, res['maxY']))
                            v = v.resolve()  # Get the absolute path
                            file_list += str(v)



                        with open(exportLog, 'w') as err:
                            subprocess.call('ffmpeg -loglevel error -y -nostdin -i "concat:{file_list}" -i "{source}" -c:v copy -c:a aac -b:a {audio}k -map 0:v:0 -map 1:a:0 "{src_name}{res}p{framerate}.mp4"'.format(file_list=file_list, source=str(sourceLocation / job_data['sourceName']), audio=res['audioBitrate'], src_name=(exportLocation / pathlib.Path(job_data['sourceName']).stem), res=res['maxY'], framerate=stream_framerate), stderr=err, shell=True) # Remove the extentio
                        verbose('Successful export of resolution %dp' % res['maxY'], True, colorama.Fore.GREEN)
                        if exportLog.stat().st_size > 0:
                            with open(exportLog, 'r') as err:
                                verbose('Export may have encountered an error: %s' % err.read(), True, colorama.Fore.YELLOW)
                    silentRemove(exportLog)  # Doesn't mean anything, because it's overwritten for each resolution

                    connection.autocommit(True)
                    execute("UPDATE job SET status = %s, completed = 1, dateCompleted = CURRENT_TIMESTAMP, mediaInfo = NULL WHERE jobUUID = %s", jobStatus.completed, job_uuid) # Mark the job as complete
                    execute('DELETE FROM ingestJob WHERE fk_jobUUID = %s', job_uuid) # Remove the listings
                    execute('DELETE FROM transcodeJob WHERE fk_jobUUID = %s', job_uuid)
                    execute('DELETE FROM exportJob WHERE fk_jobUUID = %s', job_uuid)
                    connection.autocommit(False)

                    verbose('Export successful. The video is ready for website ingest', True, colorama.Fore.CYAN)

                    # Clean-up the work files
                    shutil.rmtree(work_paths['ingest'] / job_uuid_hex, ignore_errors=True)
                    shutil.rmtree(work_paths['transcode'] / job_uuid_hex, ignore_errors=True)

                    silentRemove(os.path.join(work_paths['source'], job_data['sourceName']))

                    if move_after_export:
                        move_path = pathlib.Path(move_after_export_dir)
                        if move_path.is_dir():
                            for res in validResolution:
                                video_file_name ='{source}{res}p{framerate}.mp4'.format(source=pathlib.Path(job_data['sourceName']).stem , res=res['maxY'], framerate=stream_framerate)
                                video_file = exportLocation / video_file_name
                                if video_file.is_file():
                                    shutil.copy(str(video_file), str(move_path)) # copy will overwrite
                            verbose('Exported files have been moved to {}'.format(move_path), True, colorama.Fore.GREEN)
                            shutil.rmtree(exportLocation, ignore_errors=True)
                        else:
                            verbose('Unable to move exported files, the copy destination doesn\'t exist: {}'.format(str(move_path)), True, colorama.Fore.RED)

                    deauthorise()
                    continue
        else if (node_type == 'build'):
            verbose('Build complete. Terminating application.')
            os._exit(0)

    if authorised:
        deauthorise()
    increasesleep_time()
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        break  # Exit the program on keyboard interruption
