""" This is the custom text2image inference code provided by JumpStart"""
import base64
import json
import logging
import os
from copy import copy
from io import BytesIO
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import numpy as np
import torch
from constants import constants
from diffusers import EulerDiscreteScheduler
from diffusers import StableDiffusionPipeline as Txt2ImgPipeline
from PIL import Image
from sagemaker_inference import encoder
from transformers import set_seed


def use_scheduler(input_model_untarred_path: str) -> bool:
    """Read the model_info file from file system to check if the input model needs to be used with scheduler.

    If the __model_info__ file does not exist or if it does not contain information about scheduler, we assume that
    the scheduler was not used.
    """
    input_model_info_file_path = os.path.join(input_model_untarred_path, constants.MODEL_INFO_FILE_NAME)
    try:
        with open(input_model_info_file_path, "r") as f:
            model_info = json.load(f)
            is_scheduler_used = model_info[constants.USE_SCHEDULER]
            assert type(is_scheduler_used) == bool, (
                "model_info file corrupted "
                f"{constants.USE_SCHEDULER} parameter must be "
                f"either True or False, got {is_scheduler_used}."
            )
            return is_scheduler_used
    except FileNotFoundError:
        logging.info(f"'{input_model_info_file_path}' file could not be found. Assuming scheduler is not used.")
        return False
    except KeyError:
        logging.info(f"'{constants.USE_SCHEDULER}' not in model info file. Assuming scheduler is not used.")
        return False
    except Exception as e:
        logging.error(
            f"Could not read or parse model_info file, exception: '{e}'. To run inference,  "
            f"please create a json file {input_model_info_file_path} with"
            f" {constants.USE_SCHEDULER} parameter set to True or False. "
        )
        raise


def model_fn(model_dir: str) -> Txt2ImgPipeline:
    """Create our inference task as a delegate to the model.

    This runs only once per one worker.

    Args:
        model_dir (str): directory where the model files are stored
    Returns:
        Txt2ImgPipeline: a huggingface pipeline for generating image from text
    Raises:
        ValueError if the model file cannot be found.
    """
    try:
        if use_scheduler(model_dir):
            scheduler = EulerDiscreteScheduler.from_pretrained(model_dir, subfolder=constants.SCHEDULER)
            model = Txt2ImgPipeline.from_pretrained(model_dir, scheduler=scheduler)
        else:
            model = Txt2ImgPipeline.from_pretrained(model_dir)
        model = model.to(constants.CUDA)

        return model
    except Exception:
        logging.exception(f"Failed to load model from: {model_dir}")
        raise


def _validate_payload(payload: Dict[str, Any]) -> None:
    """Validate the parameters in the input loads.

    Checks if height, width, num_inference_steps and num_images_per_prompt are integers.
    Checks if height and width are divisible by 8.
    Checks if guidance_scale, num_return_sequences, num_beams, top_p and temprature are in bounds.
    Checks if do_sample is boolean.
    Checks max_length, num_return_sequences, num_beams and seed are integers.
    Args:
        payload: a decoded input payload (dictionary of input parameter and values)
    """

    for param_name in payload:
        if param_name not in constants.ALL_PARAM_NAMES:
            raise KeyError(
                f"Input payload contains an invalid key {param_name}. Valid keys are {constants.ALL_PARAM_NAMES}."
            )
    if constants.PROMPT not in payload:
        raise KeyError(f"Input payload must contain '{constants.PROMPT}' key.")

    for param_name in [
        constants.HEIGHT,
        constants.WIDTH,
        constants.NUM_INFERENCE_STEPS,
        constants.NUM_IMAGES_PER_PROMPT,
        constants.SEED,
    ]:
        if param_name in payload:
            if type(payload[param_name]) != int:
                raise ValueError(f"{param_name} must be an integer, got {payload[param_name]}.")

    for param_name in [constants.GUIDANCE_SCALE, constants.ETA]:
        if param_name in payload:
            if type(payload[param_name]) != float and type(payload[param_name]) != int:
                raise ValueError(f"{param_name} must be an int or float, got {payload[param_name]}.")

    if constants.HEIGHT in payload:
        if payload[constants.HEIGHT] % 8 != 0:
            raise ValueError(f"{constants.HEIGHT} must be divisible by 8, got {payload[constants.HEIGHT]}.")
    if constants.WIDTH in payload:
        if payload[constants.WIDTH] % 8 != 0:
            raise ValueError(f"{constants.WIDTH} must be divisible by 8, got {payload[constants.WIDTH]}.")
    for param_name in [constants.NUM_INFERENCE_STEPS, constants.NUM_IMAGES_PER_PROMPT, constants.BATCH_SIZE]:
        if param_name in payload:
            if payload[param_name] < 1:
                raise ValueError(f"{param_name} must be at least 1, got {payload[param_name]}.")


def encode_image_jpeg(image: Image.Image) -> str:
    """Encode the image with base64.b64 encoding after converting JPEG format and loading as bytes."""
    out = BytesIO()
    image.save(out, format=constants.JPEG_FORMAT)
    generated_image_bytes = out.getvalue()
    generated_image_encoded = base64.b64encode(generated_image_bytes).decode()
    return generated_image_encoded


def _set_default_width_height(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Set the default width and height if not in the input payload."""

    if constants.WIDTH not in payload:
        payload[constants.WIDTH] = constants.DEFAULT_WIDTH_PIXELS
    if constants.HEIGHT not in payload:
        payload[constants.HEIGHT] = constants.DEFAULT_HEIGHT_PIXELS
    return payload


def generate_images_in_batches(dreamer: Txt2ImgPipeline, payload: Dict[str, Any]) -> List[Image.Image]:
    """Split the list into batches, run inference on each items, return the list of generated image.

    Create a list of prompts of size (#prompts)*num_images_per_prompt.

    Default batch size is assumed to be 1.
    """

    num_images_per_prompt = payload.get(constants.NUM_IMAGES_PER_PROMPT, 1)

    payload_prompt = payload[constants.PROMPT]
    negative_payload_prompt = payload.get(constants.NEGATIVE_PROMPT)
    negative_prompt_delineated_list: Optional[List[str]] = None
    if isinstance(payload_prompt, list):
        prompts_delineated_list = [prompt for prompt in payload_prompt for _ in range(num_images_per_prompt)]
        if negative_payload_prompt:
            negative_prompt_delineated_list = [
                negative_prompt for negative_prompt in negative_payload_prompt for _ in range(num_images_per_prompt)
            ]
    elif isinstance(payload_prompt, str):
        prompts_delineated_list = [payload_prompt for _ in range(num_images_per_prompt)]
        if negative_payload_prompt:
            negative_prompt_delineated_list = [negative_payload_prompt for _ in range(num_images_per_prompt)]
    else:
        raise ValueError(f"{constants.PROMPT} must be a string or a list of string. Got {payload_prompt}.")

    batch_size = payload.get(constants.BATCH_SIZE, 1)
    generated_images: List[Image.Image] = []
    for pos in range(0, len(prompts_delineated_list), batch_size):
        # Construct the batch paylod to be fed into the model.
        # There are num_images_per_prompt copies of each prompt in payload_delineated_list. So, we ignore the parameter
        # in the batch_payload.
        # Batch size is a parameter to the script only. Model does not support batch_size parameter. So, we ignore the
        # batch_size parameter in batch_payload.
        batch_payload = {
            x: y
            for x, y in payload.items()
            if x
            not in [constants.PROMPT, constants.BATCH_SIZE, constants.NUM_IMAGES_PER_PROMPT, constants.NEGATIVE_PROMPT]
        }

        batch_payload[constants.PROMPT] = prompts_delineated_list[pos : pos + batch_size]
        if negative_payload_prompt:
            batch_payload[constants.NEGATIVE_PROMPT] = negative_prompt_delineated_list[pos : pos + batch_size]
        generated_images.extend(dreamer(**batch_payload).images)

    return generated_images


def transform_fn(dreamer: Txt2ImgPipeline, input_data: bytes, content_type: str, accept: str) -> bytes:
    """Make predictions against the model and return a serialized response.

    The function signature conforms to the SM contract.

    Args:
        dreamer (Txt2ImgPipeline): a huggingface pipeline
        input_data (obj): the request data.
        content_type (str): the request content type.
        accept (str): accept header expected by the client.
    Returns:
        obj: a byte string of the prediction
    """
    if content_type == constants.APPLICATION_X_TEXT:
        try:
            input_text = input_data.decode(constants.STR_DECODE_CODE)
        except Exception:
            logging.exception(
                f"Failed to parse input payload. For content_type={constants.APPLICATION_X_TEXT}, input "
                f"payload must be a string encoded in utf-8 format."
            )
            raise
        try:
            generated_img = dreamer(
                input_text,
                width=constants.DEFAULT_WIDTH_PIXELS,
                height=constants.DEFAULT_HEIGHT_PIXELS,
                guidance_scale=constants.DEFAULT_GUIDANCE_SCALE,
            ).images[0]

            if constants.JPEG_ACCEPT_EXTENSION in accept:
                output = {constants.GENERATED_IMAGE: encode_image_jpeg(generated_img), constants.PROMPT: input_text}
                accept = accept.replace(constants.JPEG_ACCEPT_EXTENSION, "")
            else:
                output = {
                    constants.GENERATED_IMAGE: np.asarray(generated_img),
                    constants.PROMPT: input_text,
                }
        except Exception:
            logging.exception("Failed to do inference")
            raise
    elif content_type == constants.APPLICATION_JSON:
        try:
            payload = json.loads(input_data)
        except Exception:
            logging.exception(
                f"Failed to parse input payload. For content_type={constants.APPLICATION_JSON}, input "
                f"payload must be a json encoded dictionary with keys {constants.ALL_PARAM_NAMES}."
            )
            raise
        _validate_payload(payload)
        if constants.SEED in payload:
            set_seed(payload[constants.SEED])
            del payload[constants.SEED]

        payload = _set_default_width_height(payload)
        generated_images: List[Image.Image] = []
        try:
            generated_images = generate_images_in_batches(dreamer, payload)

            if constants.JPEG_ACCEPT_EXTENSION in accept:
                output = {
                    constants.GENERATED_IMAGES: [encode_image_jpeg(image) for image in generated_images],
                    constants.PROMPT: payload[constants.PROMPT],
                }
                accept = accept.replace(constants.JPEG_ACCEPT_EXTENSION, "")
            else:
                output = {
                    constants.GENERATED_IMAGES: [np.asarray(generated_img) for generated_img in generated_images],
                    constants.PROMPT: payload[constants.PROMPT],
                }
        except torch.cuda.OutOfMemoryError as e:
            logging.error(
                "Model ran out of CUDA memory while generating images. Please reduce height and width or "
                f"deploy the model on an instance type with more GPU memory. Error: {e}."
            )
            raise
        except Exception:
            logging.exception("Failed to generate images.")
            raise
        finally:
            if generated_images:
                for generated_image in generated_images:
                    generated_image.close()
    else:
        raise ValueError('{{"error": "unsupported content type {}"}}'.format(content_type or "unknown"))

    if accept.endswith(constants.VERBOSE_EXTENSION):
        accept = accept.rstrip(constants.VERBOSE_EXTENSION)

    return encoder.encode(output, accept)
