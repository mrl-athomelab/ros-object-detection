#!/usr/bin/env python

PKG = 'object_detection'
import roslib; roslib.load_manifest(PKG)
import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile
import label_map_util
import visualization_utils as vis_util
import numpy as np
import cv2
import os, rospkg
import rospy
import PIL

from collections import defaultdict
from io import StringIO
from matplotlib import pyplot as plt
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

if tf.__version__ != '1.4.0':
    raise ImportError('Please upgrade your tensorflow installation to v1.4.0!')


class ImageReceiver:
    def __init__(self):
        self.image_sub = rospy.Subscriber("/camera/rgb/image_rect_color", Image, self.callback)
        self.image_pub = rospy.Publisher("/object_detection/detected_objects_frame", Image)
        self.image = None
        self.bridge = CvBridge()

    def callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            print(e)
        #np_arr = np.fromstring(ros_data.data, np.uint8)
        #image_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        self.image = cv_image
        # print 'received image of type: "%s"' % ros_data.format


rp = rospkg.RosPack()
SCRIPT_PATH = os.path.join(rp.get_path("object_detection"), "scripts")

# What model to use.
MODEL_NAME = 'faster_rcn_resnet50_coco'
MODEL_PATH = os.path.join(SCRIPT_PATH, 'models', MODEL_NAME)

# Path to frozen detection graph.
# This is the actual model that is used for the object detection.
PATH_TO_CKPT = os.path.join(MODEL_PATH, 'frozen_inference_graph.pb')

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join(SCRIPT_PATH, 'data', 'sam_label_map.pbtxt')

NUM_CLASSES = 5

detection_graph = tf.Graph()
with detection_graph.as_default():
    od_graph_def = tf.GraphDef()
    with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')

label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)


# For the sake of simplicity we will use only 2 images:
# image1.jpg
# image2.jpg
# If you want to test the code with your images, just add path to the images to the TEST_IMAGE_PATHS.
PATH_TO_TEST_IMAGES_DIR = 'dataset/test_images'
TEST_IMAGE_PATHS = [os.path.join(SCRIPT_PATH, PATH_TO_TEST_IMAGES_DIR, 'image{}.jpg'.format(i)) for i in range(1, 3)]

# Size, in inches, of the output images.
IMAGE_SIZE = (12, 8)

rospy.init_node('xtion_sam_demo', anonymous=True)
r = rospy.Rate(1)  # 1hz
    
ir = ImageReceiver()

with detection_graph.as_default():
    with tf.Session(graph=detection_graph) as sess:
        # Definite input and output Tensors for detection_graph
        image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
        # Each box represents a part of the image where a particular object was detected.
        detection_boxes = detection_graph.get_tensor_by_name(
            'detection_boxes:0')
        # Each score represent how level of confidence for each of the objects.
        # Score is shown on the result image, together with the class label.
        detection_scores = detection_graph.get_tensor_by_name(
            'detection_scores:0')
        detection_classes = detection_graph.get_tensor_by_name(
            'detection_classes:0')
        num_detections = detection_graph.get_tensor_by_name('num_detections:0')
        # cap = cv2.VideoCapture(0)
        #window = cv2.namedWindow('frame')
        while not rospy.is_shutdown():
            r.sleep()
            # Capture frame-by-frame
            # ret, image_np = cap.read()
            image_np = ir.image
            if image_np is None:
                continue
            # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
            image_np_expanded = np.expand_dims(image_np, axis=0)
            # Actual detection.
            (boxes, scores, classes, num) = sess.run(
                [detection_boxes, detection_scores, detection_classes,
                 num_detections],
                feed_dict={image_tensor: image_np_expanded})
            # Visualization of the results of a detection.
            vis_util.visualize_boxes_and_labels_on_image_array(
                image_np,
                np.squeeze(boxes),
                np.squeeze(classes).astype(np.int32),
                np.squeeze(scores),
                category_index,
                use_normalized_coordinates=True,
                line_thickness=4,
                min_score_thresh=0.6)
            # Display the resulting frame
            cv2.imshow('frame',image_np)
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
            try:
                ir.image_pub.publish(ir.bridge.cv2_to_imgmsg(image_np, "bgr8"))
            except CvBridgeError as e:
                print(e)
        # When everything done, release the capture
        # cap.release()
        cv2.destroyAllWindows()

