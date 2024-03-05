# MLOps Multi Account Setup with AWS CDK

As enterprise businesses embrace Machine Learning (ML) across their organisations, manual workflows for building, training, and deploying ML models tend to become bottlenecks to innovation. To overcome this, enterprises need to shape a clear operating model defining how multiple personas, such as Data Scientists, Data Engineers, ML Engineers, IT, and Business stakeholders, should collaborate and interact, how to separate concerns, responsibilities and skills, and how to leverage AWS services optimally. This combination of ML and Operations, so-called MLOps, is helping companies streamline their end-to-end ML lifecycle and boost productivity of data scientists while maintaining high model accuracy and enhancing security and compliance.

In this repository, we propose a framework to created a baseline infrastructure for a secure MLOps environment based on [CDK][https://github.com/aws/aws-cdk] in python. Our solution consists of three parts:

 - [mlops-commons](mlops-multi-account-cdk/mlops-commons/mlops_commons/): This folder contains common utilities and helper scripts used by mlops-infra and mlops-sm-project-template

 - [mlops-infra](mlops-multi-account-cdk/mlops-infra/): A cdk application creating the necessary multiple account secure infrastructure of MLOps including VPCs and VPC endpoints, SageMaker Studio, IAM roles for SageMaker users,  SSM, etc.

 - [mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/): A cdk application to create a Service Catalog portfolio that contains custom Amazon SageMaker Project templates that enable multi account model deployment.

Both [mlops-infra](mlops-multi-account-cdk/mlops-infra/) and [mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/) cdk applications also create their own CodeCommit repository containing the code from their respective folders, and a self-mutating CodePipeline hosted in an AWS account considered "governance", which has the capacity to propagate changes in the infrastructure as code to target accounts.

## How to use:

We recommend to start by creating a set of 4 AWS accounts. One for governance (which will host the infrastructure as code definition), one for development (where Data Scientists and ML Engineers will deploying and modifying SageMaker project templates)

### Using convenient script for local setup , creating config file & Bootstrap
To help with setup we created a script with cli commands. These will help to setp up your local environment with required software like python, nodejs, python modules, docker etc.., bootstrapping aws accounts and building and deploying cdk application.
This script is currently compatible with operating system like MacOS, AmazonLinux, Redhat, Ubuntu, Debian. 

```bash
# for installing installing virtual python, nodejs, docker, required python modules using requiremnts.txt of mlops-infra & mlops-sm-project-template, create cdk-app.yml file as per user input and bootstrapping accounts configured in mlops-commons/mlops_commons/config/cdk-app.yml
mlops-multi-account.sh setup

# for only virtual python, nodejs, docker, required python modules using requiremnts.txt of mlops-infra & mlops-sm-project-template
mlops-multi-account.sh prerequisites|dependencies|install # all are same, use any one

# for only creating cdk-app.yml file as per user input
mlops-multi-account.sh config

# for only bootstrapping accounts configured in mlops-commons/mlops_commons/config/cdk-app.yml
mlops-multi-account.sh bootstrap

# For synthesizing mlops-infra project
mlops-multi-account.sh infra synth

# For deploy mlops-infra project
mlops-multi-account.sh infra deploy --all

# For synthesizing mlops-sm-project-template project
mlops-multi-account.sh template synth

# For deploy mlops-sm-project-template project
mlops-multi-account.sh template deploy --all

# Here infra represents mlops-infra project & template represents mlops-sm-project-template. After this project name, you can use any cdk cli arguments like below
# suppose you want to deploy using auto approval
mlops-multi-account.sh infra deploy --all --require-approval never

# refresh credentials for aws internal isen account
mlops-multi-account.sh config refresh_aws_credentials

# To run make clean/init
mlops-multi-account.sh infra init
mlops-multi-account.sh infra clean
mlops-multi-account.sh template init
mlops-multi-account.sh template clean

```

First deploy [mlops-infra](mlops-multi-account-cdk/mlops-infra/):

[mlops-infra](mlops-multi-account-cdk/mlops-infra/) will deploy a Secure data science exploration environment for your data scientists to explore and train their models inside a SageMaker studio environment.
It also prepares your dev/preprod/prod accounts with the networking setup to: either run SageMaker studio in a VPC, or be able to create SageMaker Endpoints and other infrastructure inside VPCs.
Please note that the networking created by [mlops_infra](mlops-multi-account-cdk/mlops-infra/mlops_infra) is a kick start example and that the repository is also designed to be able to import existing VPCs created by your organization instead of creating its own VPCs.
The repository will also create example SageMaker users (Lead Data Scientist and Data Scientist) and associated roles and policies.

Once you have deployed [mlops-infra](mlops-multi-account-cdk/mlops-infra/), deploy [mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/):

[mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/) will create a Service Catalog portfolio that contains SageMaker project templates as Service Catalog products.
To do so, the [service_catalog](mlops-multi-account-cdk/mlops-sm-project-template/cdk_service_catalog/sm_service_catalog.py) stack iterates over the [templates](mlops-multi-account-cdk/mlops-sm-project-template/cdk_service_catalog/products) folder which contains your different organization SageMaker project templates in the form of CDK stacks.
The general idea of what those templates create is explained in [mlops-sm-project-template README](mlops-multi-account-cdk/mlops-sm-project-template/README) and in this [SageMaker Projects general architecture diagram](mlops-multi-account-cdk/mlops-sm-project-template/diagrams/mlops-sm-project-general-architecture.jpg)
These example SageMaker project templates can be customized for the need of your organization.

**Note:** Both of those folders are cdk applications which also come with their respective CICD pipelines hosted in a central governance account, to deploy and maintain the infrastructure to target accounts. This is why you will see that both also contain a `pipeline_stack` and a `codecommit_stack`.
However if you are not interested in the concept of a centralized governance account and CICD mechanism, or if you already have an internal mechanism in place for those ([AWS Control Tower](https://docs.aws.amazon.com/controltower/index.html), [ADF](https://github.com/awslabs/aws-deployment-framework), etc...), you can simply use the `CoreStage` of each of those CDK applications. See the READMEs of each subfolder for more details.

**Note:** Please follow the mandatory configuration required for both module `mlops-infra` and `mlops-sm-project-template` from [README](mlops-multi-account-cdk/mlops-commons/mlops_commons/README.md) `mlops-commons/mlops_commons/README.md`

## Contacts

If you have any comments or questions, please contact:

The maintaining Team: 

Viktor Malesevic <malesv@amazon.de>

Fotinos Kyriakides <kyriakf@amazon.com>

Ravi Bhushan Ratnakar <ravibrat@amazon.de>

Sokratis Kartakis <kartakis@amazon.com>

Georgios Schinas <schinasg@amazon.co.uk>

# Special thanks

Fatema Alkhanaizi, who is no longer at AWS but has been the major initial contributor of the project.

# Troubleshooting

