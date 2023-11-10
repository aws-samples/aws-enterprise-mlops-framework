# THIS NEEDS UPDATING TO REFLECT NEW SETUP

## Solution Setup
- Mention configuring cdk-app.yml including examples
- Account set specific configs (sh commands etc)
- Include section for manual bootstrap ( move from the infra readme here)
- Include examples of configs

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

Before you start with the deployment of the solution make sure to bootstrap your accounts. Ensure you add the pipeline/governance account details in [mlops_infra/config/constants.py](mlops_infra/config/constants.py).

```python
PIPELINE_ACCOUNT = ""     # account to host the pipeline handling updates of this repository
```

Additionally, for each organizational units composed of **DEV**, **PREPROD** and **PROD** accounts, create a new entry in [mlops_infra/config/accounts.json](mlops_infra/config/accounts.json)

```yaml
"DEV_ACCOUNT": "",        # account to setup sagemaker studio and networking stack

"PREPROD_ACCOUNT": "",    # account to setup networking stack

"PROD_ACCOUNT": "",       # account to setup networking stack
```

### Bootstrap AWS Accounts

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