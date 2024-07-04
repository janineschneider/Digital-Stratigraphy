from lxml import etree
import os
import tarfile
import sys


# make a tar archive from directory
def make_tarfile(source_dir):
    output_name = source_dir + '.tar.gz'

    # if .tar.gz file is already existing, continue
    if os.path.exists(os.path.abspath(output_name)):
        return False

    with tarfile.open(output_name, 'w:gz') as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

    print('directory compressed', '\n-> input name: ', source_dir, '\n-> output name: ', output_name, '\n', flush=True)
    return True


# try to open given xml file, read it as tree and store the result in xml_tree
def open_xml(in_path):
    output_tree = etree.Element('empty')
    try:
        tmp_f = open(in_path, 'rb')
        output_tree = etree.fromstring(tmp_f.read())
        tmp_f.close()
    except FileNotFoundError:
        print('unable to find the xml file: ', sys.exc_info()[0])
        exit(1)
    except etree.LxmlSyntaxError:
        print('unable to extract xml structure from file: ', sys.exc_info()[0])
        exit(1)

    # check if other error while reading xml file occurred
    if output_tree.tag == 'empty':
        print('error occurred while reading xml file')
        exit(1)

    return output_tree


# get sorted list of files
def get_files(in_path):
    # init files list
    files = []
    # loop over directory to append files with absolute paths
    for f in os.listdir(in_path):
        tmp_f = os.path.join(in_path, f)
        # only append existing files with extension .txt
        if os.path.isfile(tmp_f) and os.path.splitext(tmp_f)[-1] == '.txt':
            files.append(tmp_f)
    # sort files regarding creation date
    files.sort(key=lambda tmp_file: os.path.getctime(tmp_file))

    return files


# get sorted list of files with absolute file path
def get_files_ext(in_path: str, extension: str):
    # init files list
    files = []
    # loop over directory to append files with absolute paths
    for f in os.listdir(in_path):
        tmp_f = os.path.join(in_path, f)
        # only append existing files with extension .txt
        if os.path.isfile(tmp_f) and os.path.splitext(tmp_f)[-1] == '.' + extension:
            files.append(tmp_f)
    # sort files regarding creation date
    files.sort(key=lambda tmp_file: os.path.getctime(tmp_file))

    return files
