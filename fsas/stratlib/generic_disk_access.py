import logging
import os
import pytsk3


class DiskAccessorError(Exception):
    pass


class GenericDiskAccessor(object):
    """Generate list of files on partition starting at supplied dir"""

    def _populate_file_list(self, starting_dir_object, parent_path, partition_sector):
        if starting_dir_object is None:
            return

        logging.info('Folder is {}'.format(parent_path))

        self.list_of_dir_inodes.append(starting_dir_object.info.addr)

        # logging.debug('Processing {}'.format(starting_dir_object.info.names.name))
        for each_file in starting_dir_object:
            filename_decoded = each_file.info.name.name.decode('UTF-8', 'replace')
            full_path = os.path.join(parent_path, filename_decoded)
            if each_file.info.meta is None:
                logging.warning("{} has no metadata".format(full_path))
                continue

            # print(each_file.info.name.name, each_file.info.meta.type, each_file.info.meta.flags, each_file.info.meta.mode)
            # added this in trying to identify volume label entry on fat root entry

            if each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
                # is a file
                # self.list_of_files.append(FileItem(full_path, each_file.info.meta.addr, each_file.info.meta.size,
                #                                    partition_sector))
                # print(full_path)                
                # # print('content_ptr', each_file.info.meta.content_ptr)
                # print('crtime', each_file.info.meta.crtime)
                # print('inode', each_file.info.meta.addr) # inode
                # print(dir(each_file.info.fs_info))
                # print(each_file.info.meta.content_ptr)

                file_info = {'full_path': full_path, 'crtime': each_file.info.meta.crtime, 'inode': each_file.info.meta.addr, 'partition_sector': partition_sector, 'status': each_file.info.meta.flags, 'size': each_file.info.meta.size}

                self.list_of_files.append(file_info)

                # logging.debug('Added {}'.format(full_path))

            elif each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
                # is a directory
                # logging.debug(each_file.info.name.name)
                if each_file.info.name.name == b'.' or each_file.info.name.name == b'..':
                    pass
                elif each_file.info.name.name == b'$OrphanFiles':
                    logging.debug("skipped $OrphanFiles for now".format())
                else:  # is proper dir
                    if each_file.info.meta.addr not in self.list_of_dir_inodes:
                        try:
                            # has not been processed yet (needed to stop infinite recursion)
                            self._populate_file_list(each_file.as_directory(), full_path, partition_sector)
                        except OSError as e:
                            logging.error("A major error occurred reading {} ({})".format(full_path, e))
                    else:
                        logging.debug("skipped {} as in list of dir inodes".format(each_file.info.meta.addr))

            elif each_file.info.meta.type == pytsk3.TSK_FS_META_TYPE_LNK:
                # deliberately ignoring symbolic links
                pass
            else:
                logging.debug('Unsupported file type: {} {} '.format(each_file.info.name.name,
                                                                     each_file.info.meta.type))

    """NEEDS IMPLEMENTING IN SUBCLASS"""

    def _get_partitions(self):
        raise NotImplementedError('Needs implementing in subclass')

    """NEEDS IMPLEMENTING IN SUBCLASS"""

    def _try_getting_file_system_handle(self, offset):
        raise NotImplementedError('Needs implementing in subclass')

    """Populate list of files for a disk image of a volume only"""

    def _get_list_of_files_from_volume(self, fs_handle):
        self.list_of_dir_inodes = []
        root_directory_object = fs_handle.open_dir('/', 0)
        self._populate_file_list(root_directory_object, 'P_0/', 0)
        logging.info('File list populated')

    """Populate list of files for a disk image with partitions"""

    def _get_list_of_files_from_all_partitions(self):
        partitions = self._get_partitions()
        logging.info("Detected some partitions")

        for i, each_partition in enumerate(partitions):
            logging.info('processing partition: {}'.format(i))
            if each_partition.flags == pytsk3.TSK_VS_PART_FLAG_UNALLOC:
                logging.info("--- needs scanning (photorec/foremost)")
            elif each_partition.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                logging.info("--- needs processing (fls)")
                fs_handle = self._try_getting_file_system_handle(offset=512 * each_partition.start)
                if fs_handle is not None:
                    root_directory_object = fs_handle.open_dir('/', 0)
                    self._populate_file_list(root_directory_object, 'P_{}/'.format(each_partition.start),
                                             each_partition.start)
                    logging.info('File list populated for'.format(each_partition.start))
                else:
                    print('none fs found at {}'.format(each_partition.start))
            elif each_partition.flags == pytsk3.TSK_VS_PART_FLAG_META:
                # ignoring meta volumes on purpose
                pass
            else:
                logging.warning('Partition type not identified {}'.format(each_partition.flags))

    """Return a dictionary of file system handles"""

    def get_file_system_handles(self):
        handles = {}

        fs_handle = self._try_getting_file_system_handle(offset=0)
        if fs_handle:  # we just have a file system at this point, no partitions
            handles[0] = fs_handle
        else:
            partitions = self._get_partitions()
            for each_partition in partitions:
                if each_partition.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                    fs_handle = self._try_getting_file_system_handle(offset=512 * each_partition.start)
                    handles[each_partition.start] = fs_handle
        return handles
