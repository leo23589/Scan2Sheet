import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import locale
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials
from logic import parse_receipt_data

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

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

def init_sheet_if_needed(spreadsheet, nom_onglet, nom_mois, nb_jours):
    try:
        sheet = spreadsheet.worksheet(nom_onglet)
        return sheet, nb_jours + 3, nb_jours + 5
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=nom_onglet, rows="40", cols="10")
        
        updates = []
        updates.append({'range': 'A1', 'values': [[f'Mois: {nom_mois}']]})
        updates.append({'range': 'A3:F3', 'values': [['Jour', 'Espece', 'T.Resto', 'CB', 'Total', 'Alcools']]})
        
        days_data = []
        for i in range(1, nb_jours + 1):
            row_idx = i + 3
            formula = f"=B{row_idx}+C{row_idx}+D{row_idx}"
            days_data.append([i, "", "", "", formula, ""])
        
        fin_jours = nb_jours + 3
        updates.append({'range': f'A4:F{fin_jours}', 'values': days_data})
        
        ligne_total = fin_jours + 2
        total_row = [[
            'Total', 
            f'=SUM(B4:B{fin_jours})', 
            f'=SUM(C4:C{fin_jours})', 
            f'=SUM(D4:D{fin_jours})', 
            f'=SUM(E4:E{fin_jours})', 
            f'=SUM(F4:F{fin_jours})'
        ]]
        updates.append({'range': f'A{ligne_total}:F{ligne_total}', 'values': total_row})
        
        sheet.batch_update(updates, value_input_option='USER_ENTERED')
        return sheet, fin_jours, ligne_total

def update_google_sheets_journalier(data, sheet_url):
    creds = get_credentials()
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_url(sheet_url)
    
    now = datetime.now()
    nom_mois = now.strftime("%B").capitalize()
    annee = now.year
    _, nb_jours = calendar.monthrange(annee, now.month)
    nom_onglet = f"{nom_mois} {annee}"
    
    sheet, fin_jours, ligne_total = init_sheet_if_needed(spreadsheet, nom_onglet, nom_mois, nb_jours)
    
    jour = int(data["Date"])
    if jour == 0:
        jour = now.day
        
    row_idx = jour + 3
    formula = f"=B{row_idx}+C{row_idx}+D{row_idx}"
    row_data = [[
        data["Espece"],
        data["T.Resto"],
        data["CB"],
        formula,
        data["Alcols"]
    ]]
    
    sheet.update(range_name=f'B{row_idx}:F{row_idx}', values=row_data, value_input_option='USER_ENTERED')
    
    raw_data = sheet.get(f'A3:F{ligne_total}')
    return pd.DataFrame(raw_data[1:], columns=raw_data[0])

def check_monthly_total(data, sheet_url):
    creds = get_credentials()
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_url(sheet_url)
    
    now = datetime.now()
    nom_mois = now.strftime("%B").capitalize()
    annee = now.year
    _, nb_jours = calendar.monthrange(annee, now.month)
    nom_onglet = f"{nom_mois} {annee}"
    
    sheet = spreadsheet.worksheet(nom_onglet)
    ligne_total = nb_jours + 5
    
    valeur_calculee_str = sheet.acell(f'E{ligne_total}').value
    
    try:
        valeur_calculee = float(valeur_calculee_str.replace(',', '.'))
    except (ValueError, AttributeError):
        valeur_calculee = 0.0

    cell_format = {
        "backgroundColor": {
            "red": 0.0,
            "green": 1.0,
            "blue": 0.0
        } if abs(valeur_calculee - data["total_attendu"]) < 0.5 else {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0
        }
    }
    
    sheet.format(f"E{ligne_total}", cell_format)
    return valeur_calculee, data["total_attendu"]

st.title("Scanner de Bilan Journalier")

sheet_url = st.secrets["sheet_url"]
uploaded_file = st.file_uploader("Prendre une photo du ticket", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Ticket en cours d'analyse", use_column_width=True)

    if st.button("Lancer l'analyse et enregistrer"):
        texte_extrait = extract_text_from_image(uploaded_file)
        donnees = parse_receipt_data(texte_extrait)
        
        st.write("Catégories détectées :")
        st.json(donnees)
        
        if donnees["type"] == "mensuel":
            calcule, attendu = check_monthly_total(donnees, sheet_url)
            st.success(f"Vérification mensuelle effectuée ! Calculé: {calcule}€ / Attendu: {attendu}€")
        else:
            df_final = update_google_sheets_journalier(donnees, sheet_url)
            st.success("Le Google Sheet a été mis à jour !")
            st.dataframe(df_final)