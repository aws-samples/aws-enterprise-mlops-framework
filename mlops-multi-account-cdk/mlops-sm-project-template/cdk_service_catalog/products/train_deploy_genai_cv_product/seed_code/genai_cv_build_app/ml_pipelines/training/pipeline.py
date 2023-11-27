"""Example workflow pipeline script for abalone pipeline.

                                               . -ModelStep
                                              .
    Process-> Train -> Evaluate -> Condition .
                                              .
                                               . -(stop)

Implements a get_pipeline(**kwargs) method.
"""
import logging
import os
from typing import Dict, Any

import boto3
import sagemaker
import sagemaker.session

from sagemaker.inputs import TrainingInput
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import (
    ConditionStep,
)
from sagemaker.workflow.parameters import (
    ParameterString,
)
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import (
    TrainingStep,
)
from sagemaker.workflow.functions import Join
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker import model_uris
from sagemaker.huggingface import HuggingFace
from sagemaker.huggingface.model import HuggingFaceModel
from sagemaker.utils import name_from_base
from sagemaker import hyperparameters as _hyperparameters

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def get_sagemaker_client(region):
    """Gets the sagemaker client.

        Args:
            region: the aws region to start the session
            default_bucket: the bucket to use for storing the artifacts

        Returns:
            `sagemaker.session.Session instance
        """
    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")
    return sagemaker_client


def get_session(region, default_bucket):
    """Gets the sagemaker session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        `sagemaker.session.Session instance
    """

    boto_session = boto3.Session(region_name=region)

    sagemaker_client = boto_session.client("sagemaker")
    runtime_client = boto_session.client("sagemaker-runtime")
    return sagemaker.session.Session(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        sagemaker_runtime_client=runtime_client,
        default_bucket=default_bucket,
    )


def get_pipeline_session(region, default_bucket):
    """Gets the pipeline session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        PipelineSession instance
    """

    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")

    return PipelineSession(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        default_bucket=default_bucket,
    )


def get_pipeline_custom_tags(new_tags, region, sagemaker_project_name=None):
    try:
        sm_client = get_sagemaker_client(region)
        response = sm_client.describe_project(ProjectName=sagemaker_project_name)
        sagemaker_project_arn = response["ProjectArn"]
        response = sm_client.list_tags(
            ResourceArn=sagemaker_project_arn)
        project_tags = response["Tags"]
        for project_tag in project_tags:
            new_tags.append(project_tag)
    except Exception as e:
        print(f"Error getting project tags: {e}")
    return new_tags


def get_pipeline(
        region,
        sagemaker_project_name=None,
        role=None,
        default_bucket=None,
        bucket_kms_id=None,
        model_package_group_name="DreamboothPackageGroup",
        pipeline_name="DreamboothPipeline",
        base_job_prefix="Dreambooth",
        training_instance_type="ml.g5.2xlarge",
):
    """Gets a SageMaker ML Pipeline instance working with on abalone data.

    Args:

        region: AWS region to create and run the pipeline.
        sagemaker_project_name: sagemaker project name
        role: IAM role to create and run steps and pipeline.
        default_bucket: the bucket to use for storing the artifacts
        bucket_kms_id: bucket kms id
        model_package_group_name: model package group name
        pipeline_name: sagemaker pipeline name
        base_job_prefix: base job prefix
        training_instance_type: training instance type



    Returns:
        an instance of a pipeline
    """

    logging.basicConfig(level=logging.INFO)
    logger: logging.Logger = logging.getLogger('Pipeline')

    logger.info(f'sagemaker_project_name : {sagemaker_project_name}, '
                f'bucket_kms_id : {bucket_kms_id}, default_bucket : {default_bucket}, role : {role}')

    sagemaker_session = get_session(region, default_bucket)
    if role is None:
        role = sagemaker.session.get_execution_role(sagemaker_session)

    pipeline_session = get_pipeline_session(region, default_bucket)

    # parameters for pipeline execution
    model_approval_status = ParameterString(
        name="ModelApprovalStatus", default_value="PendingManualApproval"
    )

    # Sample training data is available in this bucket
    training_data_bucket = f"jumpstart-cache-prod-{region}"
    training_data_prefix = "training-datasets/dogs_sd_finetuning/"
    training_dataset_s3_path = f"s3://{training_data_bucket}/{training_data_prefix}"
    output_path = f"s3://{sagemaker_session.default_bucket()}/{base_job_prefix}/train"

    input_data = ParameterString(
        name="InputDataUrl",
        default_value=training_dataset_s3_path,
    )

    instance_token = ParameterString(
        name="InstanceToken",
        default_value="A photo of a Doppler dog",
    )
    class_token = ParameterString(
        name="ClassToken",
        default_value="A photo of a dog"
    )

    # training step for generating model artifacts
    train_model_id, train_model_version, train_scope = (
        "model-txt2img-stabilityai-stable-diffusion-v2-1-base",
        "*",
        "training",
    )

    training_job_name = name_from_base(f"jumpstart-example-{train_model_id}-transfer-learning")

    # training step for generating model artifacts
    train_model_uri = model_uris.retrieve(
        model_id=train_model_id, model_version=train_model_version, model_scope=train_scope
    )

    logger.info(f'training_job_name : {training_job_name}')
    logger.info(f'training_model_uri : {train_model_uri}')
    logger.info(f'output_path : {output_path}')

    # s3://jumpstart-cache-prod-us-east-1/stabilityai-infer/prepack/v1.0.0/infer-prepack-model-txt2img-stabilityai-stable-diffusion-v2-1-base.tar.gz

    # hyperparameters = {
    #     "instance_token": instance_token,
    #     "class_token": Join(values=["'", class_token, "'"]),
    #     # adding additional single quotes to support strings containing multiple words and spaces
    #     "max_steps": 800,
    #     "checkpointing_steps": 100,
    #     "batch_size": 2,
    #     "gradient_accumulation_steps": 2,
    #     "num_class_images": 500,
    #     "with_prior_preservation": True,
    #     "prior_loss_weight": 1
    # }

    # Retrieve the default hyper-parameters for fine-tuning the model
    hyperparameters: Dict[str, Any] = _hyperparameters.retrieve_default(
        model_id=train_model_id, model_version=train_model_version
    )

    # [Optional] Override default hyperparameters with custom values
    hyperparameters["max_steps"] = 100
    hyperparameters["instance_token"] = instance_token
    hyperparameters["class_token"] = Join(values=["'", class_token, "'"])
    hyperparameters["with_prior_preservation"] = True
    hyperparameters["num_class_images"] = 20

    logger.info(f'hyperparameters : {hyperparameters}')

    estimator = HuggingFace(
        role=role,
        source_dir="source_scripts/training",
        model_uri=train_model_uri,
        entry_point="transfer_learning.py",
        instance_count=1,
        instance_type=training_instance_type,
        max_run=360000,
        hyperparameters=hyperparameters,
        output_path=output_path,
        output_kms_key=bucket_kms_id,
        base_job_name=training_job_name,
        transformers_version="4.17.0",
        pytorch_version="1.10.2",
        py_version="py38",
        sagemaker_session=pipeline_session,
        metric_definitions=[{"Name": "score", "Regex": "final_score=([-+]?\\d\\.?\\d*)"}]
    )

    step_args = estimator.fit(
        inputs={
            "training": TrainingInput(
                s3_data=input_data,
            ),
        },
    )
    step_train = TrainingStep(
        name="TrainDreambooth",
        step_args=step_args,
    )

    # model registration step
    model = HuggingFaceModel(
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=pipeline_session,
        role=role,
        transformers_version="4.17.0",
        pytorch_version="1.10.2",
        py_version="py38",
        entry_point="inference.py",
        source_dir="source_scripts/inference",
        model_kms_key=bucket_kms_id
    )
    step_args = model.register(
        content_types=["application/json", "application/x-text"],
        response_types=["application/json", "application/json;jpeg"],
        inference_instances=["ml.g4dn.2xlarge"],
        transform_instances=["ml.g4dn.2xlarge"],
        model_package_group_name=model_package_group_name,
        approval_status=model_approval_status,
    )
    step_register = ModelStep(
        name="RegisterDreambooth",
        step_args=step_args,
    )

    # condition step for evaluating model quality and branching execution
    cond_lte = ConditionGreaterThanOrEqualTo(
        left=step_train.properties.FinalMetricDataList['score'].Value,
        right=0.2,  # TODO: select right value
    )
    step_cond = ConditionStep(
        name="CheckScoreDreambooth",
        conditions=[cond_lte],
        if_steps=[step_register],
        else_steps=[],
    )

    # pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            training_instance_type,
            model_approval_status,
            input_data,
            instance_token,
            class_token
        ],
        steps=[step_train, step_cond],
        sagemaker_session=pipeline_session,
    )
    return pipeline
