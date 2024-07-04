from datetime import datetime
import matplotlib.pyplot as plt
import os
from ..stratlib import raw_disk_access


def main(img_path: str, out_file: str, out_path: str):
    # Generate list of files sorted by timestamp
    path = img_path
    a = raw_disk_access.RawDiskAccessor(path)
    list_of_files = []

    a.get_list_of_files(list_of_files)

    b = raw_disk_access.RawDiskAccessor(path)
    file_system_handles_dict = b.get_file_system_handles()

    # populates a list of files with specific extracted properties
    for each in list_of_files:
        inode = each['inode']
        file_obj = file_system_handles_dict[each['partition_sector']].open_meta(inode)

        for attr in file_obj:
            first = True
            for run in attr:
                if first:
                    each['start_block'] = run.addr
                    first = False

    # makes a version of that file list sorted by creation time
    time_sorted_list = sorted(list_of_files, key=lambda d: d['crtime'])

    x_labels = []
    y_values = []
    for each in time_sorted_list:
        if each.get('start_block'):  # skips no start cluster files
            x_labels.append(datetime.fromtimestamp(each['crtime']).isoformat(' '))
            y_values.append(each.get('start_block'))

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(x_labels, y_values)
    plt.xlabel('File creation date')
    plt.ylabel('Start cluster')
    plt.title(f'Start cluster over time')

    # Rotate x-axis labels and adjust subplot margins
    plt.xticks(rotation=90, fontsize=5)
    # plt.subplots_adjust(bottom=0.2)

    # Get current axis and adjust x-axis limits
    ax = plt.gca()
    ax.set_xlim([-0.5, len(x_labels)-0.5])

    # Save the plot as a PNG file
    # png_filename = os.path.splitext(file)[0] + '.png'
    plt.tight_layout()
    # plt.show()
    plt.savefig(os.path.join(out_path, out_file))

    # Close the plot to free up memory
    plt.close()

    print("Processing complete. Plots saved as PNG files.")
