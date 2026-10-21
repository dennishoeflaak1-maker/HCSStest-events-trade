

import warnings

import eurostat
import numpy as np
import pandas as pd
EU = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "HU", "IE",
      "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]

def data_trade(product, landen, start, eind):
    # ---------- 1. data ophalen (alleen EU-landen kunnen reporter zijn) ----------
    NAAR_EUROSTAT = {"GR": "EL"}                                  # ISO -> Eurostat
    VAN_EUROSTAT = {v: k for k, v in NAAR_EUROSTAT.items()}


    delen = []
    for land in landen:
        if land not in EU:
            continue                       # niet-EU-landen komen alleen als partner voor
        filters = {
            "freq": "M",
            "reporter": NAAR_EUROSTAT.get(land, land),
            "partner": [NAAR_EUROSTAT.get(p, p) for p in landen if p != land],
            "product": product,
            "flow": ["1", "2"],            # 1 = import, 2 = export
            "indicators": "VALUE_EUR",
            "startPeriod": start,
            "endPeriod": eind,
        }
        delen.append(eurostat.get_data_df("DS-059341", filter_pars=filters))

    if not delen:
        raise ValueError("Geen EU-land in 'landen': Eurostat heeft dan geen data.")
    df = pd.concat(delen, ignore_index=True)

    # Eurostat levert een tabel met één kolom per maand -> omzetten naar één rij per waarde
    maand_kolommen = [c for c in df.columns if str(c)[:4].isdigit()]
    lang = df.melt(id_vars=["reporter", "partner", "flow"], value_vars=maand_kolommen,
                   var_name="maand", value_name="waarde")
    lang["flow"] = lang["flow"].astype(str)
    lang["reporter"] = lang["reporter"].replace(VAN_EUROSTAT)   # EL -> GR
    lang["partner"] = lang["partner"].replace(VAN_EUROSTAT)

    # ---------- 2. lege arrays maken (maanden vast op basis van start en eind) ----------
    maanden = pd.period_range(start, eind, freq="M").strftime("%Y-%m").tolist()
    T, N = len(maanden), len(landen)

    export_arr = np.full((T, N, N), np.nan)
    import_arr = np.full((T, N, N), np.nan)

    # posities in de array: welke index hoort bij welke maand / welk land
    t = lang["maand"].map({m: i for i, m in enumerate(maanden)})
    r = lang["reporter"].map({l: i for i, l in enumerate(landen)})
    p = lang["partner"].map({l: i for i, l in enumerate(landen)})

    # rijen die niet in de array passen eruit halen (bijv. andere maandnotatie)
    ok = (t.notna() & r.notna() & p.notna()).to_numpy()
    if not ok.all():
        print(f"LET OP: {(~ok).sum()} rijen overgeslagen. "
              f"Voorbeeld maandnotatie Eurostat: {lang['maand'].iloc[0]}")
    t = t[ok].astype(int).to_numpy()
    r = r[ok].astype(int).to_numpy()
    p = p[ok].astype(int).to_numpy()
    w = lang["waarde"].to_numpy(dtype=float)[ok]
    flow = lang["flow"].to_numpy()[ok]

    # ---------- 3. arrays vullen ----------
    is_export = flow == "2"
    is_import = flow == "1"
    export_arr[t[is_export], r[is_export], p[is_export]] = w[is_export]
    import_arr[t[is_import], r[is_import], p[is_import]] = w[is_import]

    # ---------- 4. stroom, saldo, netto en totaal ----------
    # stroom[t, A, B] = handel van A naar B
    #   EU -> EU:           gemiddelde van export van A en import van B
    #   EU -> niet-EU:      alleen de export van A
    #   niet-EU -> EU:      alleen de import van B
    #   niet-EU -> niet-EU: NaN
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)   # melding bij lege vakjes
        stroom = np.nanmean([export_arr, import_arr.transpose(0, 2, 1)], axis=0)
        terug = stroom.transpose(0, 2, 1)
        saldo = (stroom - terug) / (stroom + terug)

    netto = stroom - terug
    total = stroom + terug

    # controle: maanden zonder data (Eurostat loopt een paar maanden achter)
    leeg = [m for k, m in enumerate(maanden) if np.isnan(stroom[k]).all()]
    if leeg:
        print("Geen handelsdata voor:", leeg)

    return stroom, saldo, netto, total
