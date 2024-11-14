import sys 
import argparse
import onnxruntime
import logging
import time

import pandas as pd
import numpy as np

from pathlib import Path

from greengrass_mqtt_ipc import GreengrassMqtt

APP_DIR = Path(__file__).parent.resolve()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser("Performs inference.")

    parser.add_argument(
        "-m",
        "--model-path",
        type=str,
        help="The path of the model to import.",
    )
    parser.add_argument(
        "-i",
        "--input-data",
        type=str,
        default=APP_DIR/"data.csv",
        help="The path of the data.",
    )
    parser.add_argument(
        '--mqtt-topic', 
        type=str,       
        default="/test/inference", 
        help="topic to send results to"
    )
    
    args = parser.parse_args()
    
    mqtt_client = GreengrassMqtt(None, args.mqtt_topic, 10)
    
    # init inference session
    logger.info(f"Loading model from {args.model_path}...")
    sess = onnxruntime.InferenceSession(args.model_path, providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    
    # Load data
    df = pd.read_csv(args.input_data, header=None)
    y_test = df.iloc[:, 0].to_numpy()
    df.drop(df.columns[0], axis=1, inplace=True)
    X_test = np.array(df.values).astype(np.float32)
    
    # Model inference
    pred_onnx = sess.run([label_name], {input_name: X_test})[0]
    
    logger.info("Printing inference results:")
    logger.info(pred_onnx)
    
    while(True):
        for x, y, y_hat in zip(X_test, y_test, pred_onnx):
            payload = {
                'input': x,
                'label': y,
                'prediction': y_hat
            }
            mqtt_client.publish_message(payload)
            time.sleep(5)
    

if __name__ == "__main__":
    main()