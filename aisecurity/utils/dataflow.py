"""

"aisecurity.utils.dataflow"

Data utils.

"""

import json
import os

from aisecurity.privacy.encryptions import DataEncryption
from aisecurity.utils.preprocessing import timer


# LOAD ON THE FLY
@timer(message="Data preprocessing time")
def online_load(facenet, img_dir, people=None):
    if people is None:
        people = [f for f in os.listdir(img_dir) if not f.endswith(".DS_Store") and not f.endswith(".json")]
    data = {person.strip(".jpg").strip(".png"): facenet.predict([os.path.join(img_dir, person)]) for person in people}

    return data


# LONG TERM STORAGE
@timer(message="Data dumping time")
def dump_embeds(facenet, img_dir, dump_path, retrieve_path=None, full_overwrite=False, ignore_encrypt=None,
                retrieve_encryption=None):

    if ignore_encrypt == "all":
        ignore_encrypt = ["names", "embeddings"]
    elif ignore_encrypt is not None:
        ignore_encrypt = [ignore_encrypt]

    if not full_overwrite:
        old_embeds = retrieve_embeds(retrieve_path if retrieve_path is not None else dump_path,
                                     encrypted=retrieve_encryption)
        new_embeds = online_load(facenet, img_dir)

        embeds_dict = {**old_embeds, **new_embeds}  # combining dicts and overwriting any duplicates with new_embeds
    else:
        embeds_dict = online_load(facenet, img_dir)

    encrypted_data = DataEncryption.encrypt_data(embeds_dict, ignore=ignore_encrypt)

    with open(dump_path, "w+") as json_file:
        json.dump(encrypted_data, json_file, indent=4, ensure_ascii=False)


@timer(message="Data retrieval time")
def retrieve_embeds(path, encrypted=None):
    with open(path, "r") as json_file:
        data = json.load(json_file)

    if encrypted == "embeddings":
        return DataEncryption.decrypt_data(data, ignore=["names"])
    elif encrypted == "names":
        return DataEncryption.decrypt_data(data, ignore=["embeddings"])
    elif encrypted == "all":
        return DataEncryption.decrypt_data(data, ignore=None)
    else:
        return data
