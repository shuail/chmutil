#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_chmrunner
----------------------------------

Tests for `chmrunner.py`
"""

import unittest
import os
import tempfile
import shutil
import configparser
import stat

from chmutil import chmrunner
from chmutil.core import LoadConfigError
from chmutil.core import CHMJobCreator


class TestCHMRunner(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parse_arguments(self):
        pargs = chmrunner._parse_arguments('hi', ['taskid', 'jobdir'])
        self.assertEqual(pargs.taskid, 'taskid')
        self.assertEqual(pargs.jobdir, 'jobdir')

    def test_run_chm_job_no_config(self):
        temp_dir = tempfile.mkdtemp()
        try:
            pargs = chmrunner._parse_arguments('hi', ['taskid', temp_dir])
            chmrunner._run_chm_job(pargs)
            self.fail('Expected LoadConfigError')
        except LoadConfigError as e:
            self.assertEqual(str(e),
                             os.path.join(temp_dir,
                                          CHMJobCreator.CONFIG_FILE_NAME) +
                             ' configuration file does not exist')
        finally:
            shutil.rmtree(temp_dir)

    def test_run_single_chm_job_success(self):
        temp_dir = tempfile.mkdtemp()
        try:
            scratch = os.path.join(temp_dir,'tmp')
            os.makedirs(scratch, mode=0o755)

            chmrundir = os.path.join(temp_dir,
                                     CHMJobCreator.RUN_DIR)
            os.makedirs(chmrundir, mode=0o755)
            con = configparser.ConfigParser()
            con.set('', CHMJobCreator.CONFIG_DISABLE_HISTEQ_IMAGES,
                    'False')
            con.set('', CHMJobCreator.CONFIG_MODEL, '/model')
            con.set('', CHMJobCreator.CONFIG_IMAGES, temp_dir)
            con.set('', CHMJobCreator.CONFIG_TILE_SIZE, '3x3')
            con.set('', CHMJobCreator.CONFIG_OVERLAP_SIZE, '2x2')

            con.add_section('1')
            con.set('1', CHMJobCreator.CONFIG_INPUT_IMAGE, 'input.1.png')
            con.set('1', CHMJobCreator.CONFIG_OUTPUT_IMAGE, 'output.1.png')

            con.set('1', CHMJobCreator.CONFIG_ARGS, '-t 1,1 -t 1,2')


            fakecmd = os.path.join(temp_dir, 'fake.py')
            f = open(fakecmd, 'w')
            f.write('#!/usr/bin/env python\n\n')
            f.write('import sys\n')
            f.write('import os\n')
            f.write('sys.stdout.write("stdout")\n')
            f.write('sys.stderr.write("stderr")\n')
            f.write('img = os.path.basename(sys.argv[2])\n')
            f.write('oimg = os.path.join(sys.argv[3], img)\n')
            f.write('open(oimg, "w").close()\n')
            f.write('f = open(os.path.join(sys.argv[3], "out.txt"), "w")\n')
            f.write('f.write(" ".join(sys.argv))\n')
            f.write('f.flush()\n')
            f.write('f.close()\n')
            f.write('sys.exit(0)\n')
            f.flush()
            f.close()
            os.chmod(fakecmd, stat.S_IRWXU)
            con.set('', CHMJobCreator.CONFIG_CHM_BIN,
                    fakecmd)
            ecode = chmrunner._run_single_chm_job(temp_dir,
                                                  scratch, '1', con)
            # import time
            # time.sleep(600)
            o_image = os.path.join(chmrundir, 'output.1.png')
            self.assertTrue(os.path.isfile(o_image))
            self.assertEqual(ecode, 0)
        finally:
            shutil.rmtree(temp_dir)




if __name__ == '__main__':
    unittest.main()
