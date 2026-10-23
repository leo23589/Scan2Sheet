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
    
    jour = int(data.get("Date", 0))
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
        data.get("Espece", 0.0),
        data.get("T.Resto", 0.0),
        data.get("CB", 0.0),
        formula,
        data.get("Alcools", 0.0)
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

    attendu = data.get("total_attendu", 0.0)
    
    cell_format = {
        "backgroundColor": {
            "red": 0.0,
            "green": 1.0,
            "blue": 0.0
        } if abs(valeur_calculee - attendu) < 0.5 else {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0
        }
    }
    
    sheet.format(f"E{ligne_total}", cell_format)
    return valeur_calculee, attendu

st.title("Scanner de Bilan Journalier")

if "pending_replacements" not in st.session_state:
    st.session_state.pending_replacements = []

sheet_url = st.secrets["sheet_url"]

# Ajout du paramètre accept_multiple_files=True
uploaded_files = st.file_uploader("Prendre une ou plusieurs photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    if st.button("Lancer l'analyse et enregistrer"):
        st.session_state.pending_replacements = [] 
        
        for uploaded_file in uploaded_files:
            st.markdown("---")
            st.image(uploaded_file, width=350, caption=f"Analyse de : {uploaded_file.name}")
            
            texte_extrait = extract_text_from_image(uploaded_file)
            donnees = parse_receipt_data(texte_extrait)
            
            st.write(f"Catégories détectées ({uploaded_file.name}) :")
            st.json(donnees)
            
            if donnees.get("type") == "mensuel":
                calcule, attendu = check_monthly_total(donnees, sheet_url)
                st.success(f"Vérification mensuelle effectuée ! Calculé: {calcule}€ / Attendu: {attendu}€")
            else:
                is_filled, sheet, row_idx, nom_mois, annee_num, mois_num, nb_jours = check_if_day_filled(donnees, sheet_url)
                
                if is_filled:
                    st.session_state.pending_replacements.append({
                        "donnees": donnees,
                        "sheet": sheet,
                        "row_idx": row_idx,
                        "nb_jours": nb_jours,
                        "date_jour": donnees.get("Date", 0),
                        "mois_str": f"{nom_mois} {annee_num}",
                        "file_name": uploaded_file.name
                    })
                    st.warning(f"⚠️ Valeurs existantes pour le {donnees.get('Date', 0)} {nom_mois} {annee_num}. Mis en file d'attente.")
                else:
                    df_final = write_journalier_to_sheet(sheet, row_idx, donnees, nb_jours)
                    st.success(f"✅ Le Google Sheet a été mis à jour pour le {donnees.get('Date', 0)} {nom_mois} !")

# Gestion globale des remplacements en attente
if st.session_state.pending_replacements:
    st.markdown("---")
    st.warning("⚠️ **Confirmation de remplacement requise**")
    
    for item in st.session_state.pending_replacements:
        st.write(f"- Ticket **{item['file_name']}** : Remplacer les données du {item['date_jour']} {item['mois_str']}")
        
    if st.button("Confirmer TOUS les remplacements"):
        df_final = None
        for item in st.session_state.pending_replacements:
            df_final = write_journalier_to_sheet(item["sheet"], item["row_idx"], item["donnees"], item["nb_jours"])
            st.success(f"Les valeurs du {item['date_jour']} {item['mois_str']} ont été remplacées avec succès !")
        
        if df_final is not None:
            st.dataframe(df_final)
            
        st.session_state.pending_replacements = []