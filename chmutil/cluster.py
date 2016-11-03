# -*- coding: utf-8 -*-


import os
import stat
import logging
import shutil
import configparser

from chmutil.core import CHMJobCreator

logger = logging.getLogger(__name__)


class BatchedJobsListGenerator(object):
    """Creates Batched Jobs List file used by chmrunner.py
    """

    OLD_SUFFIX = '.old'
    def __init__(self, chmconfig):
        """Constructor
        """
        self._chmconfig = chmconfig


    def _get_incomplete_jobs_list(self):
        """Gets list of incomplete jobs
        """
        config = self._chmconfig.get_config()
        job_list = []

        for s in config.sections():
            out_file = config.get(s, CHMJobCreator.CONFIG_OUTPUT_IMAGE)
            if not os.path.isfile(out_file):
                job_list.append(s)

        logger.info('Found ' + str(len(job_list)) + ' of ' +
                    str(len(config.sections())) + ' to be incomplete jobs')
        return job_list

    def _write_batched_job_config(self, bconfig):
        """Writes out batched job config
        """
        cfile = self._chmconfig.get_batchedjob_config()
        if os.path.isfile(cfile):
            logger.debug('Previous batched job config file found. '
                         'Appending .old suffix')
            shutil.move(cfile, cfile + BatchedJobsListGenerator.OLD_SUFFIX)

        logger.debug('Writing batched job config file to ' + cfile)
        f = open(cfile, 'w')
        bconfig.write(f)
        f.flush()
        f.close()

    def generate_batched_jobs_list(self):
        """Examines chm jobs list and looks for
        incomplete jobs. The incomplete jobs are written
        into `CHMJobCreator.CONFIG_BATCHED_JOBS_FILE_NAME` batched by number
        of jobs per node set in `CHMJobCreator.CONFIG_FILE_NAME`
        :returns: Number of jobs that need to be run
        """
        job_list = self._get_incomplete_jobs_list()
        if len(job_list) is 0:
            logger.debug('All jobs complete')
            return 0

        jobspernode = self._chmconfig.get_number_jobs_per_node()

        bconfig = configparser.ConfigParser()

        total = len(job_list)
        job_counter = 1
        for j in range(0, total, jobspernode):
            bconfig.add_section(str(job_counter))
            bconfig.set(str(job_counter), CHMJobCreator.BCONFIG_TASK_ID,
                        ','.join(job_list[j:j+jobspernode]))
            job_counter += 1

        self._write_batched_job_config(bconfig)
        return job_counter


class RocceSubmitScriptGenerator(object):
    """Generates submit script for CHM job on Rocce cluster
    """
    SUBMIT_SCRIPT_NAME = 'runjobs.rocce'

    def __init__(self, chmconfig):
        """Constructor
        :param chmconfig: CHMConfig object for the job
        """
        self._chmconfig = chmconfig

    def _get_submit_script_path(self):
        """Gets path to submit script
        """
        return os.path.join(self._chmconfig.get_out_dir(),
                     RocceSubmitScriptGenerator.SUBMIT_SCRIPT_NAME)

    def _get_job_range(self):
        """Gets number of jobs in config by examining sections
        """
        config_file = self._chmconfig.get_batchedjob_config()
        config = configparser.ConfigParser()
        config.read(config_file)
        minval = -1
        maxval = 0
        for s in config.sections():
            try:
                s_as_int = int(s)
                if s_as_int > maxval:
                    maxval = s_as_int
                if minval == -1:
                    minval = s_as_int
                    continue
                if s_as_int < minval:
                    minval = s_as_int
            except ValueError:
                pass
        return minval, maxval

    def _get_instructions(self):
        """get instructions
        """
        minval, maxval = self._get_job_range()
        return ('Run: cd ' + self._chmconfig.get_out_dir() +
                '; qsub -t ' + str(minval) + '-' + str(maxval) + ' ' +
                RocceSubmitScriptGenerator.SUBMIT_SCRIPT_NAME)

    def generate_submit_script(self):
        """Creates submit script and instructions for invocation
        :returns: tuple (path to submit script, instructions for submit)
        """
        script = self._get_submit_script_path()
        out_dir = self._chmconfig.get_out_dir()
        f = open(script, 'w')
        f.write('#!/bin/sh\n')
        f.write('#\n#$ -V\n#$ -S /bin/sh\n')
        f.write('#$ -wd ' + out_dir + '\n')
        f.write('#$ -o ' + os.path.join(self._chmconfig.get_stdout_dir(),
                                        '$JOB_ID.$TASK_ID.out') + '\n')
        f.write('#$ -j y\n#$ -N chmjob\n')
        f.write('#$ -l h_rt=12:00:00,h_vmem=5G,h=\'!compute-0-20\'\n')
        f.write('#$ -q all.q\n#$ -m n\n\n')
        f.write('echo "HOST: $HOSTNAME"\n')
        f.write('echo "DATE: `date`"\n\n')
        f.write('/usr/bin/time -p ' + self._chmconfig.get_chm_binary() +
                ' $SGE_TASK_ID ' + out_dir + ' --scratchdir ' +
                self._chmconfig.get_shared_tmp_dir() + ' --log DEBUG\n')
        f.flush()
        f.close()
        os.chmod(script, stat.S_IRWXU)
        return script, self._get_instructions()

