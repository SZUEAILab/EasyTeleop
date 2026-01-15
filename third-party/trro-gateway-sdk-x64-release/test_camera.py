# test_camera.py
import cv2

import sys
print(sys.executable)  # 打印运行时的 Python 路径
# import cv2

# 尝试打开摄像头（索引 0 或 1）
cap = cv2.VideoCapture(16)
if not cap.isOpened():
    print("无法打开摄像头")
    exit()

# 显示摄像头画面
while True:
    ret, frame = cap.read()
    if not ret:
        print("无法获取画面")
        break
    cv2.imshow('Camera Test', frame)
    # 按 q 退出
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()