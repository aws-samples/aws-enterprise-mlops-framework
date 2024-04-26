from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

import os
import torch
import torch.nn.functional as F
import torch.utils.checkpoint
import transformers
from constants import constants
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms


class DreamBoothDataset(Dataset):
    """A dataset to prepare the instance and class images with the prompts for fine-tuning the model.

    Pre-processes the images and the tokenizes prompts.
    """

    def __init__(
        self,
        instance_data_root: str,
        instance_prompt: str,
        tokenizer: transformers.models.clip.tokenization_clip.CLIPTokenizer,
        class_data_root: Optional[str] = None,
        class_prompt: Optional[str] = None,
        size: int = 512,
        center_crop: bool = False,
    ):
        """Create an object for dataset used for training.

        Set length to be the maximum of class images (if class_data_dir is not None) and instance images.
        Crop images to the desired resolution (size x size) if center_crop is True.
        Resize the image to the desired resolution (size x size) even if center_crop is False.
        If class_data_root is not None and the directory does not exist, create an empty directory.
        Args:
            instance_data_root: directory with the instance images.
            instance_prompt: text describing the training images that you want your model to adapt to.
            tokenizer: Tokenizer to tokenize the dataset.
            class_data_root (optional): directory with the class images.
            class_prompt: text describing the generic image type of training images without the instance prompt tag.
            size: Resize the images before training.
            center_crop: If true, crop the image before resizing.
        """
        self.size = size
        self.center_crop = center_crop
        self.tokenizer = tokenizer

        self.instance_data_root = Path(instance_data_root)
        if not self.instance_data_root.exists():
            raise ValueError(f"Instance images root {self.instance_data_root} doesn't exists.")

        self.instance_images_path = [
            x
            for x in Path(instance_data_root).iterdir()
            if str(x) != f"{instance_data_root}/dataset_info.json" and not os.path.isdir(x)
        ]
        self.num_instance_images = len(self.instance_images_path)
        self.instance_prompt = instance_prompt
        self._length = self.num_instance_images

        if class_data_root is not None:
            self.class_data_root = Path(class_data_root)
            self.class_data_root.mkdir(parents=True, exist_ok=True)
            self.class_images_path = list(self.class_data_root.iterdir())
            self.num_class_images = len(self.class_images_path)
            self._length = max(self.num_class_images, self.num_instance_images)
            self.class_prompt = class_prompt
        else:
            self.class_data_root = None

        self.image_transforms = transforms.Compose(
            [
                transforms.Resize(size, interpolation=transforms.InterpolationMode.BILINEAR),
                transforms.CenterCrop(size) if center_crop else transforms.RandomCrop(size),
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5]),
            ]
        )

    def __len__(self) -> int:
        """Return the size of dataset."""
        return self._length

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor]:
        """Return a dictionary of instance prompt ids, instance images, class prompt ids and class images as tensors."""
        example: Dict[str, torch.Tensor] = {}
        with Image.open(self.instance_images_path[index % self.num_instance_images]) as instance_image:
            if not instance_image.mode == "RGB":
                instance_image = instance_image.convert("RGB")
            example[constants.INSTANCE_IMAGES] = self.image_transforms(instance_image)
            example[constants.INSTANCE_PROMPT_IDS] = self.tokenizer(
                self.instance_prompt,
                truncation=True,
                padding=constants.MAX_LENGTH,
                max_length=self.tokenizer.model_max_length,
                return_tensors="pt",
            ).input_ids

        if self.class_data_root:
            with Image.open(self.class_images_path[index % self.num_class_images]) as class_image:
                if not class_image.mode == "RGB":
                    class_image = class_image.convert("RGB")
                example[constants.CLASS_IMAGES] = self.image_transforms(class_image)
                example[constants.CLASS_PROMPT_IDS] = self.tokenizer(
                    self.class_prompt,
                    truncation=True,
                    padding=constants.MAX_LENGTH,
                    max_length=self.tokenizer.model_max_length,
                    return_tensors="pt",
                ).input_ids
        return example


def collate_fn(
    examples: List[Dict[str, torch.Tensor]], with_prior_preservation: bool = False
) -> Dict[str, torch.Tensor]:
    """Create a batch of dataset from list of training examples."""
    input_ids = [example[constants.INSTANCE_PROMPT_IDS] for example in examples]
    pixel_values = [example[constants.INSTANCE_IMAGES] for example in examples]

    # Concat class and instance examples for prior preservation.
    # We do this to avoid doing two forward passes.
    if with_prior_preservation:
        input_ids += [example[constants.CLASS_PROMPT_IDS] for example in examples]
        pixel_values += [example[constants.CLASS_IMAGES] for example in examples]

    pixel_values = torch.stack(pixel_values)
    pixel_values = pixel_values.to(memory_format=torch.contiguous_format).float()

    input_ids = torch.cat(input_ids, dim=0)

    batch = {
        constants.INPUT_IDS: input_ids,
        constants.PIXEL_VALUES: pixel_values,
    }
    return batch
