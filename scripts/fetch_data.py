#!/usr/bin/env python3
"""
fetch_data.py — Scarica i 3 file Excel da SharePoint e genera data/data.json
Viene eseguito automaticamente da GitHub Actions.
"""

import json
import io
import re
import sys
import os
from datetime import datetime

try:
    import pandas as pd
    import requests
    import openpyxl
except ImportError:
    print("Installo dipendenze...")
    os.system("pip install pandas requests openpyxl --quiet")
    import pandas as pd
    import requests
    import openpyxl

# ─────────────────────────────────────────────
#  CONFIGURAZIONE
# ─────────────────────────────────────────────

TESTS = [
    {
        "id": "test1",
        "name": "Test Walcu n.1",
        "url": "https://intergeanordest-my.sharepoint.com/:x:/p/mori_m/IQCTEUuKTSo5SZw_gfGPEgINAabb2G5Gc4lri4NYvtT2wVs?e=pIh7An&download=1",
    },
    {
        "id": "test2",
        "name": "Test Walcu n.2",
        "url": "https://intergeanordest-my.sharepoint.com/:x:/p/mori_m/IQBlKPqcMXqgRKBE23RiTY8GAR8NrFDz-d-fsbTYcl00hmU?e=qW6AaV&download=1",
    },
    {
        "id": "test3",
        "name": "Test Walcu n.3",
        "url": "https://intergeanordest-my.sharepoint.com/:x:/p/mori_m/IQC-ugJsw0XJRo1QZ_WCiJYYARR9dzChsHRNLt4stqEBqHI?e=cKuctP&download=1",
    },
]

# Mappatura gruppi (inline — aggiornare se cambiano)
GROUPS_MAP = {
    "Francesco Macchiella": "Usato Mantova",
    "Alessio Bustini": "Usato Modena",
    "Francesco Bove": "Usato Mantova",
    "Luigi Cirillo": "Usato Brescia",
    "Luis Lopez": "Usato Brescia",
    "Mauro Bazzana": "Usato Lonato",
    "Paola Coluccia": "Arval Parma",
    "Marco Spallanzani": "Usato Reggio",
    "Michele Bonetti": "Usato Brescia",
    "Ester Serafini": "Arval Parma",
    "Emanuele Tomasello": "Usato Reggio",
    "Alfonso Iannotta": "Usato Modena",
    "Gianluca Bergonzini": "Usato Parma",
    "Antonio Brunato": "Usato Carpi",
    "Luigi Pecora": "Usato Modena",
    "Nicholas Palmeri": "Usato Parma",
    "marco Furlani": "Usato Mantova",
    "Fabio Redaelli": "Usato Carpi",
    "Yuri Ansaldi": "Usato Carpi",
    "Vincenzo Bevilacqua": "Usato Parma",
    "Adriano Manno": "Usato Carpi",
}

SKIP_COLS = {'Id', 'Ora di inizio', 'Ora di completamento', 'Posta elettronica', 'Nome'}
NOTE_COL  = "Segnalazioni o criticità sull'utente"
USER_COL  = 'Utente che si sta valutando'

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def norm(name: str) -> str:
    """Normalizza nome per confronto fuzzy."""
    return re.sub(r'\s+', ' ', str(name).strip().lower())

def find_group(user_raw: str) -> str:
    key = norm(user_raw)
    for orig, grp in GROUPS_MAP.items():
        if norm(orig) == key:
            return grp
    return "Non assegnato"

def match_original_name(user_raw: str) -> str:
    key = norm(user_raw)
    for orig in GROUPS_MAP:
        if norm(orig) == key:
            return orig
    return user_raw.strip()

def download_excel(url: str, test_name: str) -> bytes | None:
    """Scarica il file Excel da SharePoint. Restituisce bytes o None."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
    }
    try:
        r = requests.get(url, headers=headers, allow_redirects=True, timeout=30)
        r.raise_for_status()
        # Controlla che sia un file Excel valido
        if b'PK' not in r.content[:4] and b'<?xml' not in r.content[:10]:
            print(f"  ⚠ {test_name}: risposta non sembra un file Excel (Content-Type: {r.headers.get('content-type','?')})")
            print(f"     Primi 200 bytes: {r.content[:200]}")
            return None
        print(f"  ✓ {test_name}: {len(r.content):,} bytes")
        return r.content
    except Exception as e:
        print(f"  ✗ {test_name}: errore download — {e}")
        return None

def process_dataframe(df: pd.DataFrame, test_id: str, test_name: str) -> dict:
    """Elabora un DataFrame e restituisce la struttura dati del test."""
    cols = list(df.columns)

    # Trova colonne domande (non skip, non user, non note, non "Eventuali integrazioni...")
    question_cols = []
    integ_map = {}
    for col in cols:
        if col in SKIP_COLS or col == USER_COL or col == NOTE_COL:
            continue
        if col.startswith('Eventuali integrazioni'):
            continue
        question_cols.append(col)

    # Mappa domanda → colonna integrazioni successiva
    for q in question_cols:
        idx = cols.index(q)
        if idx + 1 < len(cols) and cols[idx + 1].startswith('Eventuali integrazioni'):
            integ_map[q] = cols[idx + 1]

    df = df.iloc[1:].reset_index(drop=True)  # salta la riga di test
    responses = []
    for _, row in df.iterrows():
        user_raw = str(row.get(USER_COL, '')).strip()
        if not user_raw or user_raw == 'nan':
            continue

        scores = []
        notes  = []
        for q in question_cols:
            val = row.get(q)
            score = int(val) if pd.notna(val) and str(val) != 'nan' else None
            scores.append(score)

            integ_col = integ_map.get(q)
            if integ_col:
                nv   = row.get(integ_col, '')
                note = str(nv).strip() if pd.notna(nv) and str(nv) != 'nan' else ''
            else:
                note = ''
            notes.append('' if note == 'nan' else note)

        seg_val      = row.get(NOTE_COL, '')
        segnalazioni = str(seg_val).strip() if pd.notna(seg_val) and str(seg_val) != 'nan' else ''
        if segnalazioni == 'nan':
            segnalazioni = ''

        responses.append({
            "user":         match_original_name(user_raw),
            "group":        find_group(user_raw),
            "scores":       scores,
            "notes":        notes,
            "segnalazioni": segnalazioni,
        })

    return {
        "id":        test_id,
        "name":      test_name,
        "questions": question_cols,
        "responses": responses,
    }

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print("🚀 Avvio fetch dati Walcu...")
    tests_data = []
    errors = 0

    for test_info in TESTS:
        print(f"\n📥 {test_info['name']}...")
        raw = download_excel(test_info["url"], test_info["name"])

        if raw is None:
            errors += 1
            # Prova a usare il JSON esistente per questo test
            print(f"   Tentativo di riutilizzare dati precedenti per {test_info['name']}...")
            existing_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'data.json')
            if os.path.exists(existing_path):
                with open(existing_path) as f:
                    old = json.load(f)
                existing = next((t for t in old.get('tests', []) if t['id'] == test_info['id']), None)
                if existing:
                    tests_data.append(existing)
                    print(f"   ✓ Riutilizzati dati precedenti ({len(existing['responses'])} risposte)")
                    continue
            # Fallback: struttura vuota
            tests_data.append({"id": test_info["id"], "name": test_info["name"], "questions": [], "responses": []})
            continue

        try:
            df = pd.read_excel(io.BytesIO(raw))
            test_data = process_dataframe(df, test_info["id"], test_info["name"])
            tests_data.append(test_data)
            print(f"   ✓ {len(test_data['responses'])} risposte, {len(test_data['questions'])} domande")
        except Exception as e:
            print(f"   ✗ Errore parsing: {e}")
            errors += 1
            tests_data.append({"id": test_info["id"], "name": test_info["name"], "questions": [], "responses": []})

    # Costruisci output
    output = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tests":        tests_data,
        "groups":       GROUPS_MAP,
        "all_groups":   sorted(set(GROUPS_MAP.values())),
        "all_users":    sorted(GROUPS_MAP.keys(), key=lambda x: x.lower()),
    }

    # Scrivi data.json
    out_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'data.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_responses = sum(len(t['responses']) for t in tests_data)
    print(f"\n✅ data.json aggiornato — {total_responses} risposte totali, {errors} errori")

    if errors == len(TESTS):
        print("❌ Tutti i download hanno fallito. Controlla gli URL SharePoint.")
        sys.exit(1)

if __name__ == '__main__':
    main()
