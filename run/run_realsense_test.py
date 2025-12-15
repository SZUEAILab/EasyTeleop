import pyrealsense2 as rs
import cv2
import numpy as np
import time
import os
import sys

if __name__ == '__main__':


    # 确定图像的输入分辨率与帧率
    resolution_width = 640  # pixels
    resolution_height = 480  # pixels
    frame_rate = 15  # fps

    # 注册数据流，并对其图像
    align = rs.align(rs.stream.color)
    rs_config = rs.config()
    rs_config.enable_stream(rs.stream.depth, resolution_width, resolution_height, rs.format.z16, frame_rate)
    rs_config.enable_stream(rs.stream.color, resolution_width, resolution_height, rs.format.bgr8, frame_rate)
    ### d435i
    #
    # rs_config.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, frame_rate)
    # rs_config.enable_stream(rs.stream.infrared, 2, 640, 480, rs.format.y8, frame_rate)
    # check相机是不是进来了
    connect_device = []
    for d in rs.context().devices:
        print('Found device: ',
              d.get_info(rs.camera_info.name), ' ',
              d.get_info(rs.camera_info.serial_number))
        if d.get_info(rs.camera_info.name).lower() != 'platform camera':
            connect_device.append(d.get_info(rs.camera_info.serial_number))


    if len(connect_device) < 2:
        print('Registrition needs two camera connected.But got one.')
        exit()

    # 确认相机并获取相机的内部参数
    pipeline1 = rs.pipeline()
    rs_config.enable_device(connect_device[0])
    # pipeline_profile1 = pipeline1.start(rs_config)
    pipeline1.start(rs_config)

    pipeline2 = rs.pipeline()
    rs_config.enable_device(connect_device[1])
    # pipeline_profile2 = pipeline2.start(rs_config)
    pipeline2.start(rs_config)

    pipeline3 = rs.pipeline()
    rs_config.enable_device(connect_device[2])
    # pipeline_profile2 = pipeline2.start(rs_config)
    pipeline3.start(rs_config)

    try:

        while True:

            # 等待数据进来
            frames1 = pipeline1.wait_for_frames()
            frames2 = pipeline2.wait_for_frames()
            frames3 = pipeline3.wait_for_frames()

            # 将进来的RGBD数据对齐
            aligned_frames1 = align.process(frames1)
            aligned_frames2 = align.process(frames2)
            aligned_frames3 = align.process(frames3)

            # 将对其的RGB—D图取出来
            color_frame1 = aligned_frames1.get_color_frame()
            depth_frame1 = aligned_frames1.get_depth_frame()
            color_frame2 = aligned_frames2.get_color_frame()
            depth_frame2 = aligned_frames2.get_depth_frame()
            color_frame2 = aligned_frames3.get_color_frame()
            depth_frame3 = aligned_frames3.get_depth_frame()
            # --------------------------------------
            depth_frame1 = frames1.get_depth_frame()
            color_frame1 = frames1.get_color_frame()
            depth_frame2 = frames2.get_depth_frame()
            color_frame2 = frames2.get_color_frame()
            depth_frame3 = frames3.get_depth_frame()
            color_frame3 = frames3.get_color_frame()

            # 数组化数据便于处理

            # ir_frame_left1 = frames1.get_infrared_frame(1)
            # ir_frame_right1 = frames1.get_infrared_frame(2)
            # if not depth_frame1 or not color_frame1:
            #     continue
            # ir_frame_left2 = frames2.get_infrared_frame(1)
            # ir_frame_right2 = frames2.get_infrared_frame(2)
            # if not depth_frame2 or not color_frame2:
            #     continue

            color_image1 = np.asanyarray(color_frame1.get_data())
            depth_image1 = np.asanyarray(depth_frame1.get_data())
            # ir_left_image1 = np.asanyarray(ir_frame_left1.get_data())
            # ir_right_image1 = np.asanyarray(ir_frame_right1.get_data())

            color_image2 = np.asanyarray(color_frame2.get_data())
            depth_image2 = np.asanyarray(depth_frame2.get_data())
            # ir_left_image2 = np.asanyarray(ir_frame_left2.get_data())
            # ir_right_image2 = np.asanyarray(ir_frame_right2.get_data())

            color_image3 = np.asanyarray(color_frame3.get_data())
            depth_image3 = np.asanyarray(depth_frame3.get_data())
            # ir_left_image2 = np.asanyarray(ir_frame_left2.get_data())
            # ir_right_image2 = np.asanyarray(ir_frame_right2.get_data())

            depth_colormap1 = cv2.applyColorMap(cv2.convertScaleAbs(depth_image1, alpha=0.03), cv2.COLORMAP_JET)
            images1 = np.hstack((color_image1, depth_colormap1))

            depth_colormap2 = cv2.applyColorMap(cv2.convertScaleAbs(depth_image2, alpha=0.03), cv2.COLORMAP_JET)
            images2 = np.hstack((color_image2, depth_colormap2))

            depth_colormap3 = cv2.applyColorMap(cv2.convertScaleAbs(depth_image3, alpha=0.03), cv2.COLORMAP_JET)
            images3 = np.hstack((color_image3, depth_colormap3))

            cv2.imshow('RealSense1', images1)
            cv2.imshow('RealSense2', images2)
            cv2.imshow('RealSense3', images3)

            key = cv2.waitKey(1)

            if key & 0xFF == ord('q') or key == 27:
                cv2.destroyAllWindows()
                break
    finally:
        pipeline1.stop()
        pipeline2.stop()
