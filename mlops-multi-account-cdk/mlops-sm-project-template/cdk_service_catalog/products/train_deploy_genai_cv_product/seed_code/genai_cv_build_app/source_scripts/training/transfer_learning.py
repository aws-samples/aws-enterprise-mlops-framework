"""
Implementation is based on the StableDiffusion finetuning script by JumpStart (which is based on the HuggingFace DreamBooth training script).

Changes:
- Removed FID score computation
- Added new metric computation (based on img-img and img-text similarity)
- Added model training checkpointing (to evaluate model after different number of training stepts)
"""

import argparse
import itertools
import json
import logging
import os
import pathlib
import random
import sys
import tarfile
from typing import Optional
from typing import Tuple
from typing import List

import datasets
import diffusers
import numpy as np
import torch
import torch.nn.functional as F
import torch.utils.checkpoint
import transformers
import accelerate
from accelerate import Accelerator
from accelerate.utils import set_seed
from args import _parse_args
from class_images import generate_class_images
from constants import constants
from dataset import DreamBoothDataset
from dataset import collate_fn
from diffusers import DiffusionPipeline
from model import load_model_and_optimizer
from tqdm.auto import tqdm
from transformers import AutoTokenizer
from evaluation import compute_metrics


root = logging.getLogger()
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
root.addHandler(handler)


def get_prompts(args: argparse.Namespace) -> Tuple[str, Optional[str]]:
    """ Reads the instance and class prompt from the dataset info file. 
    If the file does not exist in the training data directory or if there is an parsing error, 
    the prompts will be created using the provided instance and class tokens. """

    dataset_info_path = os.path.join(args.train, constants.DATASET_INFO_FILE_NAME)
    get_prompts_from_file = os.path.isfile(dataset_info_path)
    
    # TODO: remove this part
    if get_prompts_from_file:
        with open(dataset_info_path) as f:
            try:
                dataset_info = json.loads(f.read())
                instance_prompt = dataset_info.get(constants.INSTANCE_PROMPT)
                class_prompt = dataset_info.get(constants.CLASS_PROMPT)
            except Exception as e:
                logging.error(f"Could not read/parse {constants.DATASET_INFO_FILE_NAME} file")
                get_prompts_from_file = False
                
    if not get_prompts_from_file:
        instance_prompt = f"a {args.instance_token} {args.class_token}"
        class_prompt = f"a {args.class_token}" if args.with_prior_preservation else None
        logging.info(f"{constants.DATASET_INFO_FILE_NAME} not found / error during parsing. Using instance and class tokens to generate prompts.")
    
    logging.info(f"Following prompts will be used for training: \ninstance_prompt={instance_prompt} \nclass_prompt={class_prompt}")
    return instance_prompt, class_prompt


def get_model_resolution() -> int:
    """ Reads the resolution from the provided pretrained model. """
    try:
        with open(os.path.join(constants.INPUT_MODEL_UNTARRED_PATH, constants.MODEL_INFO_FILE_NAME)) as f:
            model_info = json.loads(f.read())
        return model_info[constants.RESOLUTION]
    except Exception as e:
        logging.error(
            f"Could not find/read/parse {constants.MODEL_INFO_FILE_NAME} file, exception: '{e}'. "
            f"Model tarball is corrupted. Please include {constants.MODEL_INFO_FILE_NAME} with "
            "{'resolution':<<<DEFAULT_MODELRESOLUTION>>}."
        )
        raise
        
def get_validation_prompts(tokens: str) -> List[str]:
    return [
        f"a {tokens} in the jungle",
        f"a {tokens} in the snow",
        f"a {tokens} on the beach",
        f"a {tokens} on a cobblestone street",
        f"a {tokens} on top of pink fabric",
        f"a {tokens} on top of a wooden floor",
        f"a {tokens} with a city in the background",
        f"a {tokens} with a mountain in the background",
        f"a {tokens} with a blue house in the background",
        f"a {tokens} on top of a purple rug in a forest",
        f"a {tokens} with a wheat field in the background",
        f"a {tokens} with a tree and autumn leaves in the background",
        f"a {tokens} with the Eiffel Tower in the background",
        f"a {tokens} floating on top of water",
        f"a {tokens} floating in an ocean of milk",
        f"a {tokens} on top of green grass with sunflowers around it",
        f"a {tokens} on top of a mirror",
        f"a {tokens} on top of the sidewalk in a crowded street",
        f"a {tokens} on top of a dirt road",
        f"a {tokens} on top of a white rug",
        f"a red {tokens}",
        f"a purple {tokens}",
        f"a shiny {tokens}",
        f"a wet {tokens}",
        f"a cube shaped {tokens}",
    ]
      
    
def compute_validation_score(
        unet_unwrapped: diffusers.models.unet_2d_condition.UNet2DConditionModel, 
        text_encoder_unwrapped: transformers.models.clip.modeling_clip.CLIPTextModel, 
        generate_prompts: List[str], 
        compare_prompts: List[str], 
        checkpoint_path: str,
    ) -> float:

    logging.info("Start validation image generation")

    pipeline = DiffusionPipeline.from_pretrained(
        constants.INPUT_MODEL_UNTARRED_PATH,
        unet=unet_unwrapped,
        text_encoder=text_encoder_unwrapped,
        revision=None,
    )
    pipeline.set_progress_bar_config(disable=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)
    pipeline = pipeline.to(device)

    os.makedirs(checkpoint_path)
    for idx, prompt in enumerate(generate_prompts):
        image = pipeline(prompt, num_inference_steps=50, guidance_scale=7.5).images[0]
        image.save(os.path.join(checkpoint_path, f"{idx}.jpg"))
        image.close()

    del pipeline

    val_score = compute_metrics(args.train, checkpoint_path, compare_prompts)
    logging.info(f"Validation score: {val_score}")
    return val_score
        
        
def train_model(
    args: argparse.Namespace,
    text_encoder: transformers.models.clip.modeling_clip.CLIPTextModel,
    vae: diffusers.models.vae.AutoencoderKL,
    noise_scheduler: diffusers.schedulers.scheduling_ddpm.DDPMScheduler,
    unet: diffusers.models.unet_2d_condition.UNet2DConditionModel,
    accelerator: accelerate.accelerator.Accelerator,
    optimizer: accelerate.optimizer.AcceleratedOptimizer,
    lr_scheduler: accelerate.scheduler.AcceleratedScheduler,
    train_dataloader: accelerate.data_loader.DataLoaderShard,
    weight_dtype: torch.dtype,
) -> None:
    """Train the model and saves the best checkpoint."""
    # Only show the progress bar once on each machine.
    global_step = 0
    progress_bar = tqdm(range(args.max_steps), disable=not accelerator.is_local_main_process)
    progress_bar.set_description("Steps")
    
    val_generate_prompts = get_validation_prompts(f"{args.instance_token} {args.class_token}")
    val_compare_prompts = get_validation_prompts(args.class_token)
    val_scores = {}

    for epoch in range(args.epochs):
        logging.info(f"Epoch: {epoch}")
        unet.train()
        loss_accumulated = 0.0
        if args.train_text_encoder:
            text_encoder.train()
        for step, batch in enumerate(train_dataloader):
            
            with accelerator.accumulate(unet):
                # Convert images to latent space
                latents = vae.encode(batch[constants.PIXEL_VALUES].to(dtype=weight_dtype)).latent_dist.sample()
                latents = latents * 0.18215

                # Sample noise that we'll add to the latents
                noise = torch.randn_like(latents)
                bsz = latents.shape[0]
                # Sample a random timestep for each image
                timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (bsz,), device=latents.device)
                timesteps = timesteps.long()

                # Add noise to the latents according to the noise magnitude at each timestep
                # (this is the forward diffusion process)
                noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)

                # Get the text embedding for conditioning
                encoder_hidden_states = text_encoder(batch[constants.INPUT_IDS])[0]

                # Predict the noise residual
                model_pred = unet(noisy_latents, timesteps, encoder_hidden_states).sample

                # Get the target for loss depending on the prediction type
                if noise_scheduler.config.prediction_type == constants.EPSILON:
                    target = noise
                elif noise_scheduler.config.prediction_type == constants.V_PREDICTION:
                    target = noise_scheduler.get_velocity(latents, noise, timesteps)
                else:
                    raise ValueError(f"Unknown prediction type {noise_scheduler.config.prediction_type}")

                if args.with_prior_preservation:
                    # Chunk the noise and model_pred into two parts and compute the loss on each part separately.
                    model_pred, model_pred_prior = torch.chunk(model_pred, 2, dim=0)
                    target, target_prior = torch.chunk(target, 2, dim=0)

                    # Compute instance loss
                    loss = F.mse_loss(model_pred.float(), target.float(), reduction=constants.MEAN)

                    # Compute prior loss
                    prior_loss = F.mse_loss(model_pred_prior.float(), target_prior.float(), reduction=constants.MEAN)

                    # Add the prior loss to the instance loss.
                    loss = loss + args.prior_loss_weight * prior_loss
                else:
                    loss = F.mse_loss(model_pred.float(), target.float(), reduction=constants.MEAN)

                accelerator.backward(loss)
                if accelerator.sync_gradients:
                    params_to_clip = (
                        itertools.chain(unet.parameters(), text_encoder.parameters())
                        if args.train_text_encoder
                        else unet.parameters()
                    )
                    accelerator.clip_grad_norm_(params_to_clip, args.max_grad_norm)
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()

            # Checks if the accelerator has performed an optimization step behind the scenes
            if accelerator.sync_gradients:
                progress_bar.update(1)
                global_step += 1
                
                if accelerator.is_main_process:
                    if global_step % args.checkpointing_steps == 0:
                        unet_unwrapped = accelerator.unwrap_model(unet)
                        text_encoder_unwrapped =  accelerator.unwrap_model(text_encoder)
                        checkpoint_path = os.path.join(args.output_data_dir, f"checkpoint-{global_step}")
                        val_score = compute_validation_score(
                            unet_unwrapped, text_encoder_unwrapped, val_generate_prompts, val_compare_prompts, checkpoint_path
                        )
                        if len(val_scores)==0 or val_score > max(val_scores.values()):
                            logging.info(f"New best validation score ({val_score}) at step number: {global_step}")
                            logging.info(f"Saving the model")
                            pipeline = DiffusionPipeline.from_pretrained(
                                constants.INPUT_MODEL_UNTARRED_PATH,
                                unet=unet_unwrapped,
                                text_encoder=text_encoder_unwrapped,
                                revision=None,
                            )
                            pipeline.save_pretrained(args.model_dir)
                            del pipeline
                        val_scores[global_step] = val_score
                            
            logs = {"loss": loss.detach().item(), "lr": lr_scheduler.get_last_lr()[0]}
            loss_accumulated += logs["loss"]
            progress_bar.set_postfix(**logs)
            accelerator.log(logs, step=global_step)

            if global_step >= args.max_steps:
                logging.info(f"Reached max_steps={args.max_steps}. Stopping training now.")
                break

        train_avg_loss = loss_accumulated / (step + 1)
        logging.info(f"End epoch {epoch}: train_avg_loss={train_avg_loss}")
        
    logging.info(f"final_score={max(val_scores.values())}")
    with open(os.path.join(args.output_data_dir, "scores.json"), "w") as f:
        json.dump(val_scores, f)


def run_with_args(args: argparse.Namespace) -> None:
    """Generate dataset objects, set accelerate profile and train the model."""

    if args.seed is not None:
        set_seed(args.seed)
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        transformers.set_seed(args.seed)
    instance_prompt, class_prompt = get_prompts(args)
    accelerator = Accelerator(
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        mixed_precision=args.mixed_precision,
        log_with="all",
        logging_dir=args.model_dir,
    )

    if accelerator.is_local_main_process:
        datasets.utils.logging.set_verbosity_warning()
        transformers.utils.logging.set_verbosity_warning()
        diffusers.utils.logging.set_verbosity_info()
    else:
        datasets.utils.logging.set_verbosity_error()
        transformers.utils.logging.set_verbosity_error()
        diffusers.utils.logging.set_verbosity_error()

    if args.with_prior_preservation:
        generate_class_images(args, accelerator, class_prompt)
    else:
        logging.info(
            "Running without prior preservation. It may cause the model to overfit or experience language drift."
        )

    if args.scale_lr:
        args.learning_rate = (
            args.learning_rate * args.gradient_accumulation_steps * args.batch_size * accelerator.num_processes
        )
    # Taking cue from dreambooth and setting use_fast = False.
    tokenizer = AutoTokenizer.from_pretrained(
        constants.INPUT_MODEL_UNTARRED_PATH,
        subfolder=constants.TOKENIZER,
        revision=None,
        use_fast=False,
    )

    # Dataset and DataLoaders creation:
    train_dataset = DreamBoothDataset(
        instance_data_root=args.train,
        instance_prompt=instance_prompt,
        class_data_root=os.path.join(args.train, args.class_data_dir) if args.with_prior_preservation else None,
        class_prompt=class_prompt,
        tokenizer=tokenizer,
        size=get_model_resolution(),
        center_crop=args.center_crop,
    )

    train_dataloader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda examples: collate_fn(examples, args.with_prior_preservation),
        num_workers=1,
    )

    (
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
        overrode_max_train_steps,
    ) = load_model_and_optimizer(args, train_dataloader, accelerator)

    train_model(
        args=args,
        text_encoder=text_encoder,
        vae=vae,
        noise_scheduler=noise_scheduler,
        unet=unet,
        accelerator=accelerator,
        optimizer=optimizer,
        lr_scheduler=lr_scheduler,
        train_dataloader=train_dataloader,
        weight_dtype=weight_dtype,
    )
    accelerator.wait_for_everyone()
    accelerator.end_training()


def extract_pretrained_model_tarball(pretrained_tarball_dir: str, extracted_model_dir: str) -> None:
    """Extract the pre-trained model tarball to the extracted model directory."""
    input_model_path = next(pathlib.Path(pretrained_tarball_dir).glob(constants.TAR_GZ_PATTERN))
    with tarfile.open(input_model_path, "r") as saved_model_tar:
        saved_model_tar.extractall(extracted_model_dir)


if __name__ == "__main__":
    args, unknown = _parse_args()
    logging.info(f"Running training scripts with arguments: {args}.")
    logging.info(f"Ignoring unrecognized arguments: {unknown}.")
    extract_pretrained_model_tarball(args.pretrained_model, constants.INPUT_MODEL_UNTARRED_PATH)
    run_with_args(args)
