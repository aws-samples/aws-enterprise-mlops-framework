import pickle
import xgboost
import onnx
import argparse
import uuid
import tarfile
import logging

from pathlib import Path
import numpy as np

from skl2onnx.common.data_types import FloatTensorType
from onnxmltools.convert import convert_xgboost as convert_xgboost_booster

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='convert XGBOOST model to ONNX')

    parser.add_argument('--input', type=str, help="input model")
    parser.add_argument('--output', type=str, help="output onnx model")
    
    args = parser.parse_args()
    
    # Folder structure creation
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    input_tar_path = input_dir/'model.tar.gz'
    input_extract_dir = Path(f'/tmp/{str(uuid.uuid4())}')
    input_extract_dir.mkdir(exist_ok=True)
    input_tar = tarfile.open(input_tar_path, "r:gz")
    input_tar.extractall(input_extract_dir)
    
    input_model_path = input_extract_dir/'xgboost-model'
    
    # ONNX conversion
    model = pickle.load(input_model_path.open("rb"))
    onnx_path = input_model_path.with_name('model.onnx')
    initial_type = [("float_input", FloatTensorType([None, model.num_features()]))]
    onx = convert_xgboost_booster(model, "xgboost", initial_types=initial_type)
    with open(onnx_path, "wb") as f:
        f.write(onx.SerializeToString())
    
    # Load the ONNX model
    model_proto = onnx.load_model(onnx_path)
    # Check if the converted ONNX protobuf is valid
    onnx.checker.check_model(model_proto)
    
    output_tar_path = output_dir/'model.tar.gz'
    output_tar = tarfile.open(output_tar_path, "w:gz")
    output_tar.add(onnx_path, arcname=onnx_path.name)
    output_tar.close()
    
    logger.info(f'Finished.')

    
if __name__ == '__main__':
    main()
    
