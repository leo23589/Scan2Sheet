import streamlit as st
import pandas as pd
from datetime import datetime
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials
from logic import parse_receipt_data

def get_credentials():
    creds_dict = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)

def extract_text_from_image(image_file):
    creds = get_credentials()
    client = vision.ImageAnnotatorClient(credentials=creds)
    content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return ""

def update_google_sheets(data, sheet_url):
    creds = get_credentials()
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(sheet_url).sheet1
    
    row_data = [
        data["Date"],
        data["Espece"],
        data["T.Resto"],
        data["CB"],
        data["Total"],
        data["Alcols"]
    ]
    sheet.append_row(row_data)
    
    return pd.DataFrame(sheet.get_all_records())

st.title("Scanner de Bilan Journalier")

sheet_url = st.secrets["sheet_url"]
uploaded_file = st.file_uploader("Prendre une photo du ticket", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Ticket en cours d'analyse", use_column_width=True)

    if st.button("Lancer l'analyse et enregistrer"):
        texte_extrait = extract_text_from_image(uploaded_file)
        jour_actuel = datetime.now().day
        donnees = parse_receipt_data(texte_extrait, jour_actuel)
        
        st.write("Catégories détectées :")
        st.json(donnees)
        
        df_final = update_google_sheets(donnees, sheet_url)
        st.success("Le Google Sheet a été mis à jour !")
        st.dataframe(df_final)
