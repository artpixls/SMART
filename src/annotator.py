from pathlib import Path
import os
import json
from contextlib import contextmanager
import subprocess

import numpy as np
from PIL import Image
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
import hydra
from hydra.core.global_hydra import GlobalHydra
if GlobalHydra.instance().is_initialized():
    GlobalHydra.instance().clear()


@contextmanager
def pushd(d):
    old = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(old)

class Annotator:
    def __init__(self, conf):
        self.conf = conf
        sam2_checkpoint = self.conf.get_model_file()
        model_cfg = self.conf.get_model_config()
        with pushd(os.path.dirname(__file__)):
            with hydra.initialize(version_base=None,
                                  config_path="../models"):
                self.sam2_model = build_sam2(model_cfg,
                                             sam2_checkpoint,
                                             device=self.conf.device)
                self.sam2_model.eval()
        self.predictor = SAM2ImagePredictor(self.sam2_model)
        self.image_filename = None
        self.image = None
        self.mask = None
        self.masked_image = None
        self.image_real_size = -1, -1
        self.size = -1, -1
        self.positive_samples = []
        self.negative_samples = []

    def load_image(self, filename):
        def doit(fn):
            img = Image.open(fn).convert('RGB')
            self.image_real_size = img.size
            img.thumbnail((self.conf.max_image_size, self.conf.max_image_size))
            self.size = img.size
            self.image = np.array(img).astype(np.float32) / 255.0
            self.mask = None
            self.masked_image = (self.image * 255).astype(np.uint8)
            self.predictor.set_image(self.image)
            self.image_filename = os.path.abspath(fn)
        if self.conf.exiftool:
            try:
                res = subprocess.run(
                    [self.conf.exiftool, '-json', '-Sammy_mask_data', filename],
                    encoding='utf-8', capture_output=True, check=True)
                md = json.loads(res.stdout)[0]
                info = json.loads(md['Sammy_mask_data'])
                if info is not None and isinstance(info, dict):
                    fn = info.get('image', '')
                    ps = info.get('positive_samples')
                    ns = info.get('negative_samples')
                    if os.path.exists(fn) and ps is not None and ns is not None:
                        doit(fn)
                        self.positive_samples = ps
                        self.negative_samples = ns
                        self.predict()
                        return
            except Exception:
                pass
        doit(filename)

    def get_size(self):
        return self.size

    def add_point(self, point, is_positive):
        if is_positive:
            self.positive_samples.append(point)
        else:
            self.negative_samples.append(point)
        self.predict()

    def predict(self):
        if self.image is not None:
            input_points = self.positive_samples + self.negative_samples
            input_labels = [1] * len(self.positive_samples) + \
                [0] * len(self.negative_samples)
            masks, scores, logits = self.predictor.predict(
                point_coords=input_points,
                point_labels=input_labels,
                multimask_output=False
            )
            self.mask = masks[0]
            c = np.array(self.conf.mask_color, dtype=np.float32) / 255.0
            cm = np.zeros_like(self.image)[:,:] = c
            zm = np.zeros_like(self.image)
            m = np.repeat(np.expand_dims(self.mask, axis=2), 3, axis=2)
            m = np.where(m > 0, cm, zm)
            self.masked_image = \
                (np.fmin(self.image * 0.8 + m * 0.5, 1.0) * 255.0). \
                astype(np.uint8)

    def reset(self, clear_image):
        self.positive_samples = []
        self.negative_samples = []
        self.mask = None
        if clear_image:
            self.image = None
            self.masked_image = None
        else:
            self.masked_image = (self.image * 255).astype(np.uint8)

    def save_mask(self, filename):
        if self.image is None:
            raise Exception("no image loaded")
        if self.mask is not None:
            mask = (self.mask * 255).astype(np.uint8)
        else:
            mask = np.zeros_like(self.image)
        img = Image.fromarray((self.mask * 255).astype(np.uint8))
        img = img.resize(self.image_real_size, Image.BILINEAR)
        img.save(filename)
        data = {
            'image' : self.image_filename,
            'positive_samples' : self.positive_samples,
            'negative_samples' : self.negative_samples,
        }
        if self.conf.exiftool:
            subprocess.run([
                self.conf.exiftool,
                '-config',
                os.path.join(os.path.dirname(__file__), 'exiftool.config'),
                '-overwrite_original',
                '-Sammy_mask_data=' + json.dumps(data),
                filename], capture_output=True)

# end of class Annotator
