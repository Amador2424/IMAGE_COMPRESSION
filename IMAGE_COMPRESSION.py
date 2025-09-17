import streamlit as st
from PIL import Image, ImageOps
from io import BytesIO
import math

# --- Utils ---
def _pil_resample():
    # ANTIALIAS est déprécié → utiliser LANCZOS
    try:
        return Image.Resampling.LANCZOS  # Pillow ≥ 9.1
    except AttributeError:
        return Image.LANCZOS

def _img_to_bytes(img: Image.Image, fmt: str, quality: int = 85, optimize: bool = True) -> bytes:
    """Encode un PIL.Image en mémoire selon le format demandé."""
    buf = BytesIO()
    save_kwargs = {}
    fmt_upper = fmt.upper()

    if fmt_upper in ("JPG", "JPEG"):
        # S'assurer qu'on est en RGB pour JPEG (pas d'alpha)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        save_kwargs.update(dict(quality=quality, optimize=optimize))
        fmt_upper = "JPEG"  # normaliser
    elif fmt_upper == "PNG":
        # PNG : optimize=True et compression level par défaut
        save_kwargs.update(dict(optimize=optimize))

    img.save(buf, format=fmt_upper, **save_kwargs)
    return buf.getvalue()

def _binary_search_quality(img: Image.Image, fmt: str, target_kb: int, q_low: int = 5, q_high: int = 95) -> bytes:
    """
    Trouve une qualité JPEG qui rencontre le poids cible (approx).
    Pour PNG, on encode une fois (optimize=True) car la qualité n'existe pas.
    """
    if fmt.upper() in ("PNG",):
        data = _img_to_bytes(img, "PNG", optimize=True)
        return data

    best = _img_to_bytes(img, "JPEG", quality=q_high)
    if len(best) / 1024 <= target_kb:
        return best

    res = None
    low, high = q_low, q_high
    while low <= high:
        mid = (low + high) // 2
        data = _img_to_bytes(img, "JPEG", quality=mid)
        size_kb = len(data) / 1024
        if size_kb <= target_kb:
            res = data
            low = mid + 1  # essayer une qualité un peu plus haute
        else:
            high = mid - 1
    return res if res is not None else best  # si impossible, renvoyer la plus forte qualité testée

def resize_image(image: Image.Image, target_size_kb: int, percent_change: int) -> Image.Image:
    """
    - Si percent_change != 0 : on ajuste la résolution (upscale/downscale) en gardant l'aspect.
    - Si target_size_kb > 0 : on compresse l'encodage (JPEG → qualité binaire; PNG → optimize).
    Retourne un nouvel objet PIL.Image (l'affichage Streamlit utilisera cet objet).
    Le poids cible sera appliqué à l’export (download/sauvegarde) via l’encodeur, pas sur l’objet PIL.
    """
    resample = _pil_resample()
    out = image

    # 1) Redimensionnement par pourcentage (positif = agrandir, négatif = réduire)
    if percent_change != 0:
        factor = 1.0 + (percent_change / 100.0)
        # éviter les dimensions nulles
        new_w = max(1, int(round(image.width * factor)))
        new_h = max(1, int(round(image.height * factor)))
        out = image.resize((new_w, new_h), resample)

    # 2) La compression à un poids cible se fera à l'export (download/sauvegarde).
    # Ici, on retourne juste l'image PIL redimensionnée pour l'aperçu.
    return out

def export_image(img: Image.Image, filename: str, target_size_kb: int) -> bytes:
    """
    Encode l'image en bytes selon l'extension du filename.
    - Si target_size_kb > 0 et format JPEG → recherche de qualité.
    - Si PNG → optimize=True.
    """
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    if ext in ("jpg", "jpeg"):
        if target_size_kb and target_size_kb > 0:
            return _binary_search_quality(img, "JPEG", target_size_kb)
        return _img_to_bytes(img, "JPEG", quality=85)
    elif ext == "png":
        # Pas de contrôle fin de "qualité" en PNG, on optimise seulement
        return _img_to_bytes(img, "PNG", optimize=True)
    else:
        # Par défaut, on force JPEG
        if target_size_kb and target_size_kb > 0:
            return _binary_search_quality(img, "JPEG", target_size_kb)
        return _img_to_bytes(img, "JPEG", quality=85)

# --- UI Streamlit ---
st.title("Redimensionner & Compresser une image (PNG/JPEG)")
st.write("Charge une image, ajuste la taille (en %) et/ou un poids cible (Ko), puis télécharge.")

uploaded_image = st.file_uploader("Chargez une image", type=["jpg", "jpeg", "png"])

if uploaded_image is not None:
    # Chargement PIL
    try:
        image = Image.open(uploaded_image)
        image = ImageOps.exif_transpose(image)  # corrige l’orientation EXIF
    except Exception as e:
        st.error(f"Impossible de lire l'image: {e}")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Aperçu original")
        st.image(image, use_column_width=True)
        st.caption(f"{image.width} × {image.height}")

    # Contrôles
    percent_change = st.slider(
        "Pourcentage (− = réduire, + = agrandir)",
        min_value=-80, max_value=200, value=0, step=1
    )
    target_size_kb = st.number_input(
        "Poids cible (Ko) — 0 pour ignorer",
        min_value=0, step=10, value=0,
        help="Si > 0 : on tente de s’en approcher à l’export (JPEG). Pour PNG, on optimise seulement."
    )
    filename = st.text_input(
        "Nom du fichier exporté",
        value="resized_image.jpg",
        help="Extension .jpg/.jpeg ou .png recommandée."
    )

    # Traitement
    out_img = resize_image(image, target_size_kb, percent_change)

    with col2:
        st.subheader("Aperçu modifié")
        st.image(out_img, use_column_width=True)
        st.caption(f"{out_img.width} × {out_img.height}")

    # Export (bytes en mémoire)
    data = export_image(out_img, filename, target_size_kb)
    size_kb = len(data) / 1024

    st.write(f"~ Poids estimé du fichier exporté : **{size_kb:.1f} Ko**")

    # Bouton de téléchargement (recommandé)
    st.download_button(
        label="Télécharger l'image",
        data=data,
        file_name=filename,
        mime="image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
    )

    # Option : sauvegarde serveur (facultatif)
    if st.checkbox("Enregistrer côté serveur (fichier local)"):
        try:
            with open(filename, "wb") as f:
                f.write(data)
            st.success(f"Fichier enregistré : {filename}")
        except Exception as e:
            st.error(f"Échec de l'enregistrement : {e}")

    # Détails
    with st.expander("Détails"):
        st.write(f"Image d'origine : {image.width}×{image.height}")
        st.write(f"Image modifiée : {out_img.width}×{out_img.height}")
        st.write(f"Format export : {'JPEG' if filename.lower().endswith(('.jpg','.jpeg')) else 'PNG'}")
        if target_size_kb > 0 and filename.lower().endswith((".jpg", ".jpeg")):
            st.write(f"Poids cible demandé : {target_size_kb} Ko (binaire sur qualité)")
