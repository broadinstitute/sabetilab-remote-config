#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import subprocess as sub
import re
import xml.etree.ElementTree as ET
import time
import dxpy
import argparse

# Uploads an Illumina run directory (HiSeq 2500, HiSeq X, NextSeq)
# If for use with a MiSeq, users MUST change the config files to include and NOT specify the -l argument
#
# WHAT THIS SCRIPT DOES
#
# PERIODICALLY RUNS A SYNCRONIZATION SCRIPT (dx_sync_directory.py)
# incremental_upload.sh is a wrapper script around a Python utility called dx_sync_directory.py.
# This dx_sync_directory.py script will "synchronize" a specified directory to a user-specifed
# project on the DNAnexus platform.
#
# By "synchronize" we mean that each invocation of dx_sync_directory.py will create a TAR
# archive of all files in the run directory modified since the last invocation.

def parse_args():
    """Parse the command-line arguments and canonicalize file path arguments"""

    parser = argparse.ArgumentParser(description="Script to incrementally " +
            "upload an Illumina run directory (HiSeq 2500, HiSeq X, NextSeq, " +
            "MiSeq). This script can be run at any point in the instrument " +
            "run. For more information, please see the README.md file.")

    # Required inputs
    parser.add_argument("-a", "--api-token", metavar="<token>", required=True,
            help="API token to authenticate against DNAnexus platform.")
    parser.add_argument("-p", "--project", metavar="<project id>",
            required=True, help="Project ID of project to upload run " +
            "directory to")
    parser.add_argument("-r", "--run-dir", metavar="<path>", required=True,
            help="Local path to run directory.")
    parser.add_argument("-t", "--temp-dir", metavar="<path>", required=True,
            help="Local path to directory where temporary TAR archives will " +
            "be created and stored")
    parser.add_argument("-L", "--log-dir", metavar="<path>", required=True,
            help="Local path to directory where incremental upload logs " +
            "will be stored.")

    # Optional inputs
    parser.add_argument("-l", "--num-lanes", metavar="<2 or 8>", type=int,
            choices=[2, 8], help="Upload BCL files sorted by lane. Use this " +
            "option if you plan to run BCL conversion parallelized by lane. " +
            "Not applicable to single lane machines.")
    parser.add_argument("-m", "--min-age", metavar="<seconds>", type=int,
            default=1000, help="Minimum age (in seconds) of files to be " +
            "tarred and uploaded.")
    parser.add_argument("-z", "--min-size", metavar="<MB>", type=int,
            default=100, help="Minimum size (in megabytes) of TAR before it " +
            "will be uploaded.")
    parser.add_argument("-M", "--max-size", metavar="<MB>", type=int,
            default=10000, help="Maximum size (in megabytes) of TAR to be" +
            "uploaded")
    parser.add_argument("-i", "--sync-interval", metavar="<seconds>", type=int,
            default=1800, help="Interval at which the run directory will be " +
            "scanned, and new files will be tarred and uploaded")
    parser.add_argument("-u", "--upload-thumbnails", action="store_true",
            help="Flag to specify uploaded thumbnail (JPEG) files as well " +
            "as BCL files")
    parser.add_argument("-R", "--retries", metavar="<int>", type=int, default=3,
            help="Number of times the script will attempt to tar and upload " +
            "a set of files before failing.")
    parser.add_argument("-s", "--script", metavar="<filepath>",
            help="Path to a executable script that should be run (locally) after " +
            "success upload. A single command line argument (corresponding to the " +
            "path of the RUN directory will be passed to the executable. Note: " +
            "script will be run after the applet has been executed.")


    # Mutually exclusive inputs for verbose loggin (UA) vs dxpy upload
    upload_debug_group = parser.add_mutually_exclusive_group(required=False)
    upload_debug_group.add_argument("--dxpy-upload", "-d", action="store_true",
            help="This flag allows you to specify to use dxpy instead of " +
            "upload agent")
    upload_debug_group.add_argument("--verbose", "-v", action="store_true",
        help="This flag allows you to specify upload agent --verbose mode.")

    # Mutually exclusive inputs for triggering applet / workflow after upload
    downstream_analysis_group = parser.add_mutually_exclusive_group(required=False)
    downstream_analysis_group.add_argument("-A", "--applet", metavar="<applet-id>",
            help="DNAnexus applet id to execute after the RUN folder has been " +
            "successfully uploaded (e.g. for demultiplexing). A single input, " +
            "-i upload_sentinel_record will be passed to the applet, with the " +
            "appropriate sentinel record id for the uploaded run folder. " +
            "Mutually exclusive with --workflow.")
    downstream_analysis_group.add_argument("-w", "--workflow", metavar="<workflow-id>",
            help="DNAnexus workflow id to execute after the RUN fodler has been " +
            "sucessfully uploaded (e.g. for demux/variation calling). A single " +
            "input, -iupload_sentinel_record will be passed to the first stage of " +
            "the workflow (stage 0), with the appropriate sentinel record id for " +
            "uploaded run folder. Mutually exclusive with --applet.")
    # Parse args
    args = parser.parse_args()

    # Canonicalize paths
    args.run_dir = os.path.abspath(args.run_dir)
    args.temp_dir = os.path.abspath(args.temp_dir)
    args.log_dir = os.path.abspath(args.log_dir)

    # Ensure min < max
    if args.min_size > args.max_size:
        raise_error("--min-size input must be less than --max-size")

    return args

def check_input(args):
    dxpy.set_security_context({
                "auth_token_type": "Bearer",
                "auth_token": args.api_token})

    # Check API token and project context
    try:
        dxpy.get_handler(args.project).describe()
    except dxpy.exceptions.DXAPIError as e:
        if e.name == "InvalidAuthentication":
            raise_error("API token (%s) is not valid. %s"
                    % (args.api_token, e))
        if e.name == "PermissionDenied":
            raise_error("Project (%s) is not valid. %s"
                    % (args.project, e))
    except dxpy.exceptions.DXError as e:
        raise_error("Error getting project handler for project (%s). %s" %
                (args.project, e))

    # Check that chained downstream applet is valid
    if args.applet:
        try:
            dxpy.get_handler(args.applet).describe()
        except dxpy.exceptions.DXAPIError as e:
            raise_error("Unable to resolve applet %s. %s" %(args.applet, e))
        except dxpy.exceptions.DXError as e:
            raise_error("Error getting handler for applet (%s). %s" %(args.applet, e))

    # Check that chained downstream workflow is valid
    if args.workflow:
        try:
            dxpy.get_handler(args.workflow).describe()
        except dxpy.exceptions.DXAPIError as e:
            raise_error("Unable to resolve workflow %s. %s" %(args.workflow, e))
        except dxpy.exceptions.DXError as e:
            raise_error("Error getting handler for workflow (%s). %s" %(args.workflow, e))

    # Check that executable to launch locally is executable
    if args.script:
        if not (os.path.isfile(args.script) and os.access(args.script, os.X_OK)):
            raise_error("Executable/script passed by -s: (%s) is not executable" %(args.script))

    if not args.dxpy_upload:
        print_stderr("Checking if ua is in $PATH")
        try:
            sub.check_call(['ua', '--version'],
                    stdout=open(os.devnull, 'w'), close_fds=True)
        except sub.CalledProcessError:
            raise_error("Upload agent executable 'ua' was not found in the $PATH")

    try:
        # We assume that dx_sync_directory is located in the same folder as this script
        # This is resolved by absolute path of invocation
        sub.check_call(['python', '{curr_dir}/dx_sync_directory.py'.format(curr_dir=sys.path[0]), '-h'],
                stdout=open(os.devnull, 'w'), close_fds=True)
    except sub.CalledProcessError:
        raise_error("dx_sync_directory.py not found. Please run incremental " +
                "upload from the directory containing incremental_upload.py "+
                "and dx_sync_directory.py")

def get_run_id(run_dir):
    runinfo_xml = run_dir + "/RunInfo.xml"
    if os.path.isfile(runinfo_xml) == False:
        raise_error("File RunInfo.xml not found in %s" % (run_dir))
    try:
        tree = ET.parse(runinfo_xml)
        root = tree.getroot()
        for child in root:
            run_id= child.attrib['Id']
        print_stderr("Detected run %s" % (run_id))
        return run_id
    except:
        raise_error("Could not extract run id from RunInfo.xml")

def get_target_folder(base, lane):
    if lane == "all":
        return base
    else:
        return base.rstrip("/") + "/" + lane

def run_command_with_retry(my_num_retries, my_command):
    for trys in range(my_num_retries):
        print_stderr("Running (Try %d of %d): %s" %
                (trys, my_num_retries, my_command))
        try:
            output = (sub.check_output(my_command)).strip()
            return output
        except sub.CalledProcessError as e:
            print_stderr("Failed to run `%s`, retrying (Try %s)" %
                    (" ".join(my_command), trys))
        time.sleep(10)

    raise_error("Number of retries exceed %d. Please check logs to troubleshoot issues." % my_num_retries)

def raise_error(msg):
    print_stderr("ERROR: %s" % msg)
    sys.exit()

def print_stderr(msg):
    print ("[incremental_upload.py] %s" % msg, file=sys.stderr)

def upload_single_file(filepath, project, folder, properties):
    """ Upload a single file onto DNAnexus, into the project and folder specified,
    and apply the given properties. Returns None if given filepath is invalid or
    an error was thrown during upload"""
    if not os.path.exists(filepath):
        print_stderr("Invalid filepath given to upload_single_file %s" %filepath)
        return None

    try:
        f = dxpy.upload_local_file(filepath,
                           project=project,
                           folder=folder,
                           properties=properties)

        return f.id

    except dxpy. DXError as e:
        print_stderr("Failed to upload local file %s to %s:%s" %(filepath, project, folder))
        return None

def run_sync_dir(lane, args, finish=False):
    # Set list of config files to include (only if lanes are specified)
    CONFIG_FILES = ["RTAConfiguration.xml", "RunInfo.xml", "RunParameters.xml",
        "config.xml", "s.locs"]
    lane_num = lane["lane"]

    # Set lane specific patterns to include IF uploading by lane
    include_patterns = []
    if not lane_num == "all":
        include_patterns = CONFIG_FILES
        include_patterns.append("s_" + lane_num + "_")
    # If upload_thumbnails is specified, upload thumbnails
    exclude_patterns = []
    if not args.upload_thumbnails:
        exclude_patterns.append("Images")

    invocation = ["python", "{curr_dir}/dx_sync_directory.py".format(curr_dir=sys.path[0])]
    invocation.extend(["--log-file", lane["log_path"]])
    invocation.extend(["--tar-destination", args.project + ":" + lane["remote_folder"]])
    invocation.extend(["--tar-directory", args.temp_dir])
    invocation.extend(["--include-patterns"])
    invocation.extend(include_patterns)
    invocation.extend(["--exclude-patterns"])
    invocation.extend(exclude_patterns)
    invocation.extend(["--min-tar-size", str(args.min_size)])
    invocation.extend(["--max-tar-size", str(args.max_size)])
    invocation.extend(["--prefix", lane["prefix"]])
    if args.verbose:
        invocation.append("--verbose")
    if args.dxpy_upload:
        invocation.append("--dxpy-upload")
    if finish:
        invocation.append("--finish")
    else:
        invocation.extend(["--min-age", str(args.min_age)])
    invocation.append(args.run_dir)

    output = run_command_with_retry(args.retries, invocation)
    return output.split()

def main():

    args = parse_args()
    check_input(args)
    run_id = get_run_id(args.run_dir)

    # Set all naming conventions
    REMOTE_RUN_FOLDER = "/" + run_id + "/runs"
    REMOTE_READS_FOLDER = "/" + run_id + "/reads"
    REMOTE_ANALYSIS_FOLDER = "/" + run_id + "/analyses"

    FILE_PREFIX = "run." + run_id+ ".lane."

    # Prep log & record names
    lane_info = []

    # If no lanes are specified, set lane to all, otherwise, set to array of lanes
    if not args.num_lanes:
        lanes_to_upload = ["all"]
    else:
        lanes_to_upload = [str(i) for i in range(1, args.num_lanes+1)]

    for lane in lanes_to_upload:
        lane_prefix = FILE_PREFIX + lane

        lane_info.append({
                "lane": lane,
                "prefix": lane_prefix,
                "log_path": os.path.join(args.log_dir, lane_prefix + ".log"),
                "record_name": lane_prefix + ".upload_sentinel",
                "remote_folder": get_target_folder(REMOTE_RUN_FOLDER, lane),
                "uploaded": False
                })

    # Create upload sentinel for upload, if record already exists, use that
    done_count = 0
    for lane in lane_info:
        lane_num = lane["lane"]
        try:
            old_record = dxpy.find_one_data_object(zero_ok=True,
                    typename="UploadSentinel", name=lane["record_name"],
                    project=args.project, folder=lane["remote_folder"])
        except dxpy.exceptions.DXSearchError as e:
            raise_error("Encountered an error looking for %s at %s:%s. %s"
                    % (lane["record_name"], lane["remote_folder"],
                        args.project, e))

        if old_record:
            lane["dxrecord"] = dxpy.get_handler(
                    old_record["id"],
                    project=old_record["project"]
                    )
            if lane["dxrecord"].describe()["state"] == "closed":
                print_stderr("Run %s, lane %s has already been uploaded" %
                        (run_id, lane_num))
                lane["uploaded"] = True
                done_count += 1
        else:
            properties = {"run_id": run_id, "lanes": lane_num}
            lane["dxrecord"] = dxpy.new_dxrecord(
                    types=["UploadSentinel"], project=args.project,
                    folder=lane["remote_folder"], parents=True,
                    name=lane["record_name"], properties=properties)

    if done_count == len(lane_info):
        print_stderr("EXITING: All lanes already uploaded")
        sys.exit(1)

    # While loop waiting for RTAComplete.txt or RTAComplete.xml
    while (not os.path.isfile(os.path.join(args.run_dir, "RTAComplete.txt"))
        and not os.path.isfile(os.path.join(args.run_dir, "RTAComplete.xml"))):
        start_time=time.time()

        # Loop through all lanes in run directory
        for lane in lane_info:
            lane_num = lane["lane"]
            if lane["uploaded"]:
               continue
            run_sync_dir(lane, args)

        # Wait at least the minimum time interval before running the loop again
        cur_time = time.time()
        diff = cur_time - start_time
        if diff < args.sync_interval:
            print_stderr("Sleeping for %d seconds" % (int(args.sync_interval - diff)))
            time.sleep(int(args.sync_interval - diff))

    # Final synchronization, upload data, set details
    for lane in lane_info:
        if lane["uploaded"]:
            continue
        file_ids = run_sync_dir(lane, args, finish=True)
        record = lane["dxrecord"]
        properties = record.get_properties()
        log_file_id = upload_single_file(lane["log_path"], args.project, 
                                         lane["remote_folder"], properties)
        runinfo_file_id = upload_single_file(args.run_dir + "/RunInfo.xml", args.project,
                                             lane["remote_folder"], properties)
        samplesheet_file_id = upload_single_file(args.run_dir + "/SampleSheet.csv", args.project,
                                                 lane["remote_folder"], properties)

        for file_id in file_ids:
            dxpy.get_handler(file_id, project=args.project).set_properties(properties)
        details = {
            'run_id': run_id,
            'lanes': lane["lane"],
            'upload_thumbnails': str(args.upload_thumbnails).lower(),
            'dnanexus_path': args.project + ":" + lane["remote_folder"],
            'tar_file_ids': file_ids
            }

        # ID to singly uploaded file (when uploaded successfully)
        if log_file_id:
            details.update({'log_file_id': log_file_id})
        if runinfo_file_id:
            details.update({'runinfo_file_id': runinfo_file_id})
        if samplesheet_file_id:
            details.update({'samplesheet_file_id': samplesheet_file_id})

        record.set_details(details)

        record.close()

    print_stderr("Run %s successfully streamed!" % (run_id))

    if args.applet:
        # project verified in check_input, assuming no change
        project = dxpy.get_handler(args.project)

        print_stderr("Initiating downstream analysis: given app(let) id %s" %args.applet)

        for info in lane_info:
            lane = info["lane"]
            record = info["dxrecord"]

            # applet verified in check_input, assume no change
            applet = dxpy.get_handler(args.applet)

            # Prepare output folder, if downstream analysis specified
            reads_target_folder = get_target_folder(REMOTE_READS_FOLDER, lane)
            print_stderr("Creating output folder %s" %(reads_target_folder))

            try:
                project.new_folder(reads_target_folder, parents=True)
            except dxpy.DXError as e:
                raise_error("Failed to create new folder %s. %s" %(reads_target_folder, e))

            # Decide on job name (<executable>-<run_id>)
            job_name = applet.title + "-" + run_id

            # Run specified applet
            job = applet.run({"upload_sentinel_record": dxpy.dxlink(record)},
                        folder=reads_target_folder,
                        project=args.project,
                        name=job_name)

            print_stderr("Initiated job %s from applet %s for lane %s" %(job, args.applet, lane))
    # Close if args.applet

    if args.workflow:
        # project verified in check_input, assuming no change
        project = dxpy.get_handler(args.project)

        print_stderr("Initiating downstream analysis: given workflow id %s" %args.workflow)

        for info in lane_info:
            lane = info["lane"]
            record = info["dxrecord"]

            # workflow verified in check_input, assume no change
            workflow = dxpy.get_handler(args.workflow)

            # Prepare output folder, if downstream analysis specified
            analyses_target_folder = get_target_folder(REMOTE_ANALYSIS_FOLDER, lane)
            print_stderr("Creating output folder %s" %(analyses_target_folder))

            try:
                project.new_folder(analyses_target_folder, parents=True)
            except dxpy.DXError as e:
                raise_error("Failed to create new folder %s. %s" %(analyses_target_folder, e))

            # Decide on job name (<executable>-<run_id>)
            job_name = workflow.title + "-" + run_id

            # Run specified applet
            job = workflow.run({"0.upload_sentinel_record": dxpy.dxlink(record)},
                        folder=analyses_target_folder,
                        project=args.project,
                        name=job_name)

            print_stderr("Initiated analyses %s from workflow %s for lane %s" %(job, args.applet, lane))

    # Close if args.workflow

    if args.script:
        # script has been validated to be executable earlier, assume no change
        try:
            sub.check_call([args.script, args.run_dir])
        except sub.CalledProcessError, e:
            raise_error("Executable (%s) failed with error %d: %s" %(args.script, e.returncode, e.output))


if __name__ == "__main__":
    main()
