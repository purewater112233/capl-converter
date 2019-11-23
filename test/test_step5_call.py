import logging
import os
import socket
import subprocess
import time
from argparse import ArgumentParser
# from common.constants import LOG_FOLDER, PYTHON, CANOE_IMPORT_FOLDER, RUNNING_NAME, POST_PROCESS_IMPORT_FOLDER
from logging.handlers import RotatingFileHandler

ASC2ADTF = r"Tools\Asc2Adtf\Asc2Adtf"
ADTF_EXPORTER = r"Tools\AdtfExporter_1.1.1\AdtfExporter"

FAILED_PRE_PROCESS_JOBS = "FailedPreProcessJobs"

CANOE_IMPORT_FOLDER = "CANoeJobs"
FAILED_CANOE_JOBS = "FailedCANoeJobs"

LOG_FOLDER = r'LOG_FOLDER'
TEMP_FOLDER = r'TEMP_FOLDER'

POST_PROCESS_IMPORT_FOLDER = "PostProcessJobs"
FAILED_POST_PROCESS_JOBS = "FailedPostProcessJobs"

RUNNING_NAME = "ProducerIsRunning"
CANOE_JOB_FILE_NAME = "CANoeJob"

COM_MATRIX_ID = "SPA2910"
PRE_TAG_TEMP_ASC_FILE = "_tmpConv_"
RESULT_LIST_FILE = "ConvertedFiles.txt"

PYTHON = r"C:\Users\Frank.zhang\AppData\Local\Programs\Python\Python35-32\python.exe"

#from common.logger import init_logging

logger = logging.getLogger(__name__)

VERSION = "0.11"
SUCCESS = 0
FAIL = 1


if __name__ == '__main__':
    parser = ArgumentParser(description='CAPL Converter')
    parser.add_argument('-V', '--version', action='version', version='%%(prog)s (version %s)' % VERSION)
    parser.add_argument('-l', '--log-path', default=None, type=str, help='Path to store log files')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--flc2-resim-2910', dest='FLC2', action='store_true', help='FLC2 Resim with 2910 conversion')
    group.add_argument('--dai-to-flc2', dest='DAI', action='store_true', help='DAI to FLC2 conversion')
    #
    group .add_argument('--SVS-to-MVS',dest='GEEA2', action='store_true',help='svs to mvs conversion')

    parser.add_argument('batchJobId', type=str, help='Job ID')
    parser.add_argument('fileList', type=str, help='Filelist to convert')
    parser.add_argument('resultFolder', type=str, help='Result folder')
    args = parser.parse_args()

    # Inputs
    batchJobId = args.batchJobId
    fileList = args.fileList

    resultFolder = args.resultFolder

    # Initialize rotating log files
    logpath = args.log_path if args.log_path else "{}\{}".format(resultFolder, LOG_FOLDER)
    filename = "{host}.{name}.log".format(host=socket.gethostname(),
                                          name=os.path.splitext(os.path.basename(__file__))[0])
    filepath = os.path.abspath(os.path.join(logpath, filename))
   # init_logging(log_file=filepath, max_file_size_mb=5, max_backup_count=10)

    logger.info("Version {}".format(VERSION))

    #step 2

    if args.FLC2:
        conversion_spec_argument = '--flc2-resim-2910'
    elif args.DAI:
        conversion_spec_argument = '--dai-to-flc2'
    elif args.GEEA2:
        conversion_spec_argument ='--SVS-to-MVS'
    else:
        raise ValueError('No conversion specification selected!')


    cmdList = [PYTHON, r"C:\git\capl-converter\prepareForConversionTools.py", batchJobId, fileList, resultFolder]
    ret = subprocess.call(cmdList)
    if ret != 0:
        logger.error("Error code {}: Program aborted in prepareForConversionTools!".format(ret))
        exit(FAIL)
    else:
        print('step2 ok')

    # step3   build folder and some log file
    # Start pre-conversion script
    #
    canoeFolder = "{}\{}".format(resultFolder, CANOE_IMPORT_FOLDER)
    runningName = "{}\{}".format(canoeFolder, RUNNING_NAME)
    runningFP = open(runningName, "w")
    if runningFP is None:
        logger.error("Error: Failed to create file! Program aborted!")
        exit(FAIL)

    runningFP.close()

    logger.info("Start preProcessConversion.py")
    cmdList = [PYTHON, r"c:\git\capl-converter\preProcessConversion.py", batchJobId, fileList, resultFolder, conversion_spec_argument]
    p_preProcessConversion = subprocess.Popen(cmdList, stdout=None, stderr=None)
    if p_preProcessConversion is None:
        logger.error("Error: Failed to start preProcessConversion.py")

    time.sleep(1)

#step 4
    #Start CAPL-conversion script
    postProcessFolder = "{}\{}".format(resultFolder, POST_PROCESS_IMPORT_FOLDER)
    runningName = "{}\{}".format(postProcessFolder, RUNNING_NAME)
    runningFP = open(runningName, "w")
    if runningFP is None:
        logger.error("Error: Failed to create file! Program aborted!")
        exit(FAIL)

    runningFP.close()

    logger.info("Start runCAPLconverter.py")
    cmdList = [PYTHON, r"C:\git\capl-converter\RunCAPLconverter.py", batchJobId, resultFolder, conversion_spec_argument]
    p_runCAPLconverter = subprocess.Popen(cmdList, stdout=None, stderr=None)
    if p_runCAPLconverter is None:
        logger.error("Error: Failed to start runCAPLconverter.py")

    time.sleep(1)

    # step 5
    # Start post-conversion script
    #
    logger.info("Start postProcessConversion.py")
    cmdList = [PYTHON, r"C:\git\capl-converter\postProcessConversion.py", batchJobId, resultFolder, conversion_spec_argument]
    p_postProcessConversion = subprocess.Popen(cmdList, stdout=None, stderr=None)
    if p_postProcessConversion is None:
        logger.error("Error: Failed to start postProcessConversion.py")
    time.sleep(1)

    conversionRunning = True
    preProcessRunning = True
    CAPLconverterRunning = True
    CAPLconverterRunAttempt = 1
    postProcessRunning = True

    while conversionRunning:
        if p_preProcessConversion is not None and preProcessRunning:
            p_preProcessConversion.poll()
            if p_preProcessConversion.returncode is not None:
                #
                # Pre-processing is no longer ongoing
                #
                preProcessRunning = False
                os.remove("{}\{}".format(canoeFolder, RUNNING_NAME))

                if p_preProcessConversion.returncode != 0:
                    logger.error(
                        "Error: preProcessConversion.py exited with code {}".format(p_preProcessConversion.returncode))
                else:
                    logger.info("preProcessConversion.py exited successfully!")

        if p_runCAPLconverter is not None and CAPLconverterRunning:
            p_runCAPLconverter.poll()
            if p_runCAPLconverter.returncode is not None:
                #
                # CANoe converter is no longer ongoing
                #
                CAPLconverterRunning = False

                if p_runCAPLconverter.returncode != 0:
                    logger.error("Error: runCAPLconverter.py exited with code {}".format(p_runCAPLconverter.returncode))

                    if CAPLconverterRunAttempt < 6:
                        time.sleep(10)
                        CAPLconverterRunAttempt = CAPLconverterRunAttempt + 1

                        logger.info("Start runCAPLconverter.py attempt {}".format(CAPLconverterRunAttempt))
                        cmdList = [PYTHON, "c:\\git\\capl-converter\\RunCAPLconverter.py", batchJobId, resultFolder]
                        p_runCAPLconverter = subprocess.Popen(cmdList, stdout=None, stderr=None)
                        if p_runCAPLconverter is None:
                            logger.error("Error: Failed to start runCAPLconverter.py")
                            os.remove("{}\{}".format(postProcessFolder, RUNNING_NAME))
                        else:
                            CAPLconverterRunning = True
                    else:
                        os.remove("{}\{}".format(postProcessFolder, RUNNING_NAME))
                else:
                    logger.info("runCAPLconverter.py exited successfully!")
                    os.remove("{}\{}".format(postProcessFolder, RUNNING_NAME))

        if p_postProcessConversion is not None and postProcessRunning:
            p_postProcessConversion.poll()
            if p_postProcessConversion.returncode is not None:
                #
                # Post-process is no longer ongoing
                #
                postProcessRunning = False
                if p_postProcessConversion.returncode != 0:
                    logger.error("Error: postProcessConversion.py exited with code {}".format(
                        p_postProcessConversion.returncode))
                else:
                    logger.info("postProcessConversion.py exited successfully!")

        conversionRunning = preProcessRunning or CAPLconverterRunning or postProcessRunning
        time.sleep(1)

    logger.info("Conversion ended!")
    exit(SUCCESS)





    def init_logging(log_file: str, max_filre_size_mb: int, max_backup_count: int, log_level=logging.DEBUG):
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        # logging_format_extended = logging.Formatter("[%(asctime)s][%(levelname)-8s][%(name)-16s] - %(message)s (%(filename)s:%(lineno)s)")
        logging_format_simple = logging.Formatter("[%(asctime)s][%(levelname)-8s] - %(message)s")

        # File handler
        file_handler = RotatingFileHandler(filename=log_file, maxBytes=max_file_size_mb * MB,
                                           backupCount=max_backup_count)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging_format_simple)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging_format_simple)

        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        logger.info("Setting up logging to file: {0}".format(log_file))