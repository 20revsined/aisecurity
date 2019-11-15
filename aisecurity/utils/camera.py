"""

"aisecurity.utils.camera"

Camera utils.

"""

import cv2
import warnings

import requests
from aisecurity.utils.paths import CONFIG
from aisecurity.utils.preprocessing import CONSTANTS

try:
    import jetson.utils
except ModuleNotFoundError:
    warnings.warn("jetson.utils not found")


# CAMERA CLASS
class Camera(object):

    def __init__(self, mode="webcam", width=1280, height=720):
        self.mode = mode
        self.set_cap(width, height, mode)

        self.frame = None

    def set_cap(self, width, height, mode):
        self.width, self.height = width, height
        if mode is "jetson":
            self.cap = jetson.utils.gstCamera(width, height)
            self.display = jetson.utils.glDisplay()
            print(self.cap)
        elif mode is "webcam":
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        else:
            raise ValueError("mode must be 'jetson' or 'webcam'")

    def read(self):
        if self.mode is "jetson":
            self.display_frame, self.width, self.height = self.cap.CaptureRGBA()
            self.frame = jetson.utils.cudaToNumpy(self.display_frame, self.width, self.height, 4)
        elif self.mode is "webcam":
            _, self.frame = self.cap.read()


    def imshow(self, frame, title):
        if self.mode is "jetson":
            self.display.RenderOnce(self.frame, self.width, self.height)
            self.display.SetTitle(title)
        elif self.mode is "webcam":
            cv2.imshow(title, frame)

    def add_graphics(self, frame, overlay, person, width, height, is_recognized, best_match, resize, lcd):
        frame = self.frame if frame is None else frame

        assert self.mode is "webcam", "graphics for jetson.utils not supported"

        line_thickness = round(1e-6 * width * height + 1.5)
        radius = round((1e-6 * width * height + 1.5) / 2.)
        font_size = 4.5e-7 * width * height + 0.5

        # works for 6.25e4 pixel video cature to 1e6 pixel video capture

        def get_color(is_recognized, best_match):
            if not is_recognized:
                return 0, 0, 255  # red
            elif "visitor" in best_match:
                return 218, 112, 214  # purple (actually more of an "orchid")
            else:
                return 0, 255, 0  # green

        def add_box_and_label(frame, origin, corner, color, line_thickness, best_match, font_size, thickness):
            cv2.rectangle(frame, origin, corner, color, line_thickness)
            # label box
            cv2.rectangle(frame, (origin[0], corner[1] - 35), corner, color, cv2.FILLED)
            cv2.putText(frame, best_match.replace("_", " ").title(), (origin[0] + 6, corner[1] - 6),
                        cv2.FONT_HERSHEY_DUPLEX, font_size, (255, 255, 255), thickness)  # white text

        def add_features(overlay, features, radius, color, line_thickness):
            cv2.circle(overlay, (features["left_eye"]), radius, color, line_thickness)
            cv2.circle(overlay, (features["right_eye"]), radius, color, line_thickness)
            cv2.circle(overlay, (features["nose"]), radius, color, line_thickness)
            cv2.circle(overlay, (features["mouth_left"]), radius, color, line_thickness)
            cv2.circle(overlay, (features["mouth_right"]), radius, color, line_thickness)

            cv2.line(overlay, features["left_eye"], features["nose"], color, radius)
            cv2.line(overlay, features["right_eye"], features["nose"], color, radius)
            cv2.line(overlay, features["mouth_left"], features["nose"], color, radius)
            cv2.line(overlay, features["mouth_right"], features["nose"], color, radius)

        def add_lcd_display(lcd):
            lcd.clear()
            request = requests.get(CONFIG["server_address"])
            data = request.json()
            if data["accept"]:
                lcd.message = "ID Accepted \n{}".format(best_match)
            else:
                lcd.message = "No Senior Priv\n{}".format(best_match)

        features = person["keypoints"]
        x, y, height, width = person["box"]

        if resize:
            scale_factor = 1. / resize

            scale = lambda x: tuple(round(element * scale_factor) for element in x)
            features = {feature: scale(features[feature]) for feature in features}

            scale = lambda *xs: tuple(round(x * scale_factor) for x in xs)
            x, y, height, width = scale(x, y, height, width)

        color = get_color(is_recognized, best_match)

        margin = CONSTANTS["margin"]
        origin = (x - margin // 2, y - margin // 2)
        corner = (x + height + margin // 2, y + width + margin // 2)

        add_features(overlay, features, radius, color, line_thickness)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        text = best_match if is_recognized else ""
        add_box_and_label(frame, origin, corner, color, line_thickness, text, font_size, thickness=1)

        if lcd:
            add_lcd_display(lcd)

    def release(self):
        if self.mode is "jetson":
            warnings.warn("jetson capture cannot be released")
        elif self.mode is "webcam":
            self.cap.release()
