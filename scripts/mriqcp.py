#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: oesteban
# @Date:   2015-11-19 16:44:27
# @Last Modified by:   oesteban
# @Last Modified time: 2016-01-18 14:39:54

"""
=====
MRIQC
=====
"""
import os
import os.path as op
from multiprocessing import cpu_count

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from mriqc.workflows import qc_workflows
from mriqc.utils import gather_bids_data

from nipype import config as ncfg

__author__ = "Oscar Esteban"
__copyright__ = ("Copyright 2016, Center for Reproducible Neuroscience, "
                 "Stanford University")
__credits__ = "Oscar Esteban"
__license__ = "BSD"
__version__ = "0.0.1"
__maintainer__ = "Oscar Esteban"
__email__ = "code@oscaresteban.es"
__status__ = "Prototype"


if __name__ == '__main__':
    parser = ArgumentParser(description='MRI Quality Control',
                            formatter_class=RawTextHelpFormatter)

    g_input = parser.add_argument_group('Inputs')
    g_input.add_argument('-i', '--bids-root', action='store',
                         default=os.getcwd())
    g_input.add_argument('--nthreads', action='store', default=0,
                         type=int, help='number of repetitions')
    g_input.add_argument(
        "--write-graph", action='store_true', default=False,
        help="Write workflow graph.")
    g_input.add_argument(
        "--use-plugin", action='store', default=None,
        help='nipype plugin configuration file')

    g_input.add_argument(
        "--skip-anatomical", action='store_true', default=False,
        help="Skip anatomical QC workflow.")
    g_input.add_argument(
        "--skip-functional", action='store_true', default=False,
        help="Skip functional QC workflow.")

    g_outputs = parser.add_argument_group('Outputs')
    g_outputs.add_argument('-o', '--output-dir', action='store')
    g_outputs.add_argument('-w', '--work-dir', action='store')

    opts = parser.parse_args()

    settings = {'bids_root': op.abspath(opts.bids_root),
                'output_dir': os.getcwd(),
                'write_graph': opts.write_graph,
                'skip': [],
                'nthreads': opts.nthreads}

    if opts.skip_anatomical:
        settings['skip'].append('anat')
    if opts.skip_functional:
        settings['skip'].append('func')

    if opts.output_dir:
        settings['output_dir'] = op.abspath(opts.output_dir)

    if not op.exists(settings['output_dir']):
        os.makedirs(settings['output_dir'])

    if opts.work_dir:
        settings['work_dir'] = op.abspath(opts.work_dir)

        LOG_DIR = op.join(settings['work_dir'], 'log')
        if not op.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

        # Set nipype config
        ncfg.update_config({
            'logging': {'log_directory': LOG_DIR, 'log_to_file': True},
            'execution': {'crashdump_dir': LOG_DIR}
        })

    plugin_settings = {'plugin': 'Linear'}
    if opts.use_plugin is not None:
        from yaml import load as loadyml
        with open(opts.use_plugin) as f:
            plugin_settings = loadyml(f)
    else:
        # Setup multiprocessing
        if settings['nthreads'] == 0:
            settings['nthreads'] = cpu_count()

        if settings['nthreads'] > 1:
            plugin_settings['plugin'] = 'MultiProc'
            plugin_settings['plugin_args'] = {'n_procs': settings['nthreads']}

    subjects = gather_bids_data(settings['bids_root'])

    if not any([len(subjects[k]) > 0 for k in subjects.keys()]):
        raise RuntimeError('No scans found in %s' % settings['bids_root'])

    awf, fwf = qc_workflows(subjects=subjects, settings=settings)
    if awf is not None:
        awf.run(**plugin_settings)
    if fwf is not None:
        fwf.run(**plugin_settings)
