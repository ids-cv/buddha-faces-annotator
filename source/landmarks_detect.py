import os
import cv2
import yaml
import numpy as np
from TDDFA_ONNX import TDDFA_ONNX


def detect_3D(im_path, bbox=None):
    cfg = yaml.load(open('source/configs/mb1_120x120.yml'), Loader=yaml.SafeLoader)
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    os.environ['OMP_NUM_THREADS'] = '4'
    tddfa = TDDFA_ONNX(**cfg)

    img = cv2.imread(im_path)
    param_lst, roi_box_lst = tddfa(img, [bbox])
    preds = tddfa.recon_vers(param_lst, roi_box_lst, dense_flag=False)
    preds = preds[0].T
    return preds


def best_fit_transform(A, B):
    assert A.shape == B.shape
    m = A.shape[1]
    centroid_A = np.mean(A, axis=0)
    centroid_B = np.mean(B, axis=0)
    AA = A - centroid_A
    BB = B - centroid_B
    H = np.dot(AA.T, BB)
    U, S, Vt = np.linalg.svd(H)
    R = np.dot(Vt.T, U.T)
    if np.linalg.det(R) < 0:
        Vt[m - 1, :] *= -1
        R = np.dot(Vt.T, U.T)
    t = centroid_B.T - np.dot(R, centroid_A.T)
    T = np.identity(m + 1)
    T[:m, :m] = R
    T[:m, m] = t
    return T


def icp(A, B):
    assert A.shape == B.shape
    m = A.shape[1]
    src = np.ones((m+1,A.shape[0]))
    dst = np.ones((m+1,B.shape[0]))
    src[:m,:] = np.copy(A.T)
    dst[:m,:] = np.copy(B.T)
    T = best_fit_transform(src[:m,:].T, dst[:m,:].T)
    src = np.dot(T, src)
    T = best_fit_transform(A, src[:m,:].T)
    return T
