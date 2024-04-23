# Developer Guide
While the solution presented in [README](README.md) can be used as is, this repository is built with the intention to be customized for the need of your organization.

[mlops_sm_project_template](mlops_sm_project_template/) will:
- Create a Service Catalogue Portfolio via [service_catalog_stack](mlops_sm_project_template/service_catalog_stack.py).
- Create SageMaker Project Templates (Service Catalog Products) inside the Service Catalogue Portfolio. Each SageMaker Project template is a CDK stack called `MLOpsStack` inside [templates](mlops_sm_project_template/templates/)

The high level design of each of those SageMaker Project Templates as described in [README](README.md) is the same:
- Two CodeCommit repositories (one for `build` and one for `deploy`) instantiated with their respective seed code found in [seed_code](mlops_sm_project_template/templates/train_deploy_basic_product/seed_code/)
- Two CodePipelines linked to the respective repositories, whose definitions are provided as CDK Constructs under [pipeline_constructs](mlops_sm_project_template/templates/constructs/)

By default, if changes to the `build` or `deploy` repositories of a project are specific to a use case (work done by Data Scientists), we do not recommend changing seed codes.
However if you observe repeated patterns that you want to make available accross your organization, for example:
- You see many projects that would benefit from having an example SageMaker Processing step querying Amazon Athena
- You want a project that provides an example to train and deploy an LLM (Large Language Model)
- You want a project to deploy not just an endpoint but for example an API Gateway and a Lambda function

Then you could either modify an existing [template project stack](mlops_sm_project_template/templates/) or create your own.

If you want to create a new Service Catalogue Product / SageMaker Project template in the Service Catalogue Portfolio, you should:
- Create a new `<TEMPLATE_NAME>/project.py` in [templates](mlops_sm_project_template/templates/) (you can copy a pre-existing one such as [train_deploy_basic_product](mlops_sm_project_template/templates/train_deploy_basic_product/project.py))
- You can reuse existing or create new CICD pipeline constructs in as in [pipeline_constructs](mlops_sm_project_template/templates/constructs/)
- You can provide your own `seed code` for either the build or deploy app or both. Your `<TEMPLATE_NAME>/project.py` should reference to the new ones you created.
- The name of the Project Construct in `project.py` is `MLOpsStack` and it inherits from `sc.ProductStack`


By default a SageMaker Project Template contains two repositories (but you can change that based on your organization's requirements). The definitions of those repositories are contained in [seed_code](mlops_sm_project_template/templates/train_deploy_basic_product/seed_code/).
The [service_catalog_stack](mlops_sm_project_template/service_catalog_stack.py) packages the content of the subfolders in s3 via `servicecatalog.CloudFormationProduct` by converting them to CloudFormation.

This is done through helper scripts as long as the naming convention is followed: 
- Project templates need to be under the [templates](mlops_sm_project_template/templates) folder
- They need to be in their own directory with the suffix `_product`
- They need to contain an `__init__.py` and `project.py`

Tip: It is easier to retro-fit a usecase to the current standards by copying and modifing the current project templates - see section below

Whenever a SageMaker Project Template is instantiated by a user, the CodeCommit repositories will be initially populated with the seed code from local directories.

## Creating new seed code
For example if you would like to create a new seed code for model training, you should find the most similar project template and copy it at [templates](mlops_sm_project_template/templates). You can rename the folder, keeping the suffix intact. This ensures that when scanning for available project templates, the folder will get recognized. Then you can start modifying the code: 

```
├── __init__.py
├── project.py
└── seed_code
    ├── build_app
    │   ├── Makefile
    │   ├── README.md
    │   ├── buildspec.yml
    │   ├── ml_pipelines
    │   ├── notebooks
    │   ├── setup.cfg
    │   ├── setup.py
    │   └── source_scripts
    └── deploy_app
        ├── Makefile
        ├── README.md
        ├── app.py
        ├── buildspec.yml
        ├── cdk.json
        ├── config
        ├── deploy_endpoint
        ├── requirements-dev.txt
        ├── requirements.txt
        ├── source.bat
        └── tests
```

The files more often requiring changes are: 
- **project.py** - Here is where the template metadata is specified. The template name must be unique. It is also where the repositories containing the code and the relevant pipelines are created. Here it is possible to specify different pipeline constructs and create your own. 
- **seed_code/build_app/ml_pipelines/** - Here is where all the Machine Learning Code is hosted. This code is exposed to data scientists for experimentation through one of the repositories created in `project.py`. However, if your DS find themselves often having to make the same changes, it is worth reflecting them in the project template so they can be propagated. 
- **seed_code/deploy_app/deploy_endpoint/** - Here is where the application code lives. Again, this code is exposed to application developers through one of the repositories created in `project.py`. However, if your developers find themselves often having to make the same changes, it is worth reflecting them in the project template so they can be propagated. 


## Modifying / creating new CICD Pipelines (CodePipeline)
For example if you would like to create or modify a template to have different CICD pipelines definitions (eg adding you own linter checks, organization specific integration tests, etc).
You would either create a new or modify an existing [*_pipeline.py](mlops_sm_project_template/templates/constructs/) and its associated `project.py` by changing the import.

Here is a dummy example adding a manual approval after running a SageMaker Pipeline in the `build` CICD Pipeline:

Inside [build_pipeline.py](mlops_sm_project_template/templates/constructs/build_pipeline.py) you would change:

```python
# add a build stage
build_stage = build_pipeline.add_stage(stage_name="Build")
build_stage.add_action(
    codepipeline_actions.CodeBuildAction(
        action_name="SMPipeline",
        input=source_artifact,
        project=sm_pipeline_build,
    )
)
```
to instead be:

```python
# add a build stage
build_stage = build_pipeline.add_stage(
    stage_name="Build",
    actions=[
        codepipeline_actions.CodeBuildAction(
            action_name="SMPipeline",
            input=source_artifact,
            project=sm_pipeline_build,
            run_order=1,
        ),
        codepipeline_actions.ManualApprovalAction(
            action_name="Manual_Approval",
            run_order=2,
            additional_information="Manual Approval to confirm SM Pipeline ran successfuly",
        ),
    ]
```


Here is another example changing the cross account roles that the `deploy` pipeline(s) use to execute CloudFormation in your PREPROD/PROD accounts. In the `deploy` CICD Pipeline:

Inside [deploy_pipeline](mlops_sm_project_template/templates/constructs/deploy_pipeline.py) you would change:

```python
deploy_code_pipeline.add_stage(
    stage_name="DeployPreProd",
    actions=[
        codepipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name="Deploy_CFN_PreProd",
            ...
            role=iam.Role.from_role_arn(
                self,
                "PreProdActionRole",
                f"arn:{Aws.PARTITION}:iam::{preprod_account}:role/cdk-hnb659fds-deploy-role-{preprod_account}-{deployment_region}",
            ),
            deployment_role=iam.Role.from_role_arn(
                self,
                "PreProdDeploymentRole",
                f"arn:{Aws.PARTITION}:iam::{preprod_account}:role/cdk-hnb659fds-cfn-exec-role-{preprod_account}-{deployment_region}",
            ),
            ...
        ),
        ...
    ],
)
```
to
```python
deploy_code_pipeline.add_stage(
    stage_name="DeployPreProd",
    actions=[
        codepipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name="Deploy_CFN_PreProd",
            ...
            role=iam.Role.from_role_arn(
                self,
                "PreProdActionRole",
                f"{PARAMETRIZED_ARN_OF_YOUR_CROSS_ACCOUNT_ACTION_ROLE}",   <--- Role to be changed here
            ),
            deployment_role=iam.Role.from_role_arn(
                self,
                "PreProdDeploymentRole",
                f"{PARAMETRIZED_ARN_OF_YOUR_CROSS_ACCOUNT_DEPLOY_ROLE}",    <--- Role to be changed here
            ),
            ...
        ),
        ...
    ],
)
```