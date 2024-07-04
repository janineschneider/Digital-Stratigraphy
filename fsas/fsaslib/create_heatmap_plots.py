import plotly.graph_objects as go
import plotly
import os
from ..stratlib.utils import get_desc_from_bit_attr
from . import functions_heatmap


def main(base_dir: str, out_path: str):
    print(f"Generate combined CSV file with values for heatmap")
    functions_heatmap.combine_csv_files(base_dir)

    heatmap_csv_path = os.path.join(base_dir, 'heatmap.csv')

    print('Generates visualisation of file system operation-based experiments')

    f = open(heatmap_csv_path, 'r')

    block_allocation_map = []
    block_allocation_map_text = []

    print('loading data from CSV...')
    # Loads the data from teh CSV file and builds two lists (map, and map_text)
    max_block = 0
    count = 0
    first = True
    for each_line in f:
        if not first:
            parts = each_line.strip('\n').split(',')
            row = []
            row_text = []
            for each_val in parts:
                int_val = int(each_val)
                row.append(str(int_val))
                text_val = get_desc_from_bit_attr(int_val)
                row_text.append(text_val)
            block_allocation_map.append(row)
            block_allocation_map_text.append(row_text)
            max_block = len(parts)
            count = count + 1
        else:
            first = False

    f.close()

    print('generating axis labels...')
    xaxis = list(range(0, max_block))
    yaxis = list(range(0, count))
    print('blocks range: {} to {}'.format(0, max_block))
    print('operation range: {} to {}'.format(0, count))
    print('block size not known')

    colorscale = [[0, '#999999'],
                  [0.01, '#377eb8'],  # non zero
                  [0.03, '#e41a1c'],  # old data, not zero
                  [0.04, '#dede00'],  # alloc, filled with zeros
                  [0.05, '#2c642a'],  # alloc, non zero
                  [0.13, '#4daf4a'],  # new pattern, alloc, non-zero
                  [0.19, '#984ea3'],  # old data and fs struct, non-zero
                  [0.21, '#a65628'],  # poss fs struct, alloc, contains non-zero
                  [1, '#ffffff']]  # 100+ = carved of interest

    # --------------------------------------------------
    # # new code - plotly graph object
    print('generating heatmap with plotly graph object...')
    fig = go.Figure(data=go.Heatmap(z=block_allocation_map,
                                    x=xaxis,
                                    y=yaxis,
                                    zmin=0,
                                    zmax=100,
                                    customdata=['zero', 'one', 'two', 'three', 'four',
                                                'five', 'six', 'seven', 'eight', 'nine',
                                                'ten', 'eleven', '12', '13x', '14x',
                                                '15x', '16x', '17x', '18x', '19x',
                                                '20x', '21x', '22x', '23x', '24x',
                                                '25x', '26x', 'tw27xo', '28x', '29x',
                                                ],
                                    # text=block_allocation_map_text, # this is cool, but makes the file massive
                                    colorscale=colorscale,
                                    hovertemplate='Block: %{x}<br>Operation: %{y}<br>Block status: %{z}'
                                    ),
                    )
    fig.update_xaxes(title_text="Block number")
    fig.update_yaxes(title_text="Operation")
    fig.update_layout(title_text=os.path.basename(base_dir))
    fig.update_layout(legend_title_text="Block status")

    print('saving offline plot...')
    out_file = os.path.join(out_path, '{}_heatmap.html'.format(os.path.basename(base_dir)))
    plotly.offline.plot(fig, filename=out_file)
    print('done')
