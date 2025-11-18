import os
import torch
import cv2
import numpy as np
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1

# Initialize MTCNN and InceptionResnetV1 models
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(keep_all=True, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def get_face_embeddings(image_path):
    img = Image.open(image_path)
    faces = mtcnn(img)
    if faces is None:
        return None
    embeddings = []
    for face in faces:
        embedding = resnet(face.unsqueeze(0).to(device))
        embeddings.append(embedding.cpu().detach().numpy())
    return embeddings

def compare_embeddings(embedding1, embedding2):
    return np.linalg.norm(embedding1 - embedding2)

def recognize_faces_from_folder(folder_path):
    embeddings_dict = {}
    for person_folder in os.listdir(folder_path):
        person_path = os.path.join(folder_path, person_folder)
        if os.path.isdir(person_path):
            person_embeddings = []
            for image_name in os.listdir(person_path):
                image_path = os.path.join(person_path, image_name)
                embeddings = get_face_embeddings(image_path)
                if embeddings:
                    person_embeddings.extend(embeddings)
            if person_embeddings:
                embeddings_dict[person_folder] = np.mean(person_embeddings, axis=0)
    return embeddings_dict

def identify_face(test_image_path, embeddings_dict):
    test_embeddings = get_face_embeddings(test_image_path)
    if not test_embeddings:
        return None
    test_embedding = np.mean(test_embeddings, axis=0)
    min_distance = float('inf')
    identity = None
    for person, person_embedding in embeddings_dict.items():
        distance = compare_embeddings(test_embedding, person_embedding)
        if distance < min_distance:
            min_distance = distance
            identity = person
    return identity

# Example usage
folder_path = '/home/aloo/Desktop/SecureBellAI/backend/visitors/verified'
embeddings_dict = recognize_faces_from_folder(folder_path)
test_image_path = '/home/aloo/Desktop/SecureBellAI/backend/visitors/verified/ALankrit/2.jpg'
identity = identify_face(test_image_path, embeddings_dict)
print(f'Identified: {identity}')
