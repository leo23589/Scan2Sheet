# 📊 Scanner de Bilan Journalier (Restaurant)

Une application web développée avec **Streamlit** permettant de numériser automatiquement les tickets de caisse de clôture journaliers et mensuels d'un restaurant. 

L'application utilise la reconnaissance optique de caractères (OCR) via **Google Cloud Vision** pour extraire les montants et les reporter intelligemment dans un tableau **Google Sheets**.

## ✨ Fonctionnalités

- **Extraction OCR intelligente** : Lit les montants (Espèces, CB, Tickets Restaurant, Total, Alcools) et la date exacte du ticket, peu importe l'orientation de la photo.
- **Gestion automatique du tableur** : Trouve ou crée automatiquement l'onglet du mois correspondant (ex: "Janvier 2025") et génère le tableau avec les bordures et les formules de somme.
- **Sécurité anti-écrasement** : Vérifie si le jour scanné contient déjà des données et demande une confirmation globale avant de remplacer les montants.
- **Traitement par lots** : Possibilité d'importer et d'analyser plusieurs tickets simultanément.
- **Vérification mensuelle** : Scanne les tickets "Rapport Mensuel" pour vérifier visuellement (vert/rouge) si le total calculé dans le tableur correspond au ticket de la machine.

## 📂 Structure du projet

Assurez-vous que l'arborescence de votre dépôt GitHub correspond exactement à ceci :

```text
scanner-bilan/
│
├── README.md               # Ce fichier de documentation
├── requirements.txt        # Liste des dépendances (streamlit, gspread, google-cloud-vision...)
│
└── src/
    ├── app.py              # Interface utilisateur Streamlit et connexion Google Sheets
    └── logic.py            # Logique d'extraction des données avec Expressions Régulières (Regex)