def get_desc_from_bit_attr(int_val):
    # Gets a description of a block state depending on our bit flags
    if int_val == 0:
        text_val = 'zero block'
    elif int_val == 3:
        text_val = 'old data'
    elif int_val == 4:
        text_val = 'alloc, zero'
    elif int_val == 5:
        text_val = 'alloc, non-zero'
    elif int_val == 13:
        text_val = 'new pattern, allocated, non-zero'
    elif int_val == 19:
        text_val = 'old data and fs struct, non zero'
    elif int_val == 21:
        text_val = 'Poss fs struct, allocated, contains non-zero'
    elif int_val == 129:
        text_val = 'Carved data of interest'
    else:
        text_val = 'undefined'
    return text_val


def get_first_fs_block_count(file_system_handles):
    for each_fs in file_system_handles:
        block_count = file_system_handles[each_fs].info.block_count
        return block_count


def get_first_fs_block_size(file_system_handles):
    for each_fs in file_system_handles:
        block_size = file_system_handles[each_fs].info.block_size
        return block_size


def update_file_list_with_extra_info(list_of_files, file_system_handles_dict):
    # populates a list of files with specific extracted properties
    for each_file in list_of_files:
        inode = each_file['inode']
        each_file['blocks'] = []
        file_obj = file_system_handles_dict[each_file['partition_sector']].open_meta(inode)
        for attr in file_obj:
            first = True
            for run in attr:
                if first:
                    each_file['start_block'] = run.addr
                    first = False
                each_file['blocks'].extend(get_block_list_from_run(run.addr, run.len))
    return True  # list is mutable so will be updated anyway


def get_block_list_from_run(start, length):
    block_list = []
    for i in range(start, start + length):
        block_list.append(i)

    # print('run: start:{} len:{} = list{}'.format(start, len, block_list))
    return block_list
