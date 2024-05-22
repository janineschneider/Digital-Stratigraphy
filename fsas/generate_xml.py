#!/bin/python3

# import argparse
import copy
import os
import psutil
import random
from anytree import Node, RenderTree
from lxml import etree
# own imports
import functions_file
import functions_os


# function to retrieve a list containing all ids of current nodes in anytree
def get_node_ids(anytree):
    result = []
    for pre, fill, node in RenderTree(anytree):
        result.append(node.name)
    return result


# function to retrieve the path of the given node name
def get_node_path(anytree, name):
    for pre, fill, node in RenderTree(anytree):
        if node.name == name:
            return str(node.path[-1])[6:-2]
    return '-1'


# function to retrieve the node of the given node name
def get_node(anytree, name):
    for pre, fill, node in RenderTree(anytree):
        if node.name == name:
            return node
    return Node(-7)


# function to retrieve the parent node of the given node name
def get_parent_node(anytree, name):
    for pre, fill, node in RenderTree(anytree):
        if node.name == name:
            if not node.is_root:
                return node.ancestors[-1]
    return Node(-7)


# look up the node each child node and append the names to cur_dirs_delete
def iterate_delete(anytree, tmp_dirs_delete):
    tmp_dirs_delete.append(anytree.name)
    for m in anytree.children:
        iterate_delete(m, tmp_dirs_delete)
    return tmp_dirs_delete


# get operation types
def generate_op_types(bool_dir, bool_del, bool_increase, bool_decrease, write_weight):
    # possible directory operation types, #dir_create=2 to increase the weight of dir_create
    op_dir_create = ['dir_create']
    op_dir_other = []
    if bool_del:
        op_dir_other.append('dir_delete')
    dir_op_types = write_weight * op_dir_create + op_dir_other

    # possible file operation types, #write=3 to increase the weight of write
    op_write = ['write']
    op_other = []
    if bool_del:
        op_other.append('delete')
    # if increase bool is set, add increase operation
    if bool_increase:
        op_other.append('increase')
    # if decrease bool is set, add decrease operation
    if bool_decrease:
        op_other.append('decrease')
    file_op_types = write_weight * op_write + op_other

    # check if directories should be created/deleted
    if bool_dir:
        # if working with dirs file operations should be prioritized
        op_types = write_weight * file_op_types + dir_op_types
    else:
        # otherwise we only need file operations
        op_types = file_op_types

    return [op_types, file_op_types, dir_op_types]


# calculation of the estimated usage after the operations
def calc_est_size(in_bool, in_dict, in_tree):
    if in_bool:
        file_size_est = 0
        dir_size_est = 0
        for j in in_dict.values():
            file_size_est += j[0]
        for _ in RenderTree(in_tree):
            dir_size_est += 4096
        out = file_size_est
    else:
        file_size_est = 0
        for j in in_dict.values():
            file_size_est += j
        out = file_size_est

    return out


# read xml and get data from it:
def get_from_xml(in_xml, bool_dir):
    # read input xml
    old_tree = functions_file.open_xml(in_xml)
    old_usage = old_tree.attrib['usage_estimated']

    # dictionary with all currently existing file numbers
    file_dict = {}
    file_number = 0

    # tree structure for directories
    dir_tree = Node(-1)
    dir_number = 0

    for run in old_tree:
        for op in run:
            if bool_dir:
                # write operation
                if op.attrib['type'] == 'write':
                    cur_size = int(op[0].attrib['size'])
                    cur_dir_path = op[1].attrib['path']
                    file_dict.update({file_number: [cur_size, cur_dir_path]})
                    file_number += 1
                # delete operation
                elif op.attrib['type'] == 'delete':
                    cur_value = op[0].attrib['value']
                    file_dict.pop(cur_value)
                # increase and decrease operations
                elif op.attrib['type'] == 'increase' or op.attrib['type'] == 'decrease':
                    cur_value = op[0].attrib['value']
                    cur_size = file_dict.get(cur_value)[0]
                    cur_dir_path = file_dict.get(cur_value)[1]
                    cur_diff = int(op[1].attrib['diff'])
                    if op.attrib['type'] == 'decrease':
                        cur_size -= cur_diff
                    else:
                        cur_size += cur_diff
                    file_dict.update({cur_value: [cur_size, cur_dir_path]})
                elif op.attrib['type'] == 'dir_create':
                    cur_dir_path = op[0].attrib['parent']
                    cur_dir_parent = int(os.path.basename(cur_dir_path))
                    cur_node = get_node(dir_tree, cur_dir_parent)
                    if cur_node.name == -7:
                        print('parent node does not exist')
                        print('requested node:', cur_dir_parent)
                        exit(7)
                    Node(dir_number, parent=cur_node)
                    dir_number += 1
                elif op.attrib['type'] == 'dir_delete':
                    # init lists for tmp storage of deleted (sub-)dirs and files
                    cur_files_delete = []
                    cur_dir_value = int(op.attrib['id'])

                    cur_dir_node = get_node(dir_tree, cur_dir_value)
                    if cur_dir_node.name == -7:
                        print('node does not exist')
                        print('requested node:', cur_dir_value)
                        exit(7)

                    # get all files in the directory and sub_folders
                    # search for dir name in filepath, i.e. '/1/' or '/1' (if file in dir)
                    search_str = str(cur_dir_node)[6:-2]
                    for k in file_dict:
                        if search_str in str(file_dict[k][1]):
                            cur_files_delete.append(k)
                    # remove deleted files from cur_file_dict
                    for k in cur_files_delete:
                        file_dict.pop(k)
                    # remove directory in tree, therefore set new parent node
                    cur_dir_node.parent = None
            else:
                # write operation
                if op.attrib['type'] == 'write':
                    cur_size = int(op[0].attrib['size'])
                    file_dict.update({file_number: cur_size})
                    file_number += 1
                # delete operation
                elif op.attrib['type'] == 'delete':
                    cur_value = op[0].attrib['value']
                    file_dict.pop(cur_value)
                # increase and decrease operations
                elif op.attrib['type'] == 'increase' or op.attrib['type'] == 'decrease':
                    cur_value = op[0].attrib['value']
                    cur_size = file_dict.get(cur_value)[0]
                    cur_diff = int(op[1].attrib['diff'])
                    if op.attrib['type'] == 'decrease':
                        cur_size -= cur_diff
                    else:
                        cur_size += cur_diff
                    file_dict.update({cur_value: cur_size})

    return file_dict, dir_tree, old_usage


# generate xml with input xml (delete only)
def generate_from_input(in_xml, bool_dir, dev_path, op_vals):
    # check paths
    functions_os.check_path(in_xml)
    functions_os.check_path(dev_path)
    functions_os.check_mount_point(dev_path)

    file_dict, dir_tree, old_usage = get_from_xml(in_xml, bool_dir)

    old_tree = functions_file.open_xml(in_xml)
    # old_usage = old_tree.attrib['usage_estimated']

    # get the free space in bytes of the device
    disk_usage = psutil.disk_usage(dev_path)
    # used_bytes = disk_usage.used
    free_bytes = disk_usage.free
    total_bytes = disk_usage.total
    free_gib = round(disk_usage.free / (1024 ** 3), 1)

    # safety guard of the free bytes (subtract two sectors)
    free_bytes -= 2 * 4096

    # init xml tree generation (currently only run 0)
    xml_tree = etree.Element('device', path=dev_path)
    xml_tree.set('size_gib', str(free_gib))
    cur_run = etree.SubElement(xml_tree, 'run', id='0')

    # get a random number of operations
    operations = random.randint(op_vals[0], op_vals[1])

    # get possible types
    file_op_types = ['delete']
    dir_op_types = []
    if bool_dir:
        dir_op_types.append('dir_delete')
    op_types = 3 * file_op_types + dir_op_types

    # init counter
    dir_number = 0
    file_number = 0

    # loop over the number of operations
    for i in range(operations):
        # append operation in xml tree
        cur_op = etree.SubElement(cur_run, 'operation', id=str(i))

        # generate current type
        cur_type = random.choice(op_types)

        # creating a do while loop to check, if the free space of the device is enough to execute the operation
        while True:
            if bool_dir:
                # init a working copy of the file_dict and a copy of the file_number
                cur_file_dict = file_dict.copy()
                cur_file_number = file_number

                # init dictionary to store the attributes of a file/dir tag
                cur_file_attr = {}
                cur_dir_attr = {}

                # init a working copy of the dir_tree and a copy of the dir_number
                cur_dir_tree = copy.deepcopy(dir_tree)
                cur_dir_number = dir_number
                cur_dir_ids = get_node_ids(cur_dir_tree)

                # check operation type for the tag attributes

                if cur_type == 'delete':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_file_attr.update({'value': cur_value})
                    cur_dir_path = cur_file_dict.get(cur_value)[1]
                    cur_file_attr.update({'path': cur_dir_path})
                    cur_file_dict.pop(cur_value)
                elif cur_type == 'dir_delete':
                    # init lists for tmp storage of deleted (sub-)dirs and files
                    cur_files_delete = []
                    if cur_dir_ids == [-1]:
                        cur_type = random.choice(op_types)
                        continue
                    cur_dir_value = random.choice(cur_dir_ids)
                    # folder ids lower 0 are not allowed (root dir = -1)
                    while cur_dir_value < 0:
                        cur_dir_value = random.choice(cur_dir_ids)
                    # get parent node of node which should be deleted
                    cur_dir_parent = get_parent_node(cur_dir_tree, cur_dir_value)
                    if cur_dir_parent.name == -7:
                        print('parent node does not exist')
                        print('requested node:', cur_dir_value)
                        exit(7)
                    # get node which should be deleted
                    cur_dir_node = get_node(cur_dir_tree, cur_dir_value)
                    if cur_dir_node.name == -7:
                        print('node does not exist')
                        print('requested node:', cur_dir_value)
                        exit(7)
                    # store the id of the dir which should be deleted
                    cur_dir_attr.update({'id': cur_dir_value})
                    # store the path of the dir
                    cur_dir_path = get_node_path(cur_dir_tree, cur_dir_parent.name)
                    cur_dir_attr.update({'path': cur_dir_path})

                    # get all files in the directory and sub_folders
                    # search for dir name in filepath, i.e. '/1/' or '/1' (if file in dir)
                    search_str = str(cur_dir_node)[6:-2]
                    for k in cur_file_dict:
                        if search_str in str(cur_file_dict[k][1]):
                            cur_files_delete.append(k)
                    # remove deleted files from cur_file_dict
                    for k in cur_files_delete:
                        cur_file_dict.pop(k)
                    # remove directory in tree, therefore set new parent node
                    cur_dir_node.parent = None

                # condition check of the do while loop
                # calculate the overall file size & dir size of all files/dirs
                comb_file_size = 0
                comb_dir_size = 0
                for j in cur_file_dict.values():
                    comb_file_size += j[0]
                for _ in RenderTree(cur_dir_tree):
                    comb_dir_size += 4096
                comb_size = comb_dir_size + comb_file_size
                # check if the populated size of the files would fit on the disk
                if comb_size > 0 and cur_file_dict and cur_dir_ids:
                    # sets the type of the current operation
                    cur_op.set('type', cur_type)

                    # loop over the file attributes and add them to the xml tag
                    for k in cur_file_attr:
                        # insert the file tag in the xml tree
                        cur_file = etree.SubElement(cur_op, 'file')
                        cur_file.set(str(k), str(cur_file_attr.get(k)))

                    # loop over the dir attributes and add them to the xml tag
                    for k in cur_dir_attr:
                        # insert the file tag in the xml tree
                        cur_dir = etree.SubElement(cur_op, 'dir')
                        cur_dir.set(str(k), str(cur_dir_attr.get(k)))

                    # set the new values after the loop ended
                    file_dict = cur_file_dict.copy()
                    file_number = cur_file_number
                    dir_tree = copy.deepcopy(cur_dir_tree)
                    dir_number = cur_dir_number
                    # exit the loop
                    break
                else:
                    # case the condition isn't true -> back to loop
                    # set new operation type and run the loop again
                    return b'estimated_usage=1'
            else:
                # init a working copy of the file_dict and a copy of the file_number
                cur_file_dict = file_dict.copy()
                cur_file_number = file_number

                # init dictionary to store the attributes of a file/dir tag
                cur_file_attr = {}

                # check operation type for the tag attributes
                if cur_type == 'delete':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_file_attr.update({'value': cur_value})
                    cur_file_dict.pop(cur_value)

                # condition check of the do while loop
                # calculate the overall file size of all files
                comb_file_size = 0
                for j in cur_file_dict.values():
                    comb_file_size += j
                # check if the populated size of the files would fit on the disk
                if comb_file_size > 0:
                    # sets the type of the current operation
                    cur_op.set('type', cur_type)

                    # loop over the attributes and add them to the xml tag
                    for k in cur_file_attr:
                        # insert the file tag in the xml tree
                        cur_file = etree.SubElement(cur_op, 'file')
                        cur_file.set(str(k), str(cur_file_attr.get(k)))

                    # set the new values after the loop ended
                    file_dict = cur_file_dict.copy()
                    file_number = cur_file_number
                    # exit the loop
                    break
                else:
                    # case the condition isn't true -> back to loop
                    # set new operation type and run the loop again
                    cur_type = random.choice(op_types)

    # calc the estimated file system usage
    est_size = calc_est_size(bool_dir, file_dict, dir_tree)
    usage_est = total_bytes - free_bytes + est_size

    # calc estimated usage in percent and write to device tag
    usage_est_percent = round(100 * usage_est / total_bytes, 1)
    xml_tree.set('usage_estimated', str(usage_est_percent))

    # generate bytestring of the xml tree
    xml_bytes = etree.tostring(xml_tree, pretty_print=True)

    return xml_bytes


# define xml with only write operations
def generate_write_only(bool_dir, bool_del, dev_path, create_vals, op_vals):
    # check if given device path exists, is absolute and is mount point
    functions_os.check_path(dev_path)
    functions_os.check_mount_point(dev_path)

    # get the free space in bytes of the device
    disk_usage = psutil.disk_usage(dev_path)
    # used_bytes = disk_usage.used
    free_bytes = disk_usage.free
    total_bytes = disk_usage.total
    free_gib = round(disk_usage.free / (1024 ** 3), 1)

    # safety guard of the free bytes (subtract two sectors)
    free_bytes -= 2 * 4096

    # dictionary with all currently existing file numbers
    file_dict = {}
    file_number = 0

    # tree structure for directories
    dir_tree = Node(-1)
    dir_number = 0

    # init xml tree generation (currently only run 0)
    xml_tree = etree.Element('device', path=dev_path)
    xml_tree.set('size_gib', str(free_gib))
    cur_run = etree.SubElement(xml_tree, 'run', id='0')

    # get a random number of operations
    operations = random.randint(op_vals[0], op_vals[1])

    file_op_types = ['write']
    dir_op_types = ['dir_create']
    op_types = 3 * file_op_types + dir_op_types

    # loop over the number of operations
    for i in range(operations):
        # append operation in xml tree
        cur_op = etree.SubElement(cur_run, 'operation', id=str(i))

        # generate current type
        cur_type = random.choice(op_types)

        # creating a do while loop to check, if the free space of the device is enough to execute the operation
        while True:
            if bool_dir:
                # init a working copy of the file_dict and a copy of the file_number
                cur_file_dict = file_dict.copy()
                cur_file_number = file_number

                # init dictionary to store the attributes of a file/dir tag
                cur_file_attr = {}
                cur_dir_attr = {}

                # init a working copy of the dir_tree and a copy of the dir_number
                cur_dir_tree = copy.deepcopy(dir_tree)
                cur_dir_number = dir_number
                cur_dir_ids = get_node_ids(cur_dir_tree)

                # check operation type for the tag attributes
                if cur_type == 'write':
                    cur_size = random.randint(create_vals[0], create_vals[1])
                    cur_file_attr.update({'size': cur_size})
                    tmp_dir_number = random.choice(cur_dir_ids)
                    cur_dir_path = get_node_path(cur_dir_tree, tmp_dir_number)
                    cur_file_attr.update({'path': cur_dir_path})
                    cur_file_dict.update({file_number: [cur_size, cur_dir_path]})
                    cur_file_number += 1
                elif cur_type == 'dir_create':
                    cur_dir_parent = random.choice(cur_dir_ids)
                    cur_node = get_node(cur_dir_tree, cur_dir_parent)
                    if cur_node.name == -7:
                        print('parent node does not exist')
                        print('requested node:', cur_dir_parent)
                        exit(7)
                    cur_parent_path = get_node_path(cur_dir_tree, cur_node.name)
                    cur_dir_attr.update({'parent': cur_parent_path})
                    Node(cur_dir_number, parent=cur_node)
                    cur_dir_number += 1

                # condition check of the do while loop
                # calculate the overall file size & dir size of all files/dirs
                comb_file_size = 0
                comb_dir_size = 0
                for j in cur_file_dict.values():
                    comb_file_size += j[0]
                for _ in RenderTree(cur_dir_tree):
                    comb_dir_size += 4096
                comb_size = comb_dir_size + comb_file_size
                # check if the populated size of the files would fit on the disk
                if comb_size < free_bytes:
                    # sets the type of the current operation
                    cur_op.set('type', cur_type)

                    # loop over the file attributes and add them to the xml tag
                    for k in cur_file_attr:
                        # insert the file tag in the xml tree
                        cur_file = etree.SubElement(cur_op, 'file')
                        cur_file.set(str(k), str(cur_file_attr.get(k)))

                    # loop over the dir attributes and add them to the xml tag
                    for k in cur_dir_attr:
                        # insert the file tag in the xml tree
                        cur_dir = etree.SubElement(cur_op, 'dir')
                        cur_dir.set(str(k), str(cur_dir_attr.get(k)))

                    # set the new values after the loop ended
                    file_dict = cur_file_dict.copy()
                    file_number = cur_file_number
                    dir_tree = copy.deepcopy(cur_dir_tree)
                    dir_number = cur_dir_number
                    # exit the loop
                    break
                else:
                    # case the condition isn't true -> back to loop
                    # set new operation type and run the loop again
                    cur_type = random.choice(op_types)
            else:
                # init a working copy of the file_dict and a copy of the file_number
                cur_file_dict = file_dict.copy()
                cur_file_number = file_number

                # init dictionary to store the attributes of a file/dir tag
                cur_file_attr = {}

                # check operation type for the tag attributes
                if cur_type == 'write':
                    cur_size = random.randint(create_vals[0], create_vals[1])
                    cur_file_attr.update({'size': cur_size})
                    cur_file_dict.update({file_number: cur_size})
                    cur_file_number += 1

                # condition check of the do while loop
                # calculate the overall file size of all files
                comb_file_size = 0
                for j in cur_file_dict.values():
                    comb_file_size += j
                # check if the populated size of the files would fit on the disk
                if comb_file_size < free_bytes:
                    # sets the type of the current operation
                    cur_op.set('type', cur_type)

                    # loop over the attributes and add them to the xml tag
                    for k in cur_file_attr:
                        # insert the file tag in the xml tree
                        cur_file = etree.SubElement(cur_op, 'file')
                        cur_file.set(str(k), str(cur_file_attr.get(k)))

                    # set the new values after the loop ended
                    file_dict = cur_file_dict.copy()
                    file_number = cur_file_number
                    # exit the loop
                    break
                else:
                    # case the condition isn't true -> back to loop
                    # set new operation type and run the loop again
                    cur_type = random.choice(op_types)

    # calc the estimated file system usage
    est_size = calc_est_size(bool_dir, file_dict, dir_tree)
    usage_est = total_bytes - free_bytes + est_size

    # calc estimated usage in percent and write to device tag
    usage_est_percent = round(100 * usage_est / total_bytes, 1)
    xml_tree.set('usage_estimated', str(usage_est_percent))

    # generate bytestring of the xml tree
    xml_bytes = etree.tostring(xml_tree, pretty_print=True)

    # print the bytestring
    print(xml_bytes)

    return xml_bytes


# define the main generate function
def generate(bool_dir, bool_del, write_weight, dev_path, create_vals, increase_vals, decrease_vals, op_vals, in_perc):
    # check if given device path exists, is absolute and is mount point
    functions_os.check_path(dev_path)
    functions_os.check_mount_point(dev_path)

    # if min and max for increase are 0 -> set bool to false
    bool_increase = True
    if increase_vals[0] == 0 and increase_vals[1] == 0:
        bool_increase = False

    # if min and max for increase are 0 -> set bool to false
    bool_decrease = True
    if decrease_vals[0] == 0 and decrease_vals[1] == 0:
        bool_decrease = False

    # get the free space in bytes of the device
    disk_usage = psutil.disk_usage(dev_path)
    used_bytes = disk_usage.used
    free_bytes = disk_usage.free
    total_bytes = disk_usage.total
    free_gib = round(disk_usage.free / (1024 ** 3), 1)

    # safety guard of the free bytes (subtract two sectors)
    free_bytes -= 2 * 4096

    # dictionary with all currently existing file numbers
    file_dict = {}
    file_number = 0

    # tree structure for directories
    dir_tree = Node(-1)
    dir_number = 0

    # init xml tree generation (currently only run 0)
    xml_tree = etree.Element('device', path=dev_path)
    xml_tree.set('size_gib', str(free_gib))
    cur_run = etree.SubElement(xml_tree, 'run', id='0')

    # get a random number of operations
    operations = random.randint(op_vals[0], op_vals[1])

    in_op_types = generate_op_types(bool_dir, bool_del, bool_increase, bool_decrease, write_weight)

    op_types = in_op_types[0]
    file_op_types = in_op_types[1]
    dir_op_types = in_op_types[2]

    # loop over the number of operations
    for i in range(operations):
        # append operation in xml tree
        cur_op = etree.SubElement(cur_run, 'operation', id=str(i))

        # generate current type
        cur_type = random.choice(op_types)

        # if there are no files, only a write operation is allowed for files
        # and if there are no directories, only a dir_create operation is allowed for dirs
        while True:
            if not file_dict and cur_type in file_op_types and cur_type != 'write':
                cur_type = random.choice(op_types)
            elif not dir_tree.children and cur_type in dir_op_types and cur_type != 'dir_create':
                cur_type = random.choice(op_types)
            else:
                break

        # creating a do while loop to check, if the free space of the device is enough to execute the operation
        while True:
            if bool_dir:
                # init a working copy of the file_dict and a copy of the file_number
                cur_file_dict = file_dict.copy()
                cur_file_number = file_number

                # init dictionary to store the attributes of a file/dir tag
                cur_file_attr = {}
                cur_dir_attr = {}

                # init a working copy of the dir_tree and a copy of the dir_number
                cur_dir_tree = copy.deepcopy(dir_tree)
                cur_dir_number = dir_number
                cur_dir_ids = get_node_ids(cur_dir_tree)

                # check operation type for the tag attributes
                if cur_type == 'write':
                    cur_size = random.randint(create_vals[0], create_vals[1])
                    cur_file_attr.update({'size': cur_size})
                    tmp_dir_number = random.choice(cur_dir_ids)
                    cur_dir_path = get_node_path(cur_dir_tree, tmp_dir_number)
                    cur_file_attr.update({'path': cur_dir_path})
                    cur_file_dict.update({file_number: [cur_size, cur_dir_path]})
                    cur_file_number += 1
                elif cur_type == 'delete':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_file_attr.update({'value': cur_value})
                    cur_dir_path = cur_file_dict.get(cur_value)[1]
                    cur_file_attr.update({'path': cur_dir_path})
                    cur_file_dict.pop(cur_value)
                elif cur_type == 'increase':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_size = cur_file_dict.get(cur_value)[0]
                    cur_dir_path = cur_file_dict.get(cur_value)[1]
                    cur_diff = random.randint(increase_vals[0], increase_vals[1])
                    cur_size += cur_diff
                    cur_file_attr.update({'value': cur_value})
                    cur_file_attr.update({'diff': cur_diff})
                    cur_file_attr.update({'path': cur_dir_path})
                    cur_file_dict.update({cur_value: [cur_size, cur_dir_path]})
                elif cur_type == 'decrease':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_size = cur_file_dict.get(cur_value)[0]
                    cur_dir_path = cur_file_dict.get(cur_value)[1]
                    cur_diff = random.randint(decrease_vals[0], decrease_vals[1])
                    while cur_size - cur_diff <= 0:
                        cur_diff = random.randint(decrease_vals[0], decrease_vals[1])
                    cur_size -= cur_diff
                    cur_file_attr.update({'value': cur_value})
                    cur_file_attr.update({'diff': cur_diff})
                    cur_file_attr.update({'path': cur_dir_path})
                    cur_file_dict.update({cur_value: [cur_size, cur_dir_path]})
                elif cur_type == 'dir_create':
                    cur_dir_parent = random.choice(cur_dir_ids)
                    cur_node = get_node(cur_dir_tree, cur_dir_parent)
                    if cur_node.name == -7:
                        print('parent node does not exist')
                        print('requested node:', cur_dir_parent)
                        exit(7)
                    cur_parent_path = get_node_path(cur_dir_tree, cur_node.name)
                    cur_dir_attr.update({'parent': cur_parent_path})
                    Node(cur_dir_number, parent=cur_node)
                    cur_dir_number += 1
                elif cur_type == 'dir_delete':
                    # init lists for tmp storage of deleted (sub-)dirs and files
                    cur_files_delete = []
                    cur_dir_value = random.choice(cur_dir_ids)
                    # folder ids lower 0 are not allowed (root dir = -1)
                    while cur_dir_value < 0:
                        cur_dir_value = random.choice(cur_dir_ids)
                    # get parent node of node which should be deleted
                    cur_dir_parent = get_parent_node(cur_dir_tree, cur_dir_value)
                    if cur_dir_parent.name == -7:
                        print('parent node does not exist')
                        print('requested node:', cur_dir_value)
                        exit(7)
                    # get node which should be deleted
                    cur_dir_node = get_node(cur_dir_tree, cur_dir_value)
                    if cur_dir_node.name == -7:
                        print('node does not exist')
                        print('requested node:', cur_dir_value)
                        exit(7)
                    # store the id of the dir which should be deleted
                    cur_dir_attr.update({'id': cur_dir_value})
                    # store the path of the dir
                    cur_dir_path = get_node_path(cur_dir_tree, cur_dir_parent.name)
                    cur_dir_attr.update({'path': cur_dir_path})

                    # # only necessary for logging every deleted file/dir
                    # # get all ids of deleted dirs and store them in a list
                    # cur_dirs_delete = iterate_delete(cur_dir_node, [])
                    # for k in cur_dirs_delete:
                    #     cur_dir_attr.update({'id_' + str(cur_dirs_delete.index(k)): str(k)})

                    # get all files in the directory and sub_folders
                    # search for dir name in filepath, i.e. '/1/' or '/1' (if file in dir)
                    search_str = str(cur_dir_node)[6:-2]
                    for k in cur_file_dict:
                        if search_str in str(cur_file_dict[k][1]):
                            cur_files_delete.append(k)
                    # remove deleted files from cur_file_dict
                    for k in cur_files_delete:
                        cur_file_dict.pop(k)
                    # remove directory in tree, therefore set new parent node
                    cur_dir_node.parent = None

                # condition check of the do while loop
                # calculate the overall file size & dir size of all files/dirs
                est_size = calc_est_size(bool_dir, cur_file_dict, cur_dir_tree)

                # check if the populated size of the files would fit on the disk
                if est_size < free_bytes:
                    # sets the type of the current operation
                    cur_op.set('type', cur_type)

                    # loop over the file attributes and add them to the xml tag
                    for k in cur_file_attr:
                        # insert the file tag in the xml tree
                        cur_file = etree.SubElement(cur_op, 'file')
                        cur_file.set(str(k), str(cur_file_attr.get(k)))

                    # loop over the dir attributes and add them to the xml tag
                    for k in cur_dir_attr:
                        # insert the file tag in the xml tree
                        cur_dir = etree.SubElement(cur_op, 'dir')
                        cur_dir.set(str(k), str(cur_dir_attr.get(k)))

                    # set the new values after the loop ended
                    file_dict = cur_file_dict.copy()
                    file_number = cur_file_number
                    dir_tree = copy.deepcopy(cur_dir_tree)
                    dir_number = cur_dir_number
                    # exit the loop
                    break
                else:
                    # case the condition isn't true -> back to loop
                    # set new operation type and run the loop again
                    cur_type = random.choice(op_types)
            else:
                # init a working copy of the file_dict and a copy of the file_number
                cur_file_dict = file_dict.copy()
                cur_file_number = file_number

                # init dictionary to store the attributes of a file/dir tag
                cur_file_attr = {}

                # check operation type for the tag attributes
                if cur_type == 'write':
                    cur_size = random.randint(create_vals[0], create_vals[1])
                    cur_file_attr.update({'size': cur_size})
                    cur_file_dict.update({file_number: cur_size})
                    cur_file_number += 1
                elif cur_type == 'delete':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_file_attr.update({'value': cur_value})
                    cur_file_dict.pop(cur_value)
                elif cur_type == 'increase':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_size = cur_file_dict.get(cur_value)
                    cur_diff = random.randint(increase_vals[0], increase_vals[1])
                    cur_size += cur_diff
                    cur_file_attr.update({'value': cur_value})
                    cur_file_attr.update({'diff': cur_diff})
                    cur_file_dict.update({cur_value: cur_size})
                elif cur_type == 'decrease':
                    cur_value = random.choice(list(cur_file_dict.keys()))
                    cur_size = cur_file_dict.get(cur_value)
                    cur_diff = random.randint(decrease_vals[0], decrease_vals[1])
                    while cur_size - cur_diff <= 0:
                        cur_diff = random.randint(decrease_vals[0], decrease_vals[1])
                    cur_size -= cur_diff
                    cur_file_attr.update({'value': cur_value})
                    cur_file_attr.update({'diff': cur_diff})
                    cur_file_dict.update({cur_value: cur_size})

                # condition check of the do while loop
                # calculate the overall file size of all files
                est_size = calc_est_size(bool_dir, cur_file_dict, Node(-1))

                # check if the populated size of the files would fit on the disk
                if est_size < free_bytes:
                    # sets the type of the current operation
                    cur_op.set('type', cur_type)

                    # loop over the attributes and add them to the xml tag
                    for k in cur_file_attr:
                        # insert the file tag in the xml tree
                        cur_file = etree.SubElement(cur_op, 'file')
                        cur_file.set(str(k), str(cur_file_attr.get(k)))

                    # set the new values after the loop ended
                    file_dict = cur_file_dict.copy()
                    file_number = cur_file_number
                    # exit the loop
                    break
                else:
                    # case the condition isn't true -> back to loop
                    # set new operation type and run the loop again
                    cur_type = random.choice(op_types)

        # calc the estimated file system usage and if usage is in range of percentage break
        est_size = calc_est_size(bool_dir, file_dict, dir_tree)
        usage_est = used_bytes + est_size
        usage_est_percent = round(100 * usage_est / total_bytes, 1)
        if in_perc > 0 and in_perc - 3 < usage_est_percent < in_perc + 3:
            break

    # calc the estimated file system usage
    est_size = calc_est_size(bool_dir, file_dict, dir_tree)
    usage_est = used_bytes + est_size

    # calc estimated usage in percent and write to device tag
    usage_est_percent = round(100 * usage_est / total_bytes, 1)
    xml_tree.set('usage_estimated', str(usage_est_percent))

    # generate bytestring of the xml tree
    xml_bytes = etree.tostring(xml_tree, pretty_print=True)

    # print the bytestring
    print(xml_bytes)

    return xml_bytes
