import numpy as np

def test_logic():
    min_dist = 0.51
    match_threshold = 0.55
    confidence = round((1.0 - min_dist) * 100.0, 2)
    print(f'min_dist: {min_dist}, match_threshold: {match_threshold}, confidence: {confidence}')
    if min_dist <= match_threshold:
        print('MATCH')
    else:
        print('NO MATCH')

    min_dist_fail = 0.60
    confidence_fail = round((1.0 - min_dist_fail) * 100.0, 2)
    print(f'fail min_dist: {min_dist_fail}, confidence: {confidence_fail}')
test_logic()
