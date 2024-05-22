#!/bin/python3

# import argparse
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
from operator import add
import pandas as pd
import re
import time
# own imports
import functions_file
import functions_os


# function to get the file content of one file
def get_file_content(file_name: str) -> tuple[list, int, int]:
    # open alloc or entropy file and read content
    with open(file_name, 'rb') as f:
        content = f.readlines()

    # store content of file in temporary array t, elements: ([block], value)
    r = []
    last_block = 0
    last_block_nonzero = 0
    for i in content:
        tmp_line = i.decode('utf-8').replace('\r\n', '').split('|')
        if i == content[-1]:
            last_block = int(tmp_line[0])
        if not tmp_line[1] == '0':
            last_block_nonzero = int(tmp_line[0])
        r.append(([tmp_line[0]], tmp_line[1]))

    return r, last_block, last_block_nonzero


# function to get the bar for one file
def get_bar_one(file_name: str) -> (list, int):
    # call get file content function
    file_content = get_file_content(file_name)
    t = file_content[0]

    # loop over the created temporary array to get the result array r
    # elements of r should look like: [height, value]
    counter = 0
    r = []
    sum_per = 0
    while counter < len(t):
        # if not last element get the block difference of two entries
        if not t[counter] == t[-1]:
            tmp_height_block = int(t[counter + 1][0][0]) + 1 - int(t[counter][0][0])
            tmp_height = 100 * tmp_height_block / file_content[1]
            sum_per += tmp_height
            r.append([tmp_height, t[counter][1]])
        else:
            tmp_height_block = int(t[counter][0][0]) - int(t[counter - 1][0][0])
            tmp_height = 100 * tmp_height_block / file_content[1]
            sum_per += tmp_height
            r.append([tmp_height, t[counter][1]])
        counter += 2

    max_block_nonzero = round(100 * file_content[2] / file_content[1])
    return r, max_block_nonzero


# function to get the bars for all file
def get_bar_all(files: list) -> (list, int):
    # fill the input list with the generated bars from get_bar_one
    bars_in = []
    max_in = []
    for i in files:
        tmp_in = get_bar_one(i)
        bars_in.append(tmp_in[0])
        max_in.append(tmp_in[1])

    # get a list with the length of generated bars
    bars_l = []
    for i in bars_in:
        bars_l.append(len(i))

    # check length of the longest input bar and get the index
    # for multiple bars with the max length get all indices
    tmp_length = []
    max_length = max(bars_l)
    counter = 0
    for i in bars_l:
        if i == max_length:
            tmp_length.append(counter)
        counter += 1

    # set the index of the longest bar to the first index
    index_max_bar = tmp_length[0]

    # if there are multiple longest bars check,
    # if they start with the same value,
    # if not append the first longest bar with that value and height 0
    if len(tmp_length) > 1:
        for i in tmp_length:
            if not bars_in[i][0][1] == bars_in[index_max_bar][0][1]:
                if not bars_in[i][0][1] == bars_in[index_max_bar][-1][1]:
                    bars_in[index_max_bar].append([0, bars_in[i][0][1]])
                else:
                    bars_in[index_max_bar].append([0, bars_in[index_max_bar][0][1]])
                break

    # preparation of the bars out array
    # should look like: [[[23, 45, 67, 23, ...], 1], [[...], 0], ...]
    # after preparation: [[[]], [[]], [[]], ...]
    bars_out = []
    counter = 0
    while counter < len(bars_in[index_max_bar]):
        bars_out.append([[]])
        counter += 1

    # loop over first longest bar
    counter_outer = 0
    while bars_in[index_max_bar]:
        # get the first element and append it's value
        tmp_outer = bars_in[index_max_bar].pop(0)  # type: list
        bars_out[counter_outer].append(tmp_outer[1])
        counter_inner = 0
        # loop over all bars and check their first elements
        while counter_inner < len(bars_in):
            cur_bar = bars_in[counter_inner]
            # if current bar is outer bar, don't pop just add
            if counter_inner == index_max_bar:
                bars_out[counter_outer][0].append(tmp_outer[0])
            # if the current bar array has no elements with index counter_outer:
            # add height 0 for this bar
            elif not cur_bar:
                bars_out[counter_outer][0].append(0)
            # else pop first element
            else:
                tmp_inner = cur_bar.pop(0)
                # check if value for first element is same value as outer
                if tmp_inner[1] == tmp_outer[1]:
                    bars_out[counter_outer][0].append(tmp_inner[0])
                else:
                    # insert the deleted element at beginning of list
                    cur_bar.insert(0, tmp_inner)
                    bars_out[counter_outer][0].append(0)
            counter_inner += 1
        counter_outer += 1

    return bars_out, max(max_in)


# function to form arrays with x and y values for the file content
def get_arrays_one(file_name: str) -> tuple[list, list, list]:
    file_content = get_file_content(file_name)
    t = file_content[0]
    x = [[], [], [], [], []]
    y = [[], [], [], [], []]
    cur_y = int(re.search(r'\d+', os.path.basename(file_name))[0])

    for i in range(len(t)):
        cur_state = int(t[i][1])
        if cur_state == 0:
            continue
        # x[0] is reserved for allocation state 1 => for nonzero files +1
        if 'nonzero' in file_name:
            cur_state += 1
        elif 'pattern' in file_name:
            cur_state += 4
        if t[i] == t[-1]:
            x[cur_state - 1].append(int(t[i][0][0]))
            y[cur_state - 1].append(cur_y)
            break

        for j in range(int(t[i][0][0]), int(t[i + 1][0][0])):
            x[cur_state - 1].append(j)
            y[cur_state - 1].append(cur_y)

    return x, y, [int(file_content[1]), cur_y]


# function to form arrays with x and y values for the file content
def get_csv_all(files: list) -> tuple[list, list, list]:
    x_out = []
    y_out = []
    max_block_out = 0
    max_op_no = 0

    old_df = pd.DataFrame({})

    for f in files:
        if 'nonzero_000' in os.path.basename(f) or 'pattern_000' in os.path.basename(f):
            old_df = pd.DataFrame({})
        x = [[], [], [], [], []]
        y = [[], [], [], [], []]

        cur_y = int(re.search(r'\d+', os.path.basename(f))[0])
        if cur_y > max_op_no:
            max_op_no = cur_y
        cur_df = pd.read_csv(f)
        if cur_y == 0:
            for i in range(len(cur_df['SummarizedStatus'])):
                states = ['1', '2', '3']
                for s in states:
                    if s in cur_df['SummarizedStatus'][i]:
                        if 'alloc' in os.path.basename(f):
                            x[0].append(i)
                            y[0].append(cur_y)
                        elif 'pattern' in os.path.basename(f):
                            x[4].append(i)
                            y[4].append(cur_y)
                        else:
                            x[int(s)].append(i)
                            y[int(s)].append(cur_y)
        else:
            for i in range(len(cur_df['SummarizedStatus'])):
                if i > len(old_df['SummarizedStatus']) - 1:
                    states = ['1', '2', '3']
                    for s in states:
                        if s in cur_df['SummarizedStatus'][i]:
                            if 'alloc' in os.path.basename(f):
                                x[0].append(i)
                                y[0].append(cur_y)
                            elif 'pattern' in os.path.basename(f):
                                x[4].append(i)
                                y[4].append(cur_y)
                            else:
                                x[int(s)].append(i)
                                y[int(s)].append(cur_y)
                elif not cur_df['SummarizedStatus'][i] == old_df['SummarizedStatus'][i]:
                    states = ['1', '2', '3']
                    for s in states:
                        if not cur_df['SummarizedStatus'][i].count(s) == old_df['SummarizedStatus'][i].count(s):
                            if 'alloc' in os.path.basename(f):
                                x[0].append(i)
                                y[0].append(cur_y)
                            elif 'pattern' in os.path.basename(f):
                                x[4].append(i)
                                y[4].append(cur_y)
                            else:
                                x[int(s)].append(i)
                                y[int(s)].append(cur_y)

        old_df = cur_df
        x_out.append(x)
        y_out.append(y)
        if len(cur_df['SummarizedStatus']) - 1 > max_block_out:
            max_block_out = len(cur_df['SummarizedStatus']) - 1

    return x_out, y_out, [max_block_out, max_op_no]


# function to get the arrays of multiple files
def get_arrays_all(files: list) -> tuple[list, list, list]:
    # fill the input list with the generated bars from get_bar_one
    x_in = []
    y_in = []
    max_block_no = 0
    max_op_no = 0

    for i in files:
        tmp_in = get_arrays_one(i)
        x_in.append(tmp_in[0])
        y_in.append(tmp_in[1])
        if tmp_in[2][0] > max_block_no:
            max_block_no = tmp_in[2][0]
        if tmp_in[2][1] > max_op_no:
            max_op_no = tmp_in[2][1]

    return x_in, y_in, [max_block_no, max_op_no]


# helper function for plotting one bar
def prepare_helper_bars_one(files: list):
    bars, max_block = get_bar_all(files)

    # prepare helper structs
    tmp = len(bars[0][0])
    height_bars = []
    br = []
    for i in range(tmp):
        height_bars.append(0)
        br.append(i)

    return bars, height_bars, br, max_block


# adjust max found percentage to give a nice axis limit
def adjust_max(in_val: int) -> int:
    if in_val >= 95 or in_val <= 15:
        out_val = in_val + 10
    elif in_val >= 80:
        out_val = 100
    else:
        out_val = in_val + 20

    return out_val


# plot bars with one input path
def plot_bars_one(bool_h: bool, in_switch: int, files: list, ax, in_color: list) -> float:
    bar_width = 1.0

    bars, height_bars, br, max_val = prepare_helper_bars_one(files)

    # create the bars for the data set
    for i in bars:
        if in_switch == 0:
            if i[1] == '1':
                if bool_h:
                    ax.barh(br, i[0], height=bar_width, left=height_bars, color=in_color[0])
                else:
                    ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=in_color[0])
            elif i[1] == '2' and 'overw' in files[0]:
                if bool_h:
                    ax.barh(br, i[0], height=bar_width, left=height_bars, color=in_color[2])
                else:
                    ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=in_color[2])
            elif i[1] == '2' or i[1] == '3':
                if bool_h:
                    ax.barh(br, i[0], height=bar_width, left=height_bars, color=in_color[1])
                else:
                    ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=in_color[1])
            if not i == bars[-1]:
                height_bars = list(map(add, height_bars, i[0]))
        else:
            if i[1] == str(in_switch):
                if bool_h:
                    ax.barh(br, i[0], height=bar_width, left=height_bars, color=in_color[0])
                else:
                    ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=in_color[0])
            if not i == bars[-1]:
                height_bars = list(map(add, height_bars, i[0]))

    return adjust_max(max_val)


# plot scatter plot with one input path
def plot_scatter_one(bool_h: bool, bool_csv, in_switch: int, files: list, ax, in_color: list) -> (int, int):
    if bool_csv:
        x_in, y_in, max_limits = get_csv_all(files)
    else:
        x_in, y_in, max_limits = get_arrays_all(files)

    if in_switch == 3:
        tmp_switch = 4
    else:
        tmp_switch = in_switch

    for i in range(len(x_in)):
        for j in range(len(x_in[i])):
            if j == tmp_switch:
                if bool_h:
                    ax.scatter(x=x_in[i][j], y=y_in[i][j], color=in_color[0], marker='s')
                else:
                    ax.scatter(x=y_in[i][j], y=x_in[i][j], color=in_color[0], marker='s')

    return max_limits


# plot bars with two input paths and horizontal bars
def plot_bars_two(files: list, ax, in_color: list) -> float:
    bar_width = 1.0

    data = [prepare_helper_bars_one(files[1]), prepare_helper_bars_one(files[0])]

    color_list = [in_color[1], in_color[0]]

    output = []
    for j in range(2):
        bars, height_bars, br, max_val = data[j]

        # create the bars for the data set
        for i in bars:
            if i[1] == '1':
                ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=color_list[j])
            elif i[1] == '2' and 'overw' in files[0][0]:
                ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=in_color[3])
            elif i[1] == '2' or i[1] == '3':
                ax.bar(br, i[0], width=bar_width, bottom=height_bars, color=in_color[2])
            if not i == bars[-1]:
                height_bars = list(map(add, height_bars, i[0]))

        output.append(max_val)

    return adjust_max(max(output))


# plot bars with two input paths and horizontal bars
def plot_bars_two_h(files: list, ax, in_color: list) -> float:
    bar_height = 1.0

    color_list = [in_color[1], in_color[0]]

    data = [prepare_helper_bars_one(files[1]), prepare_helper_bars_one(files[0])]

    output = []
    for j in range(2):
        bars, length_bars, br, max_val = data[j]

        # create the bars for the data set
        for i in bars:
            if i[1] == '1':
                ax.barh(br, i[0], height=bar_height, left=length_bars, color=color_list[j])
            elif i[1] == '2' and 'overw' in files[0][0]:
                ax.barh(br, i[0], height=bar_height, left=length_bars, color=in_color[3])
            elif i[1] == '2' or i[1] == '3':
                ax.barh(br, i[0], height=bar_height, left=length_bars, color=in_color[2])
            if not i == bars[-1]:
                length_bars = list(map(add, length_bars, i[0]))

        output.append(max_val)

    return adjust_max(max(output))


# helper function to generate the plot title from given output file name
def get_plot_title(out_name: str) -> str:
    fs_size = out_name[:out_name.find('gb_')]
    percentage = out_name[out_name.find('p_') - 2:out_name.find('p_')]
    out_title = ''

    # add information to title and set labels
    out_title += ' - ' + fs_size + 'GB'
    out_title += ' - ' + percentage + '%'
    if 'dir' in out_name:
        out_title += ' - dir'
    if 'del' in out_name:
        out_title += ' - del'
    if 'donly' in out_name:
        out_title += ' - donly'
    elif 'wonly' in out_name:
        out_title += ' - wonly'
    elif 'overw' in out_name:
        if 'after' in out_name:
            out_title += ' - overw-after'
        else:
            out_title += ' - overw-before'

    return out_title


# helper function for both plot bars functions (plot_bars_h & plot_bars)
def plot_bars_helper(in_paths: list, in_ext: str) -> tuple[list, str, str, str]:
    # get base values for fs size, percentage and output name
    parent_dir = os.path.dirname(in_paths[0])
    output_name = os.path.basename(parent_dir)

    # get the absolute file path and the containing .txt files
    file_list = []
    for i in in_paths:
        functions_os.check_path(i)
        file_list.append(functions_file.get_files_ext(i, in_ext))
    file_list.sort()

    plot_title = get_plot_title(output_name)
    tmp_legend = ''
    if not len(file_list) == 1:
        plot_title = 'Allocation/Nonzero blocks' + plot_title
    elif 'alloc' in os.path.basename(file_list[0][0]):
        # output_name += '_alloc'
        plot_title = 'Allocation' + plot_title
        tmp_legend = 'allocation'
    elif 'nonzero' in os.path.basename(file_list[0][0]):
        # output_name += '_nonzero'
        plot_title = 'Nonzero blocks' + plot_title
        tmp_legend = 'nonzero'

    return file_list, output_name, plot_title, tmp_legend


# function to generate handles for the axis legend
def get_legend_handles(file_name: str) -> (list, list):
    color_list = ['limegreen', 'blue', 'darkgreen', 'red']

    legend_list = [mpatches.Patch(color=color_list[0], label='allocation')]

    if 'overw_after_' in file_name:
        legend_list.append(mpatches.Patch(color=color_list[1], label='nonzero (file system)'))
        legend_list.append(mpatches.Patch(color=color_list[2], label='new data'))
        legend_list.append(mpatches.Patch(color=color_list[3], label='old data'))
    else:
        legend_list.append(mpatches.Patch(color=color_list[1], label='nonzero (file system)'))
        legend_list.append(mpatches.Patch(color=color_list[2], label='file data'))

    if 'alloc' in file_name:
        return [legend_list[0]], [color_list[0]]
    elif 'nonzero' in file_name:
        return [legend_list[1], legend_list[2]], [color_list[1], color_list[2]]

    return legend_list, color_list


# generate separate bar plots with matplotlib
def matplotlib_plot_separate(bool_h: bool, bool_chs, plot_type: str, file_name: str, files: list, plot_path: str, loc_str: str) -> bool:
    plot_title = get_plot_title(file_name)
    color_list = ['#377eb8', '#ff7f00', '#4daf4a', '#f781bf', '#a65628', '#984ea3', '#999999', '#e41a1c', '#dede00']
    handles_list = [mpatches.Patch(color=color_list[0], label='allocation'), mpatches.Patch(color=color_list[1], label='nonzero (file system)'), mpatches.Patch(color=color_list[2], label='file data'),
                    mpatches.Patch(color=color_list[3], label='old data')]
    title_list = ['Allocation' + plot_title, 'Nonzero (File System)' + plot_title, 'File Content' + plot_title, 'Old Data' + plot_title]
    output_list = ['_alloc', '_nonzero', '_file-content', '_pattern']
    tmp_output_name = file_name + '_' + plot_type
    if bool_chs:
        tmp_output_name += '_csv'
    if 'pattern' in file_name:
        separate_range = len(output_list)
    else:
        separate_range = len(output_list) - 1
    for i in range(separate_range):
        cur_output_name = tmp_output_name + output_list[i] + '.png'
        if 'alloc' in output_list[i]:
            tmp_file_list = files[0]
        elif 'pattern' in output_list[i]:
            tmp_file_list = files[2]
        else:
            tmp_file_list = files[1]
        fig, axs = plt.subplots(1, sharex='all', sharey='all')
        plot_title = title_list[i]
        output_file = os.path.join(plot_path, cur_output_name)
        if os.path.exists(output_file):
            return False
        if plot_type == 'bar':
            p_max = plot_bars_one(bool_h, i, tmp_file_list, axs, [color_list[i]])
            max_values = [p_max]
        elif plot_type == 'scatter':
            max_values = plot_scatter_one(bool_h, bool_chs, i, tmp_file_list, axs, [color_list[i]])
        else:
            return False
        # axs.legend(handles=[handles_list[i]], loc=loc_str)
        save_matplotlib_fig(bool_h, fig, axs, plot_title, max_values, output_file)
        print('plot created:', os.path.basename(output_file))
    return True


# create figure and call needed functions
def matplotlib_plot_bars(bool_horizontal, bool_over, bool_separate, input_paths, out_path):
    start_time = time.time()
    functions_os.check_path(out_path)

    file_list, output_name, plot_title, tmp_legend = plot_bars_helper(input_paths, 'txt')

    cur_loc = 'upper left'

    if bool_over and not len(file_list) == 1:
        output_name += '_overlay'
    if bool_horizontal:
        cur_loc = 'lower right'
    output_file = os.path.join(out_path, output_name)
    if os.path.exists(output_file):
        return False

    # check if both bars or one
    if len(file_list) == 1:
        fig, axs = plt.subplots(1, sharex='all', sharey='all')
        handles_list, color_list = get_legend_handles(output_name)
        p_max = plot_bars_one(bool_horizontal, 0, file_list[0], axs, color_list)
        axs.legend(handles=handles_list, loc=cur_loc)
    elif bool_separate:
        matplotlib_plot_separate(bool_horizontal, False, 'bar', output_name, file_list, out_path, cur_loc)
        return True
    elif not bool_over:
        fig, axs = plt.subplots(1, 2, sharex='all', sharey='all')
        plt.subplots_adjust(wspace=0, hspace=0)
        handles_list, color_list = get_legend_handles(output_name)
        max_vals = [0, 0]
        max_vals[0] = plot_bars_one(bool_horizontal, 0, file_list[0], axs[0], color_list)
        color_list.pop(0)
        max_vals[1] = plot_bars_one(bool_horizontal, 0, file_list[1], axs[1], color_list)
        p_max = max(max_vals)
        axs[0].legend(handles=[handles_list.pop(0)], loc=cur_loc)
        axs[1].legend(handles=handles_list, loc=cur_loc)
    else:
        fig, axs = plt.subplots(1, sharex='all', sharey='all')
        handles_list, color_list = get_legend_handles(output_name)
        p_max = plot_bars_two_h(file_list, axs, color_list)
        axs.legend(handles=handles_list, loc=cur_loc)

    # save and close the created figure
    save_matplotlib_fig(bool_horizontal, fig, axs, plot_title, [p_max], output_file)
    run_time = time.time() - start_time
    print('plots created for dir:', os.path.basename(output_name), 'duration:', str(datetime.timedelta(seconds=run_time)))
    return True


# create figure and call needed functions
def matplotlib_plot_scatter(bool_separate, bool_changes, input_paths, out_path):
    start_time = time.time()
    functions_os.check_path(out_path)

    if bool_changes:
        file_list, output_name, plot_title, tmp_legend = plot_bars_helper(input_paths, 'csv')
    else:
        file_list, output_name, plot_title, tmp_legend = plot_bars_helper(input_paths, 'txt')
    cur_loc = 'lower right'

    if bool_separate:
        matplotlib_plot_separate(True, bool_changes, 'scatter', output_name, file_list, out_path, cur_loc)

    run_time = time.time() - start_time
    print('plots created for:', os.path.basename(output_name), 'duration:', str(datetime.timedelta(seconds=run_time)))
    return True


# function for the code to save an open figure
def save_matplotlib_fig(bool_horizontal: bool, in_fig, in_axs, title: str, max_values: list, out_file_abs: str):
    in_fig.suptitle(title)

    label_list = ['Operation', 'Block No. [%]', 'Block Group No.']

    if len(max_values) == 1:
        if not bool_horizontal:
            try:
                for i in in_axs:
                    i.set_xlabel(label_list[0])
                    i.set_ylabel(label_list[1])
                    i.set_ylim(0 - max_values[0] * 0.05, max_values[0] * 1.05)
            except TypeError:
                in_axs.set_xlabel(label_list[0])
                in_axs.set_ylabel(label_list[1])
                in_axs.set_ylim(0 - max_values[0] * 0.05, max_values[0] * 1.05)
        else:
            try:
                for i in in_axs:
                    i.set_xlabel(label_list[1])
                    i.set_ylabel(label_list[0])
                    i.set_xlim(0 - max_values[0] * 0.05, max_values[0] * 1.05)
            except TypeError:
                in_axs.set_xlabel(label_list[1])
                in_axs.set_ylabel(label_list[0])
                in_axs.set_xlim(0 - max_values[0] * 0.05, max_values[0] * 1.05)
            out_file_abs = out_file_abs[:-4] + '_flip.png'
    elif len(max_values) == 2:
        try:
            for i in in_axs:
                i.set_ylabel('Block Group No.')
        except TypeError:
            in_axs.set_ylabel('Block Group No.')
        if not bool_horizontal:
            try:
                for i in in_axs:
                    i.set_xlabel(label_list[0])
                    i.set_ylabel(label_list[2])
                    i.set_xlim(0 - int(max_values[1] * 0.05), int(max_values[1] * 1.05))
                    i.set_ylim(0 - int(max_values[0] * 0.05), int(max_values[0] * 1.05))
            except TypeError:
                in_axs.set_xlabel(label_list[0])
                in_axs.set_ylabel(label_list[2])
                in_axs.set_xlim(0 - int(max_values[1] * 0.05), int(max_values[1] * 1.05))
                in_axs.set_ylim(0 - int(max_values[0] * 0.05), int(max_values[0] * 1.05))
        else:
            try:
                for i in in_axs:
                    i.set_xlabel(label_list[2])
                    i.set_ylabel(label_list[0])
                    i.set_xlim(0 - int(max_values[0] * 0.05), int(max_values[0] * 1.05))
                    i.set_ylim(0 - int(max_values[1] * 0.05), int(max_values[1] * 1.05))
            except TypeError:
                in_axs.set_xlabel(label_list[2])
                in_axs.set_ylabel(label_list[0])
                in_axs.set_xlim(0 - int(max_values[0] * 0.05), int(max_values[0] * 1.05))
                in_axs.set_ylim(0 - int(max_values[1] * 0.05), int(max_values[1] * 1.05))
            out_file_abs = out_file_abs[:-4] + '_flip.png'

    # save figure as file output_name
    plt.savefig(out_file_abs)

    # close figure
    plt.close(in_fig)


# create figure and call needed functions
def matplotlib_plot_from_dir(bool_separate: bool, bool_changes: bool, in_path: str, out_path: str) -> bool:
    functions_os.check_path(out_path)
    functions_os.check_path(in_path)

    input_paths = []

    input_list = os.listdir(in_path)
    input_list.sort()

    for d in input_list:
        tmp_dir = os.path.join(in_path, d)
        if os.path.isdir(tmp_dir):
            input_paths.append(tmp_dir)

    matplotlib_plot_bars(True, False, bool_separate, input_paths, out_path)
    #matplotlib_plot_scatter(bool_separate, bool_changes, input_paths, out_path)

    return True
