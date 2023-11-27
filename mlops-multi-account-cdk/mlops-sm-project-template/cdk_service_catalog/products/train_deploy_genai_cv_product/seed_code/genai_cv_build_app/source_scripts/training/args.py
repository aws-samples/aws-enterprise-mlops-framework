import os
import argparse
from typing import Optional
from typing import Union
from constants import constants

LOW_TRUE_STR = "true"
LOW_FALSE_STR = "false"
NONE_STR = "None"


def str2bool(v: str) -> bool:
    """Convert string argument to a boolean value."""
    if v.lower() == LOW_TRUE_STR:
        return True
    elif v.lower() == LOW_FALSE_STR:
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def str2optionalint(v: str) -> Optional[int]:
    """Convert string argument to optional int."""
    if v == NONE_STR:
        return None
    else:
        try:
            return int(v)
        except Exception as e:
            raise argparse.ArgumentTypeError(f"Integer or None expected. Error: {e}.")


def str2optionalstr(v: str) -> Optional[str]:
    """Convert a string argument to optional string argument."""
    if v == NONE_STR:
        return None
    elif isinstance(v, str):
        return v
    else:
        raise argparse.ArgumentTypeError("None or string value expected.")


def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--model_dir", type=str, default=os.environ["SM_MODEL_DIR"],
                        help="Directory inside the container where the final model will be saved.")
    parser.add_argument("--output_data_dir", type=str, default=os.environ["SM_OUTPUT_DATA_DIR"],
                        help="Directory inside the container where the and validation images will be saved for "
                             "debugging purposes.")
    parser.add_argument(
        "--pretrained-model",
        type=str,
        default=os.environ["SM_CHANNEL_MODEL"],
        help="Directory with the pre-trained model.",
    )
    parser.add_argument(
        "--train", type=str, default=os.environ["SM_CHANNEL_TRAINING"], help="Directory with the training data."
    )
    parser.add_argument(
        "--class_data_dir",
        type=str,
        default=constants.DEFAULT_CLASS_DATA_DIR,
    )

    parser.add_argument(
        "--instance_token",
        type=str,
        required=True,
        help=f"Token which identifies the specific instance. Will be used to generate validation prompts. If {constants.DATASET_INFO_FILE_NAME} does not exist in the input directory, this will be used to generate a instance prompt."
    )
    parser.add_argument(
        "--class_token",
        type=str,
        required=True,
        help=f"Token which describes the class. Will be used to generate validation prompts. If {constants.DATASET_INFO_FILE_NAME} does not exist in the input directory, this will be used to generate a instance prompt."
    )
    parser.add_argument(
        "--with_prior_preservation",
        type=str2bool,
        default=constants.DEFAULT_WITH_PRIOR_PRESERVATION,
    )
    parser.add_argument(
        "--prior_loss_weight",
        type=float,
        default=constants.DEFAULT_PRIOR_LOSS_WEIGHT,
    )
    parser.add_argument(
        "--num_class_images",
        type=int,
        default=constants.DEFAULT_NUM_CLASS_IMAGES,
    )
    parser.add_argument("--seed", type=int, default=constants.DEFAULT_SEED)

    parser.add_argument("--center_crop", type=str2bool, default=constants.DEFAULT_CENTER_CROP)
    # Possible Improvement Currently text encoder = True results in results in CUDA memory issue for g4
    # machines. Fix it.
    parser.add_argument(
        "--train_text_encoder",
        type=str2bool,
        default=constants.DEFAULT_TRAIN_TEXT_ENCODER,
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=constants.DEFAULT_BATCH_SIZE,
    )
    parser.add_argument("--epochs", type=int, default=constants.DEFAULT_EPOCHS)
    parser.add_argument(
        "--max_steps",
        type=str2optionalint,
        default=constants.DEFAULT_MAX_TRAIN_STEPS,
    )
    parser.add_argument(
        "--checkpointing_steps",
        type=int,
        default=constants.DEFAULT_CHECKPOINTING_STEPS,
        help="Save a checkpoint of the training state every X updates."

    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=constants.DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )
    parser.add_argument(
        "--gradient_checkpointing",
        type=str2bool,
        default=constants.DEFAULT_GRADIENT_CHECKPOINTING,
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=constants.DEFAULT_LEARNING_RATE,
    )
    parser.add_argument(
        "--lr_scheduler",
        type=str,
        default=constants.DEFAULT_LR_SCHEDULER,
        choices=constants.LR_SCHEDULER_CHOICES,
    )

    parser.add_argument(
        "--adam_beta1",
        type=float,
        default=constants.DEFAULT_ADAM_BETA1,
    )
    parser.add_argument(
        "--adam_beta2",
        type=float,
        default=constants.DEFAULT_ADAM_BETA2,
    )
    parser.add_argument("--adam_weight_decay", type=float, default=constants.DEFAULT_ADAM_WEIGHT_DECAY)
    parser.add_argument(
        "--adam_epsilon",
        type=float,
        default=constants.DEFAULT_ADAM_EPSILON,
    )

    parser.add_argument("--max_grad_norm", default=constants.DEFAULT_MAX_GRAD_NORM, type=float)
    # parser.add_argument(
    #     "--compute_fid",
    #     type=args_utils.str2bool,
    #     default=constants.DEFAULT_COMPUTE_FID,
    # )

    # Following arguments are not yet exposed to the customer and default values are used.
    # They will be exposed when making improvements in the script.
    parser.add_argument(
        "--lr_warmup_steps",
        type=int,
        default=constants.DEFAULT_LR_WARMUP_STEPS,
        help="Number of steps for the warmup in the lr scheduler.",
    )
    parser.add_argument(
        "--use_8bit_adam",
        type=str2bool,
        default=constants.DEFAULT_USE_8BIT_ADAM,
        help="Whether or not to use 8-bit Adam from bitsandbytes.",
    )
    parser.add_argument(
        "--scale_lr",
        type=str2bool,
        default=constants.DEFAULT_SCALE_LR,
        help="Scale the learning rate by the number of GPUs, gradient accumulation steps, and batch size.",
    )
    parser.add_argument(
        "--mixed_precision",
        type=str2optionalstr,
        default=constants.DEFAULT_MIXED_PRECISION,
        choices=constants.MIXED_PRECISION_CHOICES,
        help=(
            "Whether to use mixed precision. Choose between fp16 and bf16 (bfloat16). Bf16 requires PyTorch >="
            " 1.10.and an Nvidia Ampere GPU."
        ),
    )
    parser.add_argument(
        "--prior_generation_precision",
        type=str2optionalstr,
        default=constants.DEFAULT_PRIOR_GENERATION_PRECISION,
        choices=constants.PRIOR_GENERATION_PRECISION_CHOICES,
        help=(
            "Choose prior generation precision between fp32, fp16 and bf16 (bfloat16). Bf16 requires PyTorch >="
            " 1.10.and an Nvidia Ampere GPU.  Default to  fp16 if a GPU is available else fp32."
        ),
    )
    parser.add_argument("--local_rank", type=int, default=-1, help="For distributed training: local_rank")
    return parser.parse_known_args()
