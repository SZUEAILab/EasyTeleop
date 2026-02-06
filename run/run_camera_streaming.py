import argparse
import threading
import time

import cv2

from EasyTeleop.Components.WebRTC import UnityWebRTC
from EasyTeleop.Device.Camera import TestCamera


def _start_preview_loop(stop_event: threading.Event, frame_ref: dict) -> threading.Thread:
    def _loop():
        while not stop_event.is_set():
            frame = frame_ref.get("frame")
            if frame is not None:
                cv2.imshow("Camera Preview", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop_event.set()
                    break
            time.sleep(0.01)
        cv2.destroyAllWindows()

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


def main() -> int:
    parser = argparse.ArgumentParser(description="Camera streaming via WebRTC.")
    parser.add_argument("--signaling-url", default="ws://localhost", help="WebRTC signaling url, e.g. wss://example")
    parser.add_argument("--connection-id", default="Camera", help="WebRTC connection id")
    parser.add_argument("--fps", type=int, default=30, help="Camera FPS")
    parser.add_argument("--camera", choices=["test"], default="test")
    parser.add_argument("--preview", action="store_true", help="Show OpenCV preview window")
    args = parser.parse_args()

    camera = TestCamera({"fps": args.fps})

    camera.start()
    start_wait = time.time()
    while time.time() - start_wait < 5.0 and camera.get_conn_status() != 1:
        time.sleep(0.1)

    frame_ref = {"frame": None}
    stop_event = threading.Event()
    preview_thread = None

    if args.preview:
        preview_thread = _start_preview_loop(stop_event, frame_ref)

    client = UnityWebRTC(connection_id=args.connection_id, signaling_url=args.signaling_url)

    @camera.on("frame")
    def _on_frame(frame):
        frame_ref["frame"] = frame
        client.put_frame(frame)

    try:
        client.start()
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        client.stop()
        stop_event.set()
        if preview_thread:
            preview_thread.join(timeout=1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
