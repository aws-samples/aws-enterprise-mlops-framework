import argparse
import itertools
import logging
import math
from typing import Tuple
from typing import Union

import accelerate
import diffusers
import torch
import torch.nn.functional as F
import torch.utils.checkpoint
import transformers
from constants import constants
from diffusers import AutoencoderKL
from diffusers import DDPMScheduler
from diffusers import UNet2DConditionModel
from diffusers.optimization import get_scheduler
from diffusers.pipelines.alt_diffusion.modeling_roberta_series import RobertaSeriesModelWithTransformation
from transformers import CLIPTextModel
from transformers import PretrainedConfig


def import_model_class(
    pretrained_model: str,
) -> Union[type(CLIPTextModel), type(RobertaSeriesModelWithTransformation)]:
    """Based on the model type, return the model class for the textual model."""
    text_encoder_config = PretrainedConfig.from_pretrained(
        pretrained_model,
        subfolder=constants.TEXT_ENCODER,
        revision=None,
    )
    model_class = text_encoder_config.architectures[0]

    if model_class == constants.CLIPTEXT_MODEL_TYPE:

        return CLIPTextModel
    elif model_class == constants.ROBERTASERIES_MODELWITH_TRANSFORMATION_TYPE:

        return RobertaSeriesModelWithTransformation
    else:
        raise ValueError(f"{model_class} is not supported.")


def load_model_and_optimizer(
    args: argparse.Namespace,
    train_dataloader: torch.utils.data.dataloader.DataLoader,
    accelerator: accelerate.accelerator.Accelerator,
) -> Tuple[
    accelerate.data_loader.DataLoaderShard,
    accelerate.optimizer.AcceleratedOptimizer,
    diffusers.schedulers.scheduling_ddpm.DDPMScheduler,
    accelerate.scheduler.AcceleratedScheduler,
    transformers.models.clip.modeling_clip.CLIPTextModel,
    diffusers.models.vae.AutoencoderKL,
    diffusers.models.unet_2d_condition.UNet2DConditionModel,
    int,
    accelerate.accelerator.Accelerator,
    argparse.Namespace,
    int,
    torch.dtype,
    bool,
]:
    """Load the model, learning rate scheduler, optimizer and other training related artifacts."""

    logging.info("Loading model and optimizer.")

    # import correct text encoder class
    text_encoder_cls = import_model_class(constants.INPUT_MODEL_UNTARRED_PATH)

    # Load scheduler and models
    noise_scheduler = DDPMScheduler.from_pretrained(constants.INPUT_MODEL_UNTARRED_PATH, subfolder="scheduler")
    text_encoder = text_encoder_cls.from_pretrained(
        constants.INPUT_MODEL_UNTARRED_PATH, subfolder="text_encoder", revision=None
    )
    vae = AutoencoderKL.from_pretrained(constants.INPUT_MODEL_UNTARRED_PATH, subfolder="vae", revision=None)
    unet = UNet2DConditionModel.from_pretrained(constants.INPUT_MODEL_UNTARRED_PATH, subfolder="unet", revision=None)

    vae.requires_grad_(False)
    if not args.train_text_encoder:
        text_encoder.requires_grad_(False)

    if args.gradient_checkpointing:
        logging.info("Enabling gradient checkpointing for unet.")
        unet.enable_gradient_checkpointing()
        if args.train_text_encoder:
            logging.info("Enabling gradient checkpointing for text encoder.")
            text_encoder.gradient_checkpointing_enable()

    # Use 8-bit Adam for lower memory usage or to fine-tune the model in 16GB GPUs
    if args.use_8bit_adam:
        try:
            import bitsandbytes as bnb
        except ImportError:
            logging.error(
                "To use 8-bit Adam, bitsandbytes library is required but was not found. "
                "This may be due to the cuda environment in instance type being not compatible with "
                "bitsandbytes library."
            )
            raise
        logging.info("Using AdamW8bit optimizer for training.")
        optimizer_class = bnb.optim.AdamW8bit
    else:
        logging.info("Using AdamW optimizer for training.")
        optimizer_class = torch.optim.AdamW

    # Optimizer creation
    params_to_optimize = (
        itertools.chain(unet.parameters(), text_encoder.parameters()) if args.train_text_encoder else unet.parameters()
    )
    optimizer = optimizer_class(
        params_to_optimize,
        lr=args.learning_rate,
        betas=(args.adam_beta1, args.adam_beta2),
        weight_decay=args.adam_weight_decay,
        eps=args.adam_epsilon,
    )

    # Scheduler and math around the number of training steps.
    overrode_max_steps = False
    num_update_steps_per_epoch = math.ceil(len(train_dataloader) / args.gradient_accumulation_steps)
    if args.max_steps is None:
        args.max_steps = args.epochs * num_update_steps_per_epoch
        overrode_max_steps = True

    lr_scheduler = get_scheduler(
        args.lr_scheduler,
        optimizer=optimizer,
        num_warmup_steps=args.lr_warmup_steps * args.gradient_accumulation_steps,
        num_training_steps=args.max_steps * args.gradient_accumulation_steps,
    )

    # Prepare everything with our `accelerator`.
    if args.train_text_encoder:
        logging.info("Preparing unet, text encoder, optimizer, train dataloader and lr scheduler with accelerator.")
        unet, text_encoder, optimizer, train_dataloader, lr_scheduler = accelerator.prepare(
            unet, text_encoder, optimizer, train_dataloader, lr_scheduler
        )
    else:
        logging.info("Preparing unet, optimizer, train dataloader and lr scheduler with accelerator.")
        unet, optimizer, train_dataloader, lr_scheduler = accelerator.prepare(
            unet, optimizer, train_dataloader, lr_scheduler
        )

    # For mixed precision training we cast the text_encoder and vae weights to half-precision
    # as these models are only used for inference, keeping weights in full precision is not required.
    weight_dtype = torch.float32
    if accelerator.mixed_precision == "fp16":
        weight_dtype = torch.float16
    elif accelerator.mixed_precision == "bf16":
        weight_dtype = torch.bfloat16

    # Move vae and text_encoder to device and cast to weight_dtype
    vae.to(accelerator.device, dtype=weight_dtype)
    if not args.train_text_encoder:
        logging.info(f"Moving text encoder to {accelerator.device} device.")
        text_encoder.to(accelerator.device, dtype=weight_dtype)

    # We need to recalculate our total training steps as the size of the training dataloader may have changed.
    num_update_steps_per_epoch = math.ceil(len(train_dataloader) / args.gradient_accumulation_steps)
    if overrode_max_steps:
        args.max_steps = args.epochs * num_update_steps_per_epoch
    # Afterwards we recalculate our number of training epochs
    args.epochs = math.ceil(args.max_steps / num_update_steps_per_epoch)

    # We need to initialize the trackers we use, and also store our configuration.
    # The trackers initializes automatically on the main process.
    if accelerator.is_main_process:
        accelerator.init_trackers("dreambooth", config=vars(args))

    # Train!
    total_batch_size = args.batch_size * accelerator.num_processes * args.gradient_accumulation_steps
    return (
        train_dataloader,
        optimizer,
        noise_scheduler,
        lr_scheduler,
        text_encoder,
        vae,
        unet,
        total_batch_size,
        accelerator,
        args,
        num_update_steps_per_epoch,
        weight_dtype,
        overrode_max_steps,
    )
