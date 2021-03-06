"""
Demo of HMR.

Note that HMR requires the bounding box of the person in the image. The best performance is obtained when max length of the person in the image is roughly 150px. 

When only the image path is supplied, it assumes that the image is centered on a person whose length is roughly 150px.
Alternatively, you can supply output of the openpose to figure out the bbox and the right scale factor.

Sample usage:

# On images on a tightly cropped image around the person
python -m demo --img_path data/im1963.jpg
python -m demo --img_path data/coco1.png

# On images, with openpose output
python -m demo --img_path data/random.jpg --json_path data/random_keypoints.json
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
from absl import flags
import numpy as np

import skimage.io as io
import tensorflow as tf

from src.util import renderer as vis_util
from src.util import image as img_util
from src.util import openpose as op_util
import src.config
from src.RunModel import RunModel

import cv2
import os
import imageio

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def visualize(img, proc_param, joints, verts, cam):
    """
    Renders the result in original image coordinate frame.
    """
    cam_for_render, vert_shifted, joints_orig = vis_util.get_original(
        proc_param, verts, cam, joints, img_size=img.shape[:2])

    # Render results
    rend_img = renderer(
        vert_shifted, cam=cam_for_render, img_size=img.shape[:2])
    
    return rend_img


def preprocess_image(img_path, json_path=None):
    #img = io.imread(img_path)
    img = img_path
    if img.shape[2] == 4:
        img = img[:, :, :3]

    if json_path is None:
        if np.max(img.shape[:2]) != config.img_size:
            print('Resizing so the max image size is %d..' % config.img_size)
            scale = (float(config.img_size) / np.max(img.shape[:2]))
        else:
            scale = 1.
        center = np.round(np.array(img.shape[:2]) / 2).astype(int)
        # image center in (x,y)
        center = center[::-1]
    else:
        scale, center = op_util.get_bbox(json_path)

    crop, proc_param = img_util.scale_and_crop(img, scale, center,
                                               config.img_size)

    # Normalize image to [-1, 1]
    crop = 2 * ((crop / 255.) - 0.5)

    return crop, proc_param, img


def main(img_path, json_path=None):
    

    input_img, proc_param, img = preprocess_image(img_path, json_path)
    # Add batch dimension: 1 x D x D x 3
    input_img = np.expand_dims(input_img, 0)

    joints, verts, cams, joints3d, theta = model.predict(
        input_img, get_theta=True)

    return visualize(img, proc_param, joints[0], verts[0], cams[0])


if __name__ == '__main__':
    
    config = flags.FLAGS
    config(sys.argv)
    # Using pre-trained model, change this to use your own.
    config.load_path = src.config.PRETRAINED_MODEL

    config.batch_size = 1

    renderer = vis_util.SMPLRenderer(face_path=config.smpl_face_path)
    
    vid_path = "video/federer_slowmotion_360p.mp4"
    
    if not os.path.isfile(vid_path):
        print("Input file does ", vid_path, " doesn't exist")
    
    outputFile = "output/" + vid_path.split("/")[1].split(".")[0]+"_render.avi"
    
    reader = imageio.get_reader(vid_path)
    fps = reader.get_meta_data()['fps']
    writer = imageio.get_writer(outputFile, fps = fps)
        
    # Run model
    sess = tf.Session()
    model = RunModel(config, sess=sess)
    
    for i, frame in enumerate(reader):

        plt.imshow(frame)
        plt.title('Based')
        plt.savefig('output/based.jpg')
        
        rendered_img = main(frame, json_path=None)
        
        plt.imshow(rendered_img)
        plt.title('Rendered Image')
        plt.savefig('output/rendered.jpg')
        
        writer.append_data(rendered_img)
        print(i)
        
        if cv2.waitKey(1) > 0:
            writer.close()
            break
        
    writer.close()