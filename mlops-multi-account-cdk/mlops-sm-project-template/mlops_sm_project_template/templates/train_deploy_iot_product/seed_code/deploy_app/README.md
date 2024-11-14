## Deploy Repository for MLOps@Edge

```bash
├── app
├── model_component_1
├── ...
├── model_component_N   
├── helpers 
│   ├── gg-create-build-files.py
│   ├── gg-build.sh
│   ├── gg-publish.sh
│   └── gg-deploy.sh
├── buildspec.build.yml
├── buildspec.deploy.yml
├── deployment.json
├── gg-config.yml
└── README.md
```

The repository is structured as follows:

* app: contains the code of the application that performs inference at the edge
* model_component_i: the repository contains a dedicated folder for each model component to be deployed at the edge. The folder hosts the code for any custom transformation that may be applied to the model before deployment, such as compiling it into onnx format. If no custom code is provided, a .gitkeep file needs to be placed inside the folder to tell git to version it despite being empty.
* helpers: host the helper scripts needed for the deployment of components through greengrass. In particular:
    * gdk-synth.py: defines the component versions to deploy and creates the gdk files needed to build, publish and release them on edge. For models, it queries SageMaker model registry to obtain the latest approved version and it downloads them to the build environment.
    * gg-build.sh: packages components and uploads them to the S3 greengrass artifacts bucket in the dev account which acts as a central repository for all accounts to which the components will be published 
    * gg-publish.sh: publishes greengrass components to the specified account’s IoT Core service
    * gg-deploy.sh: creates the deployment of components to the target Thing Group in of the specified account
* buildspec.build.yml: orchestrates the build of greengrass components by leveraging the following helper scripts:
    * gg-create-build-files.py
    * gg-build.sh 
* buildspec.deploy.yml: orchestrates the publish and deploy stages of greengrass components lifecycle by leveraging the following helper scripts:
    * gg-publish.sh
    * gg-deploy.sh 
* deployment.json: template file for deployment of greengrass components
* greengrass-config.yml: this file constitutes the primary interface for data scientists to specify the configurations of the components to be released on edge. Below is an example for the configuration of a generic component:
    ```yaml
        custom-components:  
          component1:
            component-name: "component-name"
            root: "folder that hosts the component within the repository"
            bucket: "bucket that hosts the component outside the repository"
            region: "eu-west-1"
            build: 
              build_system: "zip" # how components are packaged and shipped to S3
            ComponentDependencies:
              aws.greengrass.Nucleus:
                DependencyType: SOFT
                VersionRequirement: '>=2.0.3 <3.1.0'
              name_of_component2:
                DependencyType: HARD
                VersionRequirement: 'x.x.x' # auto-populated with last version
              name_of_component3:
                DependencyType: HARD
                VersionRequirement: 'x.x.x' # auto-populated with last version
            Artifacts:
            - Permission:
                Execute: OWNER
              URI: "s3://BUCKET_NAME/COMPONENT_NAME/COMPONENT_VERSION/app.zip"
              Unarchive: ZIP
            Lifecycle: 
              SetEnv:
                MODEL_DIR: '{car-detection:artifacts:decompressedPath}/car-detection/car-detection.onnx'
              Install: pip install -r {artifacts:decompressedPath}/app/requirements.txt
              Run: 
                RequiresPrivilege: "true"
                Script: python3 -u {artifacts:decompressedPath}/app/app.py --model-name $MODEL_DIR
    ```
    In particular:  

    * if a component is hosted entirely within the repo and does not consist of files (e.g. models) residing on any particular s3 bucket, bucket should default to the S3 greengrass artifact bucket  
    * the build attribute specifies how components are packaged and shipped to S3:  
        * default value is zip, meaning all the content of the root folder for that component is compressed as a zip file with the exception of recipe.json and gdk-config.json  
        * can be set to custom to use one’s own code to perform the building and producing in output only certain files with the desired extension. In this case, each word of the custom build command needs to be inserted as follows:  
        ```yaml
                    build_system: "custom"
                      custom_build_command: 
                        - "bash"
                        - "compile/custom-build.sh"
                        - "CarRecognitionModel"
        ```
    * the Artifacts section contains info on what the component will look like after build, specifically:  
        * URI: defines the URI of the component once it’s uploaded onto the S3 greengrass artifacts bucket.   
            This will be auto-populated by the helper scripts for each component, but it’s important to define the name of the packaged artifact name as it’s expected to appear in S3.   
            
            For example, for the inference app, the component will be the entire folder of the repository where the code of the application is hosted, compressed and stored as a zip file. Hence: "s3://BUCKET_NAME/COMPONENT_NAME/COMPONENT_VERSION/app.zip"   
            
            On the other hand, for a model it may look like this: "s3://BUCKET_NAME/COMPONENT_NAME/COMPONENT_VERSION/model.tar.gz"  
        * Unarchive: optional attribute that defines how to unpackage the component once on edge  

    * the Lifecycle section defines a series of commands to be run throughout the lifecycle of the component on the edge device, such as installing the required libraries and running the inference application.

## Deployment of GrenGrass components cross-account (preprod and prod)

It is important to note that the preprod and prod IoT roles defined when the project was created are not provisioned by this repository. Instead, they must exist and be deployed in the preprod and prod accounts via another process. This deployment repository is attached to a CodePipeline process that will assume the preprod and prod IoT roles with the purposes of creating the GreenGrass components and create the deployments against the specified IoT target groups. Thus, this role must contain the following permissions in order to work.

### General Policies

The role must contain similar policies such as the TokenExchangeRole created in the dev account, with some additions:

#### IoT

``` JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "iot:DescribeCertificate",
                "iot:CreateJob",
                "iot:DescribeThingGroup",
                "iot:DescribeJob",
                "logs:CreateLogGroup",
                "iot:CancelJob",
                "logs:CreateLogStream",
                "logs:DescribeLogStreams",
                "logs:PutLogEvents",
                "s3:GetBucketLocation"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```

#### GreenGrass

``` JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "greengrass:CreateComponentVersion",
                "greengrass:DescribeComponent",
                "greengrass:List*",
                "greengrass:CreateDeployment"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```

#### S3

``` JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Statement1",
            "Effect": "Allow",
            "Action": [
                "s3:Put*",
                "s3:Get*",
                "s3:List*",
                "s3:Describe*"
            ],
            "Resource": [
                "arn:aws:s3:::{DEV_ACCOUNT_BUCKET}",
                "arn:aws:s3:::{DEV_ACCOUNT_BUCKET}*",
            ]
        }
    ]
}
```


#### KMS

``` JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "iam:ListGroups",
                "iam:ListRoles",
                "iam:ListUsers",
                "kms:CreateAlias",
                "kms:CreateKey",
                "kms:Decrypt",
                "kms:DeleteAlias",
                "kms:Describe*",
                "kms:GenerateRandom",
                "kms:Get*",
                "kms:List*",
                "kms:TagResource",
                "kms:UntagResource"
            ],
            "Resource": [
                "*",
                "arn:aws:kms:eu-west-1:{DEV_ACCOUNT}:key/*"
            ],
            "Effect": "Allow"
        }
    ]
}
```



### Trust Relationship

Allow the `dev` account to access `preprod` and `prod` account:

``` JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Statement1",
            "Effect": "Allow",
            "Principal": {
                "Service": "credentials.iot.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        },
        {
            "Sid": "Statement2",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::{DEV_ACCOUNT}:root"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```


