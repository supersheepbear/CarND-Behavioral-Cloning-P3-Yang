import cv2
import pandas as pd
import numpy as np
import scipy.misc
from imgaug import augmenters as iaa
from sklearn.utils import shuffle


class ProcessData:

    def __init__(self):
        self.data_length = 0
        self.driving_log = pd.DataFrame()
        self.train_log = pd.DataFrame()
        self.valid_log = pd.DataFrame()
        self.test_log = pd.DataFrame()
        self.train_generator = 0
        self.validation_generator = 0
        self.batch_size = 64

    def image_generator(self, log, is_train):
        batch_size = self.batch_size
        num_samples = log.shape[0]
        while 1:  # Loop forever so the generator never terminates
            shuffle(log)
            for offset in range(0, num_samples, batch_size):
                batch_samples = log.iloc[offset:offset + batch_size, :]
                images = []
                angles = []
                for index, row in batch_samples.iterrows():
                    # Only use center images in validation data
                    if is_train == 1:
                        position = np.random.randint(0, 3)
                    else:
                        position = 0
                    # Randomly pick one of the image from left/mid/right camera for training
                    image_path = row[position]
                    if position == 0:
                        current_angle = float(row[3])
                    if position == 1:
                        current_angle = float(row[3]) + 0.25
                    if position == 2:
                        current_angle = float(row[3]) - 0.25
                    image = cv2.imread(image_path)
                    # Apply pre processing
                    image, current_angle = self.image_process(image, current_angle)
                    images.append(image)
                    angles.append(current_angle)

                # trim image to only see section with road
                x_data = np.array(images)
                y_data = np.array(angles)
                yield shuffle(x_data, y_data)

    def create_generator(self):
        self.train_generator = self.image_generator(self.train_log, is_train=1)
        self.validation_generator = self.image_generator(self.valid_log, is_train=0)

    def split_data(self):
        split_index_1 = int(self.data_length * 0.75)
        split_index_1 = split_index_1 - split_index_1 % 64
        split_index_2 = int(self.data_length * 0.95)
        split_index_2 = split_index_2 - (split_index_2 - split_index_1) % 64
        self.train_log = self.driving_log.iloc[:split_index_1, :]
        self.valid_log = self.driving_log.iloc[split_index_1:split_index_2, :]
        self.test_log = self.driving_log.iloc[split_index_2:, :]

        print('train size:{}'.format(len(self.train_log)))
        print('valid size:{}'.format(len(self.valid_log)))
        print('test size:{}'.format(len(self.test_log)))

    @staticmethod
    def random_shear(image, steering_angle, shear_range=100):
        rows, cols, ch = image.shape
        dx = np.random.randint(-shear_range, shear_range + 1)
        random_point = [cols / 2 + dx, rows / 2]
        pts1 = np.float32([[0, rows], [cols, rows], [cols / 2, rows / 2]])
        pts2 = np.float32([[0, rows], [cols, rows], random_point])
        dsteering = dx / (rows / 2) * 360 / (2 * np.pi * 25.0) / 6.0
        m = cv2.getAffineTransform(pts1, pts2)
        image = cv2.warpAffine(image, m, (cols, rows), borderMode=1)
        steering_angle += dsteering

        return image, steering_angle

    def adjust_images(self, image, current_angle):
        sometimes = lambda aug: iaa.Sometimes(0.3, aug)
        seq = iaa.Sequential([iaa.Multiply((0.8, 1.2), per_channel=0.2),
                              iaa.ContrastNormalization((0.75, 1.5)),
                              sometimes(iaa.GaussianBlur(sigma=(0, 3.0)))],
                             random_order=True)
        image = seq.augment_image(image)
        image, current_angle = self.random_shear(image, current_angle)
        flip_flag = np.random.randint(0, 2)
        flip_seq = iaa.Sequential([iaa.Fliplr(1.0)])
        if flip_flag == 1:
            image = flip_seq.augment_image(image)
            current_angle = current_angle * -1

        return image, current_angle

    def image_process(self, img, current_angle):
        # crop image
        img = img[35:135, :, :]
        # apply image augmentation techniques
        img, current_angle = self.adjust_images(img, current_angle)
        # resize image
        img = scipy.misc.imresize(img, (66, 200, 3))
        # change image from BGR to YUV
        img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2YUV)
        return img, current_angle

    def read_csv_data(self):
        self.driving_log = pd.read_csv(r'my_data\pure_left\driving_log.csv', header=None)
        # shuffle driving_log
        self.driving_log = shuffle(self.driving_log)
        self.data_length = self.driving_log.shape[0]

        self.split_data()

    @staticmethod
    def read_data(log):
        center_image_names = log[0]
        angle = log[3]
        images = []
        for index, image_path in center_image_names.iteritems():
            image = cv2.imread(image_path)
            images.append(image)
        images = np.array(images)
        angle = np.array(angle)
        return images, angle
