import binwalk
import csv
import os
import pandas as pd
import pytsk3
import shutil
import subprocess
# own imports
from . import functions_file


# function to get the partition size in bytes
def get_part_size(dev_name: str):
    img = pytsk3.Img_Info(dev_name)
    return img.get_size()


# Function to summarize blocks and their statuses
def summarize_blocks(blocks, statuses, blocks_to_summarize):
    summarized_blocks = []
    summarized_statuses = []
    for i in range(0, len(blocks), blocks_to_summarize):
        summarized_blocks.append(blocks[i:i + blocks_to_summarize])
        summarized_statuses.append(statuses[i:i + blocks_to_summarize])
    return summarized_blocks, summarized_statuses


# shorten the output of alloc or nonzero to only containing changes
def shorten_dump(output: list, part_size: float, bool_alloc: bool) -> tuple[bytes, int]:
    # get the blocks per blkls unit
    block_size = round(part_size / int(output[-1].split('|')[0]))
    if not block_size % 512 == 0:
        for i in range(1, 20):
            if abs(512 * i - block_size) < 64:
                block_size = 512 * i
                break
    max_blocks = round(part_size / block_size)

    # save only the allocation changes in tmp_list
    tmp_list = []
    # save the last
    for i in output:
        # separate an entry from '0|1' to ['0', '1']
        tmp = i.split('|')
        # discard every line where there is no number before '|'
        if not tmp[0].isnumeric():
            continue
        # set temporary y value to 1 for 'a', 0 for 'f', otherwise original value
        if 'a' in tmp[1]:
            tmp_y = '1'
        elif 'f' in tmp[1]:
            tmp_y = '0'
        else:
            tmp_y = tmp[1]
        # if it is the first line to add, add the line
        if not tmp_list:
            tmp_list.append(tmp[0] + '|' + tmp_y)
        # for every other line first check if different value
        else:
            # get old alloc state
            old = tmp_list[-1].split('|')[1]
            # if there is no change, skip
            if tmp_y == old and not i == output[-1]:
                continue
            elif tmp_y == old and i == output[-1]:
                tmp_list.append(tmp[0] + '|' + tmp_y)
                continue
            # for every other change add the old alloc state with decreased block number
            # and then add new alloc state
            tmp_list.append(str(int(tmp[0]) - 1) + '|' + old)
            tmp_list.append(tmp[0] + '|' + tmp_y)

    result_list = []
    for i in tmp_list:
        if i not in result_list:
            result_list.append(i)

    # check for allocation files if all blocks are listed, if not, append with unallocated blocks
    if bool_alloc:
        last_entry = result_list[-1].split('|')
        result_list.remove(result_list[-1])
        if int(last_entry[0]) < max_blocks - 1:
            if last_entry[1] == '0':
                result_list.append(str(max_blocks - 1) + '|0')
            else:
                result_list.append(last_entry[0] + '|' + last_entry[1])
                result_list.append(str(int(last_entry[0]) + 1) + '|0')
                result_list.append(str(max_blocks - 1) + '|0')

    # concat tmp_list to bytearray output with '\r' carriage return and '\n' line feed
    result = b''
    for i in result_list:
        result += i.encode('utf-8') + b'\r\n'

    return result, block_size


# define function to scan for each block if containing nonzero bytes, new or old content and a fixed pattern
def scan_blocks(in_bool: bool, block_size: int, in_op_id: str, target_path: str) -> list:
    op_id_byte = in_op_id.encode('utf-8')
    disk = target_path
    img = pytsk3.Img_Info(disk)

    r = [[], []]
    counter = 0
    zero_block = b'\x00' * block_size
    prefix_tmp = b'0' * (8 - 1 - len(op_id_byte))
    prefix_old = b'f' + prefix_tmp
    prefix_new = b'n' + prefix_tmp
    pattern = b'this is old data'

    while True:
        try:
            tmp = img.read(counter * block_size, block_size)
        except OSError:
            break

        if tmp == zero_block:
            r[0].append(str(counter) + '|0')
            r[1].append(str(counter) + '|0')
        else:
            if in_bool and tmp[:len(prefix_new)] == prefix_new:
                r[0].append(str(counter) + '|3')
            else:
                if tmp[:len(prefix_old)] == prefix_old:
                    r[0].append(str(counter) + '|2')
                else:
                    r[0].append(str(counter) + '|1')

            if pattern in tmp:
                r[1].append(str(counter) + '|1')
            else:
                r[1].append(str(counter) + '|0')

        counter += 1

    return r


# define function the sleuth kit dump
def dump_tsk(in_verb: bool, in_tar: bool, dump_path: str, disk_path: str, op_id: str, run_id: str, log):
    # switch to the dump directory
    os.chdir(dump_path)

    # create a directory for the current run and switch in this directory
    tmp_dir_name = 'tsk_run_' + run_id
    if not os.path.exists(tmp_dir_name):
        os.mkdir(tmp_dir_name)
    os.chdir(tmp_dir_name)
    if in_verb:
        print('switch in directory:', tmp_dir_name)

    # create a directory for the current operation and switch in this directory
    dir_name = 'tsk_operation_' + op_id
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    os.chdir(dir_name)
    if in_verb:
        print('switch in directory:', dir_name)

    tsk_op = ['fsstat', 'fls', 'istat']

    for i in tsk_op:
        if in_verb:
            print('current task:', i)
        if i != 'istat':
            file_name = 'tsk_' + i + '.txt'
            if i == 'fls':
                cmd = i + ' -r ' + disk_path
            else:
                cmd = i + ' ' + disk_path
            output = subprocess.run(cmd.split(), capture_output=True)
            file = open(file_name, 'wb')
            file.write(output.stdout)
            file.close()
            if in_verb:
                print(file_name, 'generated')
        else:
            file = open('tsk_fls.txt', 'rb')
            fls_arr = file.readlines()
            file.close()
            file_arr = []
            for j in fls_arr:
                if b'file_' in j:
                    for k in j.split():
                        h = k[:-1].split(b'-')[0]
                        if h.isdigit():
                            file_arr.append(h.decode('utf-8'))
            for j in file_arr:
                file_name = 'tsk_' + i + '_inum_' + j + '.txt'
                cmd = i + ' ' + disk_path + ' ' + j
                output = subprocess.run(cmd.split(), capture_output=True)
                if not output.stderr == b'':
                    print(output.stderr)
                    tmp_msg = 'error: tsk istat error occurred: ' + output.stderr.decode('utf-8')
                    log.write(tmp_msg)
                else:
                    file = open(file_name, 'wb')
                    file.write(output.stdout)
                    file.close()
                    if in_verb:
                        print(file_name, 'generated')

    if in_tar:
        # compress the current tsk directory
        tar_dir_name = os.path.abspath(os.path.join(dump_path, tmp_dir_name, dir_name))
        functions_file.make_tarfile(tar_dir_name)
        os.chdir(dump_path)
        shutil.rmtree(tar_dir_name)

    tmp_msg = 'generated tsk dump: run ' + run_id + ' operation ' + op_id + '\n'
    if in_verb:
        print(tmp_msg)
    log.write(tmp_msg)


#  define function alloc dump (based on tsk blkls)
def dump_alloc(in_verb: bool, partition_size: int, dump_path: str, disk_path: str, op_id: str, run_id: str, log) -> int:
    # switch to the dump directory
    os.chdir(dump_path)

    # create a directory for the current run and switch in this directory
    dir_name = 'alloc_' + run_id
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    os.chdir(dir_name)
    if in_verb:
        print('switch in directory:', dir_name)

    # combine command and run it via subprocess
    cmd = 'blkls -e -l ' + disk_path
    if in_verb:
        print('run command: ', cmd)
    # run the command and get the output as list
    cmd_out = subprocess.check_output(cmd.split()).decode('utf-8').splitlines()

    # get shortened command output as bytes
    output, blocks_size = shorten_dump(cmd_out, partition_size, True)

    # write the bytearray to file with name, e.g. 'alloc_001.txt'
    file_name = 'alloc_' + op_id + '.txt'
    file = open(file_name, 'wb')
    file.write(output)
    file.close()
    if in_verb:
        print(file_name, 'generated')

    tmp_msg = 'generated alloc file: run ' + run_id + ' operation ' + op_id + '\n'
    if in_verb:
        print(tmp_msg)
    log.write(tmp_msg)
    return blocks_size


# define function dump nonzero to get each block with nonzero data, file content and pattern
def dump_block_scan(in_verb, in_over, in_pattern, in_block_size, partition_size, dump_path, disk_path, op_id, run_id, log):
    # switch to the dump directory
    os.chdir(dump_path)

    # create a directory for the current run and switch in this directory
    dir_name_list = ['nonzero_' + run_id, 'pattern_' + run_id]
    dir_list = []
    for d in dir_name_list:
        if 'pattern' in d and not in_pattern:
            continue
        dir_list.append(os.path.join(dump_path, d))
        if not os.path.exists(d):
            os.mkdir(d)
            if in_verb:
                print('created directory:', d)

    cmd_out = scan_blocks(in_over, in_block_size, op_id, disk_path)

    # get shortened command output as bytes
    output_nonzero, block_size = shorten_dump(cmd_out[0], partition_size, False)
    output_pattern, block_size = shorten_dump(cmd_out[1], partition_size, False)

    # write the bytearray to file with name, e.g. 'nonzero_001.txt'
    file_name = 'nonzero_' + op_id + '.txt'
    file_name_abs = os.path.join(dir_list[0], file_name)
    with open(file_name_abs, 'wb') as file:
        file.write(output_nonzero)

    if in_verb:
        print(file_name, 'generated')

    if in_pattern:
        # write the bytearray to file with name, e.g. 'pattern_001.txt'
        file_name = 'pattern_' + op_id + '.txt'
        file_name_abs = os.path.join(dir_list[1], file_name)
        with open(file_name_abs, 'wb') as file:
            file.write(output_pattern)

        if in_verb:
            print(file_name, 'generated')

    tmp_msg = 'generated block scan files: run ' + run_id + ' operation ' + op_id + '\n'
    if in_verb:
        print(tmp_msg)
    log.write(tmp_msg)


# define function binwalk dump via binwalk python api
def dump_binwalk(in_verb, dump_path, disk_path, op_id, run_id, log):
    # switch to the dump directory
    os.chdir(dump_path)

    # create a directory for the current run and switch in this directory
    dir_name = 'binwalk_' + run_id
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    os.chdir(dir_name)
    if in_verb:
        print('switch in directory:', dir_name)

    cmd_out = binwalk.scan(disk_path, entropy=True, nplot=True, fast=True)

    # save only the allocation changes in tmp_list
    tmp_list = []
    for i in cmd_out[0].results:
        tmp = (str(round(i.offset / 512)), str(i.entropy))
        # if it is the first or last line to add, add the line
        if not tmp_list or i == cmd_out[-1]:
            tmp_list.append(tmp[0] + '|' + tmp[1])
        # for every other line first check if different alloc state
        else:
            # get old entropy value
            old = tmp_list[-1].split('|')[1]
            # if there is no change, skip
            if tmp[1] == old:
                continue
            # for every other change add the old alloc state with decreased block number
            # and then add new alloc state
            tmp_list.append(str(int(tmp[0]) - 1) + '|' + old)
            tmp_list.append(tmp[0] + '|' + tmp[1])

    # concat tmp_list to bytearray output with '\r' carriage return and '\n' line feed
    output = b''
    for i in tmp_list:
        output += i.encode('utf-8') + b'\r\n'

    # write the bytearray to file with name, e.g. 'entropy_001.txt'
    file_name = 'entropy_' + op_id + '.txt'
    file = open(file_name, 'wb')
    file.write(output)
    file.close()
    if in_verb:
        print(file_name, 'generated')

    tmp_msg = 'generated entropy file: run ' + run_id + ' operation ' + op_id + '\n'
    if in_verb:
        print(tmp_msg)
    log.write(tmp_msg)


def dump_fiwalk(in_verb, dump_path, disk_path, op_id, run_id, log):
    # switch to the dump directory
    os.chdir(dump_path)

    # create a directory for the current run and switch in this directory
    dir_name = 'fiwalk_' + run_id
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    os.chdir(dir_name)
    if in_verb:
        print('switch in directory:', dir_name)

    # combine command and run it via subprocess
    # cmd = 'fiwalk -g -z -X ' + disk_path
    cmd = 'fiwalk -g -z -X ' + disk_path
    if in_verb:
        print('run command: ', cmd)
    subprocess.run(cmd.split(), capture_output=True)

    # create new file name and rename the output xml
    new_file_name = 'fiwalk_operation_' + op_id + '.xml'
    for i in os.listdir(os.getcwd()):
        if os.path.isfile(i) and 'fiwalk' not in i:
            if in_verb:
                print('rename fiwalk file', '\n-> old name:', i, '\n-> new name:', new_file_name)
            os.renames(i, new_file_name)

    tmp_msg = 'generated fiwalk file: run ' + run_id + ' operation ' + op_id + '\n'
    if in_verb:
        print(tmp_msg)
    log.write(tmp_msg)


# define function to concat the last alloc and the last nonzero file
def dump_csv_concat(dump_path, run_id):
    # switch to the dump directory
    os.chdir(dump_path)

    # create the name of the output csv file
    csv_name = os.path.join(dump_path, 'csv_' + run_id + '.csv')

    # get the names of the last alloc and nonzero file
    in_files = []
    for i in ['alloc_', 'nonzero_']:
        tmp_path = os.path.join(dump_path, i + run_id)  # type: str
        file_list = os.listdir(tmp_path)
        file_list.sort()
        tmp_file = os.path.join(tmp_path, file_list[-1])  # type: str
        in_files.append(tmp_file)

    content_alloc = pd.read_csv(in_files[0], sep='|', header=None, names=['block', 'state'])
    content_nonzero = pd.read_csv(in_files[1], sep='|', header=None, names=['block', 'state'])

    block_counter = 0
    header = ['block', 'zero', 'probably fs', 'new', 'old', 'alloc']

    with open(csv_name, 'w') as csv_file:
        csv_write = csv.writer(csv_file)
        csv_write.writerow(header)
        while block_counter < content_alloc['block'].iloc[-1] + 1:
            tmp_alloc = 0
            tmp_nonzero = 0
            for i in range(0, len(content_alloc['block'])):
                if block_counter <= content_alloc['block'].iloc[i]:
                    tmp_alloc = content_alloc['state'].iloc[i].item()
                    break
            for i in range(0, len(content_nonzero['block'])):
                if block_counter <= content_nonzero['block'].iloc[i]:
                    tmp_nonzero = content_nonzero['state'].iloc[i].item()
                    break

            # fill the list tmp_row with the data for the dataframe
            tmp_row = [block_counter]
            # check nonzero state
            if tmp_nonzero == 0:
                tmp_row.extend((1, 0, 0, 0))
            elif tmp_nonzero == 1:
                tmp_row.extend((0, 1, 0, 0))
            elif tmp_nonzero == 2:
                tmp_row.extend((0, 0, 1, 0))
            elif tmp_nonzero == 3:
                tmp_row.extend((0, 0, 0, 1))
            # check allocation state
            if tmp_alloc == 0:
                tmp_row.append(0)
            elif tmp_alloc == 1:
                tmp_row.append(1)

            # write the collected data row to the data frame (columns: block, zero, prob fs, new, old, alloc)
            csv_write.writerow(tmp_row)

            block_counter += 1

    tmp_msg = 'generated csv file: run ' + run_id + '\n'
    print(tmp_msg)


# define function to concat the last alloc and the last nonzero file
def dump_csv(in_verb, dump_path, op_id, run_id, log):
    # switch to the dump directory
    os.chdir(dump_path)

    str_list = ['alloc', 'nonzero', 'pattern']

    for t in str_list:
        tmp_dir = t + '_' + run_id
        tmp_path = os.path.join(dump_path, tmp_dir)
        tmp_file = t + '_' + op_id
        file_path = os.path.join(tmp_path, tmp_file)

        if not os.path.exists(file_path):
            continue

        if in_verb:
            print('process txt file:', os.path.basename(file_path))

        # Get the directory, base filename, and extension from the input file path
        input_directory, input_extension = os.path.splitext(file_path)
        output_filename_extension = '.csv'  # Set extension to .csv
        output_file = input_directory + output_filename_extension

        if os.path.exists(output_file):
            print('file exists:', os.path.basename(output_file))
            return -1

        # Initialize empty lists to store values from the text file
        column1_values = []
        column2_values = []

        blocks_to_summarize = 4  # Number of blocks to summarize

        # Read the file line by line and split columns by '|'
        with open(file_path, 'r') as file:
            last_value = None
            lines = file.readlines()
            for line in lines:
                columns = line.strip().split('|')
                if len(columns) == 2:  # Ensure that there are two columns separated by '|'
                    current_value = columns[1]
                    if current_value == last_value:
                        start_range = int(column1_values[-1]) + 1 if column1_values else 0
                        end_range = int(columns[0])
                        for i in range(start_range, end_range):
                            column1_values.append(str(i))
                            column2_values.append(last_value)
                    column1_values.append(columns[0])
                    column2_values.append(current_value)
                    last_value = current_value

        # Summarize blocks and statuses
        summarized_blocks, summarized_statuses = summarize_blocks(column1_values, column2_values, blocks_to_summarize)

        # Write the values to a CSV file
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Index', 'SummarizedBlocks', 'SummarizedStatus'])  # Writing header with Index column
            for index, (blocks, status) in enumerate(zip(summarized_blocks, summarized_statuses)):
                writer.writerow([index] + [blocks] + [status])

        tmp_msg = 'generated csv file: run ' + run_id + ' operation ' + op_id + '\n'
        if in_verb:
            print(tmp_msg)
        log.write(tmp_msg)

    tmp_msg = 'generated csv files: run ' + run_id + '\n'
    if in_verb:
        print(tmp_msg)
    log.write(tmp_msg)
