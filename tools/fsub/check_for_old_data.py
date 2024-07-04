import argparse
from stratlib import raw_disk_access
from stratlib.utils import get_first_fs_block_size
from stratlib.utils import get_first_fs_block_count
from stratlib.utils import get_desc_from_bit_attr
from stratlib.utils import get_block_list_from_run
from stratlib.utils import update_file_list_with_extra_info
import re
import os

def check_blocks_in_vol_for_old_data(the_disk_image, partition_offset):
    b = the_disk_image.get_file_system_handles()

    if partition_offset not in the_disk_image.get_file_system_handles():
        raise Exception('Partition not found at offset {}'.format(partition_offset))

    block_size = b.get(partition_offset).info.block_size
    block_count = b.get(partition_offset).info.block_count
    max_block = block_count
    print('block_size  = {}'.format(block_size))
    print('block_count  = {}'.format(block_count))

    print('checking blocks...')
    block_status_list = []
    for block_number in range(0, max_block):
        block_data = the_disk_image.get_partition_block(partition_offset,
                                                        block_number,
                                                        block_size=block_size,
                                                        sector_size=512)

        if re.search(b'this is old data', block_data) is not None:
            block_attr_to_add = True
        else:
            block_attr_to_add = False

        block_status_list.append(block_attr_to_add)

    return block_status_list

def main():
    print('NOTE: Only works if disk was initialised with ''this is old data'' pattern before formatting.')
    
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--long", action='store_true')
    args = parser.parse_args()

    the_disk_image = raw_disk_access.RawDiskAccessor(args.path)
    b = the_disk_image.get_file_system_handles()

    if len(b) > 1:
        print('WARNING MULTIPLE PARTITIONS NOT SUPPORTED. Using first.')

    partition_offsets = sorted(list(b.keys()))

    print('Checks blocks contain old data or not')

    print('loaded disk image: {}'.format(os.path.split(args.path)[-1]))

    # list_of_files = []
    # the_disk_image.get_list_of_files(list_of_files)
    b = raw_disk_access.RawDiskAccessor(args.path)
    file_system_handles_dict = b.get_file_system_handles()

    # print('no files: {}'.format(len(list_of_files)))

    # print('updating file list with extra info...')
    # update_file_list_with_extra_info(list_of_files, file_system_handles_dict)

    print('looking at blocks in vol starting at {}'.format(partition_offsets[0]))
    block_status_list = check_blocks_in_vol_for_old_data(the_disk_image, partition_offsets[0])

    print('blocks with old data: ')
    for i, each_block_status in enumerate(block_status_list):
        if each_block_status == True:
            print('{}'.format(i), end=',')

if __name__ == '__main__':
    main()