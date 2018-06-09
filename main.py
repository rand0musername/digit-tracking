import cv2
import numpy as np
import math
from skimage.color import grey2rgb
from skimage import img_as_ubyte, img_as_float

from paper_finder import PaperFinder
from digit_extraction import DigitExtractor
from digit_classifier import DigitClassifier
from utils import transform_img

# Capture
cap = cv2.VideoCapture(0)

skip = 10
nb_frame = 0
patience = 0

mnist_img_width = 28
mnist_img_height = 28

# Objects
paper_finder = PaperFinder(target_patience = 5)
paper = None
clf = DigitClassifier(mnist_img_height, mnist_img_width)
ext = DigitExtractor()

def draw_candidate(target, rect, image, confs, M = None, TL = None, reason = None):
    font = cv2.FONT_HERSHEY_SIMPLEX

    # center and box are used later for positioning
    rect = rect[0]
    center = rect[0]
    #print(rect)
    box = cv2.boxPoints(rect)

    # transform?
    if TL is not None:
        center = (center[0] + TL[0], center[1] + TL[1])
    if M is not None:
        center_r = np.asarray(center).reshape(1, 1, 2)
        center_t = cv2.perspectiveTransform(center_r, M)
        center = (center_t[0][0][0], center_t[0][0][1])
    if TL is not None:
        box[:, 0] += TL[0]
        box[:, 1] += TL[1]
    if M is not None:
        box_r = box.reshape(4, 1, 2)
        box_t = cv2.perspectiveTransform(box_r, M)
        box = box_t.reshape(4, 2)

    # we need ints
    center = np.int0(center)
    box = np.int0(box)

    # done, draw

    cv2.drawContours(target,[box],0,(0,0,1),2)

    x_off = int(center[0] - image.shape[1] / 2)
    y_off = int(center[1] - image.shape[0] / 2)
    try:
        target[y_off:y_off+image.shape[0], x_off:x_off+image.shape[1]] = grey2rgb(image)
    except ValueError:
        pass

    max_j = max(range(10), key=lambda j: confs[j])
    max_c = confs[max_j]

    cv2.putText(target,str(max_j),(int(center[0]) - 5, int(center[1]) - 20), font, 0.6,(1,0,0),2,cv2.LINE_AA)
    #cv2.putText(target,reason,(int(center[0]) - 5, int(center[1]) + 20), font, 0.6,(1,0,0),2,cv2.LINE_AA)

while True:
    # Capture frame-by-frame
    nb_frame += 1
    # print("frame {}".format(nb_frame))
    ret, frame = cap.read()
    print(frame.shape)
    if frame.shape != (480, 640):
        frame = cv2.resize(frame, (640, 480))

    k = chr(cv2.waitKey(1) & 0xFF)
    #if k == 'l':
    #    ext._k += 0.02
    #    print('k=',ext._k)
    #elif k == 'k':
    #    ext._k -= 0.02
    #    print('k=',ext._k)
    #elif k == 'p':
    #    ext._ws += 2
    #    print('ws=',ext._ws)
    #elif k == 'o':
    #    ext._ws -= 2
    #    print('ws=',ext._ws)

    # Skip?
    if skip > 0:
        skip -= 1
        cv2.imshow("frame", frame)
        if paper is not None:
            cv2.imshow("paper", paper)
        continue

    # Frame info
    (height, width) = frame.shape[:2]
    frame_clean = frame.copy()

    # Find paper
    status, info = paper_finder.find(frame)
    if not status:
       # print("not find")
        cv2.imshow("frame", frame)
        continue

    # Found paper, show
    paper, h_inv, TL = info
    cv2.imshow("frame", frame)

    """
    paper_uncrop = np.pad(paper,
                          ((TL[1], TL[1]),
                           (TL[0], TL[0]),
                           (0,0)),
                          'constant',
                          constant_values = ((128,)))
    cv2.imshow("paper_uncrop", paper_uncrop)
    """

    # Extract digits
    candidates = ext.extract_digits(paper)
    if not candidates:
        continue
    transformed = [transform_img(c.image, mnist_img_height, mnist_img_width) for c in candidates]
    all_imgs = np.array(transformed)

    # Get confidences from the model
    confidences = clf.predict(all_imgs)

    # Draw candidates
    paper_result = img_as_float(paper)
    for i, cand in enumerate(candidates):
        rect = cand.rect
        image = cand.image
        draw_candidate(paper_result, cand.rect, transformed[i], confidences[i])
    cv2.imshow('paper_result', paper_result)

    # Transform back and draw on original frame
    frame_result = img_as_float(frame_clean.copy())
    for i, cand in enumerate(candidates):
        rect = cand.rect
        image = cand.image
        reason = cand.reason
        draw_candidate(frame_result, cand.rect, transformed[i], confidences[i], h_inv, TL, reason)
    cv2.imshow('frame_result', frame_result)

    # First time you find a paper target patience is one
    # TODO: we should actually 'break' here and start doing
    # incremental bullshit
    paper_finder.target_patience = 1
    continue

    # Block
    break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
