import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
import awsiot.greengrasscoreipc.client as client
from awsiot.greengrasscoreipc.model import (
    IoTCoreMessage,
    QOS,
    SubscribeToIoTCoreRequest,
    PublishToIoTCoreRequest,
    SubscriptionResponseMessage,
    PublishMessage,
    BinaryMessage,
)
import traceback
import json
from queue import Queue
import logging
import time
import numpy as np

MQTT_TIMEOUT = 10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NpEncoder(json.JSONEncoder):
    """Encoder for numpy objecs

    Args:
        json ():
    """

    def default(self, obj):
        """Runs default and change the type depending of np object

        Args:
            obj (any): Input object

        Returns:
            any: modified object
        """
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


class StreamHandler(client.SubscribeToIoTCoreStreamHandler):
    """Streamhandler

    Args:
        client (Stream): Class to deal with events from iot core
    """

    def __init__(self):
        """Init"""
        super().__init__()
        self.queue = Queue()

    def on_stream_event(self, event: IoTCoreMessage) -> None:
        """Handle string event

        Args:
            event (IoTCoreMessage): An iot core message
        """
        try:
            message = str(event.message.payload, "utf-8")
            topic_name = event.message.topic_name
            print(
                f"Primary::StreamHandler - Received message {message} on topic {topic_name}"
            )
            self.queue.put(json.loads(message))
        except Exception as e:
            traceback.print_exc()

    def on_stream_error(self, error: Exception) -> bool:
        """respond on error

        Args:
            error (Exception): Type of exception

        Returns:
            bool: True if exception is handle
        """
        # Handle error.
        return True  # Return True to close stream, False to keep stream open.

    def on_stream_closed(self) -> None:
        """on_stram_closed"""
        # Handle close.
        pass


class GreengrassMqtt:
    """Class to deal with Mqtt events"""

    def __init__(
        self, 
        incoming_topic: str, 
        outgoing_topic: str, 
        mqtt_timeout=MQTT_TIMEOUT
    ):
        """Initialization method

        Args:
            incoming_topic (str): incoming topic to handle
            outgoing_topic (str): out going topic to send messages
            mqtt_timeout (_type_, optional): Time in seconds to deal with message. Defaults to MQTT_TIMEOUT.
        """

        self.ipc_client = awsiot.greengrasscoreipc.connect()
        qos = QOS.AT_MOST_ONCE
        self.incoming_topic = incoming_topic
        self.outgoing_topic = outgoing_topic
        self.request_in = SubscribeToIoTCoreRequest()
        self.request_in.topic_name = self.incoming_topic
        self.request_in.qos = qos
        self.handler = StreamHandler()
        self.queue = self.handler.queue
        self.mqtt_timeout = mqtt_timeout
        operation = self.ipc_client.new_subscribe_to_iot_core(self.handler)
        future_response = operation.activate(self.request_in)
        # future_response = operation.get_response()
        future_response.result(self.mqtt_timeout)

        self.request_out = PublishToIoTCoreRequest()
        self.request_out.topic_name = outgoing_topic

    def publish_message(self, message: dict):
        """Publish message using mqtt

        Args:
            message (dict): A dictionary that would be converted to json
        """
        # self.request_out = PublishToIoTCoreRequest()
        # self.request_out.topic_name = self.outgoing_topic
        try:
            self.request_out.payload = bytes(
                json.dumps(message, cls=NpEncoder), "utf-8"
            )

            qos = QOS.AT_LEAST_ONCE
            self.request_out.qos = qos
            operation = self.ipc_client.new_publish_to_iot_core()
            operation.activate(self.request_out)

            future_response = operation.get_response()
            future_response.result(self.mqtt_timeout)
        except Exception as e:
            logger.warning(f"Got {e} when trying to send Mqtt message")
            exc = f"{e} | {traceback.format_exc()}"
            logger.warning(exc)
            

class GGIPCSubscriberHandler:
    def __init__(self, incoming_topic: str, callback_queue: Queue):
        """Initialized subscriber handler

        Args:
            incoming_topic (str): Name of the topic eg incoming/topic
            callback_queue (Queue): Queue to send messages
        """
        self.incoming_topic = incoming_topic
        self.incoming_queue = callback_queue

    # noinspection PyMethodMayBeStatic
    def sub_on_stream_event(self, event: SubscriptionResponseMessage) -> None:
        """Even of incoming messages

        Args:
            event (SubscriptionResponseMessage):
        """
        # message_string = str(event.binary_message.message, "utf-8")
        logging.debug(
            "IPC Message received on topic {} at : {}".format(
                self.incoming_topic, time.time()
            )
        )
        try:
            receiver_payload: str = event.binary_message.message.decode("utf-8")
            logging.debug(
                "Received message from the GG IPC topic is {}.".format(receiver_payload)
            )
            self.incoming_queue.put((self.incoming_topic, receiver_payload))
            logging.debug("Message sent to queue at : {}".format(time.time()))
            # logging.debugger.info("Message sent to queue - put completed. - Queue size is {}".format(q.qsize()))
        except (ValueError, Exception):
            logging.debug(
                "Exception - Failed during reading message from event - ",
                traceback.format_exc(),
            )

    # noinspection PyMethodMayBeStatic
    def sub_on_stream_error(self, err_info) -> bool:
        """Handle errors

        Args:
            err_info (err_info): Error information

        Returns:
            bool: True if handled error correctly
        """
        logging.debug("On Stream error {}".format(err_info))
        return True

    # noinspection PyMethodMayBeStatic
    def sub_on_stream_closed(self) -> None:
        # Handle error.
        pass


class GGIPCHandler:
    """
    message_name == JudgementEngine, PLCInterface etc
    incoming_topic_names == captureresult etc
    """

    def __init__(
        self, incoming_topic_names: str, message_name: str = None, config: dict = None
    ):
        """Initialize gg ipc class

        Args:
            incoming_topic_names (str): incoming topic
            message_name (str, optional): message name. Defaults to None.
            config (dict, optional): Configuration. Defaults to None.
        """
        logging.debug("Initiating IPC client")
        self.ipc_sub_client = GreengrassCoreIPCClientV2()
        self.incoming_queue = Queue()

        for incoming_topic_name in incoming_topic_names:
            handler = GGIPCSubscriberHandler(incoming_topic_name, self.incoming_queue)
            try:
                response, operation = self.ipc_sub_client.subscribe_to_topic(
                    topic=incoming_topic_name,
                    on_stream_event=handler.sub_on_stream_event,
                    on_stream_error=handler.sub_on_stream_error,
                    on_stream_closed=handler.sub_on_stream_closed,
                )
                logging.debug(
                    "Successfully subscribed to the topic : {}".format(
                        incoming_topic_name
                    )
                )
            except (ValueError, Exception):
                logging.debug(
                    "Exception - Failed during subscribing - ", traceback.format_exc()
                )

    def publish_ipc_message(self, topic: str, message: dict):
        """Publishes and ipc message

        Args:
            topic (str): outgoing topic
            message (dict): message as a dictionary
        """
        message_payload = json.dumps(message, cls=NpEncoder)
        self.ipc_sub_client.publish_to_topic(
            topic=topic,
            publish_message=PublishMessage(
                binary_message=BinaryMessage(message=message_payload)
            ),
        )
        logging.debug(
            f"Successfully published PLC message {message_payload} to the topic: {topic}"
        )
