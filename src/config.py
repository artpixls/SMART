import dataclasses
from typing import Literal
from pathlib import Path
import os
import json
from platformdirs import user_config_dir


@dataclasses.dataclass
class Config:
    device: Literal[
        "cuda",
        "cpu",
        "mps"
    ] = "mps"
    model: Literal[
        "sam2.1_hiera_tiny.pt",
        "sam2.1_hiera_small.pt",
        "sam2.1_hiera_base_plus.pt",
        "sam2.1_hiera_large.pt",
    ] = "sam2.1_hiera_base_plus.pt"
    mask_color: tuple[int, int, int] = (70, 230, 50)
    background_color: tuple[int, int, int] = (127, 127, 127)
    exiftool: str = 'exiftool'
    window_size: int = 1200, 800
    last_dir: str = ""
    display_icc_profile: str|None = None

    def get_model_config(self):
        confmap = {
            "sam2.1_hiera_tiny.pt": "sam2.1_hiera_t.yaml",
            "sam2.1_hiera_small.pt": "sam2.1_hiera_s.yaml",
            "sam2.1_hiera_base_plus.pt": "sam2.1_hiera_b+.yaml",
            "sam2.1_hiera_large.pt": "sam2.1_hiera_l.yaml",
        }
        name = confmap[os.path.basename(self.model)]
        return name

    def get_model_file(self):
        ret = Path(__file__).parent / '../models/' / Path(self.model)
        return str(ret)

    @staticmethod
    def get_config_file():
        return os.path.join(user_config_dir(), "artpixls-SMART.json")

    @staticmethod
    def load(filename=None):
        res = Config()
        if filename is None:
            filename = Config.get_config_file()
        if os.path.exists(filename):
            with open(filename) as f:
                res = dataclasses.replace(res, **json.load(f))
        return res

    def save(self, filename=None):
        if filename is None:
            filename = Config.get_config_file()
        with open(filename, 'w') as out:
            json.dump(dataclasses.asdict(self), out, indent=2, sort_keys=True)
            out.write('\n')

# end of class Config
