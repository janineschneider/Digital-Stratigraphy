#!/bin/python3

import argparse
import datetime
import os
import time
# own imports
from fsaslib import functions_file, generate_xml, execute_xml, create_casey_plots, create_heatmap_plots, create_scatter_plots


def fsas_execute(in_args) -> bool:
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
    cmd_out = generate_xml.generate(in_args.dir, in_args.delete, in_args.cw, in_args.p, [in_args.minc, in_args.maxc], [args.minin, args.maxin], [args.minde, args.maxde], [args.minop, args.maxop], -1)

    # check if xml file path exists
    if not os.path.exists(in_args.o):
        print('output xml file path is invalid')
        exit(1)

    # write bytestring to output file
    with open(in_args.o, 'wb') as f:
        f.write(cmd_out)
    return True


def fsas_plot(in_args):
    # checks for plot type
    if in_args.type == 'scatter':
        # create scatter plots based on created alloc and nonzero txt files
        input_args = []
        names = ['alloc_0', 'nonzero_0', 'pattern_0']
        for n in names:
            if os.path.exists(os.path.join(in_args.path, n)):
                input_args.append(os.path.join(in_args.path, n))

        # check which options are set
        if not input_args:
            print(plot_parser.print_help())
            exit(1)

        create_scatter_plots.matplotlib_plot_scatter(True, True, input_args, in_args.out)
    elif in_args.type == 'casey':
        # create casey like plots based on image files with the extensions .dd, .img or .iso
        img_files = functions_file.get_files_ext(in_args.path, 'dd')
        img_files += functions_file.get_files_ext(in_args.path, 'img')
        img_files += functions_file.get_files_ext(in_args.path, 'iso')

        if not img_files:
            print(f"No image files with the extensions dd, img or iso found in {in_args.path}.")
            exit(1)

        for f in img_files:
            print(f"Processing image file {f}...")
            tmp_f = os.path.splitext(f)[0] + '.png'
            create_casey_plots.main(os.path.join(in_args.path, f), tmp_f, in_args.out)
    elif in_args.type == 'heatmap':
        create_heatmap_plots.main(in_args.path, in_args.out)

    return True


if __name__ == '__main__':
    # ascii art
    ascii_title = ('    ___________ ___   _____\n'
                   + '   / ____/ ___//   | / ___/\n'
                   + '  / /_   \\__ \\/ /| | \\__ \\ \n'
                   + ' / __/  ___/ / ___ |___/ / \n'
                   + '/_/    /____/_/  |_/____/  \n')
    print(ascii_title)
    print(f"File System Activity Simulator (FSAS)\n")

    # define the options and init the argument parser
    parser = argparse.ArgumentParser()
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
    execute_parser.add_argument('-p', '--path', required=True, type=str, help='given path of the mounted device')
    execute_parser.add_argument('-xml', required=True, type=str, help='given path for the xml settings file')
    execute_parser.add_argument('-out', required=True, type=str, help='given path for the output (log file, tsk dump, binwalk dump, ...)')

    generate_parser = subparsers.add_parser('generate', help='Generates a XML file for the FSAS.', description='Generates a XML file for the FSAS.')

    generate_parser.add_argument('-dir', help='activate creation and deletion of directories (optional)', action='store_true')
    generate_parser.add_argument('-delete', help='activate deletion actions (optional)', action='store_true')
    generate_parser.add_argument('-p', required=True, type=str, help='given path for the device')
    generate_parser.add_argument('-cw', required=True, type=int, help='given weight of create operations')
    generate_parser.add_argument('-minc', required=True, type=int, help='given min file size for created files')
    generate_parser.add_argument('-maxc', required=True, type=int, help='given max file size for created files')
    generate_parser.add_argument('-minin', required=True, type=int, help='given min diff size for increased files')
    generate_parser.add_argument('-maxin', required=True, type=int, help='given max diff size for increased files')
    generate_parser.add_argument('-minde', required=True, type=int, help='given min diff size for decreased files')
    generate_parser.add_argument('-maxde', required=True, type=int, help='given max diff size for decreased files')
    generate_parser.add_argument('-minop', required=True, type=int, help='given min number of operations')
    generate_parser.add_argument('-maxop', required=True, type=int, help='given max number of operations')
    generate_parser.add_argument('-o', required=True, type=str, help='given path for the xml output file')

    plot_parser = subparsers.add_parser('plot', help='Generate plots regarding the output of an executed XML file.', description='Generate plots regarding the output of an executed XML file.')

    plot_parser.add_argument('-t', '--type', required=True, type=str, help='specifies the plot type; possible values: scatter, casey, heatmap')
    plot_parser.add_argument('-p', '--path', required=True, type=str, help='given input directory')
    plot_parser.add_argument('-o', '--out', required=True, type=str, help='given output directory')

    args = parser.parse_args()

    st = time.time()

    if args.sub_command == 'generate':
        fsas_generate(args)
    elif args.sub_command == 'execute':
        fsas_execute(args)
    elif args.sub_command == 'plot':
        fsas_plot(args)
    else:
        parser.print_help()

    duration = time.time() - st

    print('finished', 'duration:', str(datetime.timedelta(seconds=duration)))
