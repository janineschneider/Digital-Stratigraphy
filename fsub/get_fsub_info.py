import argparse
from stratlib import raw_disk_access
from stratlib.utils import get_first_fs_block_size
from stratlib.utils import get_first_fs_block_count
from stratlib.utils import get_desc_from_bit_attr
from stratlib.utils import get_block_list_from_run
from stratlib.utils import update_file_list_with_extra_info

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--long", action='store_true')
    args = parser.parse_args()

    the_disk_image = raw_disk_access.RawDiskAccessor(args.path)
    b = the_disk_image.get_file_system_handles()

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

    max_block = block_count

    print('no files: {}'.format(len(list_of_files)))

    print('updating file list with extra info...')
    update_file_list_with_extra_info(list_of_files, file_system_handles_dict)

    print('locating FSUB using TSK...')
    highest_start_block = -1
    highest_start_block_file = None
    highest_end_block = -1
    highest_end_block_file = None

    for fn, each_file in enumerate(sorted(list_of_files, key=lambda d: d['crtime'])):
        if each_file.get('start_block'):  # skips files with no start cluster

            # keeps track of FSUB info
            if each_file.get('start_block') > highest_start_block:
                highest_start_block = each_file.get('start_block')
                highest_start_block_file = each_file.get('full_path')

            if max(each_file['blocks']) > highest_end_block:
                highest_end_block = max(each_file['blocks'])
                highest_end_block_file = each_file.get('full_path')

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