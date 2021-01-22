import numpy as np
import os
import cv2
import yaml
from TDDFA_ONNX import TDDFA_ONNX
from sklearn.neighbors import NearestNeighbors
from utils.functions import draw_landmarks


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
    bbox = [0,0,im.shape[0],im.shape[1]]
    param_lst, roi_box_lst = tddfa(im, [bbox])
    preds = tddfa.recon_vers(param_lst, roi_box_lst, dense_flag=False)
    preds = preds[0].T
    return preds


def normalize(points):
    return (points - np.mean(points, axis=0)) / points.max(), np.mean(points, axis=0), points.max()


def revert_norm(points, mean, max):
    return (points * max) + mean


def ldk_on_im(ldk, mean, max, trans, inv=False):
    tmp = np.asarray(ldk.T.tolist() + [list([1] * 68)])
    if inv:
        tmp = (tmp.T @ np.linalg.inv(trans)).T
    else:
        tmp = (tmp.T @ trans).T
    return revert_norm(tmp[:3].T, mean, max)


def open_files(folder):
    ims = []
    names = []
    for file in os.listdir(folder):
        ims.append(cv2.imread(os.path.join(folder, file)))
        names.append(file.split('.')[0])
    return ims, names


def process_2ims(im1, im2, name1, name2):
    folder = 'source/test_data/'
    ldk1, ldk2 = find_landmarks(im1), find_landmarks(im2)
    if not os.path.exists(folder + 'base/' + name1 + '.jpg'):
        draw_landmarks(im1, ldk1.T, show_flag=False, dense_flag=False, wfp=folder + 'base/' + name1 + '.jpg')
    if not os.path.exists(folder + 'base/' + name2 + '.jpg'):
        draw_landmarks(im2, ldk2.T, show_flag=False, dense_flag=False, wfp=folder + 'base/' + name2 + '.jpg')
    ldk1, mean1, max1 = normalize(ldk1)
    ldk2, mean2, max2 = normalize(ldk2)
    T, dist, _ = icp(ldk1, ldk2)
    if not os.path.exists(folder + '/results' + name1 + 'over' + name2 + '.jpg'):
        ldk1_on_im2 = ldk_on_im(ldk1, mean2, max2, T, inv=True)
        draw_landmarks(im2, ldk1_on_im2.T, show_flag=False, dense_flag=False, wfp=folder + name1 + 'over' + name2 + '.jpg')
    if not os.path.exists(folder + '/results' + name2 + 'over' + name1 + '.jpg'):
        ldk2_on_im1 = ldk_on_im(ldk2, mean1, max1, T)
        draw_landmarks(im1, ldk2_on_im1.T, show_flag=False, dense_flag=False, wfp=folder + name2 + 'over' + name1 + '.jpg')
    return revert_norm(ldk1, mean1, max1), revert_norm(ldk2, mean2, max2), dist


def stack_all(im, id, ldks, name):
    file = 'source/test_data/concat/concat_on_' + name + '.jpg'
    if not os.path.exists(file):
        to_cast = []
        to_draw = [ldks[id].T]
        for i in ldks:
            to_cast.append(normalize(i))
        dst = to_cast.pop(id)
        for src in to_cast:
            T, _, _ = icp(dst[0], src[0])
            ldk_proj = ldk_on_im(src[0], dst[1], dst[2], T)
            to_draw.append(ldk_proj.T)
        draw_landmarks(im, to_draw, show_flag=False, dense_flag=False, wfp=file)


def draw_mean(im, id, ldks, name):
    file = 'source/test_data/mean/mean_on_' + name + '.jpg'
    if not os.path.exists(file):
        to_cast = []
        to_draw = [ldks[id].T]
        for i in ldks:
            to_cast.append(normalize(i))
        dst = to_cast.pop(id)
        for src in to_cast:
            T, _, _ = icp(dst[0], src[0])
            ldk_proj = ldk_on_im(src[0], dst[1], dst[2], T)
            to_draw.append(ldk_proj.T)
        mean = np.mean(np.array(to_draw), axis=0)
        draw_landmarks(im, mean, show_flag=False, dense_flag=False, wfp=file)


def draw_median(im, id, ldks, name):
    file = 'source/test_data/median/median_on_' + name + '.jpg'
    if not os.path.exists(file):
        to_cast = []
        to_draw = [ldks[id].T]
        for i in ldks:
            to_cast.append(normalize(i))
        dst = to_cast.pop(id)
        for src in to_cast:
            T, _, _ = icp(dst[0], src[0])
            ldk_proj = ldk_on_im(src[0], dst[1], dst[2], T)
            to_draw.append(ldk_proj.T)
        median = np.median(np.array(to_draw), axis=0)
        draw_landmarks(im, median, show_flag=False, dense_flag=False, wfp=file)


def main():
    ims, names = open_files('source/test_data/ims/')
    bad_ones = ['43094', '49856', '49857', '49860', '49869', '49873']
    ldks = []
    for id1, im1 in enumerate(ims):
        if not (names[id1] in bad_ones):
            for id2, im2 in enumerate(ims):
                if not (names[id2] in bad_ones):
                    if id2 > id1:
                        ldk1, ldk2, errors = process_2ims(im1, im2, names[id1], names[id2])
                        if id1 >= len(ldks):
                            ldks.append(ldk1)
                        if id2 >= len(ldks):
                            ldks.append(ldk2)
    for id1, im1 in enumerate(ims):
        if not (names[id1] in bad_ones):
            stack_all(im1, id1, ldks, names[id1])
            draw_mean(im1, id1, ldks, names[id1])
            draw_median(im1, id1, ldks, names[id1])


if __name__ == '__main__':
    os.mkdir('source/test_data/concat')
    os.mkdir('source/test_data/base')
    os.mkdir('source/test_data/mean')
    os.mkdir('source/test_data/median')
    os.mkdir('source/test_data/results')
    main()
