#!/bin/python3

import argparse
import datetime
# import matplotlib.pyplot as plt
# import matplotlib.patches as mpatches
import os
# from operator import add
# import pandas as pd
# import re
import time
# own imports
import execute_xml
import generate_xml
import create_plots


def fsas_execute(in_args) -> bool:
    # check if all mandatory options are set
    for a in vars(in_args):
        if getattr(in_args, a) is None:
            print(execute_parser.print_help())
            exit(1)

    # prepare bool list for execute function
    bool_values = [False, False, False, False, False, False, False, False]

    if args.verbose:
        bool_values[0] = True
    if args.compress:
        bool_values[1] = True
    if args.random:
        bool_values[2] = True
    if args.tsk:
        bool_values[3] = True
    if args.binwalk:
        bool_values[4] = True
    if args.fiwalk:
        bool_values[5] = True
    if args.alloc:
        bool_values[6] = True
    if args.nonzero:
        bool_values[7] = True

    execute_xml.execute(bool_values, in_args.path, in_args.xml, in_args.out)
    return True


def fsas_generate(in_args) -> bool:
    # check if all options are set
    for a in vars(in_args):
        if getattr(in_args, a) is None:
            print(generate_parser.print_help())
            exit(1)

    cmd_out = generate_xml.generate(in_args.d, True, 3, in_args.p, [in_args.minc, in_args.maxc], [args.minin, args.maxin], [args.minde, args.maxde], [args.minop, args.maxop], -1)

    # check if xml file path exists
    if not os.path.exists(in_args.o):
        print('output xml file path is invalid')
        exit(1)

    # write bytestring to output file
    with open(in_args.o, 'wb') as f:
        f.write(cmd_out)
    return True


def fsas_plot(in_args):
    if in_args.path is None:
        print(plot_parser.print_help())
        exit(1)

    input_args = []
    names = ['alloc_0', 'nonzero_0']
    for n in names:
        if os.path.exists(os.path.join(in_args.path, n)):
            input_args.append(os.path.join(in_args.path, n))

    # check which options are set
    if not input_args:
        print(plot_parser.print_help())
        exit(1)

    # matplotlib_plot_scatter(True, False, input_args, args.out)
    create_plots.matplotlib_plot_scatter(True, True, input_args, args.out)
    # create_plots.matplotlib_plot_bars(True, False, True, input_args, args.out)
    # matplotlib_plot_bars(False, False, True, input_args, args.out)
    return True


if __name__ == '__main__':
    # ascii art
    ascii_title = ('    ___________ ___   _____\n'
                   + '   / ____/ ___//   | / ___/\n'
                   + '  / /_   \\__ \\/ /| | \\__ \\ \n'
                   + ' / __/  ___/ / ___ |___/ / \n'
                   + '/_/    /____/_/  |_/____/  \n')
    print(ascii_title)

    # define the options and init the argument parser
    parser = argparse.ArgumentParser(description='Runs the File System Activity Simulator FSAS.')
    subparsers = parser.add_subparsers(dest='sub_command')

    execute_parser = subparsers.add_parser('execute', help='Runs the FSAS scripts for a given xml file.', description='Runs the FSAS scripts for a given xml file.')

    execute_parser.add_argument('-v', '--verbose', help='enable verbose output on stdout (optional)', action="store_true")
    execute_parser.add_argument('-c', '--compress', help='compress output files (optional)', action="store_true")
    execute_parser.add_argument('-r', '--random', help='write random file content (optional)', action="store_true")
    execute_parser.add_argument('-t', '--tsk', help='enable tsk output in output directory (optional)', action="store_true")
    execute_parser.add_argument('-b', '--binwalk', help='enable binwalk output in output directory (optional)', action="store_true")
    execute_parser.add_argument('-f', '--fiwalk', help='enable fiwalk output in output directory (optional)', action="store_true")
    execute_parser.add_argument('-a', '--alloc', help='enable tsk output of allocation status in output directory (optional)', action="store_true")
    execute_parser.add_argument('-n', '--nonzero', help='enable scan for nonzero blocks (optional)', action="store_true")
    execute_parser.add_argument('-p', '--path', type=str, help='given path of the mounted device')
    execute_parser.add_argument('-xml', type=str, help='given path for the xml settings file')
    execute_parser.add_argument('-out', type=str, help='given path for the output (log file, tsk dump, binwalk dump, ...)')

    generate_parser = subparsers.add_parser('generate', help='Generates a XML file for the FSAS.', description='Generates a XML file for the FSAS.')

    generate_parser.add_argument('-d', help='activate creation and deletion of directories', action='store_true')
    generate_parser.add_argument('-p', type=str, help='given path for the device')
    generate_parser.add_argument('-cw', type=int, help='given weight of create operations')
    generate_parser.add_argument('-minc', type=int, help='given min file size for created files')
    generate_parser.add_argument('-maxc', type=int, help='given max file size for created files')
    generate_parser.add_argument('-minin', type=int, help='given min diff size for increased files')
    generate_parser.add_argument('-maxin', type=int, help='given max diff size for increased files')
    generate_parser.add_argument('-minde', type=int, help='given min diff size for decreased files')
    generate_parser.add_argument('-maxde', type=int, help='given max diff size for decreased files')
    generate_parser.add_argument('-minop', type=int, help='given min number of operations')
    generate_parser.add_argument('-maxop', type=int, help='given max number of operations')
    generate_parser.add_argument('-o', type=str, help='given path for the xml output file')

    plot_parser = subparsers.add_parser('plot', help='Generate plots regarding the output of an executed XML file.', description='Generate plots regarding the output of an executed XML file.')

    plot_parser.add_argument('-t', '--type', type=str, help='specifies the plot type; possible values: scatter, bar, heatmap')
    plot_parser.add_argument('-p', '--path', type=str, help='given input directory')
    plot_parser.add_argument('-o', '--out', type=str, help='given output directory')

    args = parser.parse_args()

    st = time.time()

    if args.sub_command == 'generate':
        generate_parser.print_help()
        # fsas_generate(args)
    elif args.sub_command == 'execute':
        generate_parser.print_help()
        # fsas_execute(args)
    elif args.sub_command == 'plot':
        generate_parser.print_help()
        # fsas_plot(args)
    else:
        parser.print_help()

    duration = time.time() - st

    print('finished', 'duration:', str(datetime.timedelta(seconds=duration)))
