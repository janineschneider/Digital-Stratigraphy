import os
import subprocess


# check if given path exists and absolute
def check_path(in_path):
    if not os.path.exists(in_path):
        print('path:', in_path, 'does not exist')
        exit(1)
    if in_path != os.path.abspath(in_path):
        print('path:', in_path, 'is not absolute')
        exit(1)


# check if given path is mount point
def check_mount_point(in_path):
    if not os.path.ismount(in_path):
        print('path:', in_path, 'is no mount point')
        exit(1)


# check for root permissions on linux or windows
def check_root(in_linux: bool, in_win: bool) -> bool:
    if in_linux:
        # check if the script is run as effective user 0 (root)
        if os.geteuid() == 0:
            return True
    elif in_win:
        # check if the script is run as admin; therefore try to create directory in C:\Windows\system32
        try:
            os.mkdir('C:/Windows/system32/test')
        except PermissionError:
            return False
        os.rmdir('C:/Windows/system32/test')
        return True
    # only linux and windows as operating systems are supported
    else:
        return False


# get the volume guid of the drive mounted at given drive letter
def get_vol_guid(dev_letter: str) -> str:
    result = ''
    tmp_cmd = 'mountvol'
    print('run command:', tmp_cmd)
    output = b''
    try:
        output = subprocess.check_output(["powershell", "-Command", tmp_cmd])
    except subprocess.CalledProcessError as e:
        print(e)
        print('error: running mountvol failed')
        exit(e.returncode)
    tmp_out = output.decode('utf-8', errors='ignore').split()
    for i in range(len(tmp_out)):
        if dev_letter + ':' in tmp_out[i] and not i == 0:
            result = tmp_out[i - 1]
    # extract guid from Volume string (e.g. \\?\Volume{e7ff8b1f-2147-4930-a83e-956fef652bc2}\)
    if result:
        return result[result.find('{') + 1:result.find('}')]
    else:
        print('error: extracting guid from', result, 'failed')
        exit(7)
    return ''


# helper function to call diskpart with script content extracted from list
def win_diskpart(content: list) -> bytes:
    tmp_cmd = 'diskpart /s '
    file_content = content
    file_content_str = ''
    tmp_file_name = 'foo.txt'
    with open(tmp_file_name, 'w') as f:
        for i in file_content:
            f.write(i + '\n')
            file_content_str += i
    print('run command:', tmp_cmd + file_content_str)
    output = b''
    try:
        output = subprocess.check_output(tmp_cmd + tmp_file_name)
        os.remove(tmp_file_name)
    except subprocess.CalledProcessError as e:
        print(e)
        print('error: running diskpart failed for command:', tmp_cmd + file_content_str)
        exit(e.returncode)
    return output


# get the volume guid of the drive mounted at given drive letter
def get_vol_id(dev_letter: str) -> str:
    script_content = ['list volume']
    tmp_out = win_diskpart(script_content).decode('utf-8', errors='ignore').split('\r\n')
    for i in tmp_out:
        tmp_line = i.split()
        if len(tmp_line) < 2:
            continue
        if tmp_line[2] == dev_letter:
            return tmp_line[1]

    print('error: extracting volume id from', tmp_out, 'failed')
    exit(7)
    return ''


# get the volume guid of the drive mounted at given drive letter
def get_disk_id(vol_id: str) -> str:
    script_content = ['select volume ' + vol_id, 'list disk', 'exit']
    tmp_out = win_diskpart(script_content).decode('utf-8', errors='ignore').split('\r\n')
    for i in tmp_out:
        tmp_line = i.split()
        if len(tmp_line) < 2:
            continue
        if tmp_line[0] == '*':
            return tmp_line[2]

    print('error: extracting disk id from', tmp_out, 'failed')
    exit(7)
    return ''


# define linux mount command as function
def mount_linux(dev_name: str, dev_path: str):
    tmp_cmd = 'mount ' + dev_name + ' ' + dev_path
    print('run command:', tmp_cmd)
    try:
        subprocess.check_output(tmp_cmd.split())
    except subprocess.CalledProcessError as e:
        print(e)
        print('error: mount of device:', dev_name, 'mount point:', dev_path)
        exit(e.returncode)


# define windows mount command as function
def mount_win(vol_id: str, dev_letter: str):
    script_content = ['select volume ' + vol_id, 'assign letter ' + dev_letter, 'exit']
    win_diskpart(script_content)
    print('volume mounted at:', dev_letter)


# define umount command as function
def umount_linux(dev_name: str, dev_path: str):
    tmp_cmd = 'umount ' + dev_path
    print('run command:', tmp_cmd)
    try:
        subprocess.check_output(tmp_cmd.split())
    except subprocess.CalledProcessError as e:
        print(e)
        print('error: umount of device:', dev_name, 'mount point:', dev_path)
        exit(e.returncode)


# define windows mount command as function
def umount_win(vol_id: str, dev_letter: str):
    script_content = ['select volume ' + vol_id, 'remove letter ' + dev_letter, 'exit']
    win_diskpart(script_content)
    print('volume unmounted at:', dev_letter)


# define mkfs command as function (FAT32, NTFS, exFAT at the moment)
def format_linux(dev_name: str, quick_format: bool, fs_type: str):
    # set command to format regarding the given file system type
    # default type is fat32
    if fs_type == 'ntfs' and quick_format:
        tmp_cmd = 'mkfs.ntfs -Q -L ntfs_label ' + dev_name
    elif fs_type == 'ntfs':
        tmp_cmd = 'mkfs.ntfs -L ntfs_label ' + dev_name
    elif fs_type == 'exfat':
        tmp_cmd = 'mkfs.exfat -L exfat_label ' + dev_name
    else:
        tmp_cmd = 'mkfs.fat -F32 -n FAT32LABEL ' + dev_name
    print('run command:', tmp_cmd)
    try:
        subprocess.check_output(tmp_cmd.split())
    except subprocess.CalledProcessError as e:
        print(e)
        print('error: formatting of device:', dev_name)
        exit(e.returncode)


# define formatting on Windows as function (FAT32 at the moment)
def format_win(dev_letter: str, quick_format: bool, fs_type: str):
    vol_id = get_vol_id(dev_letter)
    disk_id = get_disk_id(vol_id)
    umount_win(vol_id, dev_letter)
    script_content = ['select volume ' + vol_id]
    format_str = 'format fs=' + fs_type + ' label=' + fs_type.upper() + 'LABEL quick'
    if quick_format:
        script_content.append(format_str)
    else:
        script_content.append('clean')
        script_content.append('select disk ' + disk_id)
        script_content.append('create partition primary')
        script_content.append(format_str)
    script_content.append('exit')
    win_diskpart(script_content)
    print('volume formatted at:', dev_letter)
    mount_win(vol_id, dev_letter)


# helper function to write pattern to drive
def write_pattern(in_pattern: bytes, in_name: str):
    raw_disk = open(in_name, 'wb')
    try:
        while True:
            raw_disk.write(in_pattern)
    except OSError as e:
        print(e)
        raw_disk.close()
    finally:
        raw_disk.close()
        print('pattern was written on device', in_name)
        return True


# prepare device on linux os: unmount device, wipe device, mkfs and mount it again
def wipe_device_linux(dev_name: str, wipe_pattern: bool):
    # check if bool wipe pattern is set, if set, write fixed pattern to disk
    if wipe_pattern:
        # given 512 byte pattern
        pattern = b'this is old data' * 32
        write_pattern(pattern, dev_name)
    # if the bool is False wipe with zeroes
    else:
        tmp_cmd = 'dd if=/dev/zero of=' + dev_name + ' bs=4096 status=progress'
        print('run command:', tmp_cmd)
        cmd_out = subprocess.Popen(tmp_cmd.split(), stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
        for k in cmd_out.stdout:
            print(k, end='')
        cmd_out.wait()
        return True


# prepare device on linux os: unmount device, wipe device, mkfs and mount it again
def wipe_device_win(vol_name: str, wipe_pattern: bool):
    # check if bool wipe pattern is set, if set, write fixed pattern to disk
    if wipe_pattern:
        # given 512 byte pattern
        pattern = b'this is old data' * 32
    # if the bool is False wipe with zeroes
    else:
        pattern = b'\x00' * 512
    write_pattern(pattern, '\\\\?\\Volume{' + vol_name + '}\\')


# prepare device on linux os: unmount device, wipe device, mkfs and mount it again
def prepare_device_linux(dev_name: str, dev_path: str, fs_type: str, bool_quick: bool, bool_pattern: bool):
    umount_linux(dev_name, dev_path)
    wipe_device_linux(dev_name, bool_pattern)
    format_linux(dev_name, bool_quick, fs_type)
    mount_linux(dev_name, dev_path)


# prepare device on linux os: unmount device, wipe device, mkfs and mount it again
def prepare_device_win(vol_name: str, dev_letter: str, fs_type: str, bool_pattern: bool, bool_quick: bool):
    format_win(dev_letter, bool_quick, fs_type)


# prepare device on linux os: unmount device, wipe device, mkfs and mount it again
def write_cache_win(dev_letter: str):
    tmp_cmd = 'Write-VolumeCache ' + dev_letter
    print('run command:', tmp_cmd)
    try:
        subprocess.check_output(["powershell", "-Command", tmp_cmd])
    except subprocess.CalledProcessError as e:
        print(e)
        print('error: write volume cache of mount point:', dev_letter)
        exit(e.returncode)
