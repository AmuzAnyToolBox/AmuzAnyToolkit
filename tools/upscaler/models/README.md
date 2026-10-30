# FSRCNN models

Original pretrained TensorFlow models by Saafke: https://github.com/Saafke/FSRCNN_Tensorflow/tree/master/models

Included without modifications under the upstream Apache-2.0 license (see `LICENSE`).

| File | SHA-256 |
| --- | --- |
| FSRCNN_x2.pb | 366b33f0084c7b3f2bf6724f0a2c77bca94fcec9d7b6d72389d330073b380d5c |
| FSRCNN_x4.pb | 5c68d18db561aed8ead4ffedf1b897ea615baaf60ebf6c35f8e641f8fa4a21bf |

Original authors retain copyright; see the upstream repository and included license. The models are loaded with OpenCV dnn_superres and require no download at runtime. Training code is not included. The app runs CPU inference over overlapping image tiles and preserves alpha separately.
