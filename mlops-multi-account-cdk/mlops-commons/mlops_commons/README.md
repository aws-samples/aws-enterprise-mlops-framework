
## Solution Setup
- AWS Profiles
- Configuration using config file cdk-app.yml
- Pipeline configuration
- Account set specific configurations 
- Bootstrap using execution policy
- Using convenient script for local setup & Bootstrap
- Manual Bootstrap

### Setup AWS Profiles

As the MLOps foundation is based on multiple accounts, it is necessary to create a simple way to interact with multiple AWS credentials. We recommend the creation of an AWS profile per account with enough permission to deploy to CloudFormation following the instructions [here](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/keys-profiles-credentials.html#adding-a-profile-to-the-aws-credentials-profile-file) . For example, the `.aws/credentials` should look like:

```text
[mlops-governance]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
aws_session_token = YOUR_SESSION_TOKEN  # this token is generated if you are using an IAM Role to assume into the account

[mlops-dev]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
aws_session_token = YOUR_SESSION_TOKEN  # this token is generated if you are using an IAM Role to assume into the account

[mlops-preprod]
...

[mlops-prod]
...



```
### Configuration using `cdk-app.yml`
First, copy the [configs file](config/cdk-app.yml.bak), removing the ```.bak``` suffix. Here you can modify the defaults - for pipeline configuration. You can configure account details in ```deployments``` section. The solution also supports multiplle account sets (ie multiple sets of dev/stg/prod)

Sample configuration for reference with different config options: 
```yaml
cdk_app_config:
  app_prefix:   # optional, default to mlops-cdk
  pipeline:
    account:  # mandatory
    region:   # mandatory
    bootstrap:
      enabled:    # optional, default True
      execution_policy_filepath: # optional, default to look for a file name in mlops_commons/config/execution_policy_AWS-ACCOUNT-ID_AWS-REGION.json
      execution_policy_arn: # optional, default to 'arn:aws:iam::aws:policy/AdministratorAccess', this will only be used when there is no value provided to 'execution_policy_filepath'
      aws_profile: # optional, default to profile name by cdk_AWS-ACCOUNT-ID_AWS-REGION
    code_commit:
      infra:
        repo_name:   # optional, default to mlops-infra
        branch_name: # optional, default to main
      project_template:
        repo_name:   # optional, default to mlops-sm-project-template
        branch_name: # optional, default to main

  deployments:
    - set_name: first-example # mandatory
      enabled: # optional, default True
      default_region: # optional, default to environment pipeline region
      stages:
        - stage_name: dev # mandatory value must be dev
          account:        # mandatory
          region:         # optional, default to value of 'default_region'
          enabled:        # optional, default True
          bootstrap:
            enabled:      # optional, default True
            execution_policy_filepath: # optional, default to look for a file name in mlops_commons/config/execution_policy_AWS-ACCOUNT-ID_AWS-REGION.json
            execution_policy_arn:      # optional, default to 'arn:aws:iam::aws:policy/AdministratorAccess', this will only be used when there is no value provided to 'execution_policy_filepath'
            aws_profile:               # optional, default to profile name by cdk_AWS-ACCOUNT-ID_AWS-REGION
        - stage_name: preprod  # mandatory value must be preprod
          account:        # mandatory
          region:         # optional, default to value of 'default_region'
          enabled:        # optional, default True
          bootstrap:
            enabled:      # optional, default True
            execution_policy_filepath: # optional, default to look for a file name in mlops_commons/config/execution_policy_AWS-ACCOUNT-ID_AWS-REGION.json
            execution_policy_arn:      # optional, default to 'arn:aws:iam::aws:policy/AdministratorAccess', this will only be used when there is no value provided to 'execution_policy_filepath'
            aws_profile:               # optional, default to profile name by cdk_AWS-ACCOUNT-ID_AWS-REGION

        - stage_name: prod # mandatory value must be prod
          account:         # mandatory
          region:          # optional, default to value of 'default_region'
          enabled:         # optional, default True
          bootstrap:
            enabled:       # optional, default True
            execution_policy_filepath: # optional, default to look for a file name in mlops_commons/config/execution_policy_AWS-ACCOUNT-ID_AWS-REGION.json
            execution_policy_arn:      # optional, default to 'arn:aws:iam::aws:policy/AdministratorAccess', this will only be used when there is no value provided to 'execution_policy_filepath'
            aws_profile:               # optional, default to profile name by cdk_AWS-ACCOUNT-ID_AWS-REGION



    - set_name: second-example
      stages:
        - stage_name: dev
          account: xxxxxxxxxxxx
          bootstrap:
            aws_profile: profile_name
        - stage_name: preprod
          account: xxxxxxxxxxxx
          bootstrap:
            aws_profile: profile_name
        - stage_name: prod
          account: xxxxxxxxxxxx
          bootstrap:
            aws_profile: profile_name

    - set_name: third-example
      stages:
        - stage_name: dev
          account: xxxxxxxxxxxx
        - stage_name: preprod
          account: xxxxxxxxxxxx
        - stage_name: prod
          account: xxxxxxxxxxxx


```
### Pipeline configuration
*Below is pipeline configuration with default configuration. Change defaults (eg different repository name, branch for mlops-infra and mlops-sm-project-template) with other pipeline details*

```yaml
cdk_app_config:
  app_prefix: mlops-cdk
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
    bootstrap:
      aws_profile: <YOUR PIPELINE ACCOUNT'S AWS PROFILE NAME>
    code_commit:
      infra:
        repo_name: mlops-infra
        branch_name: main
      project_template:
        repo_name: mlops-sm-project-template
        branch_name: main
```
### Account set specific configurations

*Multi account - 1 account set with same region of pipeline*

**NOTE**: if you want to have same region of pipeline account for your dev/stage/prod then you can leave region field of default/dev/stage/prod
```yaml
cdk_app_config:
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
```
*Multi account - 2 account set with same region of pipeline*

```yaml
cdk_app_config:
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
    - set_name: second-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
```
*Multi account - 1 account set with different region from pipeline but same region for dev/stage/prod, for example pipeline region - us-east-1, dev/stage/prod - eu-west-1*
```yaml
cdk_app_config:
  app_prefix: mlops-cdk
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: us-east-1
    
  deployments:
    - set_name: first-example
      default_region: eu-west-1
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
```

*Multi account - 1 account set with different region from pipeline and different region for dev/stage/prod, for example pipeline region - us-east-1, dev - eu-west-1, stage - eu-west-2, prod - eu-central-1*
```yaml
cdk_app_config:
  app_prefix: mlops-cdk
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: us-east-1
    
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          region: eu-west-1
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          region: eu-west-2
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          region: eu-central-1
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
```

### Bootstrap using execution policy

*Before you start with the deployment of the solution make sure to bootstrap your accounts. Bootstrapping your account with default execution policy arn 'arn:aws:iam::aws:policy/AdministratorAccess'*

**NOTE**: If you are using default execution policy arn 'arn:aws:iam::aws:policy/AdministratorAccess', then you don't need to do anything. An example configuration will be like below.
```yaml
cdk_app_config:
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
    bootstrap:
      aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
```

*Bootstrapping your account with existing execution policy arn*

```yaml
cdk_app_config:
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
    bootstrap:
      aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
      execution_policy_arn: <YOUR EXECUTION POLICY ARN>
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
            execution_policy_arn: <YOUR EXECUTION POLICY ARN>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
            execution_policy_arn: <YOUR EXECUTION POLICY ARN>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
            execution_policy_arn: <YOUR EXECUTION POLICY ARN>
```

*Bootstrapping your account by creating your own execution policy by given execution policy arn json file*
**NOTE**: create your execution policy file with desired name in mlops-commons/mlops_commons/config and configure it as shown in below example.
```yaml
cdk_app_config:
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
    bootstrap:
      aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
      execution_policy_filepath: <YOUR EXECUTION POLICY JSON FILE PATH>
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
            execution_policy_filepath: <YOUR EXECUTION POLICY JSON FILE PATH>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
            execution_policy_filepath: <YOUR EXECUTION POLICY JSON FILE PATH>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
            execution_policy_filepath: <YOUR EXECUTION POLICY JSON FILE PATH>
```


*Bootstrapping your account by creating your own execution policy by given execution policy arn json file*
**NOTE**: By default it looks for execution policy in folder mlops-commons/mlops_commons/config by file name by 'execution_policy_AWS-ACCOUNT-ID_AWS-REGION.json'. if you are using default execution file name, then you don't need to do anything extra. Below configuration as example.
```yaml
cdk_app_config:
  pipeline:
    account: <YOUR AWS ACCOUNT ID>
    region: <YOUR AWS REGION>
    bootstrap:
      aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
  deployments:
    - set_name: first-example
      stages:
        - stage_name: dev
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR DEV ACCOUNT'S AWS PROFILE NAME>
        - stage_name: preprod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PREPROD ACCOUNT'S AWS PROFILE NAME>
        - stage_name: prod
          account: <YOUR AWS ACCOUNT ID>
          bootstrap:
            aws_profile: <YOUR PROD ACCOUNT'S AWS PROFILE NAME>
```

### Using convenient script for local setup , creating config file & Bootstrap
For setting up your local environment for required software like python, nodejs, python modules, docker etc.., bootstrapping aws accounts and building of deploying cdk application, there are few convenient scripts with cli commands.
In the root folder i.e. mlops-multi-account-cdk, there is script `mlops-multi-account.sh`. This script is currently compatible with operating system like MacOS, AmazonLinux, Redhat, Ubuntu, Debian. 
```bash
# for installing installing virtual python, nodejs, docker, required python modules using requiremnts.txt of mlops-infra & mlops-sm-project-template, create cdk-app.yml file as per user input and bootstrapping accounts configured in mlops-commons/mlops_commons/config/cdk-app.yml
./mlops-multi-account.sh setup

# for only virtual python, nodejs, docker, required python modules using requiremnts.txt of mlops-infra & mlops-sm-project-template
./mlops-multi-account.sh prerequisites|dependencies|install # all are same, use any one

# for only creating cdk-app.yml file as per user input
./mlops-multi-account.sh config

# for only bootstrapping accounts configured in mlops-commons/mlops_commons/config/cdk-app.yml
./mlops-multi-account.sh bootstrap

# For synthesizing mlops-infra project
./mlops-multi-account.sh infra synth

# For deploy mlops-infra project
./mlops-multi-account.sh infra deploy --all

# For synthesizing mlops-sm-project-template project
./mlops-multi-account.sh template synth

# For deploy mlops-sm-project-template project
./mlops-multi-account.sh template deploy --all

# Here infra represents mlops-infra project & template represents mlops-sm-project-template. After this project name, you can use any cdk cli arguments like below
# suppose you want to deploy using auto approval
./mlops-multi-account.sh infra deploy --all --require-approval never

# To run make clean/init
./mlops-multi-account.sh infra init
./mlops-multi-account.sh infra clean
./mlops-multi-account.sh template init
./mlops-multi-account.sh template clean

```

### Manual Bootstrap of AWS Accounts

***Warning:** It is best you setup a python environment to handle all installs for this project and manage python packages. Use your preferred terminal and editor to run the following commands.*

follow the steps below to achieve that:

1. Clone this repository in your work environment (e.g. your laptop)

2. Change directory to `mlops-infra` root

```bash
cd mlops-infra
```

3. Install dependencies in a separate python environment using your favourite python packages manager. You can refer to [scripts/install-prerequisites-brew.sh](scripts/install-prerequisites-brew.sh) for commands to setup a python environment.

```bash
 pip install -r requirements.txt
```

4. Run `make init` to setup githooks

5. Ensure your docker daemon is running

6. (Option 1) Bootstrap your deployment target accounts (e.g. governance, dev, etc.) using our script in [scripts/cdk-account-setup.sh](scripts/cdk-account-setup.sh). Ensure that you have the account ids ready and the corresponding AWS profiles with credentials created in your `~/.aws/credentials` for each account (see above).

The script will request the 4 accounts, i.e. governance, dev, preprod and prod, and the corresponding AWS profiles as inputs. If you want to only deploy to 1 account you can use the same id for all account variables or pass the same values in the script.

<add screenshot here of sccript execution>

6. (Option 2) If you want to bootstrap the account manually (recommended if bootstrapping across several organization units), then run the following command for each account:

```bash
cdk bootstrap aws://<target account id>/<target region> --profile <target account profile>
```

The bootstrap stack needs only to be deployed for the first time. Once deployed, the bootstrap will be updated as part of the pipeline's regular execution. You only need to deploy bootstrap into new target accounts you plan to add to the pipeline. (in case you get an error regarding CDK version not matching run the bootstrap command again after you have locally updated your cdk) for cross account deployment setup, run the following command. This is a one time operation for each target account we want to deploy.

```bash
cdk bootstrap aws://<target account id>/<target region> --trust <deployment account> --cloudformation-execution-policies <policies arn that you would allow the deployment account to use> --profile <target account profile>
```

The following is an example of the cloud formation execution policy:

```nash
--cloudformation-execution-policies `'arn:aws:iam::aws:policy/AdministratorAccess'`
```

for more information read the [AWS CDK documentation on Bootstrapping](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html#bootstrapping-howto)
