import streamlit as st
from PIL import Image
import os

def resize_image(image, target_size_kb, increase_percentage):
    if increase_percentage > 0:
        new_width = int(image.width * (1 + increase_percentage / 100))
        new_height = int(image.height * (1 + increase_percentage / 100))
        resized_image = image.resize((new_width, new_height), Image.ANTIALIAS)
    else:
        quality = 85
        while True:
            resized_image = image.copy()
            resized_image.save("resized_image.jpg", optimize=True, quality=quality)
            resized_size_kb = os.path.getsize("resized_image.jpg") / 1024
            if resized_size_kb <= target_size_kb:
                break
            quality -= 5
            if quality < 5:
                return None, None
        resized_image = Image.open("resized_image.jpg")

    return resized_image

def save_resized_image(resized_image, filename):
    resized_image.save(filename)

# Interface Streamlit
st.title("Redimensionnement et Enregistrement d'image")
st.write("Chargez une image, spécifiez la taille souhaitée, le pourcentage d'augmentation / compression, le nom de fichier, puis affichez et enregistrez le résultat.")

# Upload de l'image
uploaded_image = st.file_uploader("Chargez une image", type=["jpg", "jpeg", "png"])

if uploaded_image is not None:
    # Charger l'image
    image = Image.open(uploaded_image)

    # Afficher l'image chargée
    st.image(image, caption="Image chargée", use_column_width=True)

    # Spécifier la taille désirée, le pourcentage d'augmentation / compression et le nom de fichier
    target_size_kb = st.number_input("Taille désirée de l'image (en Ko)", min_value=0, step=1, value=0)
    increase_percentage = st.slider("Pourcentage d'augmentation / compression", min_value=-50, max_value=50, value=0)
    filename = st.text_input("Nom de fichier de l'image redimensionnée", value="resized_image.jpg")

    # Redimensionner l'image
    resized_image = resize_image(image, target_size_kb, increase_percentage)

    if resized_image is not None:
        # Afficher l'image redimensionnée
        st.image(resized_image, caption="Image redimensionnée", use_column_width=True)

        # Enregistrer l'image redimensionnée
        save_button = st.button("Enregistrer l'image redimensionnée")
        if save_button:
            save_resized_image(resized_image, filename)
            st.success(f"L'image redimensionnée a été enregistrée sous '{filename}'.")

        # Afficher les détails de l'image
        with st.expander("Détails de l'image"):
            st.write(f"Taille de l'image chargée: {image.size[0]}x{image.size[1]}")
            st.write(f"Taille de l'image redimensionnée: {resized_image.size[0]}x{resized_image.size[1]}")
