#!/usr/bin/env python3

"""presto.

Usage:
    presto [-l <log_level> | --log <log_level>]
          [-w <workers> | --workers <workers>]
          [-p | --print]
          [-f | --force]
          [-n <node_name> | --node <node_name>]
          [-s <name:regexp> | --override_scope <name:regexp>]...
          <pipe.yaml>
    presto -c | --clean
    presto -h | --help
    presto -v |--version

Options:
    -w --workers <workers>
        Number max of different processus to launch together.
        [default: 0] -> Number of host's CPU.
    -l --log <log_level>
        Level of verbosity to print in the log file.
        Must be in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        [default: INFO]
    -p --print
        Print the execution of the pipeline only.
    -f --force
        Force execution of any node of the pipeline.
    -n --node <node_name>
        Launch pipeline from this node
    -s --override_scope <name:regexp>
        Use this option to override the regular expression used to build
        a scope.
        Example '-s SCOPE_NAME:reg-exp'
    <pipe.yaml>
        A yaml file starting with the data structure description
        and describing the pipeline.

    -c --clean
        Clean  current directory from presto generated files.

    -h --help
        Show this screen.

    -v --version
        Show version.
"""

import os
import logging
from pprint import pformat


def clean():
    print("clean")


def main(arguments):
    import log

    """Main function"""
    # ##############################################################################
    # clean ?
    # ##############################################################################

    if arguments['--clean']:
        clean()

    # ##############################################################################
    # we need this dir.
    # ##############################################################################

    presto_dir = os.path.join(os.curdir, '.presto')
    presto_log_file = os.path.join(presto_dir, 'presto.log')
    os.makedirs(presto_dir, exist_ok=True)

    # ##############################################################################
    # setup logs
    # ##############################################################################

    log_level = arguments['--log']
    log.setup(presto_log_file, log_level)
    logging.debug("cmd line arguments:\n%s", pformat(arguments))

    # ##############################################################################
    # get number of workers to use:
    # ##############################################################################

    try:
        max_workers = arguments['--workers']
        max_workers = int(max_workers)
        assert max_workers >= 0
    except (ValueError, AssertionError):
        logging.warning("<workers> must be a positive integer.\nDefault "
                        "value (auto-determine by the system) will be "
                        "used.\n")
        max_workers = 0

    try:
        if max_workers == 0:
            max_workers = os.cpu_count()
        assert max_workers is not None
    except AssertionError as err:
        logging.critical("could not find host's number of CPU please set the "
                         "--workers option yourself", err)
        sys.exit(1)

    # ##############################################################################
    # construct data model
    # ##############################################################################
    from yaml_io import YamlIO
    try:
        import path
    except ImportError:
        log.quit_with_error("Presto requiered path.py to be installed, "
                            "checkout requirement.txt.")

    yaml_document_path = path.Path(arguments['<pipe.yaml>']).abspath()
    yaml_document = YamlIO.load_all_yaml(yaml_document_path)

    scope_to_override = {}
    for s in set(arguments['--override_scope']):
        scope_regexp = s.split(':')
        try:
            scope_to_override[scope_regexp[0]] = scope_regexp[1]
        except IndexError:
            log.quit_with_error("Malformed scope to override: "
                                "'\033[91m{}\033[0m\033[1m'.\n"
                                "Have to be: SCOPE_NAME:regexp".format(s))

    try:
        from data_model import DataModel
        DataModel(yaml_document.pop(0),
                  yaml_document_path.dirname(),
                  scope_to_override)
    except IndexError:
        logging.critical("empty <pipe.yaml> file.")
        sys.exit(1)

    # ##############################################################################
    # construct pipeline
    # ##############################################################################

    from pipeline import Pipeline
    pipeline = Pipeline(yaml_document)
    from executor import ThreadedPipelineExecutor
    executor = ThreadedPipelineExecutor(pipeline, max_workers)
    executor.print_only = arguments['--print']
    executor.force_execution = arguments['--force']
    # import ipdb
    # ipdb.set_trace()

    # ##############################################################################
    # execute pipeline
    # ##############################################################################
    executor.execute(arguments['--node'])


# -- Main
if __name__ == '__main__':
    import sys
    try:
        from docopt import docopt
    except ImportError as err:
        print("presto need docopt", err)
        sys.exit(1)

    arguments = docopt(__doc__, version='presto 0.1.0')
    main(arguments)
