# MLOps Multi Account Setup with AWS CDK

As enterprise businesses embrace Machine Learning (ML) across their organisations, manual workflows for building, training, and deploying ML models tend to become bottlenecks to innovation. To overcome this, enterprises need to shape a clear operating model defining how multiple personas, such as Data Scientists, Data Engineers, ML Engineers, IT, and Business stakeholders, should collaborate and interact, how to separate concerns, responsibilities and skills, and how to leverage AWS services optimally. This combination of ML and Operations, so-called MLOps, is helping companies streamline their end-to-end ML lifecycle and boost productivity of data scientists while maintaining high model accuracy and enhancing security and compliance.

# Solution Breakdown

The solution is broken down into 2 main components spread over at 1 goverance account and an number of sets of dev, staging and production accounts. All infrastructure deployed is deployed from the governance account to the lower-level accounts using CICD pipelines:

[mlops-infra](mlops-multi-account-cdk/mlops-infra/) will deploy a Secure Governance account with all required roles and networking resources. It will create a VPC, subnets and the needed Internet Gateways. It will additionally create CodePipelines, that will deploy the below infrastructure in the dev, staging and production accounts.

![Infra](mlops-multi-account-cdk/mlops-infra/diagrams/MLOPs%20Foundation%20Architecture-mlops%20infrastructure%20architecture.jpg)

[mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/) will create a Service Catalog portfolio in each dev account that contains SageMaker project templates as Service Catalog products. This ensures that project templates are replicated across all account sets in the organization

![Templates](mlops-multi-account-cdk/mlops-sm-project-template/diagrams/MLOPs%20Foundation%20Architecture-mlops%20project%20cicd%20architecture.jpg)

## Project Templates Overview

At its core, this solution allows for a centrally managed and automatically deployable setup, which enable Machine Learning teams to self-serve in creating ML project templates. This ensures that the templates, since they are centrally managed, follow company-wide best practices and are deployed through CICD, without having to give a particular user elevated permissions. The typical Sagemaker Project Template looks as follows: 

![Project template](mlops-multi-account-cdk/mlops-sm-project-template/diagrams/MLOPs%20Foundation%20Architecture-sagemaker%20project%20architecture.jpg)

# Repository Contents

In this repository, we create a framework for a secure MLOps setup based on [CDK](https://github.com/aws/aws-cdk) in python. Our solution consists of three parts:

 - [mlops-commons](mlops-multi-account-cdk/mlops-commons/mlops_commons/): This folder contains common utilities and helper scripts used by mlops-infra and mlops-sm-project-template

 - [mlops-infra](mlops-multi-account-cdk/mlops-infra/): A cdk application creating the necessary multiple account secure infrastructure of MLOps including VPCs and VPC endpoints, SageMaker Studio, IAM roles for SageMaker users,  SSM, etc.

 - [mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/): A cdk application to create a Service Catalog portfolio that contains custom Amazon SageMaker Project templates that enable multi account model deployment.

Both [mlops-infra](mlops-multi-account-cdk/mlops-infra/) and [mlops-sm-project-template](mlops-multi-account-cdk/mlops-sm-project-template/) cdk applications also create their own CodeCommit repository containing the code from their respective folders, and a self-mutating CodePipeline hosted in an AWS account considered "governance", which has the capacity to propagate changes in the infrastructure as code to target accounts.

# Quick Setup:

We recommend to start by creating a set of 4 AWS accounts:
1.  Governance account - which will be used to manage the account sets
2. Development account - where Data Scientists and ML Engineers will deploying and modifying SageMaker project templates
3. Staging account - for integration testing the ML products with the rest of the application code
4. Production account

### Using convenient script for local setup , creating config file & Bootstrap
To help with setup we created a script with cli commands. These will help to setp up your local environment with required software like python, nodejs, python modules, docker etc.., bootstrapping aws accounts and building and deploying cdk application.
This script is currently compatible with operating system like MacOS, AmazonLinux, Redhat, Ubuntu, Debian. 

The configured helper scripts are designed to give you granular control over the operations you want automated and the ones you want to do yourself. 

1. **Fully Managed** - Installing virtual python, nodejs, docker, requirements, creating cdk-app.yml files as per user input and bootstrapping accounts configured in mlops-commons/mlops_commons/config/cdk-app.yml, run the following
    ```bash
    mlops-multi-account.sh setup
    ```

2. **Managed depenendency installer** Installing virtual python, nodejs, docker, requirements
    ```bash
    mlops-multi-account.sh prerequisites|dependencies|install # all are same, use any one
    ```

3. **Managed config file creation**  - Creating cdk-app.yml file as per user input
    ```bash
    mlops-multi-account.sh config
    ```

4. **Managed account bootstrapping** - Bootstrapping accounts configured in mlops-commons/mlops_commons/config/cdk-app.yml
    ```bash
    mlops-multi-account.sh bootstrap
    ```

5. **Managed deployment of infrastrucutre or project-template solution**
    ```bash
    mlops-multi-account.sh infra|template deploy --all  --require-approval never
    ```

6. **Refresinh credentials**
    ```bash
    mlops-multi-account.sh config refresh_aws_credentials
    ```
7. **Clean-up and Init**
    ```bash
    mlops-multi-account.sh infra init
    mlops-multi-account.sh infra clean
    mlops-multi-account.sh template init
    mlops-multi-account.sh template clean

    ```


# Contacts

If you have any comments or questions, please contact:

The maintaining Team: 

Viktor Malesevic <malesv@amazon.de>

Fotinos Kyriakides <kyriakf@amazon.com>

Ravi Bhushan Ratnakar <ravibrat@amazon.de>

Sokratis Kartakis <kartakis@amazon.com>

Georgios Schinas <schinasg@amazon.co.uk>

# Special thanks

Fatema Alkhanaizi, who is no longer at AWS but has been the major initial contributor of the project.
