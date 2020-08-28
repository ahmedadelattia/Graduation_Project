from __future__ import division
import tensorflow as tf
import tensornets as nets
import numpy as np
import matplotlib.pyplot as plt
import math
from IPython.display import clear_output
import random
import cv2
from copy import copy, deepcopy
from pathlib import Path
import os
import time 
from datetime import timedelta
from tqdm import tqdm
#import zipfile
import tarfile
import shutil
import wget
import sys
sys.path.append('~/data/nutshell')
import voc
from utils import *



C1=[238, 72, 58, 24, 203, 230, 54, 167, 246, 136, 106, 95, 226, 171, 43, 159, 231, 101, 65, 157]
C2=[122, 71, 173, 32, 147, 241, 53, 197, 228, 164, 4, 209, 175, 223, 176, 182, 48, 3, 70, 13]
C3=[148, 69, 133, 41, 157, 137, 125, 245, 89, 85, 162, 43, 16, 178, 197, 150, 13, 140, 177, 224]
idx_to_labels=['aeroplane','bicycle','bird','boat','bottle','bus','car','cat','chair','cow','diningtable','dog','horse','motorbike','person','pottedplant','sheep','sofa','train','tvmonitor']
def visualize_img(img,bboxes,thickness,name):
  img=img.reshape(img.shape[1],img.shape[1],3)
  for c, boxes_c in enumerate(bboxes):
    for b in boxes_c:

      ul_x, ul_y=int(b[0]), int(b[1])
      br_x, br_y=int(b[2]), int(b[3])

      color_class=(C1[c], C2[c], C3[c])
      img=cv2.rectangle(img, (ul_x, ul_y), (br_x, br_y), color=color_class, thickness=3) 
      label = '%s: %.2f' % (idx_to_labels[c], b[-1]) 
      labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1) 
      ul_y = max(ul_y, labelSize[1]) 
      img=cv2.rectangle(img, (ul_x, ul_y - labelSize[1]), (ul_x + labelSize[0], ul_y + baseLine),color_class, cv2.FILLED) 
      img=cv2.putText(img, label, (ul_x, ul_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0)) 

  cv2.imwrite(name+'.jpg', img)
  #cv2_imshow(img)
  return img

tf.reset_default_graph() # It's importat to resume training from latest checkpoint 

voc_dir = '/home/alex054u4/data/nutshell/newdata/VOCdevkit/VOC%d'

# Define the model hyper parameters
is_training = tf.placeholder(tf.bool)
N_classes=20
x = tf.placeholder(tf.float32, shape=(None, 416, 416, 3), name='input_x')
yolo=model(x,nets.MobileNet50, 'voc', yolo_head='sep')
# Define an optimizer
step = tf.Variable(0, trainable=False)
gstep = tf.Variable(0, trainable=False)

lr     = tf.Variable(1e-8,trainable=False,dtype=tf.float64)
lr_sch = tf.math.multiply(lr,tf.math.pow(tf.cast(0.5,tf.float64),tf.math.divide(step,10)))

train = tf.train.AdamOptimizer(lr, 0.9).minimize(yolo.loss,global_step=gstep)

current_epo= tf.Variable(0, name = 'current_epo',trainable=False,dtype=tf.int32)

#Check points for step training_trial_step
checkpoint_path   = "/home/alex054u3/data/nutshell/training_trial_step_mobilenetv1_50_voc-LRShoot_darkconv_more_filters"
checkpoint_prefix = os.path.join(checkpoint_path,"ckpt")
if not os.path.exists(checkpoint_path):
  os.mkdir(checkpoint_path)



init_op     = tf.global_variables_initializer()
train_saver = tf.train.Saver(max_to_keep=2)

def evaluate_accuracy(data_type='tr'):
  if (data_type  == 'tr'): acc_data  = voc.load(voc_dir % 2007,'trainval')
  elif(data_type == 'te') : acc_data  = voc.load(voc_dir % 2007, 'test')
  
  #print('Train Accuracy: ',voc.evaluate(boxes, voc_dir % 2007, 'trainval'))
  results = []
  idx     = np.random.randint(100)
  for i,(img,_) in enumerate(acc_data):
    acc_outs = sess.run(yolo, {x: yolo.preprocess(img),is_training: False})
    boxes=yolo.get_boxes(acc_outs, img.shape[1:3])
    results.append(boxes)
    if(i == idx):
      img_vis=img
      boxes_vis=boxes
  if (data_type  =='tr'):
    eval_print=voc.evaluate(results, voc_dir % 2007, 'trainval')
  elif (data_type=='te'):
    #visualize_img(yolo.preprocess(img_vis)*255,boxes_vis,5,'img')
    eval_print=voc.evaluate(results, voc_dir % 2007, 'test')
  print('\n')
  print(eval_print)
  return eval_print
  
acc_best, best_epoch=0.0, 0

sched={100: 1e-7, 180: 1e-6, 320: 1e-5}
def lr_sched(gstep):
	if gstep.eval() in sched.keys():
		sess.run(lr.assign(sched[gstep.eval()]))	

with tf.Session() as sess:
  ckpt_files = [f for f in os.listdir(checkpoint_path) if os.path.isfile(os.path.join(checkpoint_path, f)) and 'ckpt' in f]
  if (len(ckpt_files)!=0):
    train_saver.restore(sess,checkpoint_prefix)
  else:
    sess.run(init_op)
    sess.run(yolo.stem.pretrained())

  for i in tqdm(range(step.eval(),233)):
    # Iterate on VOC07+12 trainval once
    losses = []
    trains = voc.load_train([voc_dir % 2007, voc_dir % 2012],'trainval', batch_size=48)
    sess.run(step.assign(i))
    
    for btch, (imgs, metas) in enumerate(trains):

      # `trains` returns None when it covers the full batch once
      if imgs is None: break         
      metas.insert(0, yolo.preprocess(imgs))  # for `inputs`
      metas.append(True)                      # for `is_training`
      outs= sess.run([train, yolo.loss],dict(zip(yolo.inputs, metas)))
      losses.append(outs[-1])
      lr_sched(gstep)
    
    print('\nepoch:',step.eval(),'lr: ',lr.eval(),'loss:',np.mean(losses))
    tr_ac=evaluate_accuracy('tr')
    ts_ac=evaluate_accuracy('te')
    print ('\n')    

    acc =float(ts_ac.split(' = ')[-1])

    if(i%5 == 0):
      if (acc > acc_best):
        acc_best= acc
        sess.run(step.assign(i))
        sess.run(lr.assign(lr_sch))
      else:
        sess.run(lr.assign(1e-5))

    if (acc > acc_best):
      acc_best= acc
      train_saver.save(sess,checkpoint_prefix)
      best_epoch=i


    print ('highest val accuacy:', acc_best, 'at epoch:', best_epoch, '\n')
    print ('=================================================================================================================================================================================')