# SageMaker Build - Train Pipelines

This folder contains all the SageMaker Pipelines of your project.

`buildspec.yml` defines how to run a pipeline after each commit to this repository.
`ml_pipelines/` contains the SageMaker pipelines definitions.
The expected output of the your main pipeline (here `text2sql_finetune/pipeline.py`) is a model registered to SageMaker Model Registry.

`text2sql_finetune/source_scripts/` contains the underlying scripts run by the steps of your SageMaker Pipelines. For example, if your SageMaker Pipeline runs a Processing Job as part of a Processing Step, the code being run inside the Processing Job should be defined in this folder.

A typical folder structure for `source_scripts/` can contain `helpers`, `preprocessing`, `training`, `postprocessing`, `evaluate`, depending on the nature of the steps run as part of the SageMaker Pipeline.

We provide here an example for finetuning CodeLlama on the task text to SQL with Parameter Efficient Fine-Tuning (PEFT).

Additionally, if you use custom containers, the Dockerfile definitions should be found in that folder.

`tests/` contains the unittests for your `source_scripts/`

`notebooks/` contains experimentation notebooks.

# Run pipeline from command line from this folder

```
pip install -e .

run-pipeline --module-name ml_pipelines.text2sql_finetune.pipeline --role-arn YOUR_SAGEMAKER_EXECUTION_ROLE_ARN --kwargs '{"region":"eu-west-1"}'
```
