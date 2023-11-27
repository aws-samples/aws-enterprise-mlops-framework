import argparse
import hashlib
import logging
import os
from pathlib import Path
from typing import Dict
from typing import Union
import accelerate
import torch
import torch.nn.functional as F
import torch.utils.checkpoint
from constants import constants
from diffusers import DiffusionPipeline
from torch.utils.data import Dataset
from tqdm.auto import tqdm



class ClassPromptDataset(Dataset):
    """A simple dataset to prepare the prompts to generate class images on multiple GPUs."""

    def __init__(self, prompt: str, num_samples: int):
        """Create an object for prompt dataset."""
        self.prompt = prompt
        self.num_samples = num_samples

    def __len__(self) -> int:
        """Return the size of prompt dataset."""
        return self.num_samples

    def __getitem__(self, index: int) -> Dict[str, Union[str, int]]:
        """Get an item with prompt and the example index."""
        example = {}
        example[constants.PROMPT] = self.prompt
        example[constants.INDEX] = index
        return example


def generate_class_images(
    args: argparse.Namespace, accelerator: accelerate.accelerator.Accelerator, class_prompt: str
) -> None:
    """Generate class images."""
    logging.info("Generating class images")
    class_images_dir_path = Path(os.path.join(args.train, args.class_data_dir))
    if not class_images_dir_path.exists():
        class_images_dir_path.mkdir(parents=True)

    cur_class_images = len(list(class_images_dir_path.iterdir()))
    if cur_class_images < args.num_class_images:
        torch_dtype = torch.float16 if accelerator.device.type == "cuda" else torch.float32
        if args.prior_generation_precision == "fp32":
            torch_dtype = torch.float32
        elif args.prior_generation_precision == "fp16":
            torch_dtype = torch.float16
        elif args.prior_generation_precision == "bf16":
            torch_dtype = torch.bfloat16
        elif args.prior_generation_precision:
            logging.warning(
                f"prior_generation_precision={args.prior_generation_precision} is not supported. Please "
                f"set prior_generation_precision equal to '{constants.NONE_STR}' or 'fp32' or 'fp16' or "
                f"'bf16'."
            )
        try:
            pipeline = DiffusionPipeline.from_pretrained(
                constants.INPUT_MODEL_UNTARRED_PATH,
                torch_dtype=torch_dtype,
                safety_checker=None,
                revision=None,
            )
            pipeline.set_progress_bar_config(disable=True)
            num_new_images = args.num_class_images - cur_class_images
            logging.info(f"Number of class images to sample: {num_new_images}.")

            sample_dataset = ClassPromptDataset(class_prompt, num_new_images)
            sample_dataloader = torch.utils.data.DataLoader(sample_dataset, batch_size=args.batch_size)

            sample_dataloader = accelerator.prepare(sample_dataloader)
            pipeline.to(accelerator.device)

            for example in tqdm(
                sample_dataloader, desc="Generating class images", disable=not accelerator.is_local_main_process
            ):
                images = pipeline(example["prompt"]).images

                for i, image in enumerate(images):
                    hash_image = hashlib.sha1(image.tobytes()).hexdigest()
                    image_filename = os.path.join(
                        class_images_dir_path, f"{example['index'][i] + cur_class_images}-{hash_image}.jpg"
                    )
                    image.save(image_filename)
        finally:
            del pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
