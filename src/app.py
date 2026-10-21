import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials
from logic import parse_receipt_data

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

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

        sheet_id = sheet.id
        border_format = {
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 2,
                    "endRowIndex": ligne_total,
                    "startColumnIndex": 0,
                    "endColumnIndex": 6
                },
                "top": {"style": "SOLID", "width": 1},
                "bottom": {"style": "SOLID", "width": 1},
                "left": {"style": "SOLID", "width": 1},
                "right": {"style": "SOLID", "width": 1},
                "innerHorizontal": {"style": "SOLID", "width": 1},
                "innerVertical": {"style": "SOLID", "width": 1}
            }
        }
        
        spreadsheet.client.batch_update(spreadsheet.id, {'requests': [border_format]})

        return sheet, fin_jours, ligne_total

def check_if_day_filled(data, sheet_url):
    creds = get_credentials()
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_url(sheet_url)
    
    now = datetime.now()
    mois_num = data.get("Mois", 0)
    annee_num = data.get("Annee", 0)
    
    if mois_num == 0 or annee_num == 0:
        mois_num = now.month
        annee_num = now.year
        
    nom_mois = MOIS_FR[mois_num]
    _, nb_jours = calendar.monthrange(annee_num, mois_num)
    nom_onglet = f"{nom_mois} {annee_num}"
    
    sheet, _, _ = init_sheet_if_needed(spreadsheet, nom_onglet, nom_mois, nb_jours)
    
    jour = int(data["Date"])
    if jour == 0:
        jour = now.day
        
    row_idx = jour + 3
    valeurs = sheet.get(f'B{row_idx}:D{row_idx}')
    
    is_filled = False
    if valeurs and len(valeurs) > 0:
        for val in valeurs[0]:
            if str(val).strip() not in ["", "0", "0.0"]:
                is_filled = True
                break
                
    return is_filled, sheet, row_idx, nom_mois, annee_num, mois_num, nb_jours

def write_journalier_to_sheet(sheet, row_idx, data, nb_jours):
    formula = f"=B{row_idx}+C{row_idx}+D{row_idx}"
    row_data = [[
        data["Espece"],
        data["T.Resto"],
        data["CB"],
        formula,
        data["Alcols"]
    ]]
    sheet.update(range_name=f'B{row_idx}:F{row_idx}', values=row_data, value_input_option='USER_ENTERED')
    
    ligne_total = nb_jours + 5
    raw_data = sheet.get(f'A3:F{ligne_total}')
    return pd.DataFrame(raw_data[1:], columns=raw_data[0])

def check_monthly_total(data, sheet_url):
    creds = get_credentials()
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_url(sheet_url)
    
    now = datetime.now()
    nom_mois = MOIS_FR[now.month]
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

if "pending_data" not in st.session_state:
    st.session_state.pending_data = None
if "sheet_info" not in st.session_state:
    st.session_state.sheet_info = None

sheet_url = st.secrets["sheet_url"]
uploaded_file = st.file_uploader("Prendre une photo du ticket", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file)

    if st.button("Lancer l'analyse et enregistrer"):
        st.session_state.pending_data = None 
        texte_extrait = extract_text_from_image(uploaded_file)
        donnees = parse_receipt_data(texte_extrait)
        
        st.write("Catégories détectées :")
        st.json(donnees)
        
        if donnees["type"] == "mensuel":
            calcule, attendu = check_monthly_total(donnees, sheet_url)
            st.success(f"Vérification mensuelle effectuée ! Calculé: {calcule}€ / Attendu: {attendu}€")
        else:
            is_filled, sheet, row_idx, nom_mois, annee_num, mois_num, nb_jours = check_if_day_filled(donnees, sheet_url)
            
            if is_filled:
                st.session_state.pending_data = donnees
                st.session_state.sheet_info = (sheet, row_idx, nb_jours)
                st.session_state.mois_str = f"{nom_mois} {annee_num}"
            else:
                df_final = write_journalier_to_sheet(sheet, row_idx, donnees, nb_jours)
                st.success("Le Google Sheet a été mis à jour !")
                st.dataframe(df_final)

    if st.session_state.pending_data is not None:
        zone_bouton = st.empty()
        with zone_bouton.container():
            date_jour = st.session_state.pending_data["Date"]
            mois_str = st.session_state.get("mois_str", "")
            st.warning(f"Des valeurs existent déjà pour le jour {date_jour} du mois de {mois_str}. Voulez-vous les remplacer ?")
            
            if st.button("Confirmer le remplacement"):
                zone_bouton.empty()
                
                sheet, row_idx, nb_jours = st.session_state.sheet_info
                df_final = write_journalier_to_sheet(sheet, row_idx, st.session_state.pending_data, nb_jours)
                st.success("Les valeurs ont été remplacées avec succès !")
                st.dataframe(df_final)
                
                st.session_state.pending_data = None
                st.session_state.sheet_info = None
                st.session_state.mois_str = None