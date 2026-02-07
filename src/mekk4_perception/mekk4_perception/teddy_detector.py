import os
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ultralytics import YOLO

TEDDY_CLASS_ID = 77  # COCO teddy bear

class TeddyDetector(Node):
    def __init__(self):
        super().__init__("teddy_detector")

        self.model_path = os.environ.get("MEKK4_NCNN_MODEL", "/ws/models/yolo26n_ncnn_model")
        self.source = os.environ.get("MEKK4_CAM_SOURCE", "tcp://127.0.0.1:8888")
        self.conf = float(os.environ.get("MEKK4_CONF", "0.25"))
        self.imgsz = int(os.environ.get("MEKK4_IMGSZ", "640"))

        self.get_logger().info(f"Model:  {self.model_path}")
        self.get_logger().info(f"Source: {self.source}")
        self.get_logger().info(f"conf={self.conf} imgsz={self.imgsz}")

        # Explicit task to remove warning
        self.model = YOLO(self.model_path, task="detect")

        self.pub = self.create_publisher(String, "/teddy_detector/status", 10)
        self.last = None

        # Run inference loop in background thread
        self._stop = False
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def loop(self):
        # stream=True => generator, no RAM accumulation
        try:
            results = self.model.predict(
                source=self.source,
                stream=True,
                imgsz=self.imgsz,
                conf=self.conf,
                classes=[TEDDY_CLASS_ID],
                verbose=False,
            )
            for r in results:
                if self._stop:
                    break
                count = 0 if r.boxes is None else len(r.boxes)
                msg = String()
                msg.data = f"teddy_count={count}"
                self.pub.publish(msg)
                if msg.data != self.last:
                    self.get_logger().info(msg.data)
                    self.last = msg.data
        except Exception as e:
            self.get_logger().error(f"inference loop crashed: {e}")

    def destroy_node(self):
        self._stop = True
        super().destroy_node()

def main():
    rclpy.init()
    node = TeddyDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
