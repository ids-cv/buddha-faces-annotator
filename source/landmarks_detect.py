import os
import cv2
import yaml
import numpy as np
import mxnet as mx
from skimage import transform as trans
from TDDFA_ONNX import TDDFA_ONNX


def transform(data, center, output_size, scale, rotation):
    scale_ratio = scale
    rot = float(rotation) * np.pi / 180.0
    t1 = trans.SimilarityTransform(scale=scale_ratio)
    cx = center[0] * scale_ratio
    cy = center[1] * scale_ratio
    t2 = trans.SimilarityTransform(translation=(-1 * cx, -1 * cy))
    t3 = trans.SimilarityTransform(rotation=rot)
    t4 = trans.SimilarityTransform(translation=(output_size / 2, output_size / 2))
    t = t1 + t2 + t3 + t4
    M = t.params[0:2]
    cropped = cv2.warpAffine(data, M, (output_size, output_size), borderValue=0.0)
    return cropped, M


def trans_points2d(pts, M):
    new_pts = np.zeros(shape=pts.shape, dtype=np.float32)
    for i in range(pts.shape[0]):
        pt = pts[i]
        new_pt = np.array([pt[0], pt[1], 1.], dtype=np.float32)
        new_pt = np.dot(M, new_pt)
        new_pts[i] = new_pt[0:2]
    return new_pts


def trans_points3d(pts, M):
    scale = np.sqrt(M[0][0] * M[0][0] + M[0][1] * M[0][1])
    new_pts = np.zeros(shape=pts.shape, dtype=np.float32)
    for i in range(pts.shape[0]):
        pt = pts[i]
        new_pt = np.array([pt[0], pt[1], 1.], dtype=np.float32)
        new_pt = np.dot(M, new_pt)
        new_pts[i][0:2] = new_pt[0:2]
        new_pts[i][2] = pts[i][2] * scale
    return new_pts


def trans_points(pts, M):
    if pts.shape[1] == 2:
        return trans_points2d(pts, M)
    else:
        return trans_points3d(pts, M)


class Handler:
    def __init__(self, prefix, epoch, im_size=192):
        ctx = mx.cpu()
        image_size = (im_size, im_size)
        sym, arg_params, aux_params = mx.model.load_checkpoint(prefix, epoch)
        all_layers = sym.get_internals()
        sym = all_layers['fc1_output']
        self.image_size = image_size
        model = mx.mod.Module(symbol=sym, context=ctx, label_names=None)
        model.bind(for_training=False, data_shapes=[('data', (1, 3, image_size[0], image_size[1]))])
        model.set_params(arg_params, aux_params)
        self.model = model
        self.image_size = image_size

    def bbox_get(self, img, bbox):
        out = []
        input_blob = np.zeros((1, 3) + self.image_size, dtype=np.float32)
        w, h = (bbox[2] - bbox[0]), (bbox[3] - bbox[1])
        center = (bbox[2] + bbox[0]) / 2, (bbox[3] + bbox[1]) / 2
        rotate = 0
        _scale = self.image_size[0] * 2 / 3.0 / max(w, h)
        rimg, M = transform(img, center, self.image_size[0], _scale, rotate)
        rimg = cv2.cvtColor(rimg, cv2.COLOR_BGR2RGB)
        rimg = np.transpose(rimg, (2, 0, 1))  # 3*112*112, RGB
        input_blob[0] = rimg
        data = mx.nd.array(input_blob)
        db = mx.io.DataBatch(data=(data,))
        self.model.forward(db, is_train=False)
        pred = self.model.get_outputs()[-1].asnumpy()[0]
        if pred.shape[0] >= 3000:
            pred = pred.reshape((-1, 3))
        else:
            pred = pred.reshape((-1, 2))
        pred[:, 0:2] += 1
        pred[:, 0:2] *= (self.image_size[0] // 2)
        if pred.shape[1] == 3:
            pred[:, 2] *= (self.image_size[0] // 2)
        IM = cv2.invertAffineTransform(M)
        pred = trans_points(pred, IM)
        out.append(pred)
        return out


def detect_2D(im_path, bbox=None):
    # TODO change for 68 landmarks detection
    handler = Handler(os.path.join('source', '2d106det', '2d106det'), 0)
    im = cv2.imread(im_path)
    preds = handler.bbox_get(im, bbox)[0].tolist()
    if preds == []:
        return {}
    new_preds = {'jaw_line': [preds[1]] + preds[9:17] + preds[2:9] + [preds[0]] + preds[24:17:-1] + preds[32:24:-1] + [preds[17]],
                 'right_eye': [preds[34]] + [preds[33]] + [preds[37]] + [preds[39]] + [preds[42]] + [preds[40]] + [preds[41]] + [preds[35]] + [preds[36]] + [preds[38]],
                 'right_eyebrow': preds[43:46] + [preds[47]] + [preds[46]] + [preds[50]] + [preds[51]] + [preds[49]] + [preds[48]],
                 'mouth': [preds[52]] + preds[55:57] + [preds[53]] + [preds[59]] + [preds[58]] + [preds[61]] + [preds[68]] + [preds[67]] + preds[63:65] + [preds[66]] + [preds[62]] + [preds[70]] +[preds[69]] + [preds[57]] + [preds[60]] + [preds[54]] + [preds[65]],
                 'nose': preds[76:81] + preds[85:81:-1] + [preds[86]] + preds[74:72:-1] + [preds[81]] + [preds[72]] + [preds[75]],
                 'left_eye': [preds[88]] + [preds[87]] + [preds[90]] + [preds[89]] + [preds[95]] + [preds[94]] + [preds[96]] + [preds[93]] + [preds[91]] + [preds[92]],
                 'left_eyebrow': preds[101:96:-1] + preds[102:]
                 }
    return new_preds


def detect_3D(im_path, bbox=None):
    cfg = yaml.load(open('source/configs/mb1_120x120.yml'), Loader=yaml.SafeLoader)
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    os.environ['OMP_NUM_THREADS'] = '4'
    tddfa = TDDFA_ONNX(**cfg)

    img = cv2.imread(im_path)
    param_lst, roi_box_lst = tddfa(img, [bbox])
    preds = tddfa.recon_vers(param_lst, roi_box_lst, dense_flag=False)
    preds = preds[0][:2].T
    new_preds = {'jaw_line': preds[:17],
                 'right_eye': preds[36:42],
                 'right_eyebrow': preds[17:22],
                 'mouth': preds[49:],
                 'nose': preds[27:36],
                 'left_eye': preds[42:48],
                 'left_eyebrow': preds[22:27]
                 }
    # TODO calibrate with the previous 2D mask
    return new_preds
