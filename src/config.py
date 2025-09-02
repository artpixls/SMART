import dataclasses
from typing import Literal
from pathlib import Path
import os
import jstyleson as json


@dataclasses.dataclass
class Config:
    max_image_size: int = 1920
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
    exiftool: str = 'exiftool'

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
    def load(filename):
        res = Config()
        with open(filename) as f:
            return dataclasses.replace(res, **json.load(f))

    def save(self, filename):
        with open(filename, 'w') as out:
            json.dump(dataclasses.asdict(self), out, indent=2, sort_keys=True)
            out.write('\n')

# end of class Config
