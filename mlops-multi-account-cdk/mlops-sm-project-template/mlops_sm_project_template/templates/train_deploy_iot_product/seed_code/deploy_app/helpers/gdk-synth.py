import argparse
import json
import logging
import os
import yaml
import boto3
from botocore.exceptions import ClientError
import s3fs
import sagemaker
from pathlib import Path

logger = logging.getLogger(__name__)
sm_client = boto3.client("sagemaker")
gg_client = boto3.client('greengrassv2')
sagemaker_session = sagemaker.Session(sagemaker_client=sm_client)
fs = s3fs.S3FileSystem()
soft_dependencies = {
    "aws.greengrass.Nucleus": {
        "DependencyType": "SOFT",
        "VersionRequirement": ">=2.0.3 <3.1.0"
    },
}

class GreengrassComponent:
    def __init__(self, **kwargs):
        self.component_name = kwargs.get('component_name')
        self.folder = kwargs.get('RootFolder')
        self.bucket = kwargs.get('bucket')
        self.region = kwargs.get('region')
        self.lifecycle_instructions = kwargs.get('lifecycle_instructions')
        self.artifacts = kwargs.get("artifacts")
        self.dependencies = kwargs.get("dependencies")
        self.version = kwargs.get("version")
        self.build = kwargs.get("build")
        self.configuration = kwargs.get("configuration")


    def create_gdk_config(self, path):
        gdk_config = {
            "component": {
                self.component_name: {
                    "author": "mlops@edge-cicd",
                    "version": self.version,
                    "build": self.build,
                    "publish": {
                        "bucket": self.bucket,
                        "region": self.region
                    }
                }
            },
            "gdk_version": "1.1.0"
        }

        os.makedirs(path, exist_ok=True) 
        with open(f"{path}/gdk-config.json", "w") as f:
            json.dump(gdk_config, f, indent=4)

        return None
    

    def create_recipe(self, path):
        recipe = {
            "RecipeFormatVersion": "2020-01-25",
            "ComponentDependencies": self.dependencies,
            "Manifests": [
                {
                "Platform": {
                    "os": "all"
                },
                "Lifecycle": self.lifecycle_instructions,
                "Artifacts": self.artifacts
                }
            ]
        }
        
        if self.configuration:
            recipe["ComponentConfiguration"] = self.configuration

        os.makedirs(path, exist_ok=True) 
        with open(f"{path}/recipe.json", "w") as f:
            json.dump(recipe, f, indent=4)
        return None
    

def create_deployment(project_name_id, components):
    deployment = {
        "targetArn": "$THING_GROUP_ARN$",
        "deploymentName": f"{project_name_id}-greengrass-deployment",
        "components": {
            # Consider installing CLI separatelly to avoid Core/Cli mismatched versions
            # https://docs.aws.amazon.com/greengrass/v2/developerguide/install-gg-cli.html
            # "aws.greengrass.Cli": {
            # "componentVersion": "2.10.1",
            # "configurationUpdate": {}
            # }
        }
    }

    for component in components:
        deployment["components"][component.component_name] = {
            "componentVersion": component.version,
            "configurationUpdate": {}
        }

    with open("./deployment.json", "w") as f:
        json.dump(deployment, f, indent=4)
    return None


def get_approved_package(model_package_group_name):
    """Gets the latest approved model package for a model package group.

    Args:
        model_package_group_name: The model package group name.

    Returns:
        The SageMaker Model Package ARN.
    """
    try:
        # Get the latest approved model package
        response = sm_client.list_model_packages(
            ModelPackageGroupName=model_package_group_name,
            ModelApprovalStatus="Approved",
            SortBy="CreationTime",
            MaxResults=100,
        )
        approved_packages = response["ModelPackageSummaryList"]

        # Fetch more packages if none returned with continuation token
        while len(approved_packages) == 0 and "NextToken" in response:
            logger.debug("Getting more packages for token: {}".format(response["NextToken"]))
            response = sm_client.list_model_packages(
                ModelPackageGroupName=model_package_group_name,
                ModelApprovalStatus="Approved",
                SortBy="CreationTime",
                MaxResults=100,
                NextToken=response["NextToken"],
            )
            approved_packages.extend(response["ModelPackageSummaryList"])

        # Return error if no packages found
        if len(approved_packages) == 0:
            error_message = (
                f"No approved ModelPackage found for ModelPackageGroup: {model_package_group_name}"
            )
            logger.error(error_message)
            raise Exception(error_message)

        # Return the pmodel package arn
        model_package_arn = approved_packages[0]["ModelPackageArn"]
        logger.info(f"Identified the latest approved model package: {model_package_arn}")
        return model_package_arn
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)


def download_model_package_version(path, model_package_arn):
    """Downloads the latest approved model package for a model package group.

    Args:
        path: The path where to download the model.
        model_package_arn: The model package ARN.
        bucket: S3 bucket where the model is stored.

    Returns:
        None.
    """
    try:
        # get info on latest model package
        latest_model_package = sm_client.describe_model_package(ModelPackageName=model_package_arn)
        model_s3_uri = latest_model_package['InferenceSpecification']['Containers'][0]['ModelDataUrl']

        # download latest version of model
        fs.download(model_s3_uri, f'{path}/model.tar.gz')
    
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)


def get_latest_version(component_name):
    """Gets the latest version of a given component name, otherwise returns 0.0.0.
    Args:
        component_name: The name of the greengrass component whose version to retrieve.
    Returns:
        versions: list of archived versions for the input component.
    """
    # TODO: allow increase of major/minor version
    logger.info(f"Getting latest version for component: {component_name}")
    
    # Note = potentially include pagination control
    response = gg_client.list_components(
        maxResults=100,
        # nextToken='string'
    )
    
    components = [component['componentName'] for component in response['components']]
    if component_name in components:
        idx = components.index(component_name)
        return response['components'][idx]['latestVersion']['componentVersion']
    
    return "0.0.0" 


def update_version(last_version, how="patch"):
    how=how.lower()
    parts = ["major", "minor", "patch"]
    if how not in parts:
        raise ValueError("Incorrect versioning strategy.")
    ix = parts.index(how)
    values = last_version.split('.')
    values[ix] = str(int(values[ix]) + 1)
    # setting patch to 0 if how is minor or major
    if ix < 2:
        values[2] = '0' 
    # setting minor to 0 if how is major
    if ix < 1:
        values[1] = '0' 
    
    return ".".join(values)


# TODO: use MODEL_BUCKET_URI
def update_s3_uri(config):
    """
    Updates S3 location of greengrass components
    """
    URI = config["Artifacts"][0]["URI"]
    if ("$BUCKET_NAME$" in URI and config["bucket"]):
        URI = URI.replace("$BUCKET_NAME$", config["bucket"])
    else:
        raise ValueError("Missing bucket name")
    if ("$COMPONENT_NAME$" in URI and config["component-name"]):
        URI = URI.replace("$COMPONENT_NAME$", config["component-name"])
    else:
        raise ValueError("Missing component name")
    if ("$COMPONENT_VERSION$" in URI and config["version"]):
        URI = URI.replace("$COMPONENT_VERSION$", config["version"])
    else:
        raise ValueError("Missing component version")

    config["Artifacts"][0]["URI"]=URI

    return config


def replace_config_variable(config_field, proj_var, value):
    config_ = config_field.copy()
    tmp_json = json.dumps(config_)
    new_json = tmp_json.replace(proj_var, value)
    new_config = json.loads(new_json)

    return new_config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", type=str, default=os.environ.get("LOGLEVEL", "INFO").upper())
    parser.add_argument("--import-config-file", type=str, default="greengrass-config.yml")
    parser.add_argument("--project-name-id", type=str)
    parser.add_argument("--artifact-bucket-name", type=str)
    parser.add_argument("--region", type=str)
    parser.add_argument("--cache-models", type=str, default="False")
    parser.add_argument("--update-version", type=str, default="patch")
    args, _ = parser.parse_known_args()

    # Configure logging to output the line number and message
    log_format = "%(levelname)s: [%(filename)s:%(lineno)s] %(message)s"
    logging.basicConfig(format=log_format, level=args.log_level)

    # Read the staging config
    with open(args.import_config_file, "r") as f:
        greengrass_config = yaml.safe_load(f)

    # 1. evaluate components version and download latest models from SageMaker if SageMaker managed model
    for item, config in greengrass_config["custom-components"].items():
        # change component name to match project name
        component_name = config["component-name"]
        if '$PROJECT_NAME_ID$' in component_name:
            component_name = component_name.replace('$PROJECT_NAME_ID$', args.project_name_id)
            config["component-name"] = component_name
            config["build"] = replace_config_variable(config["build"], "$PROJECT_NAME_ID$", args.project_name_id)
            config["Lifecycle"] = replace_config_variable(config["Lifecycle"], "$PROJECT_NAME_ID$", args.project_name_id)
            
        else:
            raise ValueError("Project name missing")

        # evaluate if component is model and versioning strategy
        model = config.get("model")
        sagemaker_managed = ""
        if model: 
            sagemaker_managed = model.get("sagemaker-managed")

        if sagemaker_managed:
            # 1. Versioning by use of latest approved package version
            # TODO: change logic to allow for several model package groups
            model_package_arn = get_approved_package(args.project_name_id)
            model_version = model_package_arn.split('/')[-1]
            config["version"] = f"{model_version}.0.0"
            last_version = get_latest_version(component_name)
            # skip component creation if there is already one
            config["skip-build"] = config["version"] == last_version
            logger.info(f"Model version: {model_version}. Last Version: {last_version}.")
            
            if not config["skip-build"]:
                # downloading latest model version
                download_model_package_version(config['root'], model_package_arn)
            else:
                # avoid downloading if version is already in artifacts bucket
                logger.info(f"Skipping: {config['component-name']}. Version {config['version']} already exists.")
                (Path(config['root'])/'skip_build').touch()
        else:
            # 2. Versioning by use of versions file
            last_version = get_latest_version(component_name)
            config["version"] = update_version(last_version, how=args.update_version)

        config["bucket"] = args.artifact_bucket_name
        config = update_s3_uri(config)


    # 2. update component dependencies to match latest version and create gdk-config.json and recipe.json files
    components = [v["component-name"] for k,v in greengrass_config["custom-components"].items()]
    models = []

    model_dependencies = {}
    for item, config in greengrass_config["custom-components"].items():
        model = config.get("model")
        dependency = config.get("dependencies")
        # treat models and dependency package as the same
        if model or dependency:
            models.append(config["component-name"])
            # add soft dependencies to model components
            config["ComponentDependencies"] = soft_dependencies
            model_dependencies[config["component-name"]] = {
                "DependencyType":"HARD",
                "VersionRequirement":config["version"]
            }

    # add model dependencies to non-model components
    hard_dependencies = soft_dependencies.copy()
    hard_dependencies.update(model_dependencies)
    for item, config in greengrass_config["custom-components"].items():
        if config["component-name"] not in models:
            # config["ComponentDependencies"].update(dependencies)
            config["ComponentDependencies"] = hard_dependencies
            
    # 3. Include component configurations
    for item, config in greengrass_config["custom-components"].items():
        if "ComponentConfiguration" in config:
            if "accessControl" in config["ComponentConfiguration"]["DefaultConfiguration"]:
                for key in config["ComponentConfiguration"]["DefaultConfiguration"]["accessControl"]:
                    ipc = key.split(".")[-1]
                    component_name = next(iter(config["ComponentConfiguration"]["DefaultConfiguration"]["accessControl"][key]))
                    new_name = f"{config['component-name']}:{ipc}:1"    
                    config["ComponentConfiguration"]["DefaultConfiguration"]["accessControl"][key][new_name] = config["ComponentConfiguration"]["DefaultConfiguration"]["accessControl"][key].pop(component_name)

    # dump update yaml file
    with open("greengrass-config-updated.yml", "w") as file:
        yaml.dump(greengrass_config, file)

    ## build files
    deploy_components = []
    for item, config in greengrass_config["custom-components"].items():
            
        component = GreengrassComponent(
            component_name=config["component-name"],
            bucket=config["bucket"],
            region=args.region,
            folder=config["root"], 
            artifacts=config["Artifacts"],
            dependencies=config["ComponentDependencies"],
            lifecycle_instructions=config["Lifecycle"],
            version=config["version"],
            build=config["build"],
            configuration=config.get("ComponentConfiguration", None)
        )
        
        deploy_components.append(component)

        component.create_gdk_config(path=config["root"])
        component.create_recipe(path=config["root"])
            
    # 3. create deployment.json 
    create_deployment(args.project_name_id, deploy_components)
