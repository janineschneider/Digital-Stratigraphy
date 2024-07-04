import argparse
from stratlib import raw_disk_access
import os.path
import datetime
import re
import plotly
from datetime import datetime
from stratlib.utils import get_desc_from_bit_attr
from stratlib.utils import get_first_fs_block_count
from stratlib.utils import get_first_fs_block_size
from stratlib.utils import get_block_list_from_run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--carved_start", type=int)
    parser.add_argument("--carved_end", type=int)
    parser.add_argument("--max_block", type=int)
    parser.add_argument("--max_files", type=int)
    parser.add_argument("--disable_x_filenames", action='store_true')
    parser.add_argument("--long", action='store_true')
    args = parser.parse_args()

    if args.carved_start and args.carved_end:
        print('carved file will also be visualised: {}...{}'.format(args.carved_start, args.carved_end))

    the_disk_image = raw_disk_access.RawDiskAccessor(args.path)
    b = the_disk_image.get_file_system_handles()

    print('running on file {}'.format(os.path.split(args.path)[-1]))

    if len(b) > 1:
        print('WARNING MULTIPLE PARTITIONS NOT SUPPORTED. Using first.')

    partition_offsets = sorted(list(b.keys()))

    print('Generates visualisation of file system final state using file creations as proxy for operations')

    block_size = get_first_fs_block_size(b)
    block_count = get_first_fs_block_count(b)
    print('block_size  = {}'.format(block_size))
    print('block_count  = {}'.format(block_count))

    list_of_files = []

    the_disk_image.get_list_of_files(list_of_files)
    b = raw_disk_access.RawDiskAccessor(args.path)
    file_system_handles_dict = b.get_file_system_handles()

    #max_block = 63742 # ntfs example
    #max_block = 512000  # fat examle

    # This allows a subset of a file systemt o be examiend in cases where it is too bit (mostly FAT since sectors are used)
    if args.max_block:
        max_block = args.max_block
        print('Capping max_block to {} (based on CLI args)'.format(max_block))
    else:
        max_block = block_count
        print('max_block is {}'.format(max_block))

    if args.max_files:
        max_files = args.max_files
        print('Capping max_files to {} (based on CLI args)'.format(max_files))
    else:
        max_files = len(list_of_files)
        print('max_files is {}'.format(max_files))

    xaxis = list(range(0, max_block))
    yaxis = list(range(0, max_files))

    # Initialises labels for x and y axis
    for i, item in enumerate(xaxis):
        xaxis[i] = str(item)
    for i, item in enumerate(yaxis): #
        yaxis[i] = str(item)

    # populates a list of files with specific extracted properties
    for each_file in list_of_files:
        inode = each_file['inode']
        each_file['blocks'] = []
        file_obj = file_system_handles_dict[each_file['partition_sector']].open_meta(inode)
        for attr in file_obj:
            first = True
            for run in attr:
                if first == True:
                    each_file['start_block'] = run.addr
                    first = False
                each_file['blocks'].extend(get_block_list_from_run(run.addr, run.len))

        # populates the x-axis labels with added filename associaated with each block
        if not args.disable_x_filenames:
            for each_block_no in each_file['blocks']:
                if each_block_no < max_block:  # handle possible redueced dataset
                    xaxis[each_block_no] = xaxis[each_block_no] + ' {}'.format(each_file['full_path'])

    print('files processed.')
    print('no files: {}'.format(len(list_of_files)))

    print('total data points = {} (approx {}GB)'.format(len(list_of_files)*max_block,
                                                 int(len(list_of_files)*max_block/1024/1024/1024)))

    # makes a version of that file list sorted by creation time
    # time_sorted_list = sorted(list_of_files, key=lambda d: d['crtime'])

    highest_start_block = -1
    highest_start_block_file = None

    highest_end_block = -1
    highest_end_block_file = None

    baseline_block_allocation = []
    baseline_block_allocation_text = []

    print('building block map based on raw content...', end='')
    for block_number in range(0, max_block):
        block_data = the_disk_image.get_partition_block(partition_offsets[0],
                                                        block_number,
                                                        block_size=block_size,
                                                        sector_size=512)
        block_attr_to_add = 0b00000000

        if block_data == b'\x00' * block_size:
            block_attr_to_add = block_attr_to_add | 0b00000000
        else:
            block_attr_to_add = block_attr_to_add | 0b00000001

        if re.search(b'this is old data', block_data) is not None:
            block_attr_to_add = block_attr_to_add | 0b00000011

        baseline_block_allocation.append(block_attr_to_add)
        baseline_block_allocation_text.append(get_desc_from_bit_attr(block_attr_to_add))

    block_allocation_map = [baseline_block_allocation,]
    block_allocation_map_text = [baseline_block_allocation_text, ]
    print('Block map complete. ')

    print('sorting file list by cr_time...', end='')
    sorted_list = sorted(list_of_files, key=lambda d: d['crtime'])
    print('sorted.')

    print('updating block map based on file allocation status...')
    first = True
    file_processed_count = 0
    for fn, each_file in enumerate(sorted_list):
        if each_file.get('start_block'):  # skips files with no start cluster
            # populates y-axis labels with creation time
            yaxis[file_processed_count] = yaxis[file_processed_count] + ' {}'.format(
                datetime.utcfromtimestamp(each_file['crtime']).strftime('%Y-%m-%d %H:%M:%S'))

            if first == False:
                block_allocation_map.append(block_allocation_map[-1].copy()) # copy the last operation to a new one
                # block_allocation_map_text.append(block_allocation_map_text[-1].copy())  # copy the last operation (for text) to a new one
            for each_alloc_block in each_file['blocks']:
                val_to_set = 0b00000100 # set allocation flag
                if each_alloc_block < max_block:  # handle possible user instructed reduced dataset
                    block_allocation_map[-1][each_alloc_block] = block_allocation_map[-1][each_alloc_block] | val_to_set  # add allocated status to last operation row added
                # block_allocation_map_text[-1][each_alloc_block] = get_desc_from_bit_attr(val_to_set)  # adds text for it

            # keeps track of FSUB info
            if each_file.get('start_block') > highest_start_block:
                highest_start_block = each_file.get('start_block')
                highest_start_block_file = each_file.get('full_path')

            if max(each_file['blocks']) > highest_end_block:
                highest_end_block = max(each_file['blocks'])
                highest_end_block_file = each_file.get('full_path')

            file_processed_count += 1

            if args.max_files and file_processed_count >= args.max_files:
                break

        first = False
    print('Time/block map generated.')

    yaxis = yaxis[:file_processed_count] # strip excess yaxis due to files with no start sector

    # This draws in a simulated carved file to the map so it's context can be seen
    # print('visualising carved file...')
    # carved_data_blocks = range(46650, 47000) # example 1
    # carved_data_blocks = range(450654, 460000) # example 2
    if args.carved_start and args.carved_end:
        print('adding carved file to representation...')
        carved_data_blocks = range(int(args.carved_start), int(args.carved_end)) # example 2
        carved_file_thickness = int(len(list_of_files)/100 * 5)
        print('line thickness: {}'.format(carved_file_thickness))
        for i in range(0, carved_file_thickness):
            row_to_add = [0] * max_block
            for each_block_no in carved_data_blocks:
                val_to_set = 0b00100000
                if each_block_no < max_block:
                    row_to_add[each_block_no] = val_to_set
                    #block_allocation_map_text[each_row][each_block] = get_desc_from_bit_attr(0b10000001)
            block_allocation_map.append(row_to_add)
            yaxis.append('carved({})'.format(i))

    colorscale = [[0, '#999999'],
                  [0.01, '#377eb8'], # non zero
                  [0.03, '#e41a1c'], # old data, not zero
                  [0.04, '#dede00'], # alloc, filled with zeros
                  [0.05, '#2c642a'], # alloc, non zero
                  [0.13, '#4daf4a'], # new pattern, alloc, non-zero
                  [0.19, '#984ea3'], # old data and fs struct, non zero
                  [0.21, '#a65628'], # poss fs struct, alloc, contains non-zero
                  [0.32, '#e41a1c'],  # carved data representation
                  [1, '#ffffff']      # 100+ reserved
                  ]

    import plotly.graph_objects as go
    print('setting up heatmap...')
    fig = go.Figure(data=go.Heatmap(z=block_allocation_map,
                                    x=xaxis,
                                    y=yaxis,
                                    zmin=0,
                                    zmax=100,
                                    #text=block_allocation_map_text,
                                    hovertemplate='Block: %{x}<br>Operation: %{y}<br>Block status: %{z}',
                                    colorscale=colorscale)
                    )
    fig.update_xaxes(title_text="Block number")
    fig.update_yaxes(title_text="Operation (cr_time)")

    # Set chart title
    if args.carved_start and args.carved_end:
        fig.update_layout(title_text=
        "Generated from final disk image: {}\n plus carved file at blocks {}..{}".format(
            os.path.split(args.path)[-1], args.carved_start, args.carved_end))
    else:
        fig.update_layout(title_text="Generated from final disk image: " + os.path.split(args.path)[-1])

    print('saving offline plot...')
    plotly.offline.plot(fig, filename='df_digger_out_{}.html'.format(os.path.split(args.path)[-1]))

    print()
    print('FSUB')
    print('====')

    print('Highest start block: {}'.format(highest_start_block))
    print('Highest start block file: {}'.format(highest_start_block_file))

    print('Highest end block: {}'.format(highest_end_block))
    print('Highest end block file: {}'.format(highest_end_block_file))
    print('NOTE: Highest values are dangerous for some file systems e.g. FAT')

    print()

main()