# 📊 Dashboard Valutazione Walcu

Dashboard HTML statica per la visualizzazione dei risultati dei Test Walcu sulla rete vendita.

## Struttura del progetto

```
walcu-dashboard/
├── index.html                    ← Dashboard principale
├── data/
│   └── data.json                 ← Dati (aggiornati automaticamente)
├── scripts/
│   └── fetch_data.py             ← Script che scarica i dati da SharePoint
└── .github/
    └── workflows/
        └── update-data.yml       ← GitHub Action per aggiornamento automatico
```

## 🚀 Setup su GitHub

### 1. Crea il repository
Crea un nuovo repository su GitHub (pubblico o privato).

### 2. Carica i file
Carica tutti i file di questa cartella nel repository.

### 3. Abilita GitHub Pages
- Vai su **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/ (root)`
- Salva

La dashboard sarà disponibile su:
`https://<tuo-username>.github.io/<nome-repo>/`

### 4. Verifica l'aggiornamento automatico
- Vai su **Actions** nel repository
- Clicca su "🔄 Aggiorna dati Walcu"
- Clicca **Run workflow** → **Run workflow**
- Aspetta ~1 minuto e controlla che sia andato a buon fine ✅

L'aggiornamento automatico gira ogni 4 ore.

## ⚙️ Modifica della frequenza di aggiornamento

Nel file `.github/workflows/update-data.yml`, modifica la riga:

```yaml
- cron: '0 */4 * * *'   # ogni 4 ore
```

Esempi:
- `'0 */2 * * *'` → ogni 2 ore
- `'0 8,12,17 * * 1-5'` → alle 8, 12 e 17 nei giorni feriali

## 📋 Sezioni della dashboard

| Sezione | Descrizione |
|---------|-------------|
| **👤 Individuale** | Seleziona un venditore e vedi i suoi punteggi test per test |
| **📋 Domande** | Per ogni test, distribuzione e medie per ogni domanda |
| **🏢 Gruppi** | Classifica e confronto tra gruppi (Usato Mantova, Usato Brescia, etc.) |

## 🔧 Aggiornamento manuale della mappatura gruppi

Se i gruppi o le persone cambiano, modifica il dizionario `GROUPS_MAP` in `scripts/fetch_data.py`.

## ℹ️ Note tecniche

- I dati vengono scaricati dai link SharePoint "chiunque con il link" — non richiede autenticazione
- Se un download fallisce, vengono mantenuti i dati dell'ultimo aggiornamento riuscito
- La dashboard non ha backend: legge solo `data/data.json`
- Compatibile con tutti i browser moderni
