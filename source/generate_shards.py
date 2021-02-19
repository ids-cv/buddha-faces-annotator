import os
import shutil


shard_size = 100
list_folders = os.listdir(os.path.join('..', 'data'))
for index, folder in enumerate(list_folders):
    no_shard = str(index // shard_size)
    shutil.move(os.path.join('..', 'data', folder), os.path.join('..', 'data', 'shard_' + no_shard, folder))
