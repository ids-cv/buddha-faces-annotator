import json
import shutil
import os


def imgID2path(path_db, img_id):
    def find_ext(id, dir):
        for file in os.listdir(os.path.join(path_db, dir)):
            if id == str(file).split(".")[0]:
                return os.path.join(dir, file)

    id = img_id.split(".")[0]
    folder_in_db = "50000-59999"
    if int(id) < 50000:
        folder_in_db = "40000-49999"
        if int(id) < 40000:
            folder_in_db = "30000-39999"
            if int(id) < 30000:
                folder_in_db = "20000-29999"
                if int(id) < 20000:
                    folder_in_db = "10000-19999"
                    if int(id) < 10000:
                        folder_in_db = "00000-09999"
    path = os.path.join(path_db, find_ext(id, folder_in_db))
    return path


def retrieve_artifacts(path_db_json):
    with open(path_db_json) as file_db_json:
        db = json.load(file_db_json)
        artifact_images_dict = {}
        for key in db.keys():
            artifact_images_dict[key] = list(db[key]["Full image IDs"].keys())
        return artifact_images_dict


def write_json(path_projects, json_data, json_name):
    with open(os.path.join(path_projects, json_name), 'w') as outfile:
            json.dump(json_data, outfile)


def create_and_fill_folder(path_projects, path_db, artifact_id, artifact_images):
    dir_name = os.path.join(path_projects, "artifact_" + artifact_id)
    try:
        os.mkdir(dir_name)
    except:
        pass
    for index, im in enumerate(artifact_images):
        image_path = imgID2path(path_db, im)
        shutil.copy(image_path, dir_name)


def write_all_projects(path_db_json, path_db, path_projects):
    artifact_images_dict = retrieve_artifacts(path_db_json)
    artifact_names = list(artifact_images_dict.keys())
    for (artifact_id, artifact_images) in zip(artifact_names, list(artifact_images_dict.values())):
        create_and_fill_folder(path_projects, path_db, artifact_id, artifact_images)


if __name__ == "__main__":
    path_db_json = "/media/hlemarchant/Data/Buddha_db/Buddha_db.json"
    path_db = "labelme/data/Buddha_400"
    path_projects = "labelme/data/artifact_folders"
    write_all_projects(path_db_json, path_db, path_projects)
