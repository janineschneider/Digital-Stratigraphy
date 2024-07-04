import os
import pandas as pd
from pandas import DataFrame
from pandas import Series
import re
import shutil


# Process one txt file from 'alloc_0' or such directories to a pd.DataFrame
def process_text_file(file_path, identifier='') -> DataFrame:
    # Initialize empty lists to store values from the text file
    blk_no = []
    blk_state = []

    add_val = -7
    # Check which value has to be added
    if identifier:
        if identifier == 'alloc':
            add_val = 0
        elif identifier == 'nonzero':
            add_val = 1
        elif identifier == 'pattern':
            add_val = 3
    else:
        parent_dir = os.path.basename(os.path.dirname(file_path))
        if 'alloc' in parent_dir:
            add_val = 0
        elif 'nonzero' in parent_dir:
            add_val = 1
        elif 'pattern' in parent_dir:
            add_val = 3

    # Read the file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Read the file content line by line and split columns by '|'
    last_value = None
    for line in lines:
        columns = line.strip().split('|')
        if len(columns) == 2:  # Ensure that there are two columns separated by '|'
            current_value = columns[1]
            if current_value == last_value:
                start_range = int(blk_no[-1]) + 1 if blk_no else 0
                end_range = int(columns[0])
                for i in range(start_range, end_range):
                    blk_no.append(str(i))
                    if int(last_value) != 0:  # Add add_val to values in the second column only if the value is not zero
                        blk_state.append(str(int(last_value) + add_val))
                    else:
                        blk_state.append(last_value)

            elif current_value != last_value:
                if line is lines[-1]:
                    start_range = int(blk_no[-1]) + 1
                    end_range = int(columns[0])
                    for i in range(start_range, end_range):
                        blk_no.append(str(i))
                        if int(current_value) != 0:  # Add add_val to values in the second column only if the value is not zero
                            blk_state.append(str(int(current_value) + add_val))
                        else:
                            blk_state.append(current_value)

            blk_no.append(columns[0])
            if int(current_value) != 0:  # Add add_val to values in the second column only if the value is not zero
                blk_state.append(str(int(current_value) + add_val))
            else:
                blk_state.append(current_value)
            last_value = current_value

    # Combine x and y values in pairs and convert to data frame
    pairs = list(zip(blk_no, blk_state))
    df = pd.DataFrame(pairs, columns=['blk_no', 'blk_state'])
    
    return df


# Determine the y value regarding all set values
def get_bit_attr_val(in_series: Series) -> int:
    attr_list = in_series.iloc
    val = 0
    # if 0 in attr_list:
    #     val = val | 0b00000001   # set bit 0 if not zero
    if 4 in attr_list:
        val = val | 0b00000011   # set bit 1 if contains old data
    if 1 in attr_list:
        val = val | 0b00000100   # set bit 2 if allocated (according to TSK)
    if 3 in attr_list:
        val = val | 0b00001001   # set bit 3 if known 'new' file content
    if 2 in attr_list:
        val = val | 0b00010001   # set bit 4 poss file system structure [reserved]
    if 5 in attr_list:
        val = val | 0b00100000   # set bit 5 outside of volume [reserved]]
    if 6 in attr_list:
        val = val | 0b01000000   # set bit 6
    if 7 in attr_list:
        val = val | 0b10000000   # set bit 7 [reserved]

    return val


# Merge the DataFrames of the text files to one combined DataFrame for each number
def merge_txt_files(base_dir: str):
    number_files = []
    dir_dict = {'alloc': '', 'nonzero': '', 'pattern': ''}

    for i in ['alloc', 'nonzero', 'pattern']:
        for d in os.listdir(base_dir):
            tmp_dir = os.path.join(base_dir, d)
            if i in d and os.path.isdir(tmp_dir):
                dir_dict[i] = tmp_dir
                number_files.append(len(os.listdir(tmp_dir)))
                break

    if not all(x == number_files[0] for x in number_files):
        print(f"The number of files in the directories 'alloc_0', 'nonzero_0' and 'pattern_0' are not the same.")
        exit(1)

    number_digits = len(re.findall(r'\d+', os.listdir(dir_dict['alloc'])[0])[0])

    i = 0
    while True:
        # Clear df list for the next iteration
        df_list = []

        middle_value = f"{i:0{number_digits}d}"

        # Check if input files exist for the current middle value
        files_exist = all(
            os.path.exists(os.path.join(base_dir, f'{identifier}_0', f'{identifier}_{middle_value}.txt'))
            for identifier in ['alloc', 'nonzero', 'pattern']
            # for identifier in ['alloc', 'nonzero']
        )

        if not files_exist:
            break  # Stop if files do not exist for the current middle value

        # Create a unique name for the merged output file
        out_name = f'output_{middle_value}.csv'
        out_path = os.path.join(base_dir, 'output_0', out_name)

        for identifier in ['alloc', 'nonzero', 'pattern']:
            # for identifier in ['alloc', 'nonzero']:
            folder = os.path.join(base_dir, f'{identifier}_0')
            file_name = f'{identifier}_{middle_value}.txt'
            file_path = os.path.join(folder, file_name)
            print(f"Read file content of {file_name}")

            df_list.append(process_text_file(file_path))

            # # Read and merge values from the current file
            # read_and_merge_values(file_path, index_values)

        print(f"Combine the file contents of {middle_value}")
        # Combine the DataFrames
        comb_df = pd.concat(df_list)

        print(f"Merge the file contents of {middle_value}")
        # Group by 'x' and apply the custom function to 'y' values
        merged_df = comb_df.groupby('blk_no')['blk_state'].agg(get_bit_attr_val).reset_index()

        print(f"Write the combined values to {middle_value}")
        # Write the merged data to the unique CSV file for the current middle value (in chunks)
        # Define the chunk size
        chunk_size = 1000
        # Write DataFrame in chunks
        for start in range(0, len(merged_df), chunk_size):
            merged_df.iloc[start:start + chunk_size].to_csv(out_path, mode='a', header=False, index=False)

        print(f"Data has been exported to '{out_path}'")

        i += 1


# Combine the merged csv files to one big csv file
def combine_csv_files(base_dir: str):
    # Create output folder
    out_dir = os.path.join(base_dir, 'output_0')
    os.mkdir(out_dir)

    # Call the function to merge all text files
    merge_txt_files(base_dir)

    # Initialize an empty DataFrame to store the combined data
    combined_data = pd.DataFrame()

    # Loop through all CSV files in the given folder
    for f in os.listdir(out_dir):
        if f.endswith(".csv"):
            file_path = os.path.join(out_dir, f)

            # Read the CSV file into a DataFrame
            df = pd.read_csv(file_path)

            # Check if the DataFrame has at least 2 columns
            if len(df.columns) >= 2:
                # Extract the second column and append it to the combined DataFrame
                combined_data[f] = df.iloc[:, 1]

    combined_data = combined_data.transpose()

    out_file = os.path.join(base_dir, 'heatmap.csv')

    # Save the combined DataFrame to a new CSV file
    combined_data.to_csv(out_file, index=False)

    # Delete the temporary output files in 'output_0'
    shutil.rmtree(out_dir)
