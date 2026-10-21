from src.logic import parse_receipt_data

def test_parse_receipt_data():
    texte_test = """
    Total: 1437,47
    CB: 1425,82
    Espece: 11,65
    Alcols: 3,00
    """
    
    resultat = parse_receipt_data(texte_test, 2)
    
    assert resultat["Date"] == 2
    assert resultat["Total"] == 1437.47
    assert resultat["CB"] == 1425.82
    assert resultat["Espece"] == 11.65
    assert resultat["Alcols"] == 3.0
    assert resultat["T.Resto"] == 0.0
