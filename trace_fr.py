import sys, cv2, numpy as np
sys.path.insert(0, 'backend')
from utils.image_utils import bgr_to_rgb, resize_for_recognition, normalize_lighting
from services.face_service import FaceService
from utils.embedding_cache import EmbeddingCache
import face_recognition
from PIL import Image as PILImage

img_bgr = cv2.imread('debug_capture.jpg')
resized = resize_for_recognition(img_bgr, 640)
img_rgb = bgr_to_rgb(resized)
print('Image:', img_rgb.shape, img_rgb.dtype)

# Simulate _to_dlib_compat (PIL round-trip)
norm_bgr = normalize_lighting(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
norm_rgb_raw = cv2.cvtColor(norm_bgr, cv2.COLOR_BGR2RGB)
pil_img = PILImage.fromarray(np.clip(norm_rgb_raw, 0, 255).astype(np.uint8))
norm_rgb = np.array(pil_img)
print('norm_rgb:', norm_rgb.shape, norm_rgb.dtype, 'C_CONT:', norm_rgb.flags['C_CONTIGUOUS'])

# face_locations
try:
    locs0 = face_recognition.face_locations(norm_rgb, model='hog', number_of_times_to_upsample=0)
    locs1 = face_recognition.face_locations(norm_rgb, model='hog', number_of_times_to_upsample=1)
    print('face_locations upsample=0:', locs0)
    print('face_locations upsample=1:', locs1)
    locs = locs0 or locs1
except Exception as e:
    print('face_locations FAIL:', e)
    locs = []

if locs:
    loc = tuple(int(x) for x in locs[0])
    print('Using loc:', loc)
    try:
        encs = face_recognition.face_encodings(norm_rgb, known_face_locations=[loc], num_jitters=1, model='small')
        print('face_encodings count:', len(encs))
        if encs:
            print('Encoding norm:', round(float(np.linalg.norm(encs[0])), 4))
            print('SUCCESS - real dlib encoding generated!')
    except Exception as e:
        print('face_encodings FAIL:', e)
else:
    print('No faces found by face_recognition')

# Try register_face
print('\n--- register_face full test ---')
svc = FaceService(cache=EmbeddingCache(redis_url=''))
emb, msg = svc.register_face(img_rgb)
print('emb:', emb is not None, 'msg:', msg)
if emb is not None:
    print('NORM:', round(float(np.linalg.norm(emb)), 4), '| is_dlib:', svc._is_dlib_encoding(emb))
