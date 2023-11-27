TAR_GZ_PATTERN = "*.tar.gz"
INPUT_MODEL_UNTARRED_PATH = "/tmp"

MODEL_INFO_FILE_NAME = "__model_info__.json"

DATASET_INFO_FILE_NAME = "dataset_info.json"

FALSE_STR = "False"
NONE_STR = "None"
TRUE_STR = "True"
DEFAULT_NUM_CLASS_IMAGES = 100
DEFAULT_RESOLUTION = 512
DEFAULT_CENTER_CROP = FALSE_STR
DEFAULT_TRAIN_TEXT_ENCODER = FALSE_STR
DEFAULT_BATCH_SIZE = 1
DEFAULT_EPOCHS = 10
DEFAULT_MAX_TRAIN_STEPS = NONE_STR
DEFAULT_CHECKPOINTING_STEPS = 100
DEFAULT_LEARNING_RATE = 2e-6
DEFAULT_GRADIENT_ACCUMULATION_STEPS = 1
DEFAULT_GRADIENT_CHECKPOINTING = TRUE_STR
DEFAULT_CLASS_DATA_DIR = "class_data_dir"
DEFAULT_INSTANCE_PROMPT = NONE_STR
DEFAULT_CLASS_PROMPT = NONE_STR
DEFAULT_WITH_PRIOR_PRESERVATION = TRUE_STR
DEFAULT_PRIOR_LOSS_WEIGHT = 1.0
DEFAULT_SEED = 0
DEFAULT_SCALE_LR = FALSE_STR
DEFAULT_LR_SCHEDULER = "constant"
DEFAULT_LR_WARMUP_STEPS = 500
DEFAULT_USE_8BIT_ADAM = TRUE_STR
DEFAULT_ADAM_BETA1 = 0.9
DEFAULT_ADAM_BETA2 = 0.999
DEFAULT_ADAM_WEIGHT_DECAY = 1e-2
DEFAULT_ADAM_EPSILON = 1e-08
DEFAULT_MAX_GRAD_NORM = 1.0

DEFAULT_MIXED_PRECISION = NONE_STR
DEFAULT_PRIOR_GENERATION_PRECISION = NONE_STR

INSTANCE_PROMPT = "instance_prompt"
CLASS_PROMPT = "class_prompt"
INSTANCE_PROMPT_IDS = "instance_prompt_ids"
INSTANCE_IMAGES = "instance_images"
CLASS_PROMPT_IDS = "class_prompt_ids"
CLASS_IMAGES = "class_images"
INPUT_IDS = "input_ids"
EPSILON = "epsilon"
PIXEL_VALUES = "pixel_values"
MAX_LENGTH = "max_length"
PROMPT = "prompt"
INDEX = "index"
TOKENIZER = "tokenizer"
V_PREDICTION = "v_prediction"
MEAN = "mean"
USE_SCHEDULER = "use_scheduler"
SCHEDULER = "scheduler"
TEXT_ENCODER = "text_encoder"
CLIPTEXT_MODEL_TYPE = "CLIPTextModel"
RESOLUTION = "resolution"
ROBERTASERIES_MODELWITH_TRANSFORMATION_TYPE = "RobertaSeriesModelWithTransformation"

LR_SCHEDULER_CHOICES = {"linear", "cosine", "cosine_with_restarts", "polynomial", "constant", "constant_with_warmup"}
MIXED_PRECISION_CHOICES = {NONE_STR, "no", "fp16", "bf16"}
PRIOR_GENERATION_PRECISION_CHOICES = {NONE_STR, "no", "fp32", "fp16", "bf16"}