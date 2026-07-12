"""
Ejecuta el streaming del TSV de metadatos de GISAID (equivalente a las celdas
1.2+1.3 de TFMh.ipynb) como script standalone, fuera de VS Code/Jupyter, para
evitar el OOM de la ventana (VS Code + extensión de notebooks + kernel
consumen demasiada RAM en esta máquina de 16GB). El resultado se guarda en
tfm_data/streaming_accumulators.pkl para que el notebook lo cargue en vez de
recalcularlo.
"""
import gc
import itertools
import pickle
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

DATA_DIR = Path.cwd() / 'data'
WORKDIR  = Path.cwd() / 'tfm_data'
WORKDIR.mkdir(exist_ok=True)
GISAID_METADATA_PATH = DATA_DIR / 'GISAID_metadata_2026_02_22.zip'

CHUNKSIZE      = 50_000
TOTAL_ROWS_EST = 17_000_000
COLS_NEEDED = ['Virus name', 'Collection date', 'Clade',
               'Pango lineage', 'AA Substitutions', 'Location']
GENERIC_CLADES = {'G', 'GR', 'GRA', 'GK', 'GH', 'O', 'L', 'GV'}

IMMUNE_ESCAPE_MUTS = {
    'Spike_E484K','Spike_E484A','Spike_K417N','Spike_K417T',
    'Spike_L452R','Spike_L452Q','Spike_N501Y','Spike_N440K',
    'Spike_F490S','Spike_Q498R','Spike_Y505H',
    'Spike_R346T','Spike_K444T','Spike_V445P',
    'Spike_G446S','Spike_F456L',
}
# Ronda 3: ampliado de 39 a 66 mutaciones (top-60 Spike/NSP12 por varianza en
# train, calculado sobre el pickle de la ronda 2, unión con IMMUNE_ESCAPE_MUTS)
# para dar más cobertura real a 2.9/3.7 sin disparar el coste combinatorio
# (C(66,2)=2,145 pares, ~2.9x los 741 de antes; C(637,2)~203K habría sido
# arriesgado de repetir tras los OOM ya sufridos).
TARGET_COOC_MUTS = {
    'NSP12_G671S', 'NSP12_Y273H', 'Spike_A222V', 'Spike_A27S', 'Spike_A570D',
    'Spike_A67V', 'Spike_D1118H', 'Spike_D796Y', 'Spike_D950N', 'Spike_E156G',
    'Spike_E484A', 'Spike_E484K', 'Spike_F157del', 'Spike_F456L', 'Spike_F486P',
    'Spike_F486V', 'Spike_F490S', 'Spike_G142D', 'Spike_G252V', 'Spike_G339D',
    'Spike_G339H', 'Spike_G446S', 'Spike_G496S', 'Spike_H146Q', 'Spike_K417N',
    'Spike_K417T', 'Spike_K444T', 'Spike_L212I', 'Spike_L24del', 'Spike_L368I',
    'Spike_L452Q', 'Spike_L452R', 'Spike_L981F', 'Spike_N211del', 'Spike_N440K',
    'Spike_N501Y', 'Spike_N679K', 'Spike_N856K', 'Spike_P25del', 'Spike_P26del',
    'Spike_P681H', 'Spike_P681R', 'Spike_Q183E', 'Spike_Q493R', 'Spike_Q498R',
    'Spike_R158del', 'Spike_R346K', 'Spike_R346T', 'Spike_S371L', 'Spike_S704L',
    'Spike_S982A', 'Spike_T19I', 'Spike_T19R', 'Spike_T376A', 'Spike_T478K',
    'Spike_T547K', 'Spike_T716I', 'Spike_T95I', 'Spike_V143del', 'Spike_V213E',
    'Spike_V213G', 'Spike_V445P', 'Spike_V83A', 'Spike_Y145del', 'Spike_Y505H',
    'Spike_ins214EPE',
}


def extract_lineage_family(clade):
    if pd.isna(clade) or str(clade).strip() == '':
        return 'Unknown'
    return str(clade).split('.')[0]


def main():
    clade_week_counts      = defaultdict(Counter)
    family_week_counts     = defaultdict(Counter)
    mut_week_counts        = defaultdict(Counter)
    week_totals            = Counter()
    clade_country_sets     = defaultdict(lambda: defaultdict(set))
    clade_pango_family     = defaultdict(Counter)
    family_mut_week_counts = defaultdict(lambda: defaultdict(Counter))
    mut_pair_week_counts   = defaultdict(Counter)

    total_rows_processed = 0
    chunk_idx  = 0
    start_time = time.time()

    print(f'Iniciando streaming standalone. CHUNKSIZE={CHUNKSIZE:,}', flush=True)
    print(f'Fichero: {GISAID_METADATA_PATH}', flush=True)

    with zipfile.ZipFile(str(GISAID_METADATA_PATH), 'r') as zf:
        tsv_name = [f for f in zf.namelist() if f.endswith('.tsv')][0]
        with zf.open(tsv_name) as fh:
            reader = pd.read_csv(fh, sep='\t',
                                  usecols=lambda c: c in COLS_NEEDED,
                                  chunksize=CHUNKSIZE, dtype=str)
            for chunk in reader:
                if chunk_idx % 20 == 0:
                    elapsed = time.time() - start_time
                    pct     = min(total_rows_processed / TOTAL_ROWS_EST, 1.0)
                    speed   = total_rows_processed / elapsed if elapsed > 0 else 0
                    eta_s   = (TOTAL_ROWS_EST - total_rows_processed) / speed if speed > 0 else 0
                    print(f'  {pct*100:5.1f}%  ({total_rows_processed/1e6:.1f}M/'
                          f'{TOTAL_ROWS_EST/1e6:.0f}M filas)  '
                          f'tiempo={int(elapsed//60)}m{int(elapsed%60)}s  '
                          f'ETA={int(eta_s//60)}m{int(eta_s%60)}s', flush=True)

                chunk = chunk.rename(columns={
                    'Virus name': 'virus', 'Collection date': 'date',
                    'Clade': 'clade_nextstrain', 'Pango lineage': 'pango',
                    'AA Substitutions': 'aa_subs', 'Location': 'location'})

                chunk['clade_final'] = chunk['clade_nextstrain'].where(
                    ~chunk['clade_nextstrain'].isin(GENERIC_CLADES), chunk['pango'])
                chunk = chunk.dropna(subset=['clade_final', 'date'])

                chunk['date'] = pd.to_datetime(chunk['date'], errors='coerce')
                chunk = chunk.dropna(subset=['date'])
                chunk = chunk[(chunk['date'] >= '2019-12-01') &
                              (chunk['date'] <= '2026-12-31')].copy()

                chunk['week'] = chunk['date'].dt.to_period('W').apply(lambda r: r.start_time)
                chunk['lineage_family'] = chunk['pango'].apply(extract_lineage_family)

                for (wk, cl), cnt in chunk.groupby(['week', 'clade_final']).size().items():
                    clade_week_counts[wk][cl] += int(cnt)
                    week_totals[wk] += int(cnt)
                for (wk, fm), cnt in chunk.groupby(['week', 'lineage_family']).size().items():
                    family_week_counts[wk][fm] += int(cnt)
                for (cl, fm), cnt in chunk.groupby(['clade_final', 'lineage_family']).size().items():
                    clade_pango_family[cl][fm] += int(cnt)

                # Mutaciones a nivel de secuencia — SIN pandas .explode(): en
                # chunks con muchas mutaciones por secuencia, .explode() sobre
                # arrays de millones de elementos dispara una inferencia de
                # dtype especulativa interna de pandas/numpy (llega a probar
                # complex128) que necesita un bloque de memoria contiguo grande
                # y puede fallar aunque haya RAM libre de sobra (fragmentación).
                # Un bucle Python puro es más lento pero no tiene ese punto de
                # fallo: solo incrementa contadores, sin reconstruir arrays.
                chunk_muts = chunk.dropna(subset=['aa_subs']).copy()
                aa_clean = chunk_muts['aa_subs'].astype(str).str.strip('()')
                mask = aa_clean.str.len() > 3

                if mask.sum() > 0:
                    weeks_m = chunk_muts.loc[mask, 'week'].values
                    fams_m  = chunk_muts.loc[mask, 'lineage_family'].values
                    muts_lists = aa_clean[mask].str.split(',')

                    for wk, fam, L in zip(weeks_m, fams_m, muts_lists):
                        seq_muts = [m.strip() for m in L]
                        seq_muts = [m for m in seq_muts if len(m) > 3]
                        if not seq_muts:
                            continue

                        wk_counter  = mut_week_counts[wk]
                        fam_counter = family_mut_week_counts[wk][fam]
                        for m in seq_muts:
                            wk_counter[m]  += 1
                            fam_counter[m] += 1

                        mset = TARGET_COOC_MUTS.intersection(seq_muts)
                        if len(mset) >= 2:
                            pair_counter = mut_pair_week_counts[wk]
                            for m1, m2 in itertools.combinations(sorted(mset), 2):
                                pair_counter[frozenset((m1, m2))] += 1
                    del muts_lists

                chunk_loc = chunk.dropna(subset=['location']).copy()
                if len(chunk_loc) > 0:
                    chunk_loc['country'] = chunk_loc['location'].str.split(' / ').str[1].str.strip()
                    chunk_loc = chunk_loc.dropna(subset=['country'])
                    for row in chunk_loc[['week', 'clade_final', 'country']].itertuples(index=False):
                        clade_country_sets[row.week][row.clade_final].add(row.country)

                total_rows_processed += len(chunk)
                chunk_idx += 1
                del chunk, chunk_muts, chunk_loc
                gc.collect()

    clade_country_counts = defaultdict(Counter)
    for wk, cd in clade_country_sets.items():
        for cl, cs in cd.items():
            clade_country_counts[wk][cl] = len(cs)
    del clade_country_sets
    gc.collect()

    # Aplanar family_mut_week_counts (usa defaultdict con lambda -> no picklable)
    family_mut_week_counts_plain = {
        wk: {fam: counter for fam, counter in fam_dict.items()}
        for wk, fam_dict in family_mut_week_counts.items()
    }

    elapsed_total = time.time() - start_time
    n_clades_uniq = len({c for w in clade_week_counts.values() for c in w})
    n_muts_uniq   = len({m for w in mut_week_counts.values() for m in w})
    n_pairs_uniq  = len({p for w in mut_pair_week_counts.values() for p in w})
    print(f'\nGISAID procesado en {int(elapsed_total//60)}m {int(elapsed_total%60)}s', flush=True)
    print(f'   Filas procesadas       : {total_rows_processed:,}')
    print(f'   Clados únicos          : {n_clades_uniq:,}')
    print(f'   Familias Pango únicas  : {len({f for w in family_week_counts.values() for f in w}):,}')
    print(f'   Semanas con datos      : {len(week_totals):,}')
    print(f'   Mutaciones únicas (raw): {n_muts_uniq:,}')
    print(f'   Pares de coocurrencia real: {n_pairs_uniq:,}')

    out_path = WORKDIR / 'streaming_accumulators.pkl'
    with open(out_path, 'wb') as f:
        pickle.dump(dict(
            clade_week_counts=dict(clade_week_counts),
            family_week_counts=dict(family_week_counts),
            mut_week_counts=dict(mut_week_counts),
            week_totals=dict(week_totals),
            clade_country_counts=dict(clade_country_counts),
            clade_pango_family=dict(clade_pango_family),
            family_mut_week_counts=family_mut_week_counts_plain,
            mut_pair_week_counts=dict(mut_pair_week_counts),
            total_rows_processed=total_rows_processed,
        ), f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f'\nGuardado: {out_path}  ({out_path.stat().st_size/1e6:.1f} MB)', flush=True)


if __name__ == '__main__':
    main()
