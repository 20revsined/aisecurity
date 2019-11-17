"""

"aisecurity.logging.log"

MySQL and Firebase logging handling.

"""

import time
import warnings

import mysql.connector
import pyrebase
from pyrebase import *

from aisecurity.utils.paths import CONFIG_HOME, CONFIG


# SETUP
DATABASE, CURSOR = None, None
FIREBASE = None

THRESHOLDS = {
    "num_recognized": 5,
    "num_unknown": 5,
    "percent_diff": 0.2,
    "cooldown": 10.,
    "missed_frames": 10
}

num_recognized = 0
num_unknown = 0

last_logged = time.time() - THRESHOLDS["cooldown"] + 0.1  # don't log for first 0.1s- it's just warming up then
unk_last_logged = time.time() - THRESHOLDS["cooldown"] + 0.1

current_log = {}


# LOGGING INIT AND HELPERS
def init(flush=False, thresholds=None, logging="firebase"):
    if logging == "mysql":
        warnings.warn("logging with MySQL is deprecated and will be removed in later versions", DeprecationWarning)

        try:
            global DATABASE
            database = mysql.connector.connect(
                host="localhost",
                user=CONFIG["mysql_user"],
                passwd=CONFIG["mysql_password"],
                database="LOG"
            )
            global CURSOR
            CURSOR = database.cursor()

        except (mysql.connector.errors.DatabaseError, mysql.connector.errors.InterfaceError):
            warnings.warn("MySQ database credentials missing or incorrect")

        CURSOR.execute("USE LOG;")
        DATABASE.commit()

        if flush:
            instructions = open(CONFIG_HOME + "/bin/drop.sql")
            for cmd in instructions:
                if not cmd.startswith(" ") and not cmd.startswith("*/") and not cmd.startswith("/*"):
                    CURSOR.execute(cmd)
                    DATABASE.commit()

    elif logging == "firebase":
        firebase_config = {
            "apiKey": "AIzaSyDgAZBLrQrAeVHo1uyPa7aO4MphxWcPUWw",
            "authDomain": "aisecurity-1f693.firebaseapp.com",
            "databaseURL": "https://aisecurity-1f693.firebaseio.com",
            # "projectId": "n-d3a20",
            "storageBucket": "aisecurity-1f693.appspot.com",
            # "messagingSenderId": "626961674461",
            # "appId": "1:626961674461:web:424708683547daae",
            "serviceAccount": CONFIG_HOME + "/logging/aisecurity-1f693-5351d8b70c93.json"
        }

        global FIREBASE
        FIREBASE = pyrebase.initialize_app(firebase_config)

    if thresholds:
        global THRESHOLDS
        THRESHOLDS = {**THRESHOLDS, **thresholds}  # combining and overwriting THRESHOLDS with thresholds param


def get_now(seconds):
    date_and_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(seconds))
    return date_and_time.split(" ")


def get_id(name):
    # will be filled in later
    return "00000"


def get_percent_diff(best_match):
    return 1. - (len(current_log[best_match]) / len([item for sublist in current_log.values() for item in sublist]))


def update_current_logs(is_recognized, best_match):
    global current_log, num_recognized, num_unknown

    if is_recognized:
        now = time.time()

        if best_match not in current_log:
            current_log[best_match] = [now]
        else:
            current_log[best_match].append(now)

        if len(current_log[best_match]) == 1 or get_percent_diff(best_match) <= THRESHOLDS["percent_diff"] + 0.2:
            num_recognized += 1
            num_unknown = 0

    else:
        num_unknown += 1
        if num_unknown >= THRESHOLDS["num_unknown"]:
            num_recognized = 0


# LOGGING FUNCTIONS
def log_person(student_name, times, firebase=True):
    if not firebase:
        add = "INSERT INTO Activity (student_id, student_name, date, time) VALUES ({}, '{}', '{}', '{}');".format(
            get_id(student_name), student_name.replace("_", " ").title(), *get_now(sum(times) / len(times)))
        CURSOR.execute(add)
        DATABASE.commit()
    else: 
        path = db.child("known")
        time = get_now(sum(times)/len(times))
        data = {
            "student_id": get_id(student_name),
            "student_name": student_name.replace("_", " ").title(),
            "date": time[0],
            "time": time[1]
        }
        if path.get().val()==None:
            db.child("known").set(data)
        else:
            db.child("known").update(data)

    global last_logged
    last_logged = time.time()

    flush_current(regular_activity=True)


def log_unknown(path_to_img, firebase=True):
    if not firebase:
        add = "INSERT INTO Unknown (path_to_img, date, time) VALUES ('{}', '{}', '{}');".format(
            path_to_img, *get_now(time.time()))
        CURSOR.execute(add)
        DATABASE.commit()
    else:
        path = db.child("known")
        time = get_now(time.time())
        data = {
            "path_to_img": path_to_img,
            "date": time[0],
            "time": time[1]
        }
        if path.get().val()==None:
            db.child("unknown").set(data)
        else:
            db.child("unknown").update(data)

    global unk_last_logged
    unk_last_logged = time.time()

    flush_current(regular_activity=False)


def flush_current(regular_activity=True):
    global current_log, num_recognized, num_unknown
    if regular_activity:
        current_log = {}
        num_recognized = 0
    else:
        num_unknown = 0
