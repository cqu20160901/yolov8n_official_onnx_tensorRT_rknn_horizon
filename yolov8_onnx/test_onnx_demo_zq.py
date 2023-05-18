#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import argparse
import os
import sys
import os.path as osp
import cv2
import torch
import numpy as np
import onnxruntime as ort
from math import exp

ROOT = os.getcwd()
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

CLASSES = ['aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus', 'car', 'cat', 'chair', 'cow', 'diningtable', 'dog',
           'horse', 'motorbike', 'person', 'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor']

meshgrid = []

class_num = len(CLASSES)
headNum = 3
strides = [8, 16, 32]
mapSize = [[80, 80], [40, 40], [20, 20]]
nmsThresh = 0.45
objectThresh = 0.35

input_imgH = 640
input_imgW = 640


class DetectBox:
    def __init__(self, classId, score, xmin, ymin, xmax, ymax):
        self.classId = classId
        self.score = score
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax


def GenerateMeshgrid():
    for index in range(headNum):
        for i in range(mapSize[index][0]):
            for j in range(mapSize[index][1]):
                meshgrid.append(j + 0.5)
                meshgrid.append(i + 0.5)


def IOU(xmin1, ymin1, xmax1, ymax1, xmin2, ymin2, xmax2, ymax2):
    xmin = max(xmin1, xmin2)
    ymin = max(ymin1, ymin2)
    xmax = min(xmax1, xmax2)
    ymax = min(ymax1, ymax2)

    innerWidth = xmax - xmin
    innerHeight = ymax - ymin

    innerWidth = innerWidth if innerWidth > 0 else 0
    innerHeight = innerHeight if innerHeight > 0 else 0

    innerArea = innerWidth * innerHeight

    area1 = (xmax1 - xmin1) * (ymax1 - ymin1)
    area2 = (xmax2 - xmin2) * (ymax2 - ymin2)

    total = area1 + area2 - innerArea

    return innerArea / total


def NMS(detectResult):
    predBoxs = []

    sort_detectboxs = sorted(detectResult, key=lambda x: x.score, reverse=True)

    for i in range(len(sort_detectboxs)):
        xmin1 = sort_detectboxs[i].xmin
        ymin1 = sort_detectboxs[i].ymin
        xmax1 = sort_detectboxs[i].xmax
        ymax1 = sort_detectboxs[i].ymax
        classId = sort_detectboxs[i].classId

        if sort_detectboxs[i].classId != -1:
            predBoxs.append(sort_detectboxs[i])
            for j in range(i + 1, len(sort_detectboxs), 1):
                if classId == sort_detectboxs[j].classId:
                    xmin2 = sort_detectboxs[j].xmin
                    ymin2 = sort_detectboxs[j].ymin
                    xmax2 = sort_detectboxs[j].xmax
                    ymax2 = sort_detectboxs[j].ymax
                    iou = IOU(xmin1, ymin1, xmax1, ymax1, xmin2, ymin2, xmax2, ymax2)
                    if iou > nmsThresh:
                        sort_detectboxs[j].classId = -1
    return predBoxs


def postprocess(out, img_h, img_w):
    print('postprocess ... ')
    detectResult = []
    print(out.shape)
    scale_h = img_h / input_imgH
    scale_w = img_w / input_imgW

    coord_index = [mapSize[0][0]*mapSize[0][1], mapSize[1][0]*mapSize[1][1], mapSize[2][0]*mapSize[2][1]]

    gridIndex = -2

    for index in range(headNum):
        if 0 == index:
            cls = out[0, 4:class_num + 4, 0:coord_index[index]]
            reg = out[0, 0:4, 0:coord_index[index]]
        if 1 == index:
            cls = out[0, 4:class_num + 4, coord_index[index-1]:coord_index[index-1] + coord_index[index]]
            reg = out[0, 0:4, coord_index[index-1]:coord_index[index-1] + coord_index[index]]
        if 2 == index:
            cls = out[0, 4:class_num + 4, coord_index[index-2] + coord_index[index-1]:coord_index[index-2] + coord_index[index-1] + coord_index[index]]
            reg = out[0, 0:4, coord_index[index-2] + coord_index[index-1]:coord_index[index-2] + coord_index[index-1] + coord_index[index]]
        for h in range(mapSize[index][0]):
            for w in range(mapSize[index][1]):
                gridIndex += 2

                for cl in range(class_num):
                    cls_val = cls[cl, h * mapSize[index][1] + w]

                    if cls_val > objectThresh:

                        x1 = (meshgrid[gridIndex + 0] - reg[0, h * mapSize[index][1] + w]) * strides[index]
                        y1 = (meshgrid[gridIndex + 1] - reg[1, h * mapSize[index][1] + w]) * strides[index]
                        x2 = (meshgrid[gridIndex + 0] + reg[2, h * mapSize[index][1] + w]) * strides[index]
                        y2 = (meshgrid[gridIndex + 1] + reg[3, h * mapSize[index][1] + w]) * strides[index]

                        xmin = x1 * scale_w
                        ymin = y1 * scale_h
                        xmax = x2 * scale_w
                        ymax = y2 * scale_h

                        xmin = xmin if xmin > 0 else 0
                        ymin = ymin if ymin > 0 else 0
                        xmax = xmax if xmax < img_w else img_w
                        ymax = ymax if ymax < img_h else img_h

                        box = DetectBox(cl, cls_val, xmin, ymin, xmax, ymax)
                        detectResult.append(box)
    # NMS
    print('detectResult:', len(detectResult))
    predBox = NMS(detectResult)

    return predBox


def precess_image(img_src, resize_w, resize_h):
    image = cv2.resize(img_src, (resize_w, resize_h), interpolation=cv2.INTER_LINEAR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = image.astype(np.float32)
    image /= 255
    return image


def detect(img_path):
    orig = cv2.imread(img_path)
    img_h, img_w = orig.shape[:2]
    image = precess_image(orig, input_imgW, input_imgH)

    image = image.transpose((2, 0, 1))
    image = np.expand_dims(image, axis=0)

    ort_session = ort.InferenceSession('./yolov8n_relu_20class_zq.onnx')
    pred_results = (ort_session.run(None, {'images': image}))

    predbox = postprocess(pred_results[0], img_h, img_w)

    print('obj num is :', len(predbox))

    for i in range(len(predbox)):
        xmin = int(predbox[i].xmin)
        ymin = int(predbox[i].ymin)
        xmax = int(predbox[i].xmax)
        ymax = int(predbox[i].ymax)
        classId = predbox[i].classId
        score = predbox[i].score

        cv2.rectangle(orig, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        ptext = (xmin, ymin)
        title = CLASSES[classId] + "%.2f" % score
        cv2.putText(orig, title, ptext, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

    cv2.imwrite('./test_onnx_result.jpg', orig)


if __name__ == '__main__':
    print('This is main ....')
    GenerateMeshgrid()
    img_path = './test.jpg'
    detect(img_path)
