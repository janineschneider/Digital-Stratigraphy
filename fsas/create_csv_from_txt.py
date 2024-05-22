import csv
import os
# own import
import functions_os


# Function to summarize blocks and their statuses
def summarize_blocks(blocks, statuses, blocks_to_summarize):
    summarized_blocks = []
    summarized_statuses = []
    for i in range(0, len(blocks), blocks_to_summarize):
        summarized_blocks.append(blocks[i:i + blocks_to_summarize])
        summarized_statuses.append(statuses[i:i + blocks_to_summarize])
    return summarized_blocks, summarized_statuses


# Function to process a single file
def process_file(file_path):
    # Get the directory, base filename, and extension from the input file path
    input_directory, input_extension = os.path.splitext(file_path)
    output_filename_extension = "_output.csv"  # Add 'output' at the end and set extension to .csv
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

    print(f"Data has been exported to '{output_file}'")


# helper function to process each file in both output dirs alloc_0 and nonzero_0
def process_output_dir(dir_path: str):
    functions_os.check_path(dir_path)
    if os.path.exists(os.path.join(dir_path, 'pattern_0')):
        sub_dirs = [os.path.join(dir_path, 'alloc_0'), os.path.join(dir_path, 'nonzero_0'), os.path.join(dir_path, 'pattern_0')]
    else:
        sub_dirs = [os.path.join(dir_path, 'alloc_0'), os.path.join(dir_path, 'nonzero_0')]
    for d in sub_dirs:
        print('process files in directory', d)
        for f in os.listdir(d):
            if f.endswith('.txt'):
                print('process file', f)
                cur_file_abs = os.path.join(d, f)
                process_file(cur_file_abs)


if __name__ == '__main__':
    # Replace 'file_path.txt' with the actual path of your text file
    folder_path = 'C:/Users/JS/OneDrive/Dokumente/Digital Stratigraphy/Documents/'

    # Iterate over all files in the folder with .txt extension and process each file
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            cur_file_path = os.path.join(folder_path, filename)
            process_file(cur_file_path)
