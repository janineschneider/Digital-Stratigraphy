#!/bin/python3

import datetime
import os
import psutil
import secrets
import shutil
import subprocess
import sys
# own imports
from . import functions_file, functions_os, functions_output


# concat file path from path (xml) and given device path
# example: '/dir/dev1' + '/1/2/3'
def concat_file_path(relative_file_path: str, path: str) -> str:
    # the first 3 characters of path (xml) are '/-1' and should be removed
    if path[-1] == '/':
        result = path + relative_file_path[4:]
    else:
        result = path + relative_file_path[3:]
    return result


# define content generation function
def generate_content(in_rand: bool, in_over: bool, length: int, in_number: str) -> bytes:
    # check if content should be random
    if in_rand:
        return secrets.token_bytes(length - 3)

    # init some tmp variables
    content = b''
    # create non random file content
    while len(content) < length:
        # create the content sort of 'f0000001f00000001...' -> 8 byte long pattern
        tmp_number = bytes(in_number, 'utf-8')
        if in_over:
            tmp = b'n' + b'0' * (7 - len(tmp_number)) + tmp_number
        else:
            tmp = b'f' + b'0' * (7 - len(tmp_number)) + tmp_number
        # create the content sort of 'f1f1f1f1f1f1...f1' -> length of pattern inconsistent
        # tmp = b'f' + tmp_number

        while len(tmp) < 64:
            tmp += tmp
        content += tmp[0:64]
    return content[0:length]


# define function write
def file_write(in_over: bool, in_rand: bool, file_number: str, file_size: int, tmp_file_path: str, log, in_path: str):
    # in each run a new file with 'file_i.txt' is created and written with the amount of bytes
    # concat file name
    file_name = concat_file_path(tmp_file_path, in_path) + '/'
    # error message if the parent dir does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: creating file ' + file_number + ' failed\n'
        tmp_msg += 'parent directory ' + file_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    file_name += 'file_' + str(file_number) + '.txt'
    file = open(file_name, 'wb')

    # write file in chunks, if file size is bigger than 500MB to save RAM
    if file_size > 500 * 1024 * 1024:
        # only necessary for writing file content in blocks
        # write file content in blocks with 128 * 1024 byte length
        # calc runs for loop
        k = (file_size - 3) // (128 * 1024)
        for i in range(k):
            file.write(generate_content(in_rand, in_over, (128 * 1024), file_number))
        file.write(generate_content(in_rand, in_over, (file_size - 3 - k * 128 * 1024), file_number) + b'EOF')
    else:
        file.write(generate_content(in_rand, in_over, (file_size - 3), file_number) + b'EOF')

    file.close()
    # logging
    tmp_msg = 'file created: ' + file_name + '\n'
    log.write(tmp_msg)
    return 0


# define function delete
def file_delete(file_number: str, tmp_file_path: str, log, in_path: str):
    # concat file name
    file_name = concat_file_path(tmp_file_path, in_path) + '/'
    # error message if the parent dir does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: deleting file ' + file_number + ' failed\n'
        tmp_msg += 'parent directory ' + file_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    file_name += 'file_' + str(file_number) + '.txt'
    # error message if file does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: deleting ' + file_name + ' failed\n'
        log.write(tmp_msg)
        return -1
    # remove the file if exists
    os.remove(file_name)
    # logging
    tmp_msg = 'file deleted: ' + file_name + '\n'
    log.write(tmp_msg)
    return 0


# define function increase
def file_increase(in_over: bool, in_rand: bool, file_number: str, diff_size: int, tmp_file_path: str, log, in_path: str):
    # concat file name
    file_name = concat_file_path(tmp_file_path, in_path) + '/'
    # error message if the parent dir does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: increasing file ' + file_number + ' failed\n'
        tmp_msg += 'parent directory ' + file_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    file_name += 'file_' + file_number + '.txt'
    # error message if file does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: increasing ' + file_name + ' failed\n'
        log.write(tmp_msg)
        return -1
    # increase the file if exists
    file = open(file_name, 'ab')
    file.write(generate_content(in_rand, in_over, diff_size, file_number) + b'EOI')
    file.close()
    # logging
    tmp_msg = 'file increased: ' + file_name + '\n'
    log.write(tmp_msg)
    return 0


# define function decrease
def file_decrease(file_number: str, diff_size: int, tmp_file_path: str, log, in_path: str):
    # concat file name
    file_name = concat_file_path(tmp_file_path, in_path) + '/'
    # error message if the parent dir does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: decreasing file ' + file_number + ' failed\n'
        tmp_msg += 'parent directory ' + file_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    file_name += 'file_' + file_number + '.txt'
    # error message if file does not exist
    if not os.path.exists(file_name):
        tmp_msg = 'error: decreasing ' + file_name + ' failed\n'
        log.write(tmp_msg)
        return -1
    # decrease the file if exists
    new_size = os.path.getsize(file_name) - diff_size
    file = open(file_name, 'ab')
    file.truncate(new_size - 3)
    file.write(b'EOD')
    file.close()
    # logging
    tmp_msg = 'file decreased: ' + file_name + '\n'
    log.write(tmp_msg)
    return 0


# define function dir_create
def dir_create(dir_number: str, tmp_dir_path: str, log, in_path: str):
    # concat dir name
    dir_name = concat_file_path(tmp_dir_path, in_path) + '/'
    # error message if the parent dir does not exist
    if not os.path.exists(dir_name):
        tmp_msg = 'error: creating directory ' + dir_number + ' failed\n'
        tmp_msg += 'parent directory ' + dir_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    dir_name += dir_number
    # error message if the directory already exists
    if os.path.exists(dir_name):
        tmp_msg = 'error: creating directory ' + dir_name + ' failed\n'
        tmp_msg += 'directory ' + dir_name + ' does already exist\n'
        log.write(tmp_msg)
        return -1
    os.mkdir(dir_name)
    # logging
    tmp_msg = 'directory created: ' + dir_name + '\n'
    log.write(tmp_msg)
    return 0


# define function dir_delete
def dir_delete(dir_number: str, tmp_dir_path: str, log, in_path: str):
    # concat dir name
    dir_name = concat_file_path(tmp_dir_path, in_path) + '/'
    # error message if the parent dir does not exist
    if not os.path.exists(dir_name):
        tmp_msg = 'error: deleting directory ' + dir_number + ' failed\n'
        tmp_msg += 'parent directory ' + dir_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    dir_name += dir_number
    # error message if the directory does not exist
    if not os.path.exists(dir_name):
        tmp_msg = 'error: deleting directory ' + dir_name + ' failed\n'
        tmp_msg += 'directory ' + dir_name + ' does not exist\n'
        log.write(tmp_msg)
        return -1
    shutil.rmtree(dir_name)
    # logging
    tmp_msg = 'directory deleted: ' + dir_name + '\n'
    log.write(tmp_msg)
    return 0


def execute(in_bools, dev_path, xml_path, out_path):
    # check paths
    functions_os.check_path(xml_path)
    functions_os.check_path(out_path)

    # check operating system
    bool_linux = False
    bool_win = False
    if sys.platform.startswith('linux'):
        bool_linux = True
    elif sys.platform.startswith('win'):
        bool_win = True

    # check for root permissions
    if not functions_os.check_root(bool_linux, bool_win):
        print('error: permission denied error occurred or no linux|windows operating system detected')
        exit(1)

    # init bool vars for verbose, random, tsk, binwalk, fiwalk, alloc
    bool_verb = in_bools[0]
    bool_tar = in_bools[1]
    bool_rand = in_bools[2]
    bool_tsk = in_bools[3]
    bool_binwalk = in_bools[4]
    bool_fiwalk = in_bools[5]
    bool_alloc = in_bools[6]
    bool_nonzero = in_bools[7]
    bool_pattern = in_bools[8] or 'pattern' in out_path

    xml_tree = functions_file.open_xml(xml_path)

    # check if it is an execution of an overw_after_*.xml file
    bool_overw = False
    if 'overw_after_' in os.path.basename(xml_path):
        bool_overw = True

    # get absolute path of output directory
    cur_out = out_path

    # open log_file and begin logging
    log_file_name = cur_out + '/' + 'logfile.txt'
    log_file = open(log_file_name, 'w')
    cur_msg = datetime.datetime.now().strftime('%d.%m.%Y - %H:%M:%S') + '\n'
    cur_msg += 'starting the script execute_xml\n\n'
    log_file.write(cur_msg)

    # check if tsk is installed and reachable
    if bool_tsk or bool_alloc:
        try:
            subprocess.run('fsstat', capture_output=True)
        except FileNotFoundError:
            # print an error message on stdout and log this message
            cur_msg = 'error: the sleuth kit is not installed or the path is not reachable'
            log_file.write(cur_msg)
            print(cur_msg)
            # set bool_tsk as False
            bool_tsk = False
            bool_alloc = False

    # check if fiwalk is installed and reachable
    if bool_fiwalk:
        try:
            subprocess.run('fiwalk', capture_output=True)
        except FileNotFoundError:
            # print an error message on stdout and log this message
            cur_msg = 'error: fiwalk is not installed or the path is not reachable'
            log_file.write(cur_msg)
            print(cur_msg)
            # set bool_fiwalk as False
            bool_fiwalk = False

    # read the file system size from xml
    cur_size = float(xml_tree.attrib['size_gib'])

    # set the device path
    cur_path = dev_path

    # check if device size is smaller than cur_size
    fs_size = round(psutil.disk_usage(cur_path).total, 1)
    if fs_size < cur_size:
        cur_msg = 'warning: given path has smaller size than expected!'
        log_file.write(cur_msg)
        print(cur_msg)

    # get device name from cur_path for different operating systems
    cur_dev = ''
    drive_letter = ''
    # cur_guid = ''
    cur_vol_id = ''
    if bool_linux:
        for d in psutil.disk_partitions(all=True):
            if d.mountpoint in cur_path:
                cur_dev = d.device
    elif bool_win:
        drive_letter = cur_path[:1]
        cur_dev = '\\\\.\\' + drive_letter + ':'
        # cur_guid = functions_os.get_vol_guid(drive_letter)
        cur_vol_id = functions_os.get_vol_id(drive_letter)
        print('mount point:', drive_letter, 'volume id:', cur_vol_id)

    # should work on Windows and Linux/Unix
    disk_usage = psutil.disk_usage(cur_path)
    blocks_bytes = disk_usage.total
    free_bytes = disk_usage.free
    usage_percent = disk_usage.percent
    part_size = functions_output.get_part_size(cur_dev)

    cur_msg = 'log file: ' + log_file_name + '\n'
    cur_msg += 'device path: ' + cur_path + '\n'
    cur_msg += 'device name: ' + cur_dev + '\n'
    cur_msg += '#(total bytes): ' + str(blocks_bytes) + '\n'
    cur_msg += '#(free bytes): ' + str(free_bytes) + '\n'
    cur_msg += 'usage percent: ' + str(usage_percent) + '\n'
    log_file.write(cur_msg)

    # counters file_number and dir_number
    count_files = 0
    count_dirs = 0

    for run in xml_tree:
        last_block_blkls = 512

        print(run.tag, run.attrib)

        # get the number of op ids of this run and generate format string for leading zeros
        form_str_op = "{:0" + str(len(str(len(run) - 1))) + "d}"

        # mount and umount device on linux to disable caching
        if bool_linux:
            functions_os.umount_linux(cur_dev, cur_path)
            functions_os.mount_linux(cur_dev, cur_path)
        # mount and umount device on Windows to disable caching
        elif bool_win:
            # functions_os.write_cache_win(drive_letter)
            functions_os.umount_win(cur_vol_id, drive_letter)
            functions_os.mount_win(cur_vol_id, drive_letter)

        # run initial tsk, binwalk, fiwalk & alloc dump with operation id 0
        if bool_tsk:
            functions_output.dump_tsk(bool_verb, bool_tar, cur_out, cur_dev, form_str_op.format(0), run.attrib['id'], log_file)
        if bool_binwalk:
            functions_output.dump_binwalk(bool_verb, cur_out, cur_dev, form_str_op.format(0), run.attrib['id'], log_file)
        if bool_fiwalk:
            functions_output.dump_fiwalk(bool_verb, cur_out, cur_dev, form_str_op.format(0), run.attrib['id'], log_file)
        if bool_alloc:
            last_block_blkls = functions_output.dump_alloc(bool_verb, part_size, cur_out, cur_dev, form_str_op.format(0), run.attrib['id'], log_file)
            tmp_msg = 'last block no of blkls output saved: ' + str(last_block_blkls) + '\n'
            if bool_verb:
                print(tmp_msg)
            log_file.write(tmp_msg)
        if bool_nonzero:
            functions_output.dump_block_scan(bool_verb, bool_overw, bool_pattern, last_block_blkls, part_size, cur_out, cur_dev, form_str_op.format(0), run.attrib['id'], log_file)

        for op in run:
            # formatting the operation id with leading zeros
            cur_op_id = form_str_op.format(int(op.attrib['id']) + 1)

            # logging operation id
            tmp_msg = 'running operation ' + op.attrib['type'] + ' with ID ' + cur_op_id
            if bool_verb:
                print(tmp_msg)
            log_file.write(tmp_msg)

            # store current working directory and change directory to path
            cur_dir = os.getcwd()
            os.chdir(cur_path)
            errno = 1

            # write operation
            if op.attrib['type'] == 'write':
                cur_file_size = int(op[0].attrib['size'])
                # check if there is a tag with 'path' attribute and read it
                try:
                    cur_file_path = op[1].attrib['path']
                # if there is no second file tag use path = '/-1'
                except IndexError:
                    cur_file_path = '/-1'
                errno = file_write(bool_overw, bool_rand, str(count_files), cur_file_size, cur_file_path, log_file, cur_path)
                count_files += 1
            # delete operation
            elif op.attrib['type'] == 'delete':
                cur_attr = op[0].attrib['value']
                try:
                    cur_file_path = op[1].attrib['path']
                except IndexError:
                    cur_file_path = '/-1'
                errno = file_delete(cur_attr, cur_file_path, log_file, cur_path)
            # increase and decrease operations
            elif op.attrib['type'] == 'increase' or op.attrib['type'] == 'decrease':
                cur_file = op[0].attrib['value']
                cur_diff = int(op[1].attrib['diff'])
                try:
                    cur_file_path = op[2].attrib['path']
                except IndexError:
                    cur_file_path = '/-1'
                if op.attrib['type'] == 'increase':
                    errno = file_increase(bool_overw, bool_rand, cur_file, cur_diff, cur_file_path, log_file, cur_path)
                else:
                    errno = file_decrease(cur_file, cur_diff, cur_file_path, log_file, cur_path)
            elif op.attrib['type'] == 'dir_create':
                cur_parent_path = op[0].attrib['parent']
                errno = dir_create(str(count_dirs), cur_parent_path, log_file, cur_path)
                count_dirs += 1
            elif op.attrib['type'] == 'dir_delete':
                cur_dir_id = op[0].attrib['id']
                cur_parent_path = op[1].attrib['path']
                errno = dir_delete(cur_dir_id, cur_parent_path, log_file, cur_path)
            else:
                cur_msg = 'invalid operation: ' + op.attrib['type'] + '\n'
                log_file.write(cur_msg)

            if errno < 0:
                cur_msg = 'operation failed: ' + op.attrib['id'] + 'with type:' + op.attrib['type'] + '\n'
                log_file.write(cur_msg)
                print(cur_msg)
                exit(errno)

            # mount and umount device on linux to disable caching
            os.chdir(cur_dir)
            if bool_linux:
                functions_os.umount_linux(cur_dev, cur_path)
                functions_os.mount_linux(cur_dev, cur_path)
            # mount and umount device on Windows to disable caching
            elif bool_win:
                # functions_os.write_cache_win(drive_letter)
                functions_os.umount_win(cur_vol_id, drive_letter)
                functions_os.mount_win(cur_vol_id, drive_letter)

            # check for the bools and generate the dumps
            os.chdir(cur_path)
            if bool_tsk:
                functions_output.dump_tsk(bool_verb, bool_tar, cur_out, cur_dev, cur_op_id, run.attrib['id'], log_file)
                os.chdir(cur_path)
            if bool_binwalk:
                functions_output.dump_binwalk(bool_verb, cur_out, cur_dev, cur_op_id, run.attrib['id'], log_file)
                os.chdir(cur_path)
            if bool_fiwalk:
                functions_output.dump_fiwalk(bool_verb, cur_out, cur_dev, cur_op_id, run.attrib['id'], log_file)
                os.chdir(cur_path)
            if bool_alloc:
                functions_output.dump_alloc(bool_verb, part_size, cur_out, cur_dev, cur_op_id, run.attrib['id'], log_file)
            if bool_nonzero:
                functions_output.dump_block_scan(bool_verb, bool_overw, bool_pattern, last_block_blkls, part_size, cur_out, cur_dev, cur_op_id, run.attrib['id'], log_file)

            # restore working directory
            os.chdir(cur_dir)

    if bool_tar:
        # init directory list
        dir_list = []
        # loop over directory to append directories with absolute paths
        for d in os.listdir(cur_out):
            tmp_d = os.path.join(cur_out, d)
            # only append existing dirs
            if not os.path.isfile(tmp_d):
                dir_list.append(tmp_d)
        # compress the output directories
        for d in dir_list:
            functions_file.make_tarfile(d)
            shutil.rmtree(d)

    cur_msg = 'execution finished for ' + os.path.basename(xml_path) + '\n'
    log_file.write(cur_msg)
    log_file.close()
    print(cur_msg)
    return True
