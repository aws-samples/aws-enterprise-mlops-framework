# MLOps Foundation Infrastructure

This repository contains the resources that are required to deploy the MLOps Foundation infrastructure. It contains the definition of a secure networking with Amazon VPC, Subnets, Security Group and Amazon VPC Endpoints to be used with Amazon SageMaker Studio. It also defines the setup for Amazon SageMaker Studio Domain and creates SageMaker Studio User Profiles for Data Scientists and Lead Data Scientists.

**NOTE** To effictively use this repository you would need to have a good understanding around AWS networking services, AWS CloudFormation and AWS CDK.
- [MLOps Foundation Infrastructure](#mlops-foundation-infrastructure)
  - [Solution Architecture](#solution-architecture)
    - [Networking Stack](#networking-stack)
    - [SageMaker Studio Stack](#sagemaker-studio-stack)
    - [CodeCommit Stack](#codecommit-stack)
    - [Pipeline Stack](#pipeline-stack)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Repository Structure](#repository-structure)
    - [Setup and Customization](#setup-and-customization)
    - [Setup AWS Profiles](#setup-aws-profiles)
    - [Deployment](#deployment)
    - [Clean-up](#clean-up)
  - [Troubleshooting](#troubleshooting)

## Developer Guide

How to use and customize the repository for your own needs: [Developer Guide](DEVELOPER_GUIDE.md)

## Solution Architecture

![mlops foundation infrastruction](diagrams/MLOPs%20Foundation%20Architecture-mlops%20infrastructure%20architecture.jpg)
### Networking Stack

![networking stack](diagrams/MLOPs%20Foundation%20Architecture-mlops%20secure%20networking.jpg)

The networking stack deploys all required resources to create a secure environment to run machine learning workloads in AWS. The following resources are deployed:

1. VPC with 3 Availability Zones (AZs), 1 public subnet and 1 private subnet (attached with a NAT Gateway) in each AZ, DNS hostnames and support enabled, and 1 NAT Gateway
2. VPC Endpoints deployed in each deployment account (DEV/PREPROD/PROD) as shown in the diagram.

|S3	|SageMaker API	|SageMaker Runtime	|SageMaker Notebook	|CodeCommit	|CodeCommit Git	|
|---	|---	|---	|---	|---	|---	|
|SSM	|CloudWatch Monitoring	|CloudWatch Logs	|ECR Docker	|ECR API	|KMS	|
|STS	|CodeArtifact API	|CodeArtifact Repositories	|	|	|	|

3. SSM parameters are used to store information about the VPC and its related components in each deployment account (DEV/PREPROD/PROD)

**NOTE** This is an optional stack for the scenario that the account does not have an existing VPC configured. If you want to use an existing VPC please refer to section [Customization](#Customization).


You must ensure that the existing VPC contains most of the components that are created in this stack.

### SageMaker Studio Stack

*This stack is only deployed in the DEV account*
![sagemaker studio stack](diagrams/MLOPs%20Foundation%20Architecture-sagemaker%20studio%20stack.jpg)

This stack handles the deployment of the following resources:

1. SageMaker Studio Domain requires, along with
2. User Profile creating process is managed by the config files in [mlops-infra/config/cdk-infra-app.yml.bak](mlops-infra/config/cdk-infra-app.yml.bak). You can simply add new entries in the list to create a new user. The user will be linked to a role depending on which yml you add them to and will have a prefix defined in the yml files.

```yaml
  users:
    - user_profile_name: "X"
```

3. Default SageMaker Project Templates are also enabled on the account on the targeted region using a custom resource; the custom resource uses a lambda function, [functions/sm_studio/enable_sm_projects](functions/sm_studio/enable_sm_projects), to make necessary SDK calls to both Amazon Service Catalog and Amazon SageMaker.

### CodeCommit Stack
*This stack is only needed if you want to handle deployments of this folder of the repository to be managed through a CICD pipeline.*

This stack handles setting up an AWS CodeCommit repository for this folder of the repository. This repository will be used as the source for the CI/CD pipeline defined in [Pipeline Stack](#pipeline-stack). The repository will be named based on the value defined in [configs](../mlops-commons/mlops_commons/config/cdk-app.yml.bak). The repository will be intialised with a default branch as defined in the [configs](../mlops-commons/mlops_commons/config/cdk-app.yml.bak).

### Pipeline Stack

*This stack is only needed if you want to handle deployments of this folder of the repository to be managed through a CICD pipeline. The pipeline is configured to deploy to 3 accounts, DEV, PREPROD and PROD*

The CICD pipeline in this repository is setup to monitor an AWS CodeCommit repository as defined in [CodeCommit Stack](#codecommit-stack).

If you are using other sources like github or bitbucket for your repository, you will need to modify the connection to the appropriate repository as defined in [mlops_infra/pipeline_stack.py](mlops_infra/pipeline_stack.py). This can be done using AWS CodeStar but must be setup on the account.

Make sure the pipelines also point to your targeted branch; by default the pipeline is linked to `main` branch events, this is defined in the [configs](../mlops-commons/mlops_commons/config/cdk-app.yml.bak).

Account sets in [configs](../mlops-commons/mlops_commons/config/cdk-app.yml.bak) is created as a list where each entry is a different set of DEV/PREPROD/PROD accounts. By default we recommend starting with one entry of DEV/PREPROD/PROD accounts but this can be used to scale the infrastructure to several organizational units/teams.
The repository will create one parallel CICD pipeline for each entry. (please ensure all new target accounts you add to the list are bootstrapped)

The CICD pipeline will deploy all stacks and resources to the appropriate accounts.


## Getting Started

### Prerequisites

This is an AWS CDK project written in Python 3.8. Here's what you need to have on your workstation before you can deploy this project. It is preferred to use a linux OS to be able to run all cli commands and avoid path issues.

* [Node.js](https://nodejs.org/)
* [Python3.8](https://www.python.org/downloads/release/python-380/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
* [AWS CDK v2](https://aws.amazon.com/cdk/)
* [AWS CLI](https://aws.amazon.com/cli/)
* [Docker](https://docs.docker.com/desktop/)

### Repository Structure

```txt
.
├── ADVANCED_TOPICS.md
├── DEVELOPER_GUIDE.md
├── LICENSE.txt
├── Makefile
├── README.md
├── app.py
├── cdk.context.json
├── cdk.json
├── cdk_pipelines
│   ├── __init__.py
│   ├── codecommit_stack.py
│   └── pipeline_stack.py
├── cdk_sm_infra
│   ├── __init__.py
│   ├── constructs
│   │   ├── create_network.py
│   │   ├── import_network.py
│   │   ├── sm_network.py
│   │   ├── sm_roles.py
│   │   ├── sm_studio.py
│   │   ├── sm_studio_infra.py
│   │   └── sm_studio_network.py
│   ├── functions
│   │   └── sm_studio
│   │       └── enable_sm_projects
│   └── sm_infra_stack.py
├── cdk_utilities
│   ├── __init__.py
│   └── cdk_infra_app_config.py
├── config
│   └── cdk-infra-app.yml.bak
├── diagrams
│   ├── MLOPs Foundation Architecture-mlops infrastructure architecture.jpg
│   ├── MLOPs Foundation Architecture-mlops secure networking.jpg
│   └── MLOPs Foundation Architecture-sagemaker studio stack.jpg
├── requirements-dev.txt
├── requirements.txt
└── scripts
    ├── mlops-infra.sh
    └── project-setup.sh
```

if you are using a mac or a linux machine that supports `make` commands, you will be able to do the following:

* use `make init` to setup githooks to manage commit for this repository. This will add some helper functionalities when ever you run `git commit` to format the code, add necessary headers, and also clears any jupyter notebooks.
* use `make clean` to clear out the repo from python specific cached resources.

This repository also contains some shell scripts that you can use to setup your machine and aws accounts:

* If you have a mac machine with [Homebrew](https://brew.sh/) installed, you can use [scripts/install-prerequisites-brew.sh](../mlops-commons/mlops_commons/scripts/install-prerequisites-brew.sh) to install the prerequisites and setup the python environment

### Setup and Customization
First, copy the [configs file](config/cdk-infra-app.yml.bak), removing the ```.bak``` suffix. Here you can modify the defaults - which create a VPC and related resources. Or you can provide your pre-existing VPC and resources, by changing the ```deployments``` section, including the ```import_network``` section. The solution also supports multiplle account sets (ie multiple sets of dev/stg/prod) by including multiple entries in the ```deployments``` section.

**Note**: Not creating a ```cdk-infra-app.yml``` will automatically implement the defautls. 

Example configurations: 

*Change defaults (eg different CIDR range)*

```yaml
cdk_infra_app_config:
  network:
    default_create_network:
      vpc_cidr: "<NEW CIDR RANGE>"
```

*Multi account - 1 account set with dafaults and 1 with imported network configs*

**NOTE**: Only the second account set needs to be specified - since the first one follows the defaults.
```yaml
cdk_infra_app_config:
  network:
    deployments:
      - set_name: SECOND-example
        stages:
          - stage_name: dev
            import_network:
              vpc_id: "<YOUR IDs>"
              subnets:
                - "<YOUR IDs>"
                - "<YOUR IDs>"
                - "<YOUR IDs>"
              base_security_group: "<YOUR IDs>"
          - stage_name: preprod
            import_network:
              vpc_id: "<YOUR IDs>"
              subnets:
                - "<YOUR IDs>"
                - "<YOUR IDs>"
                - "<YOUR IDs>"
              base_security_group: "<YOUR IDs>"
          - stage_name: prod
            import_network:
              vpc_id: "<YOUR IDs>"
              subnets:
                - "<YOUR IDs>"
                - "<YOUR IDs>"
                - "<YOUR IDs>"
              base_security_group: "<YOUR IDs>"
```

*Creating networking in dev, but importing in staging and production*

```yaml
cdk_infra_app_config:
  network:
    deployments:
      - set_name: first-example
        stages:
          - stage_name: dev  # not strictly needed
          - stage_name: preprod
            import_network:
              vpc_id: "<YOUR IDs>"
              subnets:
                - "<YOUR IDs>"
                - "<YOUR IDs>"
                - "<YOUR IDs>"
              base_security_group: "<YOUR IDs>"
          - stage_name: prod
            import_network:
              vpc_id: "<YOUR IDs>"
              subnets:
                - "<YOUR IDs>"
                - "<YOUR IDs>"
                - "<YOUR IDs>"
              base_security_group: "<YOUR IDs>"
```

**NOTE**: In case that both import and create network are specified, the import always takes priority. 


### Deployment

This step will deploy 2 stacks: [CodeCommit Stack](#codecommit-stack) and [Pipeline Stack](#pipeline-stack)

1. Deploy the deployment CI/CD pipeline in your governance account (one time operation). This is the CI/CD pipeline that would deploy your required infrastructure to setup your networking in the accounts and SageMaker Studio Domain in the Dev Account:

```bash
# builds the pipeline stack and install all assets
cdk synth
# deploy stack to target account, use the governance account profile for this
cdk deploy --all --profile mlops-governance
```

2. the deployment CI/CD pipeline will now handle all deployments for the other stacks based on the updates to the main branch

### Clean-up

In case you used the local deployment, once you are done with testing the new feature that was deployed locally, run the following commands to clean-up the environment:

```bash
# destroy stage to target account (make it match your stack name)
cdk --app ./cdk.out/assembly-Personal destroy —-all --profile mlops-dev
```

This would only delete the service catalog stack deployed in the target account and not the deployed projects.

Similarly if you used the CI/CD deployment:

```bash
# destroy deployed stack in target account (make it match your stack name)
cdk destroy --all --profile mlops-governance
```

This would only delete the pipeline stack and nothing else deployed from the pipeline i.e. stacks deployed to the target accounts and the deployed projects.

**NOTE** deployed stack from the pipeline won't be deleted to delete those you have to manually delete them through CloudFormation Delete stack command.

This command could fail in the following cases:

* **S3 bucket not empty**

If you get this error just simply go to the console and empty the S3 bucket that caused the error and run the destroy command again.

* **Resource being used by another resource**

This error is harder to track and would require some effort to trace where is the resource that we want to delete is being used and severe that dependency before running the destroy command again.

**NOTE** You should just really follow CloudFormation error messages and debug from there as they would include details about which resource is causing the error and in some occasion information into what needs to happen in order to resolve it.

## Troubleshooting

* **CDK version X instead of Y**

This error relates to a new update to cdk so run `npm install -g aws-cdk` again to update your cdk to the latest version and then run the deployment step again for each account that your stacks are deployed.

* **`cdk synth`** **not running**

One of the following would solve the problem:

    * Docker is having an issue so restart your docker daemon
    * Refresh your awscli credentials
    * Clear all cached cdk outputs by running `make clean`
* **[Error at /ml-deploy-pipeline/****<****env****>****/networking] Need to perform AWS calls for account X, but no credentials have been configured**

You can resolve this error by adding availability zone information to `cdk.context.json`. This error happens as CDK tries to do a lookup on the account to check which Availability Zones does the region of the target account have available and if it can be deployed across the targeted 3 AZs.

```json
"availability-zones:account=<account_id>:region=eu-west-1": [
    "eu-west-1a",
    "eu-west-1b",
    "eu-west-1c"
]
```
