# -*- coding: utf-8 -*-
"""copy of Plant_Diease_Inception.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/19KZXkejTVUmucB5sjgrHptpYk5hDsTxC
"""

!pip install -q kaggle

import os
os.environ['KAGGLE_CONFIG_DIR']="/content"

!kaggle datasets download -d vipoooool/new-plant-diseases-dataset

import zipfile
zip_ref = zipfile.ZipFile('/content/new-plant-diseases-dataset.zip', 'r')
zip_ref.extractall('/content')
zip_ref.close()

import matplotlib.pyplot as plt
import cv2
import pandas as pd
import numpy as np
import tensorflow as tf
import seaborn as sns
import skimage
import shutil
from tensorflow.keras.preprocessing.image import ImageDataGenerator

import warnings
warnings.filterwarnings('ignore')

# The path of the dataset
train_data_path = '/content/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/train'
valid_data_path = '/content/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/valid'

categories = os.listdir(train_data_path)
print(f'The Number Of categories are : {len(categories)} Category')

cat_freq = {}
for cat in categories:
    cat_freq[cat] = len(os.listdir(train_data_path + "/" + cat))

cat_freq_df = pd.DataFrame.from_dict(cat_freq, orient='index', columns=['Frequencies'])

cat_freq_df.reset_index(inplace=True)
cat_freq_df.columns = ['Categories', 'Frequencies']
cat_freq_df

cat_freq_df.describe()

plt.figure(figsize=(15, 10))
plt.bar(cat_freq_df['Categories'], cat_freq_df['Frequencies'])
plt.xlabel('Categories')
plt.ylabel('Frequencies')
plt.title('Frequency of Items')
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()

fruits_veg = []
for cat in categories:
    fruits_veg.append(cat.split('___')[0])
unique_fruites_veg = list(np.unique(fruits_veg))

print(f'The represents {len(unique_fruites_veg)} Different types of Fruits and Vegetables as follows : ')
unique_fruites_veg

veg_fruite_cat = {}
for i in unique_fruites_veg:
    num = 0
    for j in categories:
        if i in j:
            num +=1
    veg_fruite_cat[i] = num
veg_fruite_cat

# Define paths for the sampled dataset
sampled_train_dir = 'Dataset\\Sampled\\train\\'
sampled_valid_dir = 'Dataset\\Sampled\\valid\\'

# Create directories if they don't exist
os.makedirs(sampled_train_dir, exist_ok=True)
os.makedirs(sampled_valid_dir, exist_ok=True)

def sample_dataset(data_dir, output_dir, sample_size=0.1):
    """
    Sample a subset of the dataset.

    Parameters:
    - data_dir: The directory containing the original dataset.
    - output_dir: The directory where the sampled dataset will be stored.
    - sample_size: The fraction of the dataset to sample.
    """
    categories = os.listdir(data_dir)

    for category in categories:
        # Create category directory in the sampled output directory
        os.makedirs(os.path.join(output_dir, category), exist_ok=True)

        # Get all images in the current category
        images = os.listdir(os.path.join(data_dir, category))

        # Sample a fraction of the images
        sampled_images = np.random.choice(images, int(len(images) * sample_size), replace=False)

        # Copy the sampled images to the output directory
        for image in sampled_images:
            src = os.path.join(data_dir, category, image)
            dst = os.path.join(output_dir, category, image)
            shutil.copy(src, dst)

# Sample 10-20% of the dataset
sample_percentage = 1.0 # Adjust between 0.1 and 0.2 for 10-20%
sample_dataset(train_data_path, sampled_train_dir, sample_percentage)
sample_dataset(valid_data_path, sampled_valid_dir, sample_percentage)

# Set up ImageDataGenerator
train_datagen = ImageDataGenerator(rescale=1./255)
validation_datagen = ImageDataGenerator(rescale=1./255)

# Create training data generator
train_generator = train_datagen.flow_from_directory(
    train_data_path,
    target_size=(256, 256),  # Resize images to match model input
    batch_size=32,
    class_mode='categorical',
    shuffle=True
)

# Create validation data generator
validation_generator = validation_datagen.flow_from_directory(
    valid_data_path,
    target_size=(256, 256),  # Resize images to match model input
    batch_size=32,
    class_mode='categorical',
    shuffle=False
)

import tensorflow as tf
from tensorflow.keras.applications import InceptionV3
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Load the DenseNet121 model with pre-trained weights from ImageNet, excluding the top layers
base_model = InceptionV3(weights='imagenet', include_top=False, input_shape=(256, 256, 3))

# Add new layers on top of the base model for our specific classification task
x = base_model.output
x = GlobalAveragePooling2D()(x)  # Global average pooling to reduce dimensions

x = Dense(1024, activation='relu')(x)  # Dense layer with 1024 units and ReLU activation

# Output layer - adjust the number of classes according to the dataset (e.g., train_generator.num_classes)
predictions = Dense(train_generator.num_classes, activation='softmax')(x)

# Create the final model
model = Model(inputs=base_model.input, outputs=predictions)

# Freeze the base model layers for transfer learning
for layer in base_model.layers:
    layer.trainable = False

# Compile the model
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy', tf.keras.metrics.Precision(name='precision'), tf.keras.metrics.Recall(name='recall')]
)
model.summary()

# Define callbacks
checkpoint_path = "best_InceptionV3_model.h5"  # Path where the best model will be saved

checkpoint = ModelCheckpoint(
    checkpoint_path, monitor='val_accuracy', save_best_only=True, mode='max', verbose=1
)
early_stopping = EarlyStopping(
    monitor='val_accuracy', patience=3, mode='max', verbose=1, restore_best_weights=True
)
reduce_lr = ReduceLROnPlateau(
    monitor='val_loss', factor=0.2, patience=2, verbose=1, min_lr=0.0001
)

# Train the model
history = model.fit(
    train_generator,  # Your training data generator
    epochs=10,  # Adjust the number of epochs as needed
    validation_data=validation_generator,  # Your validation data generator
    callbacks=[checkpoint, early_stopping, reduce_lr]  # Add the callbacks here
)

#Load the best model saved during training
best_model = tf.keras.models.load_model('best_model.h5')

#Evaluate the model on validation data
loss, accuracy, precision, recall = best_model.evaluate(validation_generator)
print(f'Validation Loss: {loss}')
print(f'Validation Accuracy: {accuracy}')
print(f'Validation Precision: {precision}')
print(f'Validation Recall: {recall}')

#Plotting the accuracy
plt.figure(figsize=(10, 6))
plt.plot(history.history['accuracy'], label='Training Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('InceptionV3 Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()



#Plotting the loss
plt.figure(figsize=(10, 6))
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('InceptionV3 Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend(loc='upper right')
plt.grid(True)
plt.show()

from sklearn.metrics import confusion_matrix

Y_pred = best_model.predict(validation_generator)
y_pred = np.argmax(Y_pred, axis=1)
y_true = validation_generator.classes

cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(12, 10))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix for InceptionV3')
plt.xlabel('Predicted')
plt.ylabel('True')
plt.show()

from sklearn.metrics import f1_score, roc_curve, auc, r2_score
import numpy as np
import matplotlib.pyplot as plt

validation_generator.reset()

y_pred = best_model.predict(validation_generator, verbose=1)
y_pred_class = np.argmax(y_pred, axis=1)

y_true = validation_generator.classes
class_indices = validation_generator.class_indices

inverse_class_indices = {v: k for k, v in class_indices.items()}

f1 = f1_score(y_true, y_pred_class, average='macro')
print(f"Macro F1 Score: {f1}")

# R2 Score
y_true_one_hot = tf.keras.utils.to_categorical(y_true, num_classes=len(validation_generator.class_indices))
r2 = r2_score(y_true_one_hot, Y_pred)
print(f"R2 Score: {r2}")





from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import label_binarize
import numpy as np
import matplotlib.pyplot as plt
from itertools import cycle
import matplotlib.cm as cm

# Binarize the output labels for ROC curve calculation
y_true_bin = label_binarize(y_true, classes=list(range(len(class_indices))))
n_classes = y_true_bin.shape[1]

# Calculate ROC curve and ROC area for each class
fpr = dict()
tpr = dict()
roc_auc = dict()

for i in range(n_classes):
    fpr[i], tpr[i], _ = roc_curve(y_true_bin[:, i], y_pred[:, i])
    roc_auc[i] = auc(fpr[i], tpr[i])

# Compute micro-average ROC curve and ROC area
fpr["micro"], tpr["micro"], _ = roc_curve(y_true_bin.ravel(), y_pred.ravel())
roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

# Generate a colormap with 8 different colors
colors = cm.get_cmap('tab20', n_classes)
3
# Plotting all ROC curves
plt.figure(figsize=(12, 8))

for i in range(n_classes):
    plt.plot(fpr[i], tpr[i], color=colors(i), lw=2,
             label='Class {0} (area = {1:0.2f})'.format(inverse_class_indices[i], roc_auc[i]))

plt.plot([0, 1], [0, 1], 'k--', lw=2)
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC of InceptionV3')
plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize='small')  # Adjusted font size and position
plt.show()

# ROC Curve
# Binarize the output labels for ROC curve calculation
class_indices = validation_generator.class_indices
inverse_class_indices = {v: k for k, v in class_indices.items()}
y_true_bin = label_binarize(y_true, classes=list(range(len(class_indices))))
n_classes = y_true_bin.shape[1]

# Calculate ROC curve and ROC area for each class
fpr = dict()
tpr = dict()
roc_auc = dict()

for i in range(n_classes):
    fpr[i], tpr[i], _ = roc_curve(y_true_bin[:, i], Y_pred[:, i])
    roc_auc[i] = auc(fpr[i], tpr[i])

# Compute micro-average ROC curve and ROC area
fpr["micro"], tpr["micro"], _ = roc_curve(y_true_bin.ravel(), Y_pred.ravel())
roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

# Generate a colormap with n different colors
colors = cm.get_cmap('tab20', n_classes)

# Plotting all ROC curves
plt.figure(figsize=(12, 8))

for i in range(n_classes):
    plt.plot(fpr[i], tpr[i], color=colors(i), lw=2,
             label='Class {0} (area = {1:0.2f})'.format(inverse_class_indices[i], roc_auc[i]))

plt.plot([0, 1], [0, 1], 'k--', lw=2)
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC of DenseNet')
plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize='small')  # Adjusted font size and position
plt.show()

# Create a proper inverse mapping of class indices to labels

inverse_class_indices = {v: k for k, v in class_indices.items()}  # Make sure class_indices maps string to index

def predict_image(model, image_path, class_indices):
    # Load the image
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (256, 256))
    img = img / 255.0

    # Expand dimensions to match input shape
    img = np.expand_dims(img, axis=0)

    # Make prediction
    predictions = model.predict(img)

    # Find the predicted class index
    predicted_class_index = np.argmax(predictions, axis=1)[0]
    print(f'Predicted Class Index: {predicted_class_index}')
    print(f'Available Indices in inverse_class_indices: {list(inverse_class_indices.keys())}')

    # Ensure that the predicted class index exists in class_indices
    if predicted_class_index in inverse_class_indices:
        predicted_class_label = inverse_class_indices[predicted_class_index]
        confidence_score = predictions[0][predicted_class_index]
        return predicted_class_label, confidence_score
    else:
        raise ValueError(f'Predicted index {predicted_class_index} not found in inverse_class_indices.')

# Use the prediction function again
image_path = '/content/test/test/AppleScab1.JPG' # Replace with your image path
predicted_label, confidence = predict_image(best_model, image_path, inverse_class_indices)

# Print the result
print(f'Predicted Label: {predicted_label}')
print(f'Confidence Score: {confidence:.4f}')

