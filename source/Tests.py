import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import open3d as o3d
from FaceBoxes.FaceBoxes_ONNX import FaceBoxes_ONNX
import numpy as np
import copy
import os
import cv2
import yaml
from TDDFA_ONNX import TDDFA_ONNX
from sklearn.neighbors import NearestNeighbors


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
       Vt[m-1,:] *= -1
       R = np.dot(Vt.T, U.T)
    t = centroid_B.T - np.dot(R,centroid_A.T)
    T = np.identity(m+1)
    T[:m, :m] = R
    T[:m, m] = t
    return T, R, t


def nearest_neighbor(src, dst):
    assert src.shape == dst.shape
    neigh = NearestNeighbors(n_neighbors=1)
    neigh.fit(dst)
    distances, indices = neigh.kneighbors(src, return_distance=True)
    return distances.ravel(), indices.ravel()


def icp(A, B, init_pose=None, max_iterations=20, tolerance=0.001):
    assert A.shape == B.shape
    m = A.shape[1]
    src = np.ones((m+1,A.shape[0]))
    dst = np.ones((m+1,B.shape[0]))
    src[:m,:] = np.copy(A.T)
    dst[:m,:] = np.copy(B.T)
    if init_pose is not None:
        src = np.dot(init_pose, src)
    prev_error = 0
    for i in range(max_iterations):
        distances, indices = nearest_neighbor(src[:m,:].T, dst[:m,:].T)
        T,_,_ = best_fit_transform(src[:m,:].T, dst[:m,:].T)
        src = np.dot(T, src)
        mean_error = np.mean(distances)
        if np.abs(prev_error - mean_error) < tolerance:
            break
        prev_error = mean_error
    T,_,_ = best_fit_transform(A, src[:m,:].T)
    return T, distances, i


def find_landmarks(im):
    cfg = yaml.load(open('source/configs/mb1_120x120.yml'), Loader=yaml.SafeLoader)
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    os.environ['OMP_NUM_THREADS'] = '4'
    tddfa = TDDFA_ONNX(**cfg)
    face_boxes = FaceBoxes_ONNX()
    boxes = face_boxes(im)
    print(boxes)
    param_lst, roi_box_lst = tddfa(im, boxes)
    preds = tddfa.recon_vers(param_lst, roi_box_lst, dense_flag=False)
    return preds[0][:2].T


def normalize(points):
    return (points - np.mean(points, axis=0)) / points.max, np.mean(points, axis=0), points.max


def revert_norm(points, mean, max):
    return (points * max) + mean


def open_files(folder):
    ims = []
    for file in os.walk(folder):
        ims.append(cv2.imread(file))
    return ims


def main():
    ims = open_files('test_data/')
    ldks, means, maxs = [], [], []

    for im in ims:
        ldk = find_landmarks(im)
        ldk, mean, max = normalize(ldk)
        ldks.append(ldk), means.append(mean), maxs.append(max)
    ldks_tmp = copy.deepcopy(ldks)
    for i in len(ldks):
        ldk_src = ldks_tmp.pop(0)
        for ldk_cmp in ldks_tmp:
            T, dist, i = icp(ldk_src, ldk_cmp)
            tmp = np.asarray(ldk_cmp.tolist() + [list([1] * 68)])
            new_ldk_cmp = (tmp.T @ T).T
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            ax.scatter(ldk_src[0], ldk_src[1], ldk_src[2], c='r', marker='x')
            ax.scatter(new_ldk_cmp[0], new_ldk_cmp[1], new_ldk_cmp[2], c='b', marker='x')
            plt.show()




if __name__ == '__main__':
    main()
