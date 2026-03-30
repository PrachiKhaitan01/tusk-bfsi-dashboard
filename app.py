import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Tusk BFSI Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .stApp { background-color: #0F1923; }
    .main .block-container { padding-top: 1.5rem; }
    h1,h2,h3 { color: #E8F4FD; }
    .stTabs [data-baseweb="tab-list"] { background-color: #1A2940; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #8BADC7; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #2E6DA4; color: white; border-radius: 6px; }
    .stSelectbox label,.stMultiSelect label { color: #8BADC7; font-weight: 600; font-size: 13px; }
    div[data-testid="stMetricValue"] { color: #4FC3F7; font-size: 1.3rem; font-weight: 700; }
    label { color: #8BADC7 !important; }
    .stRadio label { color: #C8D8E8 !important; }
    p { color: #C8D8E8; }
    .stButton button { background-color: #2E6DA4; color: white; border: none; border-radius: 6px; font-weight: 600; }
    .stDataFrame { border-radius: 8px; }
    .stInfo { background-color: #1A2940; border-color: #2E4A6B; }
</style>
""", unsafe_allow_html=True)

QUARTER_ORDER = ['Q1-FY23','Q2-FY23','Q3-FY23','Q4-FY23',
                 'Q1-FY24','Q2-FY24','Q3-FY24','Q4-FY24',
                 'Q1-FY25','Q2-FY25','Q3-FY25','Q4-FY25',
                 'Q1-FY26','Q2-FY26','Q3-FY26','Q4-FY26']

PCT_METRICS = ['Yields','CoFs','NIMs','Opex to AUM','Credit Cost','RoA','RoE',
               'Cost to Income','CAR','GNPA','NNPA','PCR','CASA']
ABS_METRICS = ['Advances (INR Crs)','Deposits (INR Crs)','NII','Other Income','PAT (INR Crs)']
HIGHER_BETTER = ['NIMs','RoA','RoE','PCR','CASA','CAR','Yields','NII','Other Income',
                 'PAT (INR Crs)','Advances (INR Crs)','Deposits (INR Crs)']
LOWER_BETTER = ['CoFs','Credit Cost','GNPA','NNPA','Cost to Income','Opex to AUM']

COLORS = {
    'HDFCBANK':'#4FC3F7','ICICIBANK':'#81C784','AXISBANK':'#FFB74D',
    'KOTAKBANK':'#F06292','FEDERALBNK':'#CE93D8','CSBBBANK':'#80DEEA',
    'SBIN':'#FF8A65','CANBK':'#A5D6A7','BANKBARODA':'#FFF176',
    'BANKINDIA':'#FFCC02','INDIANB':'#B39DDB','PNB':'#80CBC4','UNIONBANK':'#FFAB91',
}

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Tusk_Banking_Dashboard_Data.csv')
    except:
        df = pd.read_excel('Tusk_Banking_Dashboard.xlsx', sheet_name='Dashboard Data')
    df['Quarter_Order'] = df['Quarter'].apply(lambda q: QUARTER_ORDER.index(q) if q in QUARTER_ORDER else 99)
    return df.sort_values('Quarter_Order')

@st.cache_data
def compute_derived(df):
    rows = []
    for co in df['Company'].unique():
        cat = df[df['Company']==co]['Category'].iloc[0]
        co_df = df[df['Company']==co].copy()
        pivot = co_df.pivot_table(index='Metric', columns='Quarter', values='Value', aggfunc='first')
        quarters = [q for q in QUARTER_ORDER if q in pivot.columns]

        for q_idx, q in enumerate(quarters):
            def get(m): return pivot.at[m, q] if m in pivot.index and q in pivot.columns else np.nan

            adv   = get('Advances (INR Crs)')
            dep   = get('Deposits (INR Crs)')
            nii   = get('NII')
            pat   = get('PAT (INR Crs)')
            yields= get('Yields')
            cofs  = get('CoFs')

            # Credit Deposit Ratio
            cd_ratio = adv / dep if not (pd.isna(adv) or pd.isna(dep) or dep == 0) else np.nan

            # Net Interest Spread
            spread = yields - cofs if not (pd.isna(yields) or pd.isna(cofs)) else np.nan

            def pct_growth(metric, periods):
                if q_idx < periods: return np.nan
                prev_q = quarters[q_idx - periods]
                curr = pivot.at[metric, q] if metric in pivot.index else np.nan
                prev = pivot.at[metric, prev_q] if metric in pivot.index else np.nan
                if pd.isna(curr) or pd.isna(prev) or prev == 0: return np.nan
                return (curr - prev) / abs(prev)

            derived = {
                'Advances Growth QoQ': pct_growth('Advances (INR Crs)', 1),
                'Advances Growth YoY': pct_growth('Advances (INR Crs)', 4),
                'Deposits Growth QoQ': pct_growth('Deposits (INR Crs)', 1),
                'Deposits Growth YoY': pct_growth('Deposits (INR Crs)', 4),
                'NII Growth QoQ':      pct_growth('NII', 1),
                'NII Growth YoY':      pct_growth('NII', 4),
                'PAT Growth QoQ':      pct_growth('PAT (INR Crs)', 1),
                'PAT Growth YoY':      pct_growth('PAT (INR Crs)', 4),
                'Credit Deposit Ratio': cd_ratio,
                'Net Interest Spread':  spread,
            }

            for metric, val in derived.items():
                if not pd.isna(val):
                    rows.append({'Metric':metric,'Category':cat,'Company':co,
                                 'Quarter':q,'Value':val,'Quarter_Order':QUARTER_ORDER.index(q)})
    return pd.DataFrame(rows)

def fmt(val, metric):
    if pd.isna(val) or metric is None: return "—"
    if metric in PCT_METRICS or 'Growth' in str(metric) or metric == 'Net Interest Spread':
        return f"{val*100:.2f}%"
    if metric == 'Credit Deposit Ratio':
        return f"{val:.2f}x"
    if metric in ABS_METRICS:
        return f"₹{val/1e5:.1f}L Cr" if val > 1e5 else f"₹{val:,.0f}"
    return f"{val:.2f}"

def pct_fmt(val, metric):
    if pd.isna(val): return "—"
    if metric in PCT_METRICS: return f"{val*100:+.0f}bps"
    if metric in ABS_METRICS: return f"{val:+,.0f}"
    return f"{val:+.3f}"

def apply_theme(fig, is_pct=False):
    fig.update_layout(
        plot_bgcolor='#0F1923', paper_bgcolor='#0F1923',
        font=dict(family="Arial", color="#C8D8E8", size=12),
        title_font=dict(size=15, color="#E8F4FD"),
        legend=dict(bgcolor='#1A2940', bordercolor='#2E4A6B', borderwidth=1, font=dict(color="#C8D8E8")),
        xaxis=dict(gridcolor='#1A2940', color='#8BADC7', tickfont=dict(color='#C8D8E8', size=11)),
        yaxis=dict(gridcolor='#1A2940', color='#8BADC7', tickfont=dict(color='#C8D8E8', size=11)),
        margin=dict(t=50, b=40, l=60, r=20),
    )
    if is_pct:
        fig.update_yaxes(tickformat='.2%')
    return fig

def make_heatmap(pivot, title, fmt_metric=None, rows_are_metrics=False):
    """
    Row-normalised heatmap: each row has its own independent colour scale.
    fmt_metric: metric name for formatting (used when rows=companies).
    rows_are_metrics: True when pivot.index contains metric names.
    """
    raw_z = pivot.values.astype(float)
    rows_list = list(pivot.index)
    cols_list = list(pivot.columns)
    norm_z = np.full_like(raw_z, np.nan, dtype=float)
    text = []

    for i, row_id in enumerate(rows_list):
        row = raw_z[i]
        valid = row[~np.isnan(row)]
        m_for_fmt = row_id if rows_are_metrics else fmt_metric
        flip = m_for_fmt in LOWER_BETTER if m_for_fmt else False
        text.append([fmt(raw_z[i][j], m_for_fmt) for j in range(len(cols_list))])
        if len(valid) == 0:
            norm_z[i] = 0.5
            continue
        rmin, rmax = valid.min(), valid.max()
        if rmax == rmin:
            norm_z[i] = 0.5
        else:
            scaled = (row - rmin) / (rmax - rmin)
            norm_z[i] = (1 - scaled) if flip else scaled

    fig = go.Figure(go.Heatmap(
        z=norm_z, x=cols_list, y=rows_list,
        text=text, texttemplate="%{text}",
        textfont=dict(size=11, color="white", family="Arial"),
        colorscale='RdYlGn',
        zmin=0, zmax=1,
        showscale=False,
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#E8F4FD")),
        plot_bgcolor='#0F1923', paper_bgcolor='#0F1923',
        font=dict(family="Arial", color="#C8D8E8"),
        xaxis=dict(tickfont=dict(color='#C8D8E8', size=11), side='top'),
        yaxis=dict(tickfont=dict(color='#C8D8E8', size=11), autorange='reversed'),
        margin=dict(t=80, b=20, l=160, r=20),
        height=max(300, len(pivot.index) * 38 + 100)
    )
    return fig

def compute_change(df, metric, companies, change_type):
    rows = df[(df['Metric']==metric) & (df['Company'].isin(companies))].copy()
    rows = rows.sort_values('Quarter_Order')
    results = []
    lookback = 1 if change_type == 'QoQ' else 4
    for co in companies:
        co_data = rows[rows['Company']==co].set_index('Quarter')['Value']
        quarters = [q for q in QUARTER_ORDER if q in co_data.index]
        for i, q in enumerate(quarters):
            if i >= lookback:
                prev = co_data.get(quarters[i-lookback])
                val = co_data[q]
                if prev is not None and not pd.isna(prev) and not pd.isna(val):
                    results.append({'Company':co,'Quarter':q,'Change':val-prev,
                                    'Quarter_Order':QUARTER_ORDER.index(q)})
    return pd.DataFrame(results)

# ── LOAD DATA ──────────────────────────────────────────────
df_raw = load_data()
df_derived = compute_derived(df_raw)
df = pd.concat([df_raw, df_derived], ignore_index=True)

quarters_in_data = [q for q in QUARTER_ORDER if q in df['Quarter'].unique()]
all_companies = sorted(df['Company'].unique())

BASE_METRICS = sorted(df_raw['Metric'].unique())
DERIVED_METRIC_NAMES = sorted(df_derived['Metric'].unique()) if len(df_derived) > 0 else []
all_metrics = BASE_METRICS + DERIVED_METRIC_NAMES

GROWTH_METRICS = [m for m in all_metrics if 'Growth' in m or 'Ratio' in m or 'Spread' in m]

# ── ROE TREE COMPONENTS ────────────────────────────────────
ROE_TREE_METRICS = [
    ('RoE',             'Return on Equity',          '= RoA × Leverage'),
    ('RoA',             'Return on Assets',          '= NIM + Other Income Yield − Opex − Credit Cost'),
    ('Leverage',        'Equity Multiplier',         '= Assets / Equity'),
    ('NIMs',            'Net Interest Margin',       '= Yields − CoFs'),
    ('Yields',          'Yield on Advances',         'Interest Income / Advances'),
    ('CoFs',            'Cost of Funds',             'Interest Expense / Deposits'),
    ('Net Interest Spread', 'Spread',                '= Yields − CoFs (volume-neutral)'),
    ('Credit Cost',     'Provision / Advances',      'Drag on RoA'),
    ('Opex to AUM',     'Operating Cost / AUM',      'Efficiency drag on RoA'),
    ('Cost to Income',  'Cost-to-Income Ratio',      'Operating efficiency'),
    ('GNPA',            'Gross NPA Ratio',            'Asset quality — stock'),
    ('NNPA',            'Net NPA Ratio',              'After provisions'),
    ('PCR',             'Provision Coverage',         'Buffer strength'),
    ('CASA',            'CASA Ratio',                 'Low-cost deposit franchise'),
    ('CAR',             'Capital Adequacy',           'Regulatory capital buffer'),
]

st.markdown("## 📊 Tusk Investments — BFSI Results Dashboard")
st.caption(f"{df_raw['Quarter'].nunique()} quarters | {df_raw['Company'].nunique()} companies | {len(BASE_METRICS)} base + {len(DERIVED_METRIC_NAMES)} derived metrics")

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📋 Scorecard", "🏦 Cross-Bank", "🌡 Heatmaps", "📈 Trends",
    "📊 Growth Metrics", "🌳 RoE Tree", "🔬 Deep Dive", "➕ Add Data", "📥 Batch Import"
])


# ══════════════════════════════════════════════
# TAB 0 — LATEST QUARTER SCORECARD
# ══════════════════════════════════════════════
with tab0:
    st.subheader("Latest Quarter Scorecard")
    latest_q = quarters_in_data[-1]
    prev_q = quarters_in_data[-2] if len(quarters_in_data) > 1 else None
    prev_y_q = quarters_in_data[-5] if len(quarters_in_data) >= 5 else None

    sc1, sc2 = st.columns(2)
    with sc1:
        sc_cat = st.selectbox("Category", ["ALL"] + sorted(df['Category'].unique()), key='sc_cat')
    with sc2:
        sc_metrics = st.multiselect("Key metrics to show",
            ['NIMs','RoA','RoE','GNPA','Credit Cost','CASA','CAR','Advances (INR Crs)','PAT (INR Crs)'],
            default=['NIMs','RoA','GNPA','Credit Cost'],
            key='sc_metrics')

    sc_df = df.copy()
    if sc_cat != "ALL":
        sc_df = sc_df[sc_df['Category'] == sc_cat]
    companies_sc = sorted(sc_df['Company'].unique())

    st.markdown(f"**{latest_q} vs {prev_q} (QoQ) | {latest_q} vs {prev_y_q if prev_y_q else 'N/A'} (YoY)**")
    st.markdown("---")

    for m in sc_metrics:
        st.markdown(f"#### {m}")
        latest_vals = sc_df[(sc_df['Metric']==m)&(sc_df['Quarter']==latest_q)].set_index('Company')['Value']
        prev_vals = sc_df[(sc_df['Metric']==m)&(sc_df['Quarter']==prev_q)].set_index('Company')['Value'] if prev_q else {}
        yoy_vals = sc_df[(sc_df['Metric']==m)&(sc_df['Quarter']==prev_y_q)].set_index('Company')['Value'] if prev_y_q else {}

        metric_cols = st.columns(min(len(companies_sc), 6))
        for i, co in enumerate(companies_sc):
            if co not in latest_vals.index or pd.isna(latest_vals[co]):
                continue
            val = latest_vals[co]
            qoq = None
            if co in prev_vals.index and not pd.isna(prev_vals[co]):
                diff = val - prev_vals[co]
                qoq = pct_fmt(diff, m)
            with metric_cols[i % 6]:
                st.metric(co, fmt(val, m), delta=qoq)
        st.markdown("")

    st.markdown("---")
    st.markdown("#### Movers — biggest QoQ changes this quarter")
    if prev_q:
        mover_rows = []
        for m in ['NIMs','RoA','GNPA','Credit Cost','Advances (INR Crs)','PAT (INR Crs)']:
            lat = sc_df[(sc_df['Metric']==m)&(sc_df['Quarter']==latest_q)][['Company','Value']].rename(columns={'Value':'Latest'})
            prv = sc_df[(sc_df['Metric']==m)&(sc_df['Quarter']==prev_q)][['Company','Value']].rename(columns={'Value':'Prior'})
            merged = lat.merge(prv, on='Company').dropna()
            merged['Change'] = merged['Latest'] - merged['Prior']
            merged['AbsChange'] = merged['Change'].abs()
            merged['Metric'] = m
            merged['ChangeStr'] = merged.apply(lambda r: pct_fmt(r['Change'], m), axis=1)
            merged['LatestStr'] = merged.apply(lambda r: fmt(r['Latest'], m), axis=1)
            mover_rows.append(merged)

        if mover_rows:
            movers = pd.concat(mover_rows)
            better = movers[movers['Change'].apply(lambda x: x > 0)].nlargest(5, 'AbsChange')[['Company','Metric','LatestStr','ChangeStr']]
            worse = movers[movers['Change'].apply(lambda x: x < 0)].nlargest(5, 'AbsChange')[['Company','Metric','LatestStr','ChangeStr']]
            mv1, mv2 = st.columns(2)
            with mv1:
                st.markdown("**Improved**")
                for _, r in better.iterrows():
                    icon = "▲" if r['Metric'] not in LOWER_BETTER else "▼"
                    color = "#26C06A" if r['Metric'] not in LOWER_BETTER else "#EF5350"
                    st.markdown(f"<span style='color:{color}'>{icon}</span> **{r['Company']}** {r['Metric']} → {r['LatestStr']} ({r['ChangeStr']})", unsafe_allow_html=True)
            with mv2:
                st.markdown("**Deteriorated**")
                for _, r in worse.iterrows():
                    icon = "▼" if r['Metric'] not in LOWER_BETTER else "▲"
                    color = "#EF5350" if r['Metric'] not in LOWER_BETTER else "#26C06A"
                    st.markdown(f"<span style='color:{color}'>{icon}</span> **{r['Company']}** {r['Metric']} → {r['LatestStr']} ({r['ChangeStr']})", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 1 — CROSS-BANK COMPARISON
# ══════════════════════════════════════════════
with tab1:
    c1,c2,c3,c4 = st.columns(4)
    with c1: m1 = st.selectbox("Metric", all_metrics, index=all_metrics.index('NIMs') if 'NIMs' in all_metrics else 0, key='t1m')
    with c2: cat1 = st.selectbox("Category", ["ALL"]+sorted(df['Category'].unique()), key='t1c')
    with c3: view1 = st.selectbox("View", ["Latest Quarter","QoQ Change","YoY Change"], key='t1v')
    with c4: q_sel = st.selectbox("Quarter", ["Latest"]+quarters_in_data[::-1], key='t1q')

    filt = df[df['Metric']==m1].copy()
    if cat1 != "ALL": filt = filt[filt['Category']==cat1]
    q_use = quarters_in_data[-1] if q_sel=="Latest" else q_sel
    is_pct = m1 in PCT_METRICS or 'Growth' in m1

    if view1 == "Latest Quarter":
        data = filt[filt['Quarter']==q_use].dropna(subset=['Value']).sort_values('Value', ascending=False)
        fig = go.Figure(go.Bar(
            x=data['Company'], y=data['Value'],
            marker_color=[COLORS.get(c,'#4FC3F7') for c in data['Company']],
            text=[fmt(v,m1) for v in data['Value']],
            textposition='outside', textfont=dict(size=13, color='white'),
        ))
        apply_theme(fig, is_pct)
        fig.update_layout(title=f"{m1} — {q_use}", height=450)
        st.plotly_chart(fig, use_container_width=True)
        cols = st.columns(min(len(data),5))
        for i,(_,row) in enumerate(data.head(5).iterrows()):
            with cols[i]: st.metric(row['Company'], fmt(row['Value'],m1))
    else:
        ct = 'QoQ' if view1=='QoQ Change' else 'YoY'
        chg = compute_change(df, m1, sorted(filt['Company'].unique()), ct)
        if not chg.empty:
            lchg = chg[chg['Quarter']==q_use].sort_values('Change', ascending=False)
            fig = go.Figure(go.Bar(
                x=lchg['Company'], y=lchg['Change'],
                marker_color=['#26C06A' if v>=0 else '#EF5350' for v in lchg['Change']],
                text=[pct_fmt(v,m1) for v in lchg['Change']],
                textposition='outside', textfont=dict(size=13, color='white'),
            ))
            apply_theme(fig, is_pct)
            fig.update_layout(title=f"{m1} — {ct} Change ({q_use})", height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough quarters for this change type.")

# ══════════════════════════════════════════════
# TAB 2 — HEATMAPS
# ══════════════════════════════════════════════
with tab2:
    ht = st.radio("Heatmap type", ["Metric across companies","All metrics for one company"], horizontal=True, key='htype')

    if ht == "Metric across companies":
        h1,h2 = st.columns(2)
        with h1: hm = st.selectbox("Metric", all_metrics, index=all_metrics.index('NIMs') if 'NIMs' in all_metrics else 0, key='hm1')
        with h2: hcat = st.selectbox("Category", ["ALL"]+sorted(df['Category'].unique()), key='hcat1')
        hfilt = df[df['Metric']==hm].copy()
        if hcat != "ALL": hfilt = hfilt[hfilt['Category']==hcat]
        pivot = hfilt.pivot_table(index='Company', columns='Quarter', values='Value', aggfunc='first')
        pivot = pivot[[q for q in QUARTER_ORDER if q in pivot.columns]]
        st.plotly_chart(make_heatmap(pivot, f"{hm} — {hcat}", fmt_metric=hm, rows_are_metrics=False), use_container_width=True)
        st.markdown("**Latest quarter ranking**")
        latest_q = [q for q in QUARTER_ORDER if q in pivot.columns][-1]
        ranking = pivot[latest_q].dropna().sort_values(ascending=(hm in LOWER_BETTER))
        rcols = st.columns(min(len(ranking),6))
        for i,(co,val) in enumerate(ranking.items()):
            with rcols[i%6]:
                medal = ["🥇","🥈","🥉"][i] if i<3 else f"#{i+1}"
                st.markdown(f"**{medal} {co}**")
                st.markdown(f"<span style='color:#4FC3F7;font-size:1.1rem;font-weight:700'>{fmt(val,hm)}</span>", unsafe_allow_html=True)
    else:
        hco = st.selectbox("Company", all_companies, key='hco2')
        show_derived = st.toggle("Include derived metrics (growth, CD ratio)", value=False)
        metrics_to_show = BASE_METRICS + (DERIVED_METRIC_NAMES if show_derived else [])
        pivot = df[(df['Company']==hco)&(df['Metric'].isin(metrics_to_show))].pivot_table(
            index='Metric', columns='Quarter', values='Value', aggfunc='first')
        pivot = pivot[[q for q in QUARTER_ORDER if q in pivot.columns]]
        groups = [
            ([m for m in pivot.index if m in PCT_METRICS], "% Metrics"),
            ([m for m in pivot.index if m in ABS_METRICS], "Absolute Metrics"),
            ([m for m in pivot.index if 'Growth' in m], "Growth Metrics"),
            ([m for m in pivot.index if m not in PCT_METRICS and m not in ABS_METRICS and 'Growth' not in m], "Other Ratios"),
        ]
        for group, label in groups:
            sub = [m for m in group if m in pivot.index]
            if not sub: continue
            st.plotly_chart(make_heatmap(pivot.loc[sub], f"{hco} — {label}", rows_are_metrics=True), use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — MULTI-COMPANY TRENDS
# ══════════════════════════════════════════════
with tab3:
    r1,r2,r3 = st.columns([3,4,2])
    with r1: tm = st.selectbox("Metric", all_metrics, index=all_metrics.index('NIMs') if 'NIMs' in all_metrics else 0, key='trm')
    with r2: tcos = st.multiselect("Companies", all_companies, default=all_companies[:6], key='trco')
    with r3: tchg = st.radio("Show", ["Value","QoQ Δ","YoY Δ"], key='trchg')

    is_pct_t = tm in PCT_METRICS or 'Growth' in tm

    if tcos:
        if tchg == "Value":
            tdata = df[(df['Metric']==tm)&(df['Company'].isin(tcos))].dropna(subset=['Value']).sort_values('Quarter_Order')
            fig = go.Figure()
            for co in tcos:
                d = tdata[tdata['Company']==co]
                if len(d)==0: continue
                fig.add_trace(go.Scatter(
                    x=d['Quarter'], y=d['Value'], name=co, mode='lines+markers',
                    line=dict(color=COLORS.get(co,'#4FC3F7'), width=2.5),
                    marker=dict(size=8, color=COLORS.get(co,'#4FC3F7')),
                    text=[fmt(v,tm) for v in d['Value']],
                    hovertemplate="<b>"+co+"</b><br>%{x}: %{text}<extra></extra>"
                ))
            # Add sector average line
            avg_data = df[(df['Metric']==tm)&(df['Company'].isin(tcos))].groupby('Quarter')['Value'].mean().reset_index()
            avg_data['Quarter_Order'] = avg_data['Quarter'].apply(lambda q: QUARTER_ORDER.index(q) if q in QUARTER_ORDER else 99)
            avg_data = avg_data.sort_values('Quarter_Order')
            if len(avg_data) > 0:
                fig.add_trace(go.Scatter(
                    x=avg_data['Quarter'], y=avg_data['Value'],
                    name='Sector Avg', mode='lines',
                    line=dict(color='white', width=1.5, dash='dash'),
                    opacity=0.6,
                    hovertemplate="<b>Sector Avg</b><br>%{x}: "+("<b>%{y:.2%}</b>" if is_pct_t else "<b>%{y:.2f}</b>")+"<extra></extra>"
                ))
            apply_theme(fig, is_pct_t)
            fig.update_layout(title=f"{tm} — Multi-Company", height=480,
                             xaxis=dict(categoryorder='array', categoryarray=quarters_in_data))
            st.plotly_chart(fig, use_container_width=True)
        else:
            ct = 'QoQ' if 'QoQ' in tchg else 'YoY'
            chg = compute_change(df, tm, tcos, ct)
            if not chg.empty:
                chg = chg.sort_values('Quarter_Order')
                fig = go.Figure()
                for co in tcos:
                    d = chg[chg['Company']==co]
                    if len(d)==0: continue
                    fig.add_trace(go.Scatter(
                        x=d['Quarter'], y=d['Change'], name=co, mode='lines+markers',
                        line=dict(color=COLORS.get(co,'#4FC3F7'), width=2.5),
                        marker=dict(size=8, color=COLORS.get(co,'#4FC3F7')),
                        text=[pct_fmt(v,tm) for v in d['Change']],
                        hovertemplate="<b>"+co+"</b><br>%{x}: %{text}<extra></extra>"
                    ))
                fig.add_hline(y=0, line_dash="dash", line_color="#5A7A9A")
                apply_theme(fig, is_pct_t)
                fig.update_layout(title=f"{tm} — {ct} Change", height=480,
                                 xaxis=dict(categoryorder='array', categoryarray=quarters_in_data))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        latest_q = quarters_in_data[-1]
        prev_q = quarters_in_data[-2] if len(quarters_in_data)>1 else None
        latest_vals = df[(df['Metric']==tm)&(df['Company'].isin(tcos))&(df['Quarter']==latest_q)].dropna(subset=['Value'])
        latest_vals = latest_vals.sort_values('Value', ascending=(tm in LOWER_BETTER))
        mcols = st.columns(min(len(latest_vals),6))
        for i,(_,row) in enumerate(latest_vals.iterrows()):
            with mcols[i]:
                delta = None
                if prev_q:
                    prev = df[(df['Metric']==tm)&(df['Company']==row['Company'])&(df['Quarter']==prev_q)]['Value']
                    if len(prev) and not pd.isna(prev.iloc[0]):
                        delta = pct_fmt(row['Value']-prev.iloc[0], tm)
                st.metric(row['Company'], fmt(row['Value'],tm), delta=delta)

# ══════════════════════════════════════════════
# TAB 4 — GROWTH METRICS
# ══════════════════════════════════════════════
with tab4:
    st.subheader("Derived Growth Metrics")
    g1,g2,g3 = st.columns(3)
    with g1: gcat = st.selectbox("Category", ["ALL"]+sorted(df['Category'].unique()), key='gc')
    with g2: gq = st.selectbox("Quarter", ["Latest"]+quarters_in_data[::-1], key='gq')
    with g3: gview = st.selectbox("Growth type", ["QoQ","YoY","Both side by side"], key='gv')

    gq_use = quarters_in_data[-1] if gq=="Latest" else gq
    gfilt = df.copy()
    if gcat != "ALL": gfilt = gfilt[gfilt['Category']==gcat]

    growth_pairs = [
        ("Advances Growth", "Advances Growth QoQ", "Advances Growth YoY"),
        ("Deposits Growth", "Deposits Growth QoQ", "Deposits Growth YoY"),
        ("NII Growth",      "NII Growth QoQ",      "NII Growth YoY"),
        ("PAT Growth",      "PAT Growth QoQ",      "PAT Growth YoY"),
    ]

    for label, qoq_m, yoy_m in growth_pairs:
        st.markdown(f"#### {label}")
        if gview == "Both side by side":
            col_a, col_b = st.columns(2)
            for col, gm in [(col_a, qoq_m),(col_b, yoy_m)]:
                with col:
                    gdata = gfilt[(gfilt['Metric']==gm)&(gfilt['Quarter']==gq_use)].dropna(subset=['Value'])
                    gdata = gdata.sort_values('Value', ascending=False)
                    if len(gdata)==0:
                        st.caption(f"No data for {gm}")
                        continue
                    fig = go.Figure(go.Bar(
                        x=gdata['Company'], y=gdata['Value'],
                        marker_color=['#26C06A' if v>=0 else '#EF5350' for v in gdata['Value']],
                        text=[fmt(v,gm) for v in gdata['Value']],
                        textposition='outside', textfont=dict(size=12, color='white'),
                        name=gm
                    ))
                    apply_theme(fig, True)
                    fig.update_layout(title=f"{gm} ({gq_use})", height=350)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            gm = qoq_m if gview=="QoQ" else yoy_m
            gdata = gfilt[(gfilt['Metric']==gm)&(gfilt['Quarter']==gq_use)].dropna(subset=['Value'])
            gdata = gdata.sort_values('Value', ascending=False)
            if len(gdata)==0:
                st.caption(f"No data for {gm}")
                continue
            fig = go.Figure(go.Bar(
                x=gdata['Company'], y=gdata['Value'],
                marker_color=['#26C06A' if v>=0 else '#EF5350' for v in gdata['Value']],
                text=[fmt(v,gm) for v in gdata['Value']],
                textposition='outside', textfont=dict(size=12, color='white'),
            ))
            apply_theme(fig, True)
            fig.update_layout(title=f"{gm} ({gq_use})", height=350)
            st.plotly_chart(fig, use_container_width=True)

    # Credit Deposit Ratio
    st.markdown("#### Credit Deposit Ratio")
    cd_data = gfilt[(gfilt['Metric']=='Credit Deposit Ratio')&(gfilt['Quarter']==gq_use)].dropna(subset=['Value'])
    cd_data = cd_data.sort_values('Value', ascending=False)
    if len(cd_data):
        fig = go.Figure(go.Bar(
            x=cd_data['Company'], y=cd_data['Value'],
            marker_color=[COLORS.get(c,'#4FC3F7') for c in cd_data['Company']],
            text=[fmt(v,'Credit Deposit Ratio') for v in cd_data['Value']],
            textposition='outside', textfont=dict(size=12,color='white'),
        ))
        fig.add_hline(y=1.0, line_dash="dash", line_color="#EF5350", annotation_text="1.0x = fully funded")
        apply_theme(fig)
        fig.update_layout(title=f"Credit Deposit Ratio ({gq_use})", height=380)
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 5 — ROE TREE
# ══════════════════════════════════════════════
with tab5:
    st.subheader("RoE Tree — All components side by side across quarters")
    rt1,rt2 = st.columns(2)
    with rt1: tree_co = st.selectbox("Company", all_companies, key='tree_co')
    with rt2: tree_view = st.radio("Format", ["All quarters","Latest vs prior quarter","Latest vs prior year"], horizontal=True, key='tree_v')

    co_pivot = df[df['Company']==tree_co].pivot_table(index='Metric', columns='Quarter', values='Value', aggfunc='first')
    cols_sorted = [q for q in QUARTER_ORDER if q in co_pivot.columns]

    if tree_view == "All quarters":
        show_cols = cols_sorted
    elif tree_view == "Latest vs prior quarter":
        show_cols = cols_sorted[-2:] if len(cols_sorted)>=2 else cols_sorted
    else:
        show_cols = [cols_sorted[-5], cols_sorted[-1]] if len(cols_sorted)>=5 else cols_sorted

    tree_data = []
    for m, label, note in ROE_TREE_METRICS:
        row = {'Component': m, 'Description': label, 'Formula / Note': note}
        for q in show_cols:
            if m in co_pivot.index and q in co_pivot.columns:
                val = co_pivot.at[m, q]
                row[q] = fmt(val, m)
            else:
                row[q] = "—"
        tree_data.append(row)

    tree_df = pd.DataFrame(tree_data)
    st.markdown(f"**{tree_co} — RoE Decomposition**")

    def style_tree(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        styles.iloc[0] = 'background-color: #1B3A6B; color: #4FC3F7; font-weight: bold; font-size: 14px'
        styles.iloc[1] = 'background-color: #1A3050; color: #81C784; font-weight: bold'
        styles.iloc[2] = 'background-color: #1A3050; color: #81C784; font-weight: bold'
        for i in [3,4,5,6]:
            if i < len(styles):
                styles.iloc[i] = 'background-color: #162535; color: #FFB74D'
        return styles

    st.dataframe(
        tree_df.style.apply(style_tree, axis=None),
        use_container_width=True, height=600
    )

    st.markdown("---")
    st.markdown("**RoE trend over time**")
    if 'RoE' in co_pivot.index and 'RoA' in co_pivot.index:
        roe_vals = co_pivot.loc['RoE', cols_sorted].dropna()
        roa_vals = co_pivot.loc['RoA', cols_sorted].dropna()
        lev_vals = co_pivot.loc['Leverage', cols_sorted].dropna() if 'Leverage' in co_pivot.index else pd.Series()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(roe_vals.index), y=list(roe_vals.values),
            name='RoE', mode='lines+markers', line=dict(color='#F06292', width=3),
            marker=dict(size=8), text=[fmt(v,'RoE') for v in roe_vals],
            hovertemplate="<b>RoE</b><br>%{x}: %{text}<extra></extra>"))
        fig.add_trace(go.Scatter(x=list(roa_vals.index), y=list(roa_vals.values),
            name='RoA', mode='lines+markers', line=dict(color='#4FC3F7', width=3),
            marker=dict(size=8), yaxis='y2', text=[fmt(v,'RoA') for v in roa_vals],
            hovertemplate="<b>RoA</b><br>%{x}: %{text}<extra></extra>"))
        fig.update_layout(
            title=f"{tree_co} — RoE vs RoA", height=350,
            yaxis=dict(tickformat='.1%', title='RoE', color='#F06292'),
            yaxis2=dict(tickformat='.1%', title='RoA', overlaying='y', side='right', color='#4FC3F7'),
            xaxis=dict(categoryorder='array', categoryarray=cols_sorted)
        )
        apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 6 — COMPANY DEEP DIVE
# ══════════════════════════════════════════════
with tab6:
    d1,d2,d3 = st.columns([2,4,2])
    with d1: dco = st.selectbox("Company", all_companies, key='dco')
    with d2: dms = st.multiselect("Metrics", all_metrics,
        default=[m for m in ['NIMs','RoA','GNPA','Credit Cost','PAT (INR Crs)'] if m in all_metrics], key='dms')
    with d3: dchg = st.radio("Change overlay", ["None","QoQ","YoY"], key='dchg')

    co_df = df[df['Company']==dco].copy().sort_values('Quarter_Order')
    for m in dms:
        mdata = co_df[co_df['Metric']==m].dropna(subset=['Value'])
        if len(mdata)==0: continue
        is_pct_d = m in PCT_METRICS or 'Growth' in m
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=mdata['Quarter'], y=mdata['Value'], name=m, mode='lines+markers',
            line=dict(color='#4FC3F7', width=3),
            marker=dict(size=9, color='#4FC3F7', line=dict(color='white',width=1.5)),
            text=[fmt(v,m) for v in mdata['Value']],
            hovertemplate="<b>%{x}</b><br>"+m+": %{text}<extra></extra>",
            fill='tozeroy', fillcolor='rgba(79,195,247,0.08)'
        ))
        if dchg != "None":
            cd = compute_change(df, m, [dco], dchg)
            if not cd.empty:
                fig.add_trace(go.Bar(
                    x=cd['Quarter'], y=cd['Change'], name=f"{dchg} Δ",
                    marker_color=['#26C06A' if v>=0 else '#EF5350' for v in cd['Change']],
                    opacity=0.7, yaxis='y2',
                    text=[pct_fmt(v,m) for v in cd['Change']],
                    textposition='outside', textfont=dict(size=10,color='white'),
                ))
                fig.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False,
                    tickfont=dict(color='#8BADC7'), color='#8BADC7'))
        apply_theme(fig, is_pct_d)
        fig.update_layout(title=f"{dco} — {m}", height=300,
                         xaxis=dict(categoryorder='array', categoryarray=quarters_in_data))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    pivot = df[df['Company']==dco].pivot_table(index='Metric', columns='Quarter', values='Value', aggfunc='first')
    pivot = pivot[[q for q in QUARTER_ORDER if q in pivot.columns]]
    fmt_pivot = pivot.copy().astype(object)
    for m in fmt_pivot.index:
        fmt_pivot.loc[m] = [fmt(v, m) for v in pivot.loc[m]]
    st.dataframe(fmt_pivot, use_container_width=True, height=420)

# ══════════════════════════════════════════════
# TAB 7 — ADD NEW DATA
# ══════════════════════════════════════════════
with tab7:
    st.subheader("Add new quarterly data")
    st.info("💡 Upload the quarterly PDF to Claude.ai → use the extraction prompt in Tusk_Banking_Dashboard.xlsx Sheet 3 → enter the 19 values below → derived metrics (growth, CD ratio) calculate automatically.")

    a1,a2 = st.columns(2)
    with a1:
        co_choice = st.selectbox("Company", ["➕ New company"]+sorted(df_raw['Company'].unique()), key='aco')
        if co_choice == "➕ New company":
            new_co = st.text_input("Ticker (e.g. IDFCFIRST)", key='acon')
            new_cat = st.selectbox("Category", sorted(df['Category'].unique()), key='acatn')
        else:
            new_co = co_choice
            new_cat = df_raw[df_raw['Company']==co_choice]['Category'].iloc[0]
    with a2:
        used_q = list(df_raw[df_raw['Company']==new_co]['Quarter'].unique()) if new_co in df_raw['Company'].unique() else []
        remaining = [q for q in QUARTER_ORDER if q not in used_q]
        new_q = st.selectbox("Quarter", remaining[::-1] if remaining else QUARTER_ORDER[::-1], key='aq')

    st.markdown("---")
    metrics_entry = ['Advances (INR Crs)','Deposits (INR Crs)','Yields','CoFs','NIMs',
                     'Opex to AUM','Credit Cost','RoA','RoE','Cost to Income',
                     'NII','Other Income','PAT (INR Crs)','Leverage','CAR','GNPA','NNPA','PCR','CASA']
    new_values = {}
    g1,g2,g3 = st.columns(3)
    for i,m in enumerate(metrics_entry):
        with [g1,g2,g3][i%3]:
            hint = "decimal e.g. 0.035 = 3.5%" if m in PCT_METRICS else "INR Crores"
            new_values[m] = st.number_input(m, value=None, format="%.6f", help=hint, key=f"av_{m}")

    if st.button("✅ Save", type="primary"):
        if new_co and new_q:
            rows = [{'Metric':m,'Category':new_cat,'Company':new_co,'Quarter':new_q,'Value':v,
                     'Quarter_Order':QUARTER_ORDER.index(new_q) if new_q in QUARTER_ORDER else 99,
                     'FY':new_q.split('-')[1],'Q':new_q.split('-')[0]}
                    for m,v in new_values.items() if v is not None]
            if rows:
                updated = pd.concat([df_raw, pd.DataFrame(rows)], ignore_index=True)
                updated.to_csv('Tusk_Banking_Dashboard_Data.csv', index=False)
                st.success(f"✅ Saved {len(rows)} base metrics for {new_co} {new_q}. Derived metrics (growth, CD ratio) will auto-calculate on next load.")
                st.cache_data.clear()


# ══════════════════════════════════════════════
# TAB 8 — BATCH IMPORT
# ══════════════════════════════════════════════
with tab8:
    st.subheader("Batch Import — add multiple companies or historical quarters at once")
    st.info("Paste a CSV table with columns: Company, Category, Quarter, Metric, Value — one row per data point. Values for % metrics must be decimals (3.5% = 0.035).")

    sample = """Company,Category,Quarter,Metric,Value
IDFCFIRST,PRIVATE BANK,Q4-FY26,NIMs,0.0612
IDFCFIRST,PRIVATE BANK,Q4-FY26,RoA,0.0098
IDFCFIRST,PRIVATE BANK,Q4-FY26,GNPA,0.0198
HDFCBANK,PRIVATE BANK,Q4-FY24,NIMs,0.0363
HDFCBANK,PRIVATE BANK,Q4-FY24,RoA,0.0189"""

    st.markdown("**Template:**")
    st.code(sample, language='csv')

    paste_data = st.text_area("Paste your data here (CSV format with header row):", height=200, key='batch_paste')

    if st.button("Preview import", key='batch_preview'):
        if paste_data.strip():
            try:
                import io
                batch_df = pd.read_csv(io.StringIO(paste_data))
                required = ['Company','Category','Quarter','Metric','Value']
                missing_cols = [c for c in required if c not in batch_df.columns]
                if missing_cols:
                    st.error(f"Missing columns: {missing_cols}")
                else:
                    st.success(f"Preview: {len(batch_df)} rows ready to import")
                    st.dataframe(batch_df, use_container_width=True)
                    st.session_state['batch_ready'] = batch_df.to_csv(index=False)
            except Exception as e:
                st.error(f"Could not parse data: {e}")

    if st.button("✅ Confirm and import", type="primary", key='batch_confirm'):
        if 'batch_ready' in st.session_state:
            import io
            batch_df = pd.read_csv(io.StringIO(st.session_state['batch_ready']))
            batch_df['Quarter_Order'] = batch_df['Quarter'].apply(lambda q: QUARTER_ORDER.index(q) if q in QUARTER_ORDER else 99)
            batch_df['FY'] = batch_df['Quarter'].str.extract(r'(FY\d+)')
            batch_df['Q'] = batch_df['Quarter'].str.extract(r'(Q\d)')
            updated = pd.concat([df_raw, batch_df], ignore_index=True).drop_duplicates(
                subset=['Company','Metric','Quarter'], keep='last')
            updated.to_csv('Tusk_Banking_Dashboard_Data.csv', index=False)
            st.success(f"✅ Imported {len(batch_df)} rows. Refresh the page to see updated charts.")
            st.cache_data.clear()
        else:
            st.warning("Click Preview first to validate your data.")

st.markdown("---")
st.caption("Tusk Investments | BFSI Results Dashboard | Streamlit + Plotly")
Metric,Category,Company,Quarter,Value,Quarter_Order,FY,Q
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q1-FY25,1059724.0,0,FY25,Q1
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q2-FY25,999979.0,1,FY25,Q2
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q3-FY25,1014564.0,2,FY25,Q3
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q4-FY25,1040811.0,3,FY25,Q4
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q1-FY26,980092.0,4,FY26,Q1
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q2-FY26,1116703.0,5,FY26,Q2
Advances (INR Crs),PRIVATE BANK,AXISBANK,Q3-FY26,1159052.0,6,FY26,Q3
CAR,PRIVATE BANK,AXISBANK,Q1-FY25,0.1658,0,FY25,Q1
CAR,PRIVATE BANK,AXISBANK,Q2-FY25,,1,FY25,Q2
CAR,PRIVATE BANK,AXISBANK,Q3-FY25,0.1701,2,FY25,Q3
CAR,PRIVATE BANK,AXISBANK,Q4-FY25,,3,FY25,Q4
CAR,PRIVATE BANK,AXISBANK,Q1-FY26,,4,FY26,Q1
CAR,PRIVATE BANK,AXISBANK,Q2-FY26,0.1655,5,FY26,Q2
CAR,PRIVATE BANK,AXISBANK,Q3-FY26,0.1655,6,FY26,Q3
CASA,PRIVATE BANK,AXISBANK,Q1-FY25,0.38,0,FY25,Q1
CASA,PRIVATE BANK,AXISBANK,Q2-FY25,,1,FY25,Q2
CASA,PRIVATE BANK,AXISBANK,Q3-FY25,0.39,2,FY25,Q3
CASA,PRIVATE BANK,AXISBANK,Q4-FY25,,3,FY25,Q4
CASA,PRIVATE BANK,AXISBANK,Q1-FY26,,4,FY26,Q1
CASA,PRIVATE BANK,AXISBANK,Q2-FY26,,5,FY26,Q2
CASA,PRIVATE BANK,AXISBANK,Q3-FY26,0.39,6,FY26,Q3
CoFs,PRIVATE BANK,AXISBANK,Q1-FY25,0.0544,0,FY25,Q1
CoFs,PRIVATE BANK,AXISBANK,Q2-FY25,0.0545,1,FY25,Q2
CoFs,PRIVATE BANK,AXISBANK,Q3-FY25,0.0546,2,FY25,Q3
CoFs,PRIVATE BANK,AXISBANK,Q4-FY25,0.055,3,FY25,Q4
CoFs,PRIVATE BANK,AXISBANK,Q1-FY26,0.0539,4,FY26,Q1
CoFs,PRIVATE BANK,AXISBANK,Q2-FY26,0.0515,5,FY26,Q2
CoFs,PRIVATE BANK,AXISBANK,Q3-FY26,0.0507,6,FY26,Q3
Cost to Income,PRIVATE BANK,AXISBANK,Q1-FY25,0.475,0,FY25,Q1
Cost to Income,PRIVATE BANK,AXISBANK,Q2-FY25,0.47,1,FY25,Q2
Cost to Income,PRIVATE BANK,AXISBANK,Q3-FY25,0.462,2,FY25,Q3
Cost to Income,PRIVATE BANK,AXISBANK,Q4-FY25,0.478,3,FY25,Q4
Cost to Income,PRIVATE BANK,AXISBANK,Q1-FY26,0.447,4,FY26,Q1
Cost to Income,PRIVATE BANK,AXISBANK,Q2-FY26,0.489,5,FY26,Q2
Cost to Income,PRIVATE BANK,AXISBANK,Q3-FY26,0.4594594594594595,6,FY26,Q3
Credit Cost,PRIVATE BANK,AXISBANK,Q1-FY25,0.0097,0,FY25,Q1
Credit Cost,PRIVATE BANK,AXISBANK,Q2-FY25,0.0054,1,FY25,Q2
Credit Cost,PRIVATE BANK,AXISBANK,Q3-FY25,0.008,2,FY25,Q3
Credit Cost,PRIVATE BANK,AXISBANK,Q4-FY25,0.005,3,FY25,Q4
Credit Cost,PRIVATE BANK,AXISBANK,Q1-FY26,0.0138,4,FY26,Q1
Credit Cost,PRIVATE BANK,AXISBANK,Q2-FY26,0.0065,5,FY26,Q2
Credit Cost,PRIVATE BANK,AXISBANK,Q3-FY26,0.0063,6,FY26,Q3
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q1-FY25,1161615.0,0,FY25,Q1
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q2-FY25,1086744.0,1,FY25,Q2
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q3-FY25,1095883.0,2,FY25,Q3
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q4-FY25,1172952.0,3,FY25,Q4
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q1-FY26,1062484.0,4,FY26,Q1
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q2-FY26,1203487.0,5,FY26,Q2
Deposits (INR Crs),PRIVATE BANK,AXISBANK,Q3-FY26,1260786.0,6,FY26,Q3
GNPA,PRIVATE BANK,AXISBANK,Q1-FY25,0.0154,0,FY25,Q1
GNPA,PRIVATE BANK,AXISBANK,Q2-FY25,0.0144,1,FY25,Q2
GNPA,PRIVATE BANK,AXISBANK,Q3-FY25,0.0146,2,FY25,Q3
GNPA,PRIVATE BANK,AXISBANK,Q4-FY25,0.0128,3,FY25,Q4
GNPA,PRIVATE BANK,AXISBANK,Q1-FY26,0.0157,4,FY26,Q1
GNPA,PRIVATE BANK,AXISBANK,Q2-FY26,0.0146,5,FY26,Q2
GNPA,PRIVATE BANK,AXISBANK,Q3-FY26,0.014,6,FY26,Q3
Leverage,PRIVATE BANK,AXISBANK,Q1-FY25,7.265272328796775,0,FY25,Q1
Leverage,PRIVATE BANK,AXISBANK,Q2-FY25,,1,FY25,Q2
Leverage,PRIVATE BANK,AXISBANK,Q3-FY25,,2,FY25,Q3
Leverage,PRIVATE BANK,AXISBANK,Q4-FY25,,3,FY25,Q4
Leverage,PRIVATE BANK,AXISBANK,Q1-FY26,,4,FY26,Q1
Leverage,PRIVATE BANK,AXISBANK,Q2-FY26,,5,FY26,Q2
Leverage,PRIVATE BANK,AXISBANK,Q3-FY26,,6,FY26,Q3
NII,PRIVATE BANK,AXISBANK,Q1-FY25,13448.0,0,FY25,Q1
NII,PRIVATE BANK,AXISBANK,Q2-FY25,13483.0,1,FY25,Q2
NII,PRIVATE BANK,AXISBANK,Q3-FY25,13606.0,2,FY25,Q3
NII,PRIVATE BANK,AXISBANK,Q4-FY25,13811.0,3,FY25,Q4
NII,PRIVATE BANK,AXISBANK,Q1-FY26,13560.0,4,FY26,Q1
NII,PRIVATE BANK,AXISBANK,Q2-FY26,13745.0,5,FY26,Q2
NII,PRIVATE BANK,AXISBANK,Q3-FY26,14287.0,6,FY26,Q3
NIMs,PRIVATE BANK,AXISBANK,Q1-FY25,0.0405,0,FY25,Q1
NIMs,PRIVATE BANK,AXISBANK,Q2-FY25,0.0399,1,FY25,Q2
NIMs,PRIVATE BANK,AXISBANK,Q3-FY25,0.0393,2,FY25,Q3
NIMs,PRIVATE BANK,AXISBANK,Q4-FY25,0.0397,3,FY25,Q4
NIMs,PRIVATE BANK,AXISBANK,Q1-FY26,0.038,4,FY26,Q1
NIMs,PRIVATE BANK,AXISBANK,Q2-FY26,0.0373,5,FY26,Q2
NIMs,PRIVATE BANK,AXISBANK,Q3-FY26,0.0364,6,FY26,Q3
NNPA,PRIVATE BANK,AXISBANK,Q1-FY25,0.0034,0,FY25,Q1
NNPA,PRIVATE BANK,AXISBANK,Q2-FY25,0.0034,1,FY25,Q2
NNPA,PRIVATE BANK,AXISBANK,Q3-FY25,0.0035,2,FY25,Q3
NNPA,PRIVATE BANK,AXISBANK,Q4-FY25,0.0033,3,FY25,Q4
NNPA,PRIVATE BANK,AXISBANK,Q1-FY26,0.0045,4,FY26,Q1
NNPA,PRIVATE BANK,AXISBANK,Q2-FY26,0.0044,5,FY26,Q2
NNPA,PRIVATE BANK,AXISBANK,Q3-FY26,0.0042,6,FY26,Q3
Opex to AUM,PRIVATE BANK,AXISBANK,Q1-FY25,,0,FY25,Q1
Opex to AUM,PRIVATE BANK,AXISBANK,Q2-FY25,,1,FY25,Q2
Opex to AUM,PRIVATE BANK,AXISBANK,Q3-FY25,,2,FY25,Q3
Opex to AUM,PRIVATE BANK,AXISBANK,Q4-FY25,0.0251,3,FY25,Q4
Opex to AUM,PRIVATE BANK,AXISBANK,Q1-FY26,0.0241,4,FY26,Q1
Opex to AUM,PRIVATE BANK,AXISBANK,Q2-FY26,0.0238,5,FY26,Q2
Opex to AUM,PRIVATE BANK,AXISBANK,Q3-FY26,0.0233,6,FY26,Q3
Other Income,PRIVATE BANK,AXISBANK,Q1-FY25,5784.0,0,FY25,Q1
Other Income,PRIVATE BANK,AXISBANK,Q2-FY25,6722.0,1,FY25,Q2
Other Income,PRIVATE BANK,AXISBANK,Q3-FY25,5972.0,2,FY25,Q3
Other Income,PRIVATE BANK,AXISBANK,Q4-FY25,6780.0,3,FY25,Q4
Other Income,PRIVATE BANK,AXISBANK,Q1-FY26,7258.0,4,FY26,Q1
Other Income,PRIVATE BANK,AXISBANK,Q2-FY26,6037.0,5,FY26,Q2
Other Income,PRIVATE BANK,AXISBANK,Q3-FY26,6100.0,6,FY26,Q3
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q1-FY25,5806.0,0,FY25,Q1
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q2-FY25,6918.0,1,FY25,Q2
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q3-FY25,6304.0,2,FY25,Q3
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q4-FY25,7118.0,3,FY25,Q4
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q1-FY26,5806.0,4,FY26,Q1
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q2-FY26,5090.0,5,FY26,Q2
PAT (INR Crs),PRIVATE BANK,AXISBANK,Q3-FY26,6490.0,6,FY26,Q3
PCR,PRIVATE BANK,AXISBANK,Q1-FY25,0.78,0,FY25,Q1
PCR,PRIVATE BANK,AXISBANK,Q2-FY25,0.77,1,FY25,Q2
PCR,PRIVATE BANK,AXISBANK,Q3-FY25,0.76,2,FY25,Q3
PCR,PRIVATE BANK,AXISBANK,Q4-FY25,0.75,3,FY25,Q4
PCR,PRIVATE BANK,AXISBANK,Q1-FY26,0.71,4,FY26,Q1
PCR,PRIVATE BANK,AXISBANK,Q2-FY26,0.7,5,FY26,Q2
PCR,PRIVATE BANK,AXISBANK,Q3-FY26,0.7,6,FY26,Q3
RoA,PRIVATE BANK,AXISBANK,Q1-FY25,0.0147,0,FY25,Q1
RoA,PRIVATE BANK,AXISBANK,Q2-FY25,0.0192,1,FY25,Q2
RoA,PRIVATE BANK,AXISBANK,Q3-FY25,0.0164,2,FY25,Q3
RoA,PRIVATE BANK,AXISBANK,Q4-FY25,0.0182,3,FY25,Q4
RoA,PRIVATE BANK,AXISBANK,Q1-FY26,0.0145,4,FY26,Q1
RoA,PRIVATE BANK,AXISBANK,Q2-FY26,0.0123,5,FY26,Q2
RoA,PRIVATE BANK,AXISBANK,Q3-FY26,0.0149,6,FY26,Q3
RoE,PRIVATE BANK,AXISBANK,Q1-FY25,0.1314,0,FY25,Q1
RoE,PRIVATE BANK,AXISBANK,Q2-FY25,0.1808,1,FY25,Q2
RoE,PRIVATE BANK,AXISBANK,Q3-FY25,0.1537,2,FY25,Q3
RoE,PRIVATE BANK,AXISBANK,Q4-FY25,,3,FY25,Q4
RoE,PRIVATE BANK,AXISBANK,Q1-FY26,,4,FY26,Q1
RoE,PRIVATE BANK,AXISBANK,Q2-FY26,0.1106,5,FY26,Q2
RoE,PRIVATE BANK,AXISBANK,Q3-FY26,0.1368,6,FY26,Q3
Yields,PRIVATE BANK,AXISBANK,Q1-FY25,0.085,0,FY25,Q1
Yields,PRIVATE BANK,AXISBANK,Q2-FY25,,1,FY25,Q2
Yields,PRIVATE BANK,AXISBANK,Q3-FY25,,2,FY25,Q3
Yields,PRIVATE BANK,AXISBANK,Q4-FY25,,3,FY25,Q4
Yields,PRIVATE BANK,AXISBANK,Q1-FY26,,4,FY26,Q1
Yields,PRIVATE BANK,AXISBANK,Q2-FY26,,5,FY26,Q2
Yields,PRIVATE BANK,AXISBANK,Q3-FY26,,6,FY26,Q3
Advances (INR Crs),PSU BANK,BANKBARODA,Q1-FY25,1071681.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,BANKBARODA,Q2-FY25,1143000.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,BANKBARODA,Q3-FY25,1173034.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,BANKBARODA,Q4-FY25,1230461.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,BANKBARODA,Q1-FY26,1207056.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,BANKBARODA,Q2-FY26,1279100.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,BANKBARODA,Q3-FY26,1344904.0,6,FY26,Q3
CAR,PSU BANK,BANKBARODA,Q1-FY25,0.1682,0,FY25,Q1
CAR,PSU BANK,BANKBARODA,Q2-FY25,0.1626,1,FY25,Q2
CAR,PSU BANK,BANKBARODA,Q3-FY25,0.1596,2,FY25,Q3
CAR,PSU BANK,BANKBARODA,Q4-FY25,0.1719,3,FY25,Q4
CAR,PSU BANK,BANKBARODA,Q1-FY26,0.1761,4,FY26,Q1
CAR,PSU BANK,BANKBARODA,Q2-FY26,0.1665,5,FY26,Q2
CAR,PSU BANK,BANKBARODA,Q3-FY26,0.1529,6,FY26,Q3
CASA,PSU BANK,BANKBARODA,Q1-FY25,0.4062,0,FY25,Q1
CASA,PSU BANK,BANKBARODA,Q2-FY25,0.3984,1,FY25,Q2
CASA,PSU BANK,BANKBARODA,Q3-FY25,0.3933,2,FY25,Q3
CASA,PSU BANK,BANKBARODA,Q4-FY25,0.3997,3,FY25,Q4
CASA,PSU BANK,BANKBARODA,Q1-FY26,0.3933,4,FY26,Q1
CASA,PSU BANK,BANKBARODA,Q2-FY26,0.3842,5,FY26,Q2
CASA,PSU BANK,BANKBARODA,Q3-FY26,0.3845,6,FY26,Q3
CoFs,PSU BANK,BANKBARODA,Q1-FY25,0.0506,0,FY25,Q1
CoFs,PSU BANK,BANKBARODA,Q2-FY25,0.0512,1,FY25,Q2
CoFs,PSU BANK,BANKBARODA,Q3-FY25,0.0508,2,FY25,Q3
CoFs,PSU BANK,BANKBARODA,Q4-FY25,0.0512,3,FY25,Q4
CoFs,PSU BANK,BANKBARODA,Q1-FY26,0.0505,4,FY26,Q1
CoFs,PSU BANK,BANKBARODA,Q2-FY26,0.0491,5,FY26,Q2
CoFs,PSU BANK,BANKBARODA,Q3-FY26,0.0475,6,FY26,Q3
Cost to Income,PSU BANK,BANKBARODA,Q1-FY25,0.4917,0,FY25,Q1
Cost to Income,PSU BANK,BANKBARODA,Q2-FY25,0.436,1,FY25,Q2
Cost to Income,PSU BANK,BANKBARODA,Q3-FY25,0.4953,2,FY25,Q3
Cost to Income,PSU BANK,BANKBARODA,Q4-FY25,0.4989,3,FY25,Q4
Cost to Income,PSU BANK,BANKBARODA,Q1-FY26,0.4887,4,FY26,Q1
Cost to Income,PSU BANK,BANKBARODA,Q2-FY26,0.5102,5,FY26,Q2
Cost to Income,PSU BANK,BANKBARODA,Q3-FY26,0.521,6,FY26,Q3
Credit Cost,PSU BANK,BANKBARODA,Q1-FY25,0.0047,0,FY25,Q1
Credit Cost,PSU BANK,BANKBARODA,Q2-FY25,0.0065,1,FY25,Q2
Credit Cost,PSU BANK,BANKBARODA,Q3-FY25,0.009,2,FY25,Q3
Credit Cost,PSU BANK,BANKBARODA,Q4-FY25,0.01,3,FY25,Q4
Credit Cost,PSU BANK,BANKBARODA,Q1-FY26,0.0116,4,FY26,Q1
Credit Cost,PSU BANK,BANKBARODA,Q2-FY26,0.0091,5,FY26,Q2
Credit Cost,PSU BANK,BANKBARODA,Q3-FY26,0.0086,6,FY26,Q3
Deposits (INR Crs),PSU BANK,BANKBARODA,Q1-FY25,1306994.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,BANKBARODA,Q2-FY25,1372600.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,BANKBARODA,Q3-FY25,1402909.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,BANKBARODA,Q4-FY25,1472035.0,3,FY25,Q4
Deposits (INR Crs),PSU BANK,BANKBARODA,Q1-FY26,1435634.0,4,FY26,Q1
Deposits (INR Crs),PSU BANK,BANKBARODA,Q2-FY26,1500000.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,BANKBARODA,Q3-FY26,1546749.0,6,FY26,Q3
GNPA,PSU BANK,BANKBARODA,Q1-FY25,0.0288,0,FY25,Q1
GNPA,PSU BANK,BANKBARODA,Q2-FY25,0.025,1,FY25,Q2
GNPA,PSU BANK,BANKBARODA,Q3-FY25,0.0243,2,FY25,Q3
GNPA,PSU BANK,BANKBARODA,Q4-FY25,0.0226,3,FY25,Q4
GNPA,PSU BANK,BANKBARODA,Q1-FY26,0.0228,4,FY26,Q1
GNPA,PSU BANK,BANKBARODA,Q2-FY26,0.0216,5,FY26,Q2
GNPA,PSU BANK,BANKBARODA,Q3-FY26,0.0204,6,FY26,Q3
Leverage,PSU BANK,BANKBARODA,Q1-FY25,,0,FY25,Q1
Leverage,PSU BANK,BANKBARODA,Q2-FY25,,1,FY25,Q2
Leverage,PSU BANK,BANKBARODA,Q3-FY25,,2,FY25,Q3
Leverage,PSU BANK,BANKBARODA,Q4-FY25,13.2,3,FY25,Q4
Leverage,PSU BANK,BANKBARODA,Q1-FY26,15.2,4,FY26,Q1
Leverage,PSU BANK,BANKBARODA,Q2-FY26,,5,FY26,Q2
Leverage,PSU BANK,BANKBARODA,Q3-FY26,,6,FY26,Q3
NII,PSU BANK,BANKBARODA,Q1-FY25,11600.0,0,FY25,Q1
NII,PSU BANK,BANKBARODA,Q2-FY25,11637.0,1,FY25,Q2
NII,PSU BANK,BANKBARODA,Q3-FY25,11786.0,2,FY25,Q3
NII,PSU BANK,BANKBARODA,Q4-FY25,11020.0,3,FY25,Q4
NII,PSU BANK,BANKBARODA,Q1-FY26,11435.0,4,FY26,Q1
NII,PSU BANK,BANKBARODA,Q2-FY26,11954.0,5,FY26,Q2
NII,PSU BANK,BANKBARODA,Q3-FY26,11800.0,6,FY26,Q3
NIMs,PSU BANK,BANKBARODA,Q1-FY25,0.0318,0,FY25,Q1
NIMs,PSU BANK,BANKBARODA,Q2-FY25,0.0311,1,FY25,Q2
NIMs,PSU BANK,BANKBARODA,Q3-FY25,0.0304,2,FY25,Q3
NIMs,PSU BANK,BANKBARODA,Q4-FY25,0.0286,3,FY25,Q4
NIMs,PSU BANK,BANKBARODA,Q1-FY26,0.0291,4,FY26,Q1
NIMs,PSU BANK,BANKBARODA,Q2-FY26,0.0296,5,FY26,Q2
NIMs,PSU BANK,BANKBARODA,Q3-FY26,0.0279,6,FY26,Q3
NNPA,PSU BANK,BANKBARODA,Q1-FY25,0.0069,0,FY25,Q1
NNPA,PSU BANK,BANKBARODA,Q2-FY25,0.006,1,FY25,Q2
NNPA,PSU BANK,BANKBARODA,Q3-FY25,0.0059,2,FY25,Q3
NNPA,PSU BANK,BANKBARODA,Q4-FY25,0.0058,3,FY25,Q4
NNPA,PSU BANK,BANKBARODA,Q1-FY26,0.006,4,FY26,Q1
NNPA,PSU BANK,BANKBARODA,Q2-FY26,0.0057,5,FY26,Q2
NNPA,PSU BANK,BANKBARODA,Q3-FY26,0.0057,6,FY26,Q3
Opex to AUM,PSU BANK,BANKBARODA,Q1-FY25,,0,FY25,Q1
Opex to AUM,PSU BANK,BANKBARODA,Q2-FY25,,1,FY25,Q2
Opex to AUM,PSU BANK,BANKBARODA,Q3-FY25,,2,FY25,Q3
Opex to AUM,PSU BANK,BANKBARODA,Q4-FY25,,3,FY25,Q4
Opex to AUM,PSU BANK,BANKBARODA,Q1-FY26,,4,FY26,Q1
Opex to AUM,PSU BANK,BANKBARODA,Q2-FY26,,5,FY26,Q2
Opex to AUM,PSU BANK,BANKBARODA,Q3-FY26,,6,FY26,Q3
Other Income,PSU BANK,BANKBARODA,Q1-FY25,2479.0,0,FY25,Q1
Other Income,PSU BANK,BANKBARODA,Q2-FY25,5181.0,1,FY25,Q2
Other Income,PSU BANK,BANKBARODA,Q3-FY25,3400.0,2,FY25,Q3
Other Income,PSU BANK,BANKBARODA,Q4-FY25,5210.0,3,FY25,Q4
Other Income,PSU BANK,BANKBARODA,Q1-FY26,4675.0,4,FY26,Q1
Other Income,PSU BANK,BANKBARODA,Q2-FY26,3515.0,5,FY26,Q2
Other Income,PSU BANK,BANKBARODA,Q3-FY26,3600.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,BANKBARODA,Q1-FY25,4458.0,0,FY25,Q1
PAT (INR Crs),PSU BANK,BANKBARODA,Q2-FY25,5238.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,BANKBARODA,Q3-FY25,4837.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,BANKBARODA,Q4-FY25,5048.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,BANKBARODA,Q1-FY26,4541.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,BANKBARODA,Q2-FY26,4809.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,BANKBARODA,Q3-FY26,5055.0,6,FY26,Q3
PCR,PSU BANK,BANKBARODA,Q1-FY25,0.9332,0,FY25,Q1
PCR,PSU BANK,BANKBARODA,Q2-FY25,0.7631,1,FY25,Q2
PCR,PSU BANK,BANKBARODA,Q3-FY25,0.9351,2,FY25,Q3
PCR,PSU BANK,BANKBARODA,Q4-FY25,0.9329,3,FY25,Q4
PCR,PSU BANK,BANKBARODA,Q1-FY26,0.9318,4,FY26,Q1
PCR,PSU BANK,BANKBARODA,Q2-FY26,0.9321,5,FY26,Q2
PCR,PSU BANK,BANKBARODA,Q3-FY26,0.9273,6,FY26,Q3
RoA,PSU BANK,BANKBARODA,Q1-FY25,0.0113,0,FY25,Q1
RoA,PSU BANK,BANKBARODA,Q2-FY25,0.013,1,FY25,Q2
RoA,PSU BANK,BANKBARODA,Q3-FY25,0.0115,2,FY25,Q3
RoA,PSU BANK,BANKBARODA,Q4-FY25,0.0116,3,FY25,Q4
RoA,PSU BANK,BANKBARODA,Q1-FY26,0.0103,4,FY26,Q1
RoA,PSU BANK,BANKBARODA,Q2-FY26,0.0107,5,FY26,Q2
RoA,PSU BANK,BANKBARODA,Q3-FY26,0.0109,6,FY26,Q3
RoE,PSU BANK,BANKBARODA,Q1-FY25,0.1745,0,FY25,Q1
RoE,PSU BANK,BANKBARODA,Q2-FY25,0.1922,1,FY25,Q2
RoE,PSU BANK,BANKBARODA,Q3-FY25,0.1701,2,FY25,Q3
RoE,PSU BANK,BANKBARODA,Q4-FY25,0.1749,3,FY25,Q4
RoE,PSU BANK,BANKBARODA,Q1-FY26,0.1505,4,FY26,Q1
RoE,PSU BANK,BANKBARODA,Q2-FY26,0.1537,5,FY26,Q2
RoE,PSU BANK,BANKBARODA,Q3-FY26,0.1559,6,FY26,Q3
Yields,PSU BANK,BANKBARODA,Q1-FY25,0.0855,0,FY25,Q1
Yields,PSU BANK,BANKBARODA,Q2-FY25,0.0848,1,FY25,Q2
Yields,PSU BANK,BANKBARODA,Q3-FY25,0.0835,2,FY25,Q3
Yields,PSU BANK,BANKBARODA,Q4-FY25,0.0821,3,FY25,Q4
Yields,PSU BANK,BANKBARODA,Q1-FY26,0.0809,4,FY26,Q1
Yields,PSU BANK,BANKBARODA,Q2-FY26,0.0781,5,FY26,Q2
Yields,PSU BANK,BANKBARODA,Q3-FY26,0.0756,6,FY26,Q3
Advances (INR Crs),PSU BANK,BANKINDIA,Q1-FY25,600264.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,BANKINDIA,Q2-FY25,621919.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,BANKINDIA,Q3-FY25,651507.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,BANKINDIA,Q4-FY25,666047.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,BANKINDIA,Q1-FY26,672444.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,BANKINDIA,Q2-FY26,709145.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,BANKINDIA,Q3-FY26,740314.0,6,FY26,Q3
CAR,PSU BANK,BANKINDIA,Q1-FY25,0.1618,0,FY25,Q1
CAR,PSU BANK,BANKINDIA,Q2-FY25,0.1663,1,FY25,Q2
CAR,PSU BANK,BANKINDIA,Q3-FY25,0.16,2,FY25,Q3
CAR,PSU BANK,BANKINDIA,Q4-FY25,0.1777,3,FY25,Q4
CAR,PSU BANK,BANKINDIA,Q1-FY26,0.1739,4,FY26,Q1
CAR,PSU BANK,BANKINDIA,Q2-FY26,0.1669,5,FY26,Q2
CAR,PSU BANK,BANKINDIA,Q3-FY26,0.1709,6,FY26,Q3
CASA,PSU BANK,BANKINDIA,Q1-FY25,0.4268,0,FY25,Q1
CASA,PSU BANK,BANKINDIA,Q2-FY25,0.4118,1,FY25,Q2
CASA,PSU BANK,BANKINDIA,Q3-FY25,0.4105,2,FY25,Q3
CASA,PSU BANK,BANKINDIA,Q4-FY25,0.4029,3,FY25,Q4
CASA,PSU BANK,BANKINDIA,Q1-FY26,0.3988,4,FY26,Q1
CASA,PSU BANK,BANKINDIA,Q2-FY26,0.3939,5,FY26,Q2
CASA,PSU BANK,BANKINDIA,Q3-FY26,0.3797,6,FY26,Q3
CoFs,PSU BANK,BANKINDIA,Q1-FY25,0.0481,0,FY25,Q1
CoFs,PSU BANK,BANKINDIA,Q2-FY25,0.0494,1,FY25,Q2
CoFs,PSU BANK,BANKINDIA,Q3-FY25,0.0481,2,FY25,Q3
CoFs,PSU BANK,BANKINDIA,Q4-FY25,0.0473,3,FY25,Q4
CoFs,PSU BANK,BANKINDIA,Q1-FY26,0.0466,4,FY26,Q1
CoFs,PSU BANK,BANKINDIA,Q2-FY26,0.0484,5,FY26,Q2
CoFs,PSU BANK,BANKINDIA,Q3-FY26,0.0457,6,FY26,Q3
Cost to Income,PSU BANK,BANKINDIA,Q1-FY25,0.5147155866437905,0,FY25,Q1
Cost to Income,PSU BANK,BANKINDIA,Q2-FY25,0.5122,1,FY25,Q2
Cost to Income,PSU BANK,BANKINDIA,Q3-FY25,0.5263,2,FY25,Q3
Cost to Income,PSU BANK,BANKINDIA,Q4-FY25,0.485196501949215,3,FY25,Q4
Cost to Income,PSU BANK,BANKINDIA,Q1-FY26,0.5131163468545057,4,FY26,Q1
Cost to Income,PSU BANK,BANKINDIA,Q2-FY26,0.5302,5,FY26,Q2
Cost to Income,PSU BANK,BANKINDIA,Q3-FY26,0.5202,6,FY26,Q3
Credit Cost,PSU BANK,BANKINDIA,Q1-FY25,0.0085,0,FY25,Q1
Credit Cost,PSU BANK,BANKINDIA,Q2-FY25,0.0097,1,FY25,Q2
Credit Cost,PSU BANK,BANKINDIA,Q3-FY25,0.0039,2,FY25,Q3
Credit Cost,PSU BANK,BANKINDIA,Q4-FY25,0.0084,3,FY25,Q4
Credit Cost,PSU BANK,BANKINDIA,Q1-FY26,0.0068,4,FY26,Q1
Credit Cost,PSU BANK,BANKINDIA,Q2-FY26,0.0028,5,FY26,Q2
Credit Cost,PSU BANK,BANKINDIA,Q3-FY26,0.0034,6,FY26,Q3
Deposits (INR Crs),PSU BANK,BANKINDIA,Q1-FY25,764396.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,BANKINDIA,Q2-FY25,775181.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,BANKINDIA,Q3-FY25,794788.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,BANKINDIA,Q4-FY25,816541.0,3,FY25,Q4
Deposits (INR Crs),PSU BANK,BANKINDIA,Q1-FY26,833698.0,4,FY26,Q1
Deposits (INR Crs),PSU BANK,BANKINDIA,Q2-FY26,853301.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,BANKINDIA,Q3-FY26,887288.0,6,FY26,Q3
GNPA,PSU BANK,BANKINDIA,Q1-FY25,0.0462,0,FY25,Q1
GNPA,PSU BANK,BANKINDIA,Q2-FY25,0.0442,1,FY25,Q2
GNPA,PSU BANK,BANKINDIA,Q3-FY25,0.0369,2,FY25,Q3
GNPA,PSU BANK,BANKINDIA,Q4-FY25,0.0327,3,FY25,Q4
GNPA,PSU BANK,BANKINDIA,Q1-FY26,0.0292,4,FY26,Q1
GNPA,PSU BANK,BANKINDIA,Q2-FY26,0.0254,5,FY26,Q2
GNPA,PSU BANK,BANKINDIA,Q3-FY26,0.0226,6,FY26,Q3
Leverage,PSU BANK,BANKINDIA,Q1-FY25,12.289855072463768,0,FY25,Q1
Leverage,PSU BANK,BANKINDIA,Q2-FY25,,1,FY25,Q2
Leverage,PSU BANK,BANKINDIA,Q3-FY25,,2,FY25,Q3
Leverage,PSU BANK,BANKINDIA,Q4-FY25,11.961783439490446,3,FY25,Q4
Leverage,PSU BANK,BANKINDIA,Q1-FY26,12.164556962025316,4,FY26,Q1
Leverage,PSU BANK,BANKINDIA,Q2-FY26,,5,FY26,Q2
Leverage,PSU BANK,BANKINDIA,Q3-FY26,,6,FY26,Q3
NII,PSU BANK,BANKINDIA,Q1-FY25,6275.0,0,FY25,Q1
NII,PSU BANK,BANKINDIA,Q2-FY25,5886.0,1,FY25,Q2
NII,PSU BANK,BANKINDIA,Q3-FY25,6070.0,2,FY25,Q3
NII,PSU BANK,BANKINDIA,Q4-FY25,6063.0,3,FY25,Q4
NII,PSU BANK,BANKINDIA,Q1-FY26,6068.0,4,FY26,Q1
NII,PSU BANK,BANKINDIA,Q2-FY26,5912.0,5,FY26,Q2
NII,PSU BANK,BANKINDIA,Q3-FY26,6461.0,6,FY26,Q3
NIMs,PSU BANK,BANKINDIA,Q1-FY25,0.0307,0,FY25,Q1
NIMs,PSU BANK,BANKINDIA,Q2-FY25,0.0281,1,FY25,Q2
NIMs,PSU BANK,BANKINDIA,Q3-FY25,0.028,2,FY25,Q3
NIMs,PSU BANK,BANKINDIA,Q4-FY25,0.0261,3,FY25,Q4
NIMs,PSU BANK,BANKINDIA,Q1-FY26,0.0255,4,FY26,Q1
NIMs,PSU BANK,BANKINDIA,Q2-FY26,0.0241,5,FY26,Q2
NIMs,PSU BANK,BANKINDIA,Q3-FY26,0.0257,6,FY26,Q3
NNPA,PSU BANK,BANKINDIA,Q1-FY25,0.0099,0,FY25,Q1
NNPA,PSU BANK,BANKINDIA,Q2-FY25,0.0094,1,FY25,Q2
NNPA,PSU BANK,BANKINDIA,Q3-FY25,0.0085,2,FY25,Q3
NNPA,PSU BANK,BANKINDIA,Q4-FY25,0.0082,3,FY25,Q4
NNPA,PSU BANK,BANKINDIA,Q1-FY26,0.0075,4,FY26,Q1
NNPA,PSU BANK,BANKINDIA,Q2-FY26,0.0065,5,FY26,Q2
NNPA,PSU BANK,BANKINDIA,Q3-FY26,0.006,6,FY26,Q3
Opex to AUM,PSU BANK,BANKINDIA,Q1-FY25,,0,FY25,Q1
Opex to AUM,PSU BANK,BANKINDIA,Q2-FY25,,1,FY25,Q2
Opex to AUM,PSU BANK,BANKINDIA,Q3-FY25,,2,FY25,Q3
Opex to AUM,PSU BANK,BANKINDIA,Q4-FY25,,3,FY25,Q4
Opex to AUM,PSU BANK,BANKINDIA,Q1-FY26,,4,FY26,Q1
Opex to AUM,PSU BANK,BANKINDIA,Q2-FY26,,5,FY26,Q2
Opex to AUM,PSU BANK,BANKINDIA,Q3-FY26,,6,FY26,Q3
Other Income,PSU BANK,BANKINDIA,Q1-FY25,1302.0,0,FY25,Q1
Other Income,PSU BANK,BANKINDIA,Q2-FY25,2518.0,1,FY25,Q2
Other Income,PSU BANK,BANKINDIA,Q3-FY25,1747.0,2,FY25,Q3
Other Income,PSU BANK,BANKINDIA,Q4-FY25,3428.0,3,FY25,Q4
Other Income,PSU BANK,BANKINDIA,Q1-FY26,2166.0,4,FY26,Q1
Other Income,PSU BANK,BANKINDIA,Q2-FY26,2220.0,5,FY26,Q2
Other Income,PSU BANK,BANKINDIA,Q3-FY26,2279.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,BANKINDIA,Q1-FY25,1703.0,0,FY25,Q1
PAT (INR Crs),PSU BANK,BANKINDIA,Q2-FY25,2374.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,BANKINDIA,Q3-FY25,2517.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,BANKINDIA,Q4-FY25,2626.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,BANKINDIA,Q1-FY26,2252.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,BANKINDIA,Q2-FY26,2555.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,BANKINDIA,Q3-FY26,2705.0,6,FY26,Q3
PCR,PSU BANK,BANKINDIA,Q1-FY25,0.9211,0,FY25,Q1
PCR,PSU BANK,BANKINDIA,Q2-FY25,0.9222,1,FY25,Q2
PCR,PSU BANK,BANKINDIA,Q3-FY25,0.9248,2,FY25,Q3
PCR,PSU BANK,BANKINDIA,Q4-FY25,0.9239,3,FY25,Q4
PCR,PSU BANK,BANKINDIA,Q1-FY26,0.9294,4,FY26,Q1
PCR,PSU BANK,BANKINDIA,Q2-FY26,0.9339,5,FY26,Q2
PCR,PSU BANK,BANKINDIA,Q3-FY26,0.936,6,FY26,Q3
RoA,PSU BANK,BANKINDIA,Q1-FY25,0.007,0,FY25,Q1
RoA,PSU BANK,BANKINDIA,Q2-FY25,0.0094,1,FY25,Q2
RoA,PSU BANK,BANKINDIA,Q3-FY25,0.0096,2,FY25,Q3
RoA,PSU BANK,BANKINDIA,Q4-FY25,0.0098,3,FY25,Q4
RoA,PSU BANK,BANKINDIA,Q1-FY26,0.0082,4,FY26,Q1
RoA,PSU BANK,BANKINDIA,Q2-FY26,0.0091,5,FY26,Q2
RoA,PSU BANK,BANKINDIA,Q3-FY26,0.0096,6,FY26,Q3
RoE,PSU BANK,BANKINDIA,Q1-FY25,0.1348,0,FY25,Q1
RoE,PSU BANK,BANKINDIA,Q2-FY25,0.1633,1,FY25,Q2
RoE,PSU BANK,BANKINDIA,Q3-FY25,0.1653,2,FY25,Q3
RoE,PSU BANK,BANKINDIA,Q4-FY25,0.1641,3,FY25,Q4
RoE,PSU BANK,BANKINDIA,Q1-FY26,0.1355,4,FY26,Q1
RoE,PSU BANK,BANKINDIA,Q2-FY26,0.1494,5,FY26,Q2
RoE,PSU BANK,BANKINDIA,Q3-FY26,0.1534,6,FY26,Q3
Yields,PSU BANK,BANKINDIA,Q1-FY25,0.086,0,FY25,Q1
Yields,PSU BANK,BANKINDIA,Q2-FY25,0.0843,1,FY25,Q2
Yields,PSU BANK,BANKINDIA,Q3-FY25,0.0855,2,FY25,Q3
Yields,PSU BANK,BANKINDIA,Q4-FY25,0.0827,3,FY25,Q4
Yields,PSU BANK,BANKINDIA,Q1-FY26,0.0801,4,FY26,Q1
Yields,PSU BANK,BANKINDIA,Q2-FY26,0.0781,5,FY26,Q2
Yields,PSU BANK,BANKINDIA,Q3-FY26,0.0781,6,FY26,Q3
Advances (INR Crs),PSU BANK,CANBK,Q1-FY25,975183.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,CANBK,Q2-FY25,1011997.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,CANBK,Q3-FY25,1011997.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,CANBK,Q4-FY25,1073332.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,CANBK,Q1-FY26,1096329.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,CANBK,Q2-FY26,1151041.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,CANBK,Q3-FY26,1192326.0,6,FY26,Q3
CAR,PSU BANK,CANBK,Q1-FY25,0.1628,0,FY25,Q1
CAR,PSU BANK,CANBK,Q2-FY25,0.1657,1,FY25,Q2
CAR,PSU BANK,CANBK,Q3-FY25,0.1644,2,FY25,Q3
CAR,PSU BANK,CANBK,Q4-FY25,0.1633,3,FY25,Q4
CAR,PSU BANK,CANBK,Q1-FY26,0.1652,4,FY26,Q1
CAR,PSU BANK,CANBK,Q2-FY26,0.162,5,FY26,Q2
CAR,PSU BANK,CANBK,Q3-FY26,0.165,6,FY26,Q3
CASA,PSU BANK,CANBK,Q1-FY25,0.2853932584269663,0,FY25,Q1
CASA,PSU BANK,CANBK,Q2-FY25,,1,FY25,Q2
CASA,PSU BANK,CANBK,Q3-FY25,,2,FY25,Q3
CASA,PSU BANK,CANBK,Q4-FY25,0.2847632120796156,3,FY25,Q4
CASA,PSU BANK,CANBK,Q1-FY26,0.269550408719346,4,FY26,Q1
CASA,PSU BANK,CANBK,Q2-FY26,0.3069,5,FY26,Q2
CASA,PSU BANK,CANBK,Q3-FY26,,6,FY26,Q3
CoFs,PSU BANK,CANBK,Q1-FY25,0.0525,0,FY25,Q1
CoFs,PSU BANK,CANBK,Q2-FY25,0.0526,1,FY25,Q2
CoFs,PSU BANK,CANBK,Q3-FY25,0.0528,2,FY25,Q3
CoFs,PSU BANK,CANBK,Q4-FY25,0.0528,3,FY25,Q4
CoFs,PSU BANK,CANBK,Q1-FY26,0.0527,4,FY26,Q1
CoFs,PSU BANK,CANBK,Q2-FY26,0.0521,5,FY26,Q2
CoFs,PSU BANK,CANBK,Q3-FY26,0.0518,6,FY26,Q3
Cost to Income,PSU BANK,CANBK,Q1-FY25,0.4742,0,FY25,Q1
Cost to Income,PSU BANK,CANBK,Q2-FY25,0.4755,1,FY25,Q2
Cost to Income,PSU BANK,CANBK,Q3-FY25,0.5037,2,FY25,Q3
Cost to Income,PSU BANK,CANBK,Q4-FY25,0.4755,3,FY25,Q4
Cost to Income,PSU BANK,CANBK,Q1-FY26,0.4677,4,FY26,Q1
Cost to Income,PSU BANK,CANBK,Q2-FY26,0.4697,5,FY26,Q2
Cost to Income,PSU BANK,CANBK,Q3-FY26,0.4683,6,FY26,Q3
Credit Cost,PSU BANK,CANBK,Q1-FY25,0.009,0,FY25,Q1
Credit Cost,PSU BANK,CANBK,Q2-FY25,0.0097,1,FY25,Q2
Credit Cost,PSU BANK,CANBK,Q3-FY25,0.0064,2,FY25,Q3
Credit Cost,PSU BANK,CANBK,Q4-FY25,0.0092,3,FY25,Q4
Credit Cost,PSU BANK,CANBK,Q1-FY26,0.0072,4,FY26,Q1
Credit Cost,PSU BANK,CANBK,Q2-FY26,0.0068,5,FY26,Q2
Credit Cost,PSU BANK,CANBK,Q3-FY26,0.0064,6,FY26,Q3
Deposits (INR Crs),PSU BANK,CANBK,Q1-FY25,1335167.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,CANBK,Q2-FY25,1347347.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,CANBK,Q3-FY25,1347347.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,CANBK,Q4-FY25,1456883.0,3,FY25,Q4
Deposits (INR Crs),PSU BANK,CANBK,Q1-FY26,1467655.0,4,FY26,Q1
Deposits (INR Crs),PSU BANK,CANBK,Q2-FY26,1527922.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,CANBK,Q3-FY26,1521268.0,6,FY26,Q3
GNPA,PSU BANK,CANBK,Q1-FY25,0.0414,0,FY25,Q1
GNPA,PSU BANK,CANBK,Q2-FY25,0.0373,1,FY25,Q2
GNPA,PSU BANK,CANBK,Q3-FY25,0.0334,2,FY25,Q3
GNPA,PSU BANK,CANBK,Q4-FY25,0.0294,3,FY25,Q4
GNPA,PSU BANK,CANBK,Q1-FY26,0.0269,4,FY26,Q1
GNPA,PSU BANK,CANBK,Q2-FY26,0.0235,5,FY26,Q2
GNPA,PSU BANK,CANBK,Q3-FY26,0.0208,6,FY26,Q3
Leverage,PSU BANK,CANBK,Q1-FY25,,0,FY25,Q1
Leverage,PSU BANK,CANBK,Q2-FY25,,1,FY25,Q2
Leverage,PSU BANK,CANBK,Q3-FY25,,2,FY25,Q3
Leverage,PSU BANK,CANBK,Q4-FY25,,3,FY25,Q4
Leverage,PSU BANK,CANBK,Q1-FY26,,4,FY26,Q1
Leverage,PSU BANK,CANBK,Q2-FY26,,5,FY26,Q2
Leverage,PSU BANK,CANBK,Q3-FY26,,6,FY26,Q3
NII,PSU BANK,CANBK,Q1-FY25,9009.0,0,FY25,Q1
NII,PSU BANK,CANBK,Q2-FY25,9315.0,1,FY25,Q2
NII,PSU BANK,CANBK,Q3-FY25,9149.0,2,FY25,Q3
NII,PSU BANK,CANBK,Q4-FY25,9442.0,3,FY25,Q4
NII,PSU BANK,CANBK,Q1-FY26,9166.0,4,FY26,Q1
NII,PSU BANK,CANBK,Q2-FY26,9141.0,5,FY26,Q2
NII,PSU BANK,CANBK,Q3-FY26,9252.0,6,FY26,Q3
NIMs,PSU BANK,CANBK,Q1-FY25,0.029,0,FY25,Q1
NIMs,PSU BANK,CANBK,Q2-FY25,0.0286,1,FY25,Q2
NIMs,PSU BANK,CANBK,Q3-FY25,0.0283,2,FY25,Q3
NIMs,PSU BANK,CANBK,Q4-FY25,0.0273,3,FY25,Q4
NIMs,PSU BANK,CANBK,Q1-FY26,0.0255,4,FY26,Q1
NIMs,PSU BANK,CANBK,Q2-FY26,0.025,5,FY26,Q2
NIMs,PSU BANK,CANBK,Q3-FY26,0.0245,6,FY26,Q3
NNPA,PSU BANK,CANBK,Q1-FY25,0.0124,0,FY25,Q1
NNPA,PSU BANK,CANBK,Q2-FY25,0.0099,1,FY25,Q2
NNPA,PSU BANK,CANBK,Q3-FY25,0.0089,2,FY25,Q3
NNPA,PSU BANK,CANBK,Q4-FY25,0.007,3,FY25,Q4
NNPA,PSU BANK,CANBK,Q1-FY26,0.0063,4,FY26,Q1
NNPA,PSU BANK,CANBK,Q2-FY26,0.0054,5,FY26,Q2
NNPA,PSU BANK,CANBK,Q3-FY26,0.0045,6,FY26,Q3
Opex to AUM,PSU BANK,CANBK,Q1-FY25,,0,FY25,Q1
Opex to AUM,PSU BANK,CANBK,Q2-FY25,,1,FY25,Q2
Opex to AUM,PSU BANK,CANBK,Q3-FY25,,2,FY25,Q3
Opex to AUM,PSU BANK,CANBK,Q4-FY25,,3,FY25,Q4
Opex to AUM,PSU BANK,CANBK,Q1-FY26,,4,FY26,Q1
Opex to AUM,PSU BANK,CANBK,Q2-FY26,,5,FY26,Q2
Opex to AUM,PSU BANK,CANBK,Q3-FY26,,6,FY26,Q3
Other Income,PSU BANK,CANBK,Q1-FY25,5319.0,0,FY25,Q1
Other Income,PSU BANK,CANBK,Q2-FY25,4981.0,1,FY25,Q2
Other Income,PSU BANK,CANBK,Q3-FY25,5802.0,2,FY25,Q3
Other Income,PSU BANK,CANBK,Q4-FY25,6351.0,3,FY25,Q4
Other Income,PSU BANK,CANBK,Q1-FY26,7060.0,4,FY26,Q1
Other Income,PSU BANK,CANBK,Q2-FY26,7054.0,5,FY26,Q2
Other Income,PSU BANK,CANBK,Q3-FY26,7900.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,CANBK,Q1-FY25,4752.0,0,FY25,Q1
PAT (INR Crs),PSU BANK,CANBK,Q2-FY25,4014.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,CANBK,Q3-FY25,4104.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,CANBK,Q4-FY25,5004.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,CANBK,Q1-FY26,4752.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,CANBK,Q2-FY26,4774.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,CANBK,Q3-FY26,5155.0,6,FY26,Q3
PCR,PSU BANK,CANBK,Q1-FY25,0.8922,0,FY25,Q1
PCR,PSU BANK,CANBK,Q2-FY25,0.9089,1,FY25,Q2
PCR,PSU BANK,CANBK,Q3-FY25,0.9126,2,FY25,Q3
PCR,PSU BANK,CANBK,Q4-FY25,0.927,3,FY25,Q4
PCR,PSU BANK,CANBK,Q1-FY26,0.9317,4,FY26,Q1
PCR,PSU BANK,CANBK,Q2-FY26,0.9359,5,FY26,Q2
PCR,PSU BANK,CANBK,Q3-FY26,0.9419,6,FY26,Q3
RoA,PSU BANK,CANBK,Q1-FY25,0.0105,0,FY25,Q1
RoA,PSU BANK,CANBK,Q2-FY25,0.0105,1,FY25,Q2
RoA,PSU BANK,CANBK,Q3-FY25,0.0101,2,FY25,Q3
RoA,PSU BANK,CANBK,Q4-FY25,0.0125,3,FY25,Q4
RoA,PSU BANK,CANBK,Q1-FY26,0.0114,4,FY26,Q1
RoA,PSU BANK,CANBK,Q2-FY26,0.011,5,FY26,Q2
RoA,PSU BANK,CANBK,Q3-FY26,0.0113,6,FY26,Q3
RoE,PSU BANK,CANBK,Q1-FY25,0.2088,0,FY25,Q1
RoE,PSU BANK,CANBK,Q2-FY25,0.1978,1,FY25,Q2
RoE,PSU BANK,CANBK,Q3-FY25,0.2106,2,FY25,Q3
RoE,PSU BANK,CANBK,Q4-FY25,0.2323,3,FY25,Q4
RoE,PSU BANK,CANBK,Q1-FY26,0.2105,4,FY26,Q1
RoE,PSU BANK,CANBK,Q2-FY26,0.2,5,FY26,Q2
RoE,PSU BANK,CANBK,Q3-FY26,0.2055,6,FY26,Q3
Yields,PSU BANK,CANBK,Q1-FY25,0.0866,0,FY25,Q1
Yields,PSU BANK,CANBK,Q2-FY25,0.0877,1,FY25,Q2
Yields,PSU BANK,CANBK,Q3-FY25,0.0879,2,FY25,Q3
Yields,PSU BANK,CANBK,Q4-FY25,0.0883,3,FY25,Q4
Yields,PSU BANK,CANBK,Q1-FY26,0.0847,4,FY26,Q1
Yields,PSU BANK,CANBK,Q2-FY26,0.084,5,FY26,Q2
Yields,PSU BANK,CANBK,Q3-FY26,0.0843,6,FY26,Q3
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q1-FY25,24844.0,0,FY25,Q1
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q2-FY25,26602.1,1,FY25,Q2
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q3-FY25,28639.0,2,FY25,Q3
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q4-FY25,31507.1,3,FY25,Q4
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q1-FY26,32552.0,4,FY26,Q1
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q2-FY26,34712.0,5,FY26,Q2
Advances (INR Crs),PRIVATE BANK,CSBBBANK,Q3-FY26,37208.0,6,FY26,Q3
CAR,PRIVATE BANK,CSBBBANK,Q1-FY25,0.2361,0,FY25,Q1
CAR,PRIVATE BANK,CSBBBANK,Q2-FY25,0.2274,1,FY25,Q2
CAR,PRIVATE BANK,CSBBBANK,Q3-FY25,0.2108,2,FY25,Q3
CAR,PRIVATE BANK,CSBBBANK,Q4-FY25,0.2246,3,FY25,Q4
CAR,PRIVATE BANK,CSBBBANK,Q1-FY26,0.2171,4,FY26,Q1
CAR,PRIVATE BANK,CSBBBANK,Q2-FY26,0.2099,5,FY26,Q2
CAR,PRIVATE BANK,CSBBBANK,Q3-FY26,0.1941,6,FY26,Q3
CASA,PRIVATE BANK,CSBBBANK,Q1-FY25,0.249,0,FY25,Q1
CASA,PRIVATE BANK,CSBBBANK,Q2-FY25,0.241,1,FY25,Q2
CASA,PRIVATE BANK,CSBBBANK,Q3-FY25,0.241,2,FY25,Q3
CASA,PRIVATE BANK,CSBBBANK,Q4-FY25,0.242,3,FY25,Q4
CASA,PRIVATE BANK,CSBBBANK,Q1-FY26,0.235,4,FY26,Q1
CASA,PRIVATE BANK,CSBBBANK,Q2-FY26,0.2117,5,FY26,Q2
CASA,PRIVATE BANK,CSBBBANK,Q3-FY26,0.2055,6,FY26,Q3
CoFs,PRIVATE BANK,CSBBBANK,Q1-FY25,0.0608,0,FY25,Q1
CoFs,PRIVATE BANK,CSBBBANK,Q2-FY25,0.0625,1,FY25,Q2
CoFs,PRIVATE BANK,CSBBBANK,Q3-FY25,0.0632,2,FY25,Q3
CoFs,PRIVATE BANK,CSBBBANK,Q4-FY25,0.0657,3,FY25,Q4
CoFs,PRIVATE BANK,CSBBBANK,Q1-FY26,0.0662,4,FY26,Q1
CoFs,PRIVATE BANK,CSBBBANK,Q2-FY26,0.0653,5,FY26,Q2
CoFs,PRIVATE BANK,CSBBBANK,Q3-FY26,0.0646,6,FY26,Q3
Cost to Income,PRIVATE BANK,CSBBBANK,Q1-FY25,0.677,0,FY25,Q1
Cost to Income,PRIVATE BANK,CSBBBANK,Q2-FY25,0.646,1,FY25,Q2
Cost to Income,PRIVATE BANK,CSBBBANK,Q3-FY25,0.629,2,FY25,Q3
Cost to Income,PRIVATE BANK,CSBBBANK,Q4-FY25,0.579,3,FY25,Q4
Cost to Income,PRIVATE BANK,CSBBBANK,Q1-FY26,0.647,4,FY26,Q1
Cost to Income,PRIVATE BANK,CSBBBANK,Q2-FY26,0.6386,5,FY26,Q2
Cost to Income,PRIVATE BANK,CSBBBANK,Q3-FY26,0.6008230452674898,6,FY26,Q3
Credit Cost,PRIVATE BANK,CSBBBANK,Q1-FY25,0.0022,0,FY25,Q1
Credit Cost,PRIVATE BANK,CSBBBANK,Q2-FY25,0.0015,1,FY25,Q2
Credit Cost,PRIVATE BANK,CSBBBANK,Q3-FY25,0.0017,2,FY25,Q3
Credit Cost,PRIVATE BANK,CSBBBANK,Q4-FY25,0.0057,3,FY25,Q4
Credit Cost,PRIVATE BANK,CSBBBANK,Q1-FY26,0.0053,4,FY26,Q1
Credit Cost,PRIVATE BANK,CSBBBANK,Q2-FY26,0.0053,5,FY26,Q2
Credit Cost,PRIVATE BANK,CSBBBANK,Q3-FY26,0.0063,6,FY26,Q3
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q1-FY25,29920.0,0,FY25,Q1
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q2-FY25,31840.2,1,FY25,Q2
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q3-FY25,33407.0,2,FY25,Q3
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q4-FY25,36861.5,3,FY25,Q4
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q1-FY26,35935.0,4,FY26,Q1
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q2-FY26,39651.0,5,FY26,Q2
Deposits (INR Crs),PRIVATE BANK,CSBBBANK,Q3-FY26,40460.0,6,FY26,Q3
GNPA,PRIVATE BANK,CSBBBANK,Q1-FY25,0.017,0,FY25,Q1
GNPA,PRIVATE BANK,CSBBBANK,Q2-FY25,0.017,1,FY25,Q2
GNPA,PRIVATE BANK,CSBBBANK,Q3-FY25,0.016,2,FY25,Q3
GNPA,PRIVATE BANK,CSBBBANK,Q4-FY25,0.016,3,FY25,Q4
GNPA,PRIVATE BANK,CSBBBANK,Q1-FY26,0.018,4,FY26,Q1
GNPA,PRIVATE BANK,CSBBBANK,Q2-FY26,0.0181,5,FY26,Q2
GNPA,PRIVATE BANK,CSBBBANK,Q3-FY26,0.0196,6,FY26,Q3
Leverage,PRIVATE BANK,CSBBBANK,Q1-FY25,,0,FY25,Q1
Leverage,PRIVATE BANK,CSBBBANK,Q2-FY25,,1,FY25,Q2
Leverage,PRIVATE BANK,CSBBBANK,Q3-FY25,,2,FY25,Q3
Leverage,PRIVATE BANK,CSBBBANK,Q4-FY25,,3,FY25,Q4
Leverage,PRIVATE BANK,CSBBBANK,Q1-FY26,,4,FY26,Q1
Leverage,PRIVATE BANK,CSBBBANK,Q2-FY26,,5,FY26,Q2
Leverage,PRIVATE BANK,CSBBBANK,Q3-FY26,,6,FY26,Q3
NII,PRIVATE BANK,CSBBBANK,Q1-FY25,362.0,0,FY25,Q1
NII,PRIVATE BANK,CSBBBANK,Q2-FY25,367.5,1,FY25,Q2
NII,PRIVATE BANK,CSBBBANK,Q3-FY25,375.5,2,FY25,Q3
NII,PRIVATE BANK,CSBBBANK,Q4-FY25,371.3,3,FY25,Q4
NII,PRIVATE BANK,CSBBBANK,Q1-FY26,379.4,4,FY26,Q1
NII,PRIVATE BANK,CSBBBANK,Q2-FY26,424.0,5,FY26,Q2
NII,PRIVATE BANK,CSBBBANK,Q3-FY26,453.0,6,FY26,Q3
NIMs,PRIVATE BANK,CSBBBANK,Q1-FY25,0.0436,0,FY25,Q1
NIMs,PRIVATE BANK,CSBBBANK,Q2-FY25,0.043,1,FY25,Q2
NIMs,PRIVATE BANK,CSBBBANK,Q3-FY25,0.0411,2,FY25,Q3
NIMs,PRIVATE BANK,CSBBBANK,Q4-FY25,0.0375,3,FY25,Q4
NIMs,PRIVATE BANK,CSBBBANK,Q1-FY26,0.0354,4,FY26,Q1
NIMs,PRIVATE BANK,CSBBBANK,Q2-FY26,0.0381,5,FY26,Q2
NIMs,PRIVATE BANK,CSBBBANK,Q3-FY26,0.0386,6,FY26,Q3
NNPA,PRIVATE BANK,CSBBBANK,Q1-FY25,0.0069999999999999,0,FY25,Q1
NNPA,PRIVATE BANK,CSBBBANK,Q2-FY25,0.0069999999999999,1,FY25,Q2
NNPA,PRIVATE BANK,CSBBBANK,Q3-FY25,0.006,2,FY25,Q3
NNPA,PRIVATE BANK,CSBBBANK,Q4-FY25,0.005,3,FY25,Q4
NNPA,PRIVATE BANK,CSBBBANK,Q1-FY26,0.0069999999999999,4,FY26,Q1
NNPA,PRIVATE BANK,CSBBBANK,Q2-FY26,0.0052,5,FY26,Q2
NNPA,PRIVATE BANK,CSBBBANK,Q3-FY26,0.0067,6,FY26,Q3
Opex to AUM,PRIVATE BANK,CSBBBANK,Q1-FY25,,0,FY25,Q1
Opex to AUM,PRIVATE BANK,CSBBBANK,Q2-FY25,,1,FY25,Q2
Opex to AUM,PRIVATE BANK,CSBBBANK,Q3-FY25,,2,FY25,Q3
Opex to AUM,PRIVATE BANK,CSBBBANK,Q4-FY25,,3,FY25,Q4
Opex to AUM,PRIVATE BANK,CSBBBANK,Q1-FY26,,4,FY26,Q1
Opex to AUM,PRIVATE BANK,CSBBBANK,Q2-FY26,,5,FY26,Q2
Opex to AUM,PRIVATE BANK,CSBBBANK,Q3-FY26,,6,FY26,Q3
Other Income,PRIVATE BANK,CSBBBANK,Q1-FY25,171.8,0,FY25,Q1
Other Income,PRIVATE BANK,CSBBBANK,Q2-FY25,199.4,1,FY25,Q2
Other Income,PRIVATE BANK,CSBBBANK,Q3-FY25,219.4,2,FY25,Q3
Other Income,PRIVATE BANK,CSBBBANK,Q4-FY25,381.5,3,FY25,Q4
Other Income,PRIVATE BANK,CSBBBANK,Q1-FY26,244.7,4,FY26,Q1
Other Income,PRIVATE BANK,CSBBBANK,Q2-FY26,349.0,5,FY26,Q2
Other Income,PRIVATE BANK,CSBBBANK,Q3-FY26,276.0,6,FY26,Q3
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q1-FY25,113.3,0,FY25,Q1
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q2-FY25,138.4,1,FY25,Q2
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q3-FY25,151.6,2,FY25,Q3
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q4-FY25,190.4,3,FY25,Q4
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q1-FY26,118.6,4,FY26,Q1
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q2-FY26,160.0,5,FY26,Q2
PAT (INR Crs),PRIVATE BANK,CSBBBANK,Q3-FY26,152.67,6,FY26,Q3
PCR,PRIVATE BANK,CSBBBANK,Q1-FY25,,0,FY25,Q1
PCR,PRIVATE BANK,CSBBBANK,Q2-FY25,,1,FY25,Q2
PCR,PRIVATE BANK,CSBBBANK,Q3-FY25,0.6012,2,FY25,Q3
PCR,PRIVATE BANK,CSBBBANK,Q4-FY25,0.6719,3,FY25,Q4
PCR,PRIVATE BANK,CSBBBANK,Q1-FY26,0.6452,4,FY26,Q1
PCR,PRIVATE BANK,CSBBBANK,Q2-FY26,0.7162,5,FY26,Q2
PCR,PRIVATE BANK,CSBBBANK,Q3-FY26,0.6632,6,FY26,Q3
RoA,PRIVATE BANK,CSBBBANK,Q1-FY25,0.0124,0,FY25,Q1
RoA,PRIVATE BANK,CSBBBANK,Q2-FY25,0.0148,1,FY25,Q2
RoA,PRIVATE BANK,CSBBBANK,Q3-FY25,0.0148,2,FY25,Q3
RoA,PRIVATE BANK,CSBBBANK,Q4-FY25,0.0179,3,FY25,Q4
RoA,PRIVATE BANK,CSBBBANK,Q1-FY26,0.0103,4,FY26,Q1
RoA,PRIVATE BANK,CSBBBANK,Q2-FY26,0.0133,5,FY26,Q2
RoA,PRIVATE BANK,CSBBBANK,Q3-FY26,0.0118,6,FY26,Q3
RoE,PRIVATE BANK,CSBBBANK,Q1-FY25,0.1269,0,FY25,Q1
RoE,PRIVATE BANK,CSBBBANK,Q2-FY25,0.1453,1,FY25,Q2
RoE,PRIVATE BANK,CSBBBANK,Q3-FY25,0.1528,2,FY25,Q3
RoE,PRIVATE BANK,CSBBBANK,Q4-FY25,0.188,3,FY25,Q4
RoE,PRIVATE BANK,CSBBBANK,Q1-FY26,0.109,4,FY26,Q1
RoE,PRIVATE BANK,CSBBBANK,Q2-FY26,0.1446,5,FY26,Q2
RoE,PRIVATE BANK,CSBBBANK,Q3-FY26,0.1338,6,FY26,Q3
Yields,PRIVATE BANK,CSBBBANK,Q1-FY25,0.1125,0,FY25,Q1
Yields,PRIVATE BANK,CSBBBANK,Q2-FY25,0.1121,1,FY25,Q2
Yields,PRIVATE BANK,CSBBBANK,Q3-FY25,0.1106,2,FY25,Q3
Yields,PRIVATE BANK,CSBBBANK,Q4-FY25,0.1098,3,FY25,Q4
Yields,PRIVATE BANK,CSBBBANK,Q1-FY26,0.1073,4,FY26,Q1
Yields,PRIVATE BANK,CSBBBANK,Q2-FY26,0.1095,5,FY26,Q2
Yields,PRIVATE BANK,CSBBBANK,Q3-FY26,0.1082,6,FY26,Q3
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q1-FY25,220800.0,0,FY25,Q1
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q2-FY25,230312.0,1,FY25,Q2
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q3-FY25,244666.0,2,FY25,Q3
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q4-FY25,234800.0,3,FY25,Q4
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q1-FY26,241200.0,4,FY26,Q1
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q2-FY26,244657.0,5,FY26,Q2
Advances (INR Crs),PRIVATE BANK,FEDERALBNK,Q3-FY26,265722.0,6,FY26,Q3
CAR,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.1557,0,FY25,Q1
CAR,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.152,1,FY25,Q2
CAR,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.1516,2,FY25,Q3
CAR,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.164,3,FY25,Q4
CAR,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.1603,4,FY26,Q1
CAR,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.1571,5,FY26,Q2
CAR,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.152,6,FY26,Q3
CASA,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.1,0,FY25,Q1
CASA,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.3007,1,FY25,Q2
CASA,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.3016,2,FY25,Q3
CASA,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.3,3,FY25,Q4
CASA,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.304,4,FY26,Q1
CASA,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.3101,5,FY26,Q2
CASA,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.3207,6,FY26,Q3
CoFs,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.059,0,FY25,Q1
CoFs,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.0593,1,FY25,Q2
CoFs,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0601,2,FY25,Q3
CoFs,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0606,3,FY25,Q4
CoFs,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0585,4,FY26,Q1
CoFs,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.0561,5,FY26,Q2
CoFs,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.055,6,FY26,Q3
Cost to Income,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.5320217011723621,0,FY25,Q1
Cost to Income,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.5301,1,FY25,Q2
Cost to Income,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.5312,2,FY25,Q3
Cost to Income,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.566885381568836,3,FY25,Q4
Cost to Income,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.5488723983999072,4,FY26,Q1
Cost to Income,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.5404,5,FY26,Q2
Cost to Income,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.5392,6,FY26,Q3
Credit Cost,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.0018,0,FY25,Q1
Credit Cost,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.003,1,FY25,Q2
Credit Cost,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0058,2,FY25,Q3
Credit Cost,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0027,3,FY25,Q4
Credit Cost,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0065,4,FY26,Q1
Credit Cost,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.005,5,FY26,Q2
Credit Cost,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.0047,6,FY26,Q3
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q1-FY25,266100.0,0,FY25,Q1
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q2-FY25,269107.0,1,FY25,Q2
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q3-FY25,217214.0,2,FY25,Q3
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q4-FY25,283600.0,3,FY25,Q4
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q1-FY26,287400.0,4,FY26,Q1
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q2-FY26,288920.0,5,FY26,Q2
Deposits (INR Crs),PRIVATE BANK,FEDERALBNK,Q3-FY26,250355.0,6,FY26,Q3
GNPA,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.0209,0,FY25,Q1
GNPA,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.0195,1,FY25,Q2
GNPA,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0195,2,FY25,Q3
GNPA,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0184,3,FY25,Q4
GNPA,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0191,4,FY26,Q1
GNPA,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.0183,5,FY26,Q2
GNPA,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.0172,6,FY26,Q3
Leverage,PRIVATE BANK,FEDERALBNK,Q1-FY25,,0,FY25,Q1
Leverage,PRIVATE BANK,FEDERALBNK,Q2-FY25,,1,FY25,Q2
Leverage,PRIVATE BANK,FEDERALBNK,Q3-FY25,,2,FY25,Q3
Leverage,PRIVATE BANK,FEDERALBNK,Q4-FY25,,3,FY25,Q4
Leverage,PRIVATE BANK,FEDERALBNK,Q1-FY26,8.742857142857142,4,FY26,Q1
Leverage,PRIVATE BANK,FEDERALBNK,Q2-FY26,8.892753623188407,5,FY26,Q2
Leverage,PRIVATE BANK,FEDERALBNK,Q3-FY26,,6,FY26,Q3
NII,PRIVATE BANK,FEDERALBNK,Q1-FY25,2292.0,0,FY25,Q1
NII,PRIVATE BANK,FEDERALBNK,Q2-FY25,2367.0,1,FY25,Q2
NII,PRIVATE BANK,FEDERALBNK,Q3-FY25,2431.0,2,FY25,Q3
NII,PRIVATE BANK,FEDERALBNK,Q4-FY25,2377.4,3,FY25,Q4
NII,PRIVATE BANK,FEDERALBNK,Q1-FY26,2336.8,4,FY26,Q1
NII,PRIVATE BANK,FEDERALBNK,Q2-FY26,2495.0,5,FY26,Q2
NII,PRIVATE BANK,FEDERALBNK,Q3-FY26,2653.0,6,FY26,Q3
NIMs,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.0297,0,FY25,Q1
NIMs,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.0291,1,FY25,Q2
NIMs,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0311,2,FY25,Q3
NIMs,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0287,3,FY25,Q4
NIMs,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0246,4,FY26,Q1
NIMs,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.0269,5,FY26,Q2
NIMs,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.0318,6,FY26,Q3
NNPA,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.0057,0,FY25,Q1
NNPA,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.0049,1,FY25,Q2
NNPA,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0049,2,FY25,Q3
NNPA,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0044,3,FY25,Q4
NNPA,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0048,4,FY26,Q1
NNPA,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.0048,5,FY26,Q2
NNPA,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.0042,6,FY26,Q3
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q1-FY25,,0,FY25,Q1
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q2-FY25,,1,FY25,Q2
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q3-FY25,,2,FY25,Q3
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q4-FY25,,3,FY25,Q4
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q1-FY26,,4,FY26,Q1
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q2-FY26,,5,FY26,Q2
Opex to AUM,PRIVATE BANK,FEDERALBNK,Q3-FY26,,6,FY26,Q3
Other Income,PRIVATE BANK,FEDERALBNK,Q1-FY25,915.0,0,FY25,Q1
Other Income,PRIVATE BANK,FEDERALBNK,Q2-FY25,964.0,1,FY25,Q2
Other Income,PRIVATE BANK,FEDERALBNK,Q3-FY25,916.0,2,FY25,Q3
Other Income,PRIVATE BANK,FEDERALBNK,Q4-FY25,1006.0,3,FY25,Q4
Other Income,PRIVATE BANK,FEDERALBNK,Q1-FY26,1113.0,4,FY26,Q1
Other Income,PRIVATE BANK,FEDERALBNK,Q2-FY26,1082.0,5,FY26,Q2
Other Income,PRIVATE BANK,FEDERALBNK,Q3-FY26,1100.0,6,FY26,Q3
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q1-FY25,1009.5,0,FY25,Q1
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q2-FY25,1057.0,1,FY25,Q2
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q3-FY25,955.0,2,FY25,Q3
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q4-FY25,1030.0,3,FY25,Q4
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q1-FY26,862.0,4,FY26,Q1
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q2-FY26,955.0,5,FY26,Q2
PAT (INR Crs),PRIVATE BANK,FEDERALBNK,Q3-FY26,1041.0,6,FY26,Q3
PCR,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.719,0,FY25,Q1
PCR,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.7182,1,FY25,Q2
PCR,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.7421,2,FY25,Q3
PCR,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.7537,3,FY25,Q4
PCR,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.7441,4,FY26,Q1
PCR,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.7345,5,FY26,Q2
PCR,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.7514,6,FY26,Q3
RoA,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.0127,0,FY25,Q1
RoA,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.0128,1,FY25,Q2
RoA,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0114,2,FY25,Q3
RoA,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0124,3,FY25,Q4
RoA,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0098,4,FY26,Q1
RoA,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.0109,5,FY26,Q2
RoA,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.0115,6,FY26,Q3
RoE,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.1364,0,FY25,Q1
RoE,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.1365,1,FY25,Q2
RoE,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.12,2,FY25,Q3
RoE,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.1282,3,FY25,Q4
RoE,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.103,4,FY26,Q1
RoE,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.1101,5,FY26,Q2
RoE,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.1168,6,FY26,Q3
Yields,PRIVATE BANK,FEDERALBNK,Q1-FY25,0.0943,0,FY25,Q1
Yields,PRIVATE BANK,FEDERALBNK,Q2-FY25,0.0935,1,FY25,Q2
Yields,PRIVATE BANK,FEDERALBNK,Q3-FY25,0.0939,2,FY25,Q3
Yields,PRIVATE BANK,FEDERALBNK,Q4-FY25,0.0931,3,FY25,Q4
Yields,PRIVATE BANK,FEDERALBNK,Q1-FY26,0.0904,4,FY26,Q1
Yields,PRIVATE BANK,FEDERALBNK,Q2-FY26,0.0886,5,FY26,Q2
Yields,PRIVATE BANK,FEDERALBNK,Q3-FY26,0.0874,6,FY26,Q3
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q1-FY25,2532700.0,0,FY25,Q1
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q2-FY25,2519000.0,1,FY25,Q2
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q3-FY25,2542600.0,2,FY25,Q3
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q4-FY25,2695500.0,3,FY25,Q4
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q1-FY26,2742300.0,4,FY26,Q1
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q2-FY26,2769000.0,5,FY26,Q2
Advances (INR Crs),PRIVATE BANK,HDFCBANK,Q3-FY26,2844500.0,6,FY26,Q3
CAR,PRIVATE BANK,HDFCBANK,Q1-FY25,0.193,0,FY25,Q1
CAR,PRIVATE BANK,HDFCBANK,Q2-FY25,0.198,1,FY25,Q2
CAR,PRIVATE BANK,HDFCBANK,Q3-FY25,0.2,2,FY25,Q3
CAR,PRIVATE BANK,HDFCBANK,Q4-FY25,0.196,3,FY25,Q4
CAR,PRIVATE BANK,HDFCBANK,Q1-FY26,0.199,4,FY26,Q1
CAR,PRIVATE BANK,HDFCBANK,Q2-FY26,0.2,5,FY26,Q2
CAR,PRIVATE BANK,HDFCBANK,Q3-FY26,0.199,6,FY26,Q3
CASA,PRIVATE BANK,HDFCBANK,Q1-FY25,0.36,0,FY25,Q1
CASA,PRIVATE BANK,HDFCBANK,Q2-FY25,0.35,1,FY25,Q2
CASA,PRIVATE BANK,HDFCBANK,Q3-FY25,0.34,2,FY25,Q3
CASA,PRIVATE BANK,HDFCBANK,Q4-FY25,0.35,3,FY25,Q4
CASA,PRIVATE BANK,HDFCBANK,Q1-FY26,0.34,4,FY26,Q1
CASA,PRIVATE BANK,HDFCBANK,Q2-FY26,0.34,5,FY26,Q2
CASA,PRIVATE BANK,HDFCBANK,Q3-FY26,0.34,6,FY26,Q3
CoFs,PRIVATE BANK,HDFCBANK,Q1-FY25,0.049,0,FY25,Q1
CoFs,PRIVATE BANK,HDFCBANK,Q2-FY25,0.049,1,FY25,Q2
CoFs,PRIVATE BANK,HDFCBANK,Q3-FY25,0.049,2,FY25,Q3
CoFs,PRIVATE BANK,HDFCBANK,Q4-FY25,0.049,3,FY25,Q4
CoFs,PRIVATE BANK,HDFCBANK,Q1-FY26,0.048,4,FY26,Q1
CoFs,PRIVATE BANK,HDFCBANK,Q2-FY26,0.046,5,FY26,Q2
CoFs,PRIVATE BANK,HDFCBANK,Q3-FY26,0.045,6,FY26,Q3
Cost to Income,PRIVATE BANK,HDFCBANK,Q1-FY25,0.41,0,FY25,Q1
Cost to Income,PRIVATE BANK,HDFCBANK,Q2-FY25,0.4061072373166627,1,FY25,Q2
Cost to Income,PRIVATE BANK,HDFCBANK,Q3-FY25,0.406,2,FY25,Q3
Cost to Income,PRIVATE BANK,HDFCBANK,Q4-FY25,0.398,3,FY25,Q4
Cost to Income,PRIVATE BANK,HDFCBANK,Q1-FY26,0.396,4,FY26,Q1
Cost to Income,PRIVATE BANK,HDFCBANK,Q2-FY26,0.3917211328976035,5,FY26,Q2
Cost to Income,PRIVATE BANK,HDFCBANK,Q3-FY26,0.392,6,FY26,Q3
Credit Cost,PRIVATE BANK,HDFCBANK,Q1-FY25,0.0029,0,FY25,Q1
Credit Cost,PRIVATE BANK,HDFCBANK,Q2-FY25,0.0029,1,FY25,Q2
Credit Cost,PRIVATE BANK,HDFCBANK,Q3-FY25,0.0036,2,FY25,Q3
Credit Cost,PRIVATE BANK,HDFCBANK,Q4-FY25,0.0048,3,FY25,Q4
Credit Cost,PRIVATE BANK,HDFCBANK,Q1-FY26,0.0041,4,FY26,Q1
Credit Cost,PRIVATE BANK,HDFCBANK,Q2-FY26,0.0037,5,FY26,Q2
Credit Cost,PRIVATE BANK,HDFCBANK,Q3-FY26,0.0041,6,FY26,Q3
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q1-FY25,2283100.0,0,FY25,Q1
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q2-FY25,2500100.0,1,FY25,Q2
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q3-FY25,2563800.0,2,FY25,Q3
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q4-FY25,2528000.0,3,FY25,Q4
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q1-FY26,2657600.0,4,FY26,Q1
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q2-FY26,2801500.0,5,FY26,Q2
Deposits (INR Crs),PRIVATE BANK,HDFCBANK,Q3-FY26,2859500.0,6,FY26,Q3
GNPA,PRIVATE BANK,HDFCBANK,Q1-FY25,0.013,0,FY25,Q1
GNPA,PRIVATE BANK,HDFCBANK,Q2-FY25,0.014,1,FY25,Q2
GNPA,PRIVATE BANK,HDFCBANK,Q3-FY25,0.014,2,FY25,Q3
GNPA,PRIVATE BANK,HDFCBANK,Q4-FY25,0.013,3,FY25,Q4
GNPA,PRIVATE BANK,HDFCBANK,Q1-FY26,0.014,4,FY26,Q1
GNPA,PRIVATE BANK,HDFCBANK,Q2-FY26,0.0124,5,FY26,Q2
GNPA,PRIVATE BANK,HDFCBANK,Q3-FY26,0.012,6,FY26,Q3
Leverage,PRIVATE BANK,HDFCBANK,Q1-FY25,6.493132766514061,0,FY25,Q1
Leverage,PRIVATE BANK,HDFCBANK,Q2-FY25,6.6573894282632144,1,FY25,Q2
Leverage,PRIVATE BANK,HDFCBANK,Q3-FY25,,2,FY25,Q3
Leverage,PRIVATE BANK,HDFCBANK,Q4-FY25,6.50568295114656,3,FY25,Q4
Leverage,PRIVATE BANK,HDFCBANK,Q1-FY26,6.265212399540758,4,FY26,Q1
Leverage,PRIVATE BANK,HDFCBANK,Q2-FY26,6.338820826952527,5,FY26,Q2
Leverage,PRIVATE BANK,HDFCBANK,Q3-FY26,,6,FY26,Q3
NII,PRIVATE BANK,HDFCBANK,Q1-FY25,29829.2220113852,0,FY25,Q1
NII,PRIVATE BANK,HDFCBANK,Q2-FY25,30110.0,1,FY25,Q2
NII,PRIVATE BANK,HDFCBANK,Q3-FY25,30650.0,2,FY25,Q3
NII,PRIVATE BANK,HDFCBANK,Q4-FY25,32070.0,3,FY25,Q4
NII,PRIVATE BANK,HDFCBANK,Q1-FY26,31440.0,4,FY26,Q1
NII,PRIVATE BANK,HDFCBANK,Q2-FY26,31550.0,5,FY26,Q2
NII,PRIVATE BANK,HDFCBANK,Q3-FY26,30650.0,6,FY26,Q3
NIMs,PRIVATE BANK,HDFCBANK,Q1-FY25,0.035,0,FY25,Q1
NIMs,PRIVATE BANK,HDFCBANK,Q2-FY25,0.035,1,FY25,Q2
NIMs,PRIVATE BANK,HDFCBANK,Q3-FY25,0.034,2,FY25,Q3
NIMs,PRIVATE BANK,HDFCBANK,Q4-FY25,0.0346,3,FY25,Q4
NIMs,PRIVATE BANK,HDFCBANK,Q1-FY26,0.0335,4,FY26,Q1
NIMs,PRIVATE BANK,HDFCBANK,Q2-FY26,0.0327,5,FY26,Q2
NIMs,PRIVATE BANK,HDFCBANK,Q3-FY26,0.0335,6,FY26,Q3
NNPA,PRIVATE BANK,HDFCBANK,Q1-FY25,0.004,0,FY25,Q1
NNPA,PRIVATE BANK,HDFCBANK,Q2-FY25,0.004,1,FY25,Q2
NNPA,PRIVATE BANK,HDFCBANK,Q3-FY25,0.005,2,FY25,Q3
NNPA,PRIVATE BANK,HDFCBANK,Q4-FY25,0.004,3,FY25,Q4
NNPA,PRIVATE BANK,HDFCBANK,Q1-FY26,0.005,4,FY26,Q1
NNPA,PRIVATE BANK,HDFCBANK,Q2-FY26,0.004,5,FY26,Q2
NNPA,PRIVATE BANK,HDFCBANK,Q3-FY26,0.004,6,FY26,Q3
Opex to AUM,PRIVATE BANK,HDFCBANK,Q1-FY25,0.019,0,FY25,Q1
Opex to AUM,PRIVATE BANK,HDFCBANK,Q2-FY25,0.019,1,FY25,Q2
Opex to AUM,PRIVATE BANK,HDFCBANK,Q3-FY25,0.019,2,FY25,Q3
Opex to AUM,PRIVATE BANK,HDFCBANK,Q4-FY25,0.019,3,FY25,Q4
Opex to AUM,PRIVATE BANK,HDFCBANK,Q1-FY26,0.019,4,FY26,Q1
Opex to AUM,PRIVATE BANK,HDFCBANK,Q2-FY26,0.019,5,FY26,Q2
Opex to AUM,PRIVATE BANK,HDFCBANK,Q3-FY26,0.019,6,FY26,Q3
Other Income,PRIVATE BANK,HDFCBANK,Q1-FY25,10651.960784313726,0,FY25,Q1
Other Income,PRIVATE BANK,HDFCBANK,Q2-FY25,11480.0,1,FY25,Q2
Other Income,PRIVATE BANK,HDFCBANK,Q3-FY25,11450.0,2,FY25,Q3
Other Income,PRIVATE BANK,HDFCBANK,Q4-FY25,12030.0,3,FY25,Q4
Other Income,PRIVATE BANK,HDFCBANK,Q1-FY26,21730.0,4,FY26,Q1
Other Income,PRIVATE BANK,HDFCBANK,Q2-FY26,14350.0,5,FY26,Q2
Other Income,PRIVATE BANK,HDFCBANK,Q3-FY26,11450.0,6,FY26,Q3
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q1-FY25,16170.0,0,FY25,Q1
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q2-FY25,16820.0,1,FY25,Q2
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q3-FY25,16680.0,2,FY25,Q3
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q4-FY25,17620.0,3,FY25,Q4
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q1-FY26,18160.0,4,FY26,Q1
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q2-FY26,18640.0,5,FY26,Q2
PAT (INR Crs),PRIVATE BANK,HDFCBANK,Q3-FY26,16740.0,6,FY26,Q3
PCR,PRIVATE BANK,HDFCBANK,Q1-FY25,0.71,0,FY25,Q1
PCR,PRIVATE BANK,HDFCBANK,Q2-FY25,0.7,1,FY25,Q2
PCR,PRIVATE BANK,HDFCBANK,Q3-FY25,0.68,2,FY25,Q3
PCR,PRIVATE BANK,HDFCBANK,Q4-FY25,0.68,3,FY25,Q4
PCR,PRIVATE BANK,HDFCBANK,Q1-FY26,0.67,4,FY26,Q1
PCR,PRIVATE BANK,HDFCBANK,Q2-FY26,0.67,5,FY26,Q2
PCR,PRIVATE BANK,HDFCBANK,Q3-FY26,0.7,6,FY26,Q3
RoA,PRIVATE BANK,HDFCBANK,Q1-FY25,0.0189,0,FY25,Q1
RoA,PRIVATE BANK,HDFCBANK,Q2-FY25,0.019,1,FY25,Q2
RoA,PRIVATE BANK,HDFCBANK,Q3-FY25,0.0187,2,FY25,Q3
RoA,PRIVATE BANK,HDFCBANK,Q4-FY25,0.0194,3,FY25,Q4
RoA,PRIVATE BANK,HDFCBANK,Q1-FY26,0.0185,4,FY26,Q1
RoA,PRIVATE BANK,HDFCBANK,Q2-FY26,0.0193,5,FY26,Q2
RoA,PRIVATE BANK,HDFCBANK,Q3-FY26,0.0192,6,FY26,Q3
RoE,PRIVATE BANK,HDFCBANK,Q1-FY25,0.15,0,FY25,Q1
RoE,PRIVATE BANK,HDFCBANK,Q2-FY25,0.147,1,FY25,Q2
RoE,PRIVATE BANK,HDFCBANK,Q3-FY25,0.141,2,FY25,Q3
RoE,PRIVATE BANK,HDFCBANK,Q4-FY25,0.144,3,FY25,Q4
RoE,PRIVATE BANK,HDFCBANK,Q1-FY26,0.141,4,FY26,Q1
RoE,PRIVATE BANK,HDFCBANK,Q2-FY26,0.144,5,FY26,Q2
RoE,PRIVATE BANK,HDFCBANK,Q3-FY26,0.139,6,FY26,Q3
Yields,PRIVATE BANK,HDFCBANK,Q1-FY25,0.084,0,FY25,Q1
Yields,PRIVATE BANK,HDFCBANK,Q2-FY25,0.083,1,FY25,Q2
Yields,PRIVATE BANK,HDFCBANK,Q3-FY25,0.083,2,FY25,Q3
Yields,PRIVATE BANK,HDFCBANK,Q4-FY25,0.083,3,FY25,Q4
Yields,PRIVATE BANK,HDFCBANK,Q1-FY26,0.081,4,FY26,Q1
Yields,PRIVATE BANK,HDFCBANK,Q2-FY26,0.078,5,FY26,Q2
Yields,PRIVATE BANK,HDFCBANK,Q3-FY26,0.078,6,FY26,Q3
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q1-FY25,1223154.0,0,FY25,Q1
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q2-FY25,1277240.0,1,FY25,Q2
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q3-FY25,1314366.0,2,FY25,Q3
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q4-FY25,1341766.0,3,FY25,Q4
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q1-FY26,1364157.0,4,FY26,Q1
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q2-FY26,1408456.0,5,FY26,Q2
Advances (INR Crs),PRIVATE BANK,ICICIBANK,Q3-FY26,1466154.0,6,FY26,Q3
CAR,PRIVATE BANK,ICICIBANK,Q1-FY25,0.1596,0,FY25,Q1
CAR,PRIVATE BANK,ICICIBANK,Q2-FY25,,1,FY25,Q2
CAR,PRIVATE BANK,ICICIBANK,Q3-FY25,,2,FY25,Q3
CAR,PRIVATE BANK,ICICIBANK,Q4-FY25,0.1555,3,FY25,Q4
CAR,PRIVATE BANK,ICICIBANK,Q1-FY26,0.1631,4,FY26,Q1
CAR,PRIVATE BANK,ICICIBANK,Q2-FY26,0.17,5,FY26,Q2
CAR,PRIVATE BANK,ICICIBANK,Q3-FY26,0.1734,6,FY26,Q3
CASA,PRIVATE BANK,ICICIBANK,Q1-FY25,0.396,0,FY25,Q1
CASA,PRIVATE BANK,ICICIBANK,Q2-FY25,0.4064231822127261,1,FY25,Q2
CASA,PRIVATE BANK,ICICIBANK,Q3-FY25,0.39,2,FY25,Q3
CASA,PRIVATE BANK,ICICIBANK,Q4-FY25,0.384,3,FY25,Q4
CASA,PRIVATE BANK,ICICIBANK,Q1-FY26,0.387,4,FY26,Q1
CASA,PRIVATE BANK,ICICIBANK,Q2-FY26,0.392,5,FY26,Q2
CASA,PRIVATE BANK,ICICIBANK,Q3-FY26,0.39,6,FY26,Q3
CoFs,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0505,0,FY25,Q1
CoFs,PRIVATE BANK,ICICIBANK,Q2-FY25,0.051,1,FY25,Q2
CoFs,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0509,2,FY25,Q3
CoFs,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0518,3,FY25,Q4
CoFs,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0502,4,FY26,Q1
CoFs,PRIVATE BANK,ICICIBANK,Q2-FY26,0.0478,5,FY26,Q2
CoFs,PRIVATE BANK,ICICIBANK,Q3-FY26,0.0467,6,FY26,Q3
Cost to Income,PRIVATE BANK,ICICIBANK,Q1-FY25,0.397,0,FY25,Q1
Cost to Income,PRIVATE BANK,ICICIBANK,Q2-FY25,0.386,1,FY25,Q2
Cost to Income,PRIVATE BANK,ICICIBANK,Q3-FY25,0.385,2,FY25,Q3
Cost to Income,PRIVATE BANK,ICICIBANK,Q4-FY25,0.379,3,FY25,Q4
Cost to Income,PRIVATE BANK,ICICIBANK,Q1-FY26,0.378,4,FY26,Q1
Cost to Income,PRIVATE BANK,ICICIBANK,Q2-FY26,0.406,5,FY26,Q2
Cost to Income,PRIVATE BANK,ICICIBANK,Q3-FY26,0.408,6,FY26,Q3
Credit Cost,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0043,0,FY25,Q1
Credit Cost,PRIVATE BANK,ICICIBANK,Q2-FY25,0.0038,1,FY25,Q2
Credit Cost,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0037,2,FY25,Q3
Credit Cost,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0043,3,FY25,Q4
Credit Cost,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0053,4,FY26,Q1
Credit Cost,PRIVATE BANK,ICICIBANK,Q2-FY26,0.0026,5,FY26,Q2
Credit Cost,PRIVATE BANK,ICICIBANK,Q3-FY26,0.0071,6,FY26,Q3
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q1-FY25,1426150.0,0,FY25,Q1
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q2-FY25,1428095.0,1,FY25,Q2
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q3-FY25,1520309.0,2,FY25,Q3
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q4-FY25,1610348.0,3,FY25,Q4
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q1-FY26,1608517.0,4,FY26,Q1
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q2-FY26,1612825.0,5,FY26,Q2
Deposits (INR Crs),PRIVATE BANK,ICICIBANK,Q3-FY26,1659611.0,6,FY26,Q3
GNPA,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0251,0,FY25,Q1
GNPA,PRIVATE BANK,ICICIBANK,Q2-FY25,0.0197,1,FY25,Q2
GNPA,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0196,2,FY25,Q3
GNPA,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0167,3,FY25,Q4
GNPA,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0167,4,FY26,Q1
GNPA,PRIVATE BANK,ICICIBANK,Q2-FY26,0.0158,5,FY26,Q2
GNPA,PRIVATE BANK,ICICIBANK,Q3-FY26,0.0153,6,FY26,Q3
Leverage,PRIVATE BANK,ICICIBANK,Q1-FY25,6.23,0,FY25,Q1
Leverage,PRIVATE BANK,ICICIBANK,Q2-FY25,,1,FY25,Q2
Leverage,PRIVATE BANK,ICICIBANK,Q3-FY25,,2,FY25,Q3
Leverage,PRIVATE BANK,ICICIBANK,Q4-FY25,5.936400332788956,3,FY25,Q4
Leverage,PRIVATE BANK,ICICIBANK,Q1-FY26,5.63,4,FY26,Q1
Leverage,PRIVATE BANK,ICICIBANK,Q2-FY26,,5,FY26,Q2
Leverage,PRIVATE BANK,ICICIBANK,Q3-FY26,,6,FY26,Q3
NII,PRIVATE BANK,ICICIBANK,Q1-FY25,19553.0,0,FY25,Q1
NII,PRIVATE BANK,ICICIBANK,Q2-FY25,20048.0,1,FY25,Q2
NII,PRIVATE BANK,ICICIBANK,Q3-FY25,20371.0,2,FY25,Q3
NII,PRIVATE BANK,ICICIBANK,Q4-FY25,21193.0,3,FY25,Q4
NII,PRIVATE BANK,ICICIBANK,Q1-FY26,21635.0,4,FY26,Q1
NII,PRIVATE BANK,ICICIBANK,Q2-FY26,21529.0,5,FY26,Q2
NII,PRIVATE BANK,ICICIBANK,Q3-FY26,21932.0,6,FY26,Q3
NIMs,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0436,0,FY25,Q1
NIMs,PRIVATE BANK,ICICIBANK,Q2-FY25,0.0427,1,FY25,Q2
NIMs,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0425,2,FY25,Q3
NIMs,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0441,3,FY25,Q4
NIMs,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0434,4,FY26,Q1
NIMs,PRIVATE BANK,ICICIBANK,Q2-FY26,0.043,5,FY26,Q2
NIMs,PRIVATE BANK,ICICIBANK,Q3-FY26,0.043,6,FY26,Q3
NNPA,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0045,0,FY25,Q1
NNPA,PRIVATE BANK,ICICIBANK,Q2-FY25,0.0042,1,FY25,Q2
NNPA,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0042,2,FY25,Q3
NNPA,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0039,3,FY25,Q4
NNPA,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0041,4,FY26,Q1
NNPA,PRIVATE BANK,ICICIBANK,Q2-FY26,0.0039,5,FY26,Q2
NNPA,PRIVATE BANK,ICICIBANK,Q3-FY26,0.0037,6,FY26,Q3
Opex to AUM,PRIVATE BANK,ICICIBANK,Q1-FY25,0.022,0,FY25,Q1
Opex to AUM,PRIVATE BANK,ICICIBANK,Q2-FY25,0.021,1,FY25,Q2
Opex to AUM,PRIVATE BANK,ICICIBANK,Q3-FY25,0.021,2,FY25,Q3
Opex to AUM,PRIVATE BANK,ICICIBANK,Q4-FY25,0.02,3,FY25,Q4
Opex to AUM,PRIVATE BANK,ICICIBANK,Q1-FY26,0.021,4,FY26,Q1
Opex to AUM,PRIVATE BANK,ICICIBANK,Q2-FY26,0.022,5,FY26,Q2
Opex to AUM,PRIVATE BANK,ICICIBANK,Q3-FY26,0.022,6,FY26,Q3
Other Income,PRIVATE BANK,ICICIBANK,Q1-FY25,6389.0,0,FY25,Q1
Other Income,PRIVATE BANK,ICICIBANK,Q2-FY25,6496.0,1,FY25,Q2
Other Income,PRIVATE BANK,ICICIBANK,Q3-FY25,6697.0,2,FY25,Q3
Other Income,PRIVATE BANK,ICICIBANK,Q4-FY25,7021.0,3,FY25,Q4
Other Income,PRIVATE BANK,ICICIBANK,Q1-FY26,7264.0,4,FY26,Q1
Other Income,PRIVATE BANK,ICICIBANK,Q2-FY26,7356.0,5,FY26,Q2
Other Income,PRIVATE BANK,ICICIBANK,Q3-FY26,7525.0,6,FY26,Q3
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q1-FY25,11696.0,0,FY25,Q1
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q2-FY25,11746.0,1,FY25,Q2
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q3-FY25,11792.0,2,FY25,Q3
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q4-FY25,12630.0,3,FY25,Q4
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q1-FY26,13358.0,4,FY26,Q1
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q2-FY26,12359.0,5,FY26,Q2
PAT (INR Crs),PRIVATE BANK,ICICIBANK,Q3-FY26,11318.0,6,FY26,Q3
PCR,PRIVATE BANK,ICICIBANK,Q1-FY25,0.797,0,FY25,Q1
PCR,PRIVATE BANK,ICICIBANK,Q2-FY25,0.785,1,FY25,Q2
PCR,PRIVATE BANK,ICICIBANK,Q3-FY25,0.782,2,FY25,Q3
PCR,PRIVATE BANK,ICICIBANK,Q4-FY25,0.762,3,FY25,Q4
PCR,PRIVATE BANK,ICICIBANK,Q1-FY26,0.753,4,FY26,Q1
PCR,PRIVATE BANK,ICICIBANK,Q2-FY26,0.75,5,FY26,Q2
PCR,PRIVATE BANK,ICICIBANK,Q3-FY26,0.754,6,FY26,Q3
RoA,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0236,0,FY25,Q1
RoA,PRIVATE BANK,ICICIBANK,Q2-FY25,0.0239,1,FY25,Q2
RoA,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0236,2,FY25,Q3
RoA,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0236,3,FY25,Q4
RoA,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0244,4,FY26,Q1
RoA,PRIVATE BANK,ICICIBANK,Q2-FY26,0.0233,5,FY26,Q2
RoA,PRIVATE BANK,ICICIBANK,Q3-FY26,0.0211,6,FY26,Q3
RoE,PRIVATE BANK,ICICIBANK,Q1-FY25,0.177,0,FY25,Q1
RoE,PRIVATE BANK,ICICIBANK,Q2-FY25,0.181,1,FY25,Q2
RoE,PRIVATE BANK,ICICIBANK,Q3-FY25,0.176,2,FY25,Q3
RoE,PRIVATE BANK,ICICIBANK,Q4-FY25,0.181,3,FY25,Q4
RoE,PRIVATE BANK,ICICIBANK,Q1-FY26,0.169,4,FY26,Q1
RoE,PRIVATE BANK,ICICIBANK,Q2-FY26,0.16,5,FY26,Q2
RoE,PRIVATE BANK,ICICIBANK,Q3-FY26,0.143,6,FY26,Q3
Yields,PRIVATE BANK,ICICIBANK,Q1-FY25,0.0869,0,FY25,Q1
Yields,PRIVATE BANK,ICICIBANK,Q2-FY25,0.0863,1,FY25,Q2
Yields,PRIVATE BANK,ICICIBANK,Q3-FY25,0.0862,2,FY25,Q3
Yields,PRIVATE BANK,ICICIBANK,Q4-FY25,0.0882,3,FY25,Q4
Yields,PRIVATE BANK,ICICIBANK,Q1-FY26,0.0861,4,FY26,Q1
Yields,PRIVATE BANK,ICICIBANK,Q2-FY26,0.0834,5,FY26,Q2
Yields,PRIVATE BANK,ICICIBANK,Q3-FY26,0.0823,6,FY26,Q3
Advances (INR Crs),PSU BANK,INDIANB,Q1-FY25,539123.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,INDIANB,Q2-FY25,551000.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,INDIANB,Q3-FY25,559000.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,INDIANB,Q4-FY25,588000.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,INDIANB,Q1-FY26,601000.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,INDIANB,Q2-FY26,620000.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,INDIANB,Q3-FY26,640000.0,6,FY26,Q3
CAR,PSU BANK,INDIANB,Q1-FY25,0.1647,0,FY25,Q1
CAR,PSU BANK,INDIANB,Q2-FY25,0.1655,1,FY25,Q2
CAR,PSU BANK,INDIANB,Q3-FY25,0.1592,2,FY25,Q3
CAR,PSU BANK,INDIANB,Q4-FY25,0.1794,3,FY25,Q4
CAR,PSU BANK,INDIANB,Q1-FY26,0.178,4,FY26,Q1
CAR,PSU BANK,INDIANB,Q2-FY26,0.1730999999999999,5,FY26,Q2
CAR,PSU BANK,INDIANB,Q3-FY26,0.1658,6,FY26,Q3
CASA,PSU BANK,INDIANB,Q1-FY25,0.4056,0,FY25,Q1
CASA,PSU BANK,INDIANB,Q2-FY25,0.4047,1,FY25,Q2
CASA,PSU BANK,INDIANB,Q3-FY25,0.4114,2,FY25,Q3
CASA,PSU BANK,INDIANB,Q4-FY25,0.4017,3,FY25,Q4
CASA,PSU BANK,INDIANB,Q1-FY26,0.3897,4,FY26,Q1
CASA,PSU BANK,INDIANB,Q2-FY26,0.3887,5,FY26,Q2
CASA,PSU BANK,INDIANB,Q3-FY26,0.3908,6,FY26,Q3
CoFs,PSU BANK,INDIANB,Q1-FY25,0.0512,0,FY25,Q1
CoFs,PSU BANK,INDIANB,Q2-FY25,0.0522,1,FY25,Q2
CoFs,PSU BANK,INDIANB,Q3-FY25,0.0522,2,FY25,Q3
CoFs,PSU BANK,INDIANB,Q4-FY25,0.0521,3,FY25,Q4
CoFs,PSU BANK,INDIANB,Q1-FY26,0.0523,4,FY26,Q1
CoFs,PSU BANK,INDIANB,Q2-FY26,0.0509,5,FY26,Q2
CoFs,PSU BANK,INDIANB,Q3-FY26,0.0493,6,FY26,Q3
Cost to Income,PSU BANK,INDIANB,Q1-FY25,0.4430974764967837,0,FY25,Q1
Cost to Income,PSU BANK,INDIANB,Q2-FY25,0.4512534818941504,1,FY25,Q2
Cost to Income,PSU BANK,INDIANB,Q3-FY25,0.4456635928563091,2,FY25,Q3
Cost to Income,PSU BANK,INDIANB,Q4-FY25,0.4504543961458447,3,FY25,Q4
Cost to Income,PSU BANK,INDIANB,Q1-FY26,0.4577176631052512,4,FY26,Q1
Cost to Income,PSU BANK,INDIANB,Q2-FY26,0.464815224607214,5,FY26,Q2
Cost to Income,PSU BANK,INDIANB,Q3-FY26,0.4690340308602832,6,FY26,Q3
Credit Cost,PSU BANK,INDIANB,Q1-FY25,0.0071,0,FY25,Q1
Credit Cost,PSU BANK,INDIANB,Q2-FY25,0.0065,1,FY25,Q2
Credit Cost,PSU BANK,INDIANB,Q3-FY25,0.0047,2,FY25,Q3
Credit Cost,PSU BANK,INDIANB,Q4-FY25,0.0081,3,FY25,Q4
Credit Cost,PSU BANK,INDIANB,Q1-FY26,0.0028,4,FY26,Q1
Credit Cost,PSU BANK,INDIANB,Q2-FY26,0.0026,5,FY26,Q2
Credit Cost,PSU BANK,INDIANB,Q3-FY26,0.0021,6,FY26,Q3
Deposits (INR Crs),PSU BANK,INDIANB,Q1-FY25,681183.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,INDIANB,Q2-FY25,693000.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,INDIANB,Q3-FY25,702000.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,INDIANB,Q4-FY25,737000.0,3,FY25,Q4
Deposits (INR Crs),PSU BANK,INDIANB,Q1-FY26,744000.0,4,FY26,Q1
Deposits (INR Crs),PSU BANK,INDIANB,Q2-FY26,777000.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,INDIANB,Q3-FY26,790000.0,6,FY26,Q3
GNPA,PSU BANK,INDIANB,Q1-FY25,0.038,0,FY25,Q1
GNPA,PSU BANK,INDIANB,Q2-FY25,0.0348,1,FY25,Q2
GNPA,PSU BANK,INDIANB,Q3-FY25,0.0326,2,FY25,Q3
GNPA,PSU BANK,INDIANB,Q4-FY25,0.0308999999999999,3,FY25,Q4
GNPA,PSU BANK,INDIANB,Q1-FY26,0.0301,4,FY26,Q1
GNPA,PSU BANK,INDIANB,Q2-FY26,0.026,5,FY26,Q2
GNPA,PSU BANK,INDIANB,Q3-FY26,0.0223,6,FY26,Q3
Leverage,PSU BANK,INDIANB,Q1-FY25,14.39516129032258,0,FY25,Q1
Leverage,PSU BANK,INDIANB,Q2-FY25,11.762767710049422,1,FY25,Q2
Leverage,PSU BANK,INDIANB,Q3-FY25,11.0119940029985,2,FY25,Q3
Leverage,PSU BANK,INDIANB,Q4-FY25,11.364963503649635,3,FY25,Q4
Leverage,PSU BANK,INDIANB,Q1-FY26,11.27536231884058,4,FY26,Q1
Leverage,PSU BANK,INDIANB,Q2-FY26,11.069444444444445,5,FY26,Q2
Leverage,PSU BANK,INDIANB,Q3-FY26,10.73432946469656,6,FY26,Q3
NII,PSU BANK,INDIANB,Q1-FY25,6178.0,0,FY25,Q1
NII,PSU BANK,INDIANB,Q2-FY25,6194.0,1,FY25,Q2
NII,PSU BANK,INDIANB,Q3-FY25,6415.0,2,FY25,Q3
NII,PSU BANK,INDIANB,Q4-FY25,6389.0,3,FY25,Q4
NII,PSU BANK,INDIANB,Q1-FY26,6359.0,4,FY26,Q1
NII,PSU BANK,INDIANB,Q2-FY26,6551.0,5,FY26,Q2
NII,PSU BANK,INDIANB,Q3-FY26,6896.0,6,FY26,Q3
NIMs,PSU BANK,INDIANB,Q1-FY25,0.0344,0,FY25,Q1
NIMs,PSU BANK,INDIANB,Q2-FY25,0.0339,1,FY25,Q2
NIMs,PSU BANK,INDIANB,Q3-FY25,0.0339,2,FY25,Q3
NIMs,PSU BANK,INDIANB,Q4-FY25,0.0337,3,FY25,Q4
NIMs,PSU BANK,INDIANB,Q1-FY26,0.0323,4,FY26,Q1
NIMs,PSU BANK,INDIANB,Q2-FY26,0.0323,5,FY26,Q2
NIMs,PSU BANK,INDIANB,Q3-FY26,0.034,6,FY26,Q3
NNPA,PSU BANK,INDIANB,Q1-FY25,,0,FY25,Q1
NNPA,PSU BANK,INDIANB,Q2-FY25,0.0027,1,FY25,Q2
NNPA,PSU BANK,INDIANB,Q3-FY25,0.0021,2,FY25,Q3
NNPA,PSU BANK,INDIANB,Q4-FY25,0.0019,3,FY25,Q4
NNPA,PSU BANK,INDIANB,Q1-FY26,0.0018,4,FY26,Q1
NNPA,PSU BANK,INDIANB,Q2-FY26,0.0016,5,FY26,Q2
NNPA,PSU BANK,INDIANB,Q3-FY26,0.0015,6,FY26,Q3
Opex to AUM,PSU BANK,INDIANB,Q1-FY25,,0,FY25,Q1
Opex to AUM,PSU BANK,INDIANB,Q2-FY25,,1,FY25,Q2
Opex to AUM,PSU BANK,INDIANB,Q3-FY25,,2,FY25,Q3
Opex to AUM,PSU BANK,INDIANB,Q4-FY25,,3,FY25,Q4
Opex to AUM,PSU BANK,INDIANB,Q1-FY26,,4,FY26,Q1
Opex to AUM,PSU BANK,INDIANB,Q2-FY26,,5,FY26,Q2
Opex to AUM,PSU BANK,INDIANB,Q3-FY26,,6,FY26,Q3
Other Income,PSU BANK,INDIANB,Q1-FY25,1905.0,0,FY25,Q1
Other Income,PSU BANK,INDIANB,Q2-FY25,2422.0,1,FY25,Q2
Other Income,PSU BANK,INDIANB,Q3-FY25,2153.0,2,FY25,Q3
Other Income,PSU BANK,INDIANB,Q4-FY25,2743.0,3,FY25,Q4
Other Income,PSU BANK,INDIANB,Q1-FY26,2438.0,4,FY26,Q1
Other Income,PSU BANK,INDIANB,Q2-FY26,2487.0,5,FY26,Q2
Other Income,PSU BANK,INDIANB,Q3-FY26,2566.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,INDIANB,Q1-FY25,2403.0,0,FY25,Q1
PAT (INR Crs),PSU BANK,INDIANB,Q2-FY25,2706.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,INDIANB,Q3-FY25,2852.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,INDIANB,Q4-FY25,2959.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,INDIANB,Q1-FY26,2973.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,INDIANB,Q2-FY26,3018.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,INDIANB,Q3-FY26,3061.0,6,FY26,Q3
PCR,PSU BANK,INDIANB,Q1-FY25,,0,FY25,Q1
PCR,PSU BANK,INDIANB,Q2-FY25,0.976,1,FY25,Q2
PCR,PSU BANK,INDIANB,Q3-FY25,0.9809,2,FY25,Q3
PCR,PSU BANK,INDIANB,Q4-FY25,0.981,3,FY25,Q4
PCR,PSU BANK,INDIANB,Q1-FY26,0.982,4,FY26,Q1
PCR,PSU BANK,INDIANB,Q2-FY26,0.9828,5,FY26,Q2
PCR,PSU BANK,INDIANB,Q3-FY26,0.9828,6,FY26,Q3
RoA,PSU BANK,INDIANB,Q1-FY25,0.012,0,FY25,Q1
RoA,PSU BANK,INDIANB,Q2-FY25,0.0133,1,FY25,Q2
RoA,PSU BANK,INDIANB,Q3-FY25,0.0133,2,FY25,Q3
RoA,PSU BANK,INDIANB,Q4-FY25,0.0137,3,FY25,Q4
RoA,PSU BANK,INDIANB,Q1-FY26,0.0134,4,FY26,Q1
RoA,PSU BANK,INDIANB,Q2-FY26,0.0132,5,FY26,Q2
RoA,PSU BANK,INDIANB,Q3-FY26,0.013,6,FY26,Q3
RoE,PSU BANK,INDIANB,Q1-FY25,0.1976,0,FY25,Q1
RoE,PSU BANK,INDIANB,Q2-FY25,0.2104,1,FY25,Q2
RoE,PSU BANK,INDIANB,Q3-FY25,0.2104,2,FY25,Q3
RoE,PSU BANK,INDIANB,Q4-FY25,0.2101,3,FY25,Q4
RoE,PSU BANK,INDIANB,Q1-FY26,0.2026,4,FY26,Q1
RoE,PSU BANK,INDIANB,Q2-FY26,0.1958,5,FY26,Q2
RoE,PSU BANK,INDIANB,Q3-FY26,0.1911,6,FY26,Q3
Yields,PSU BANK,INDIANB,Q1-FY25,0.0869,0,FY25,Q1
Yields,PSU BANK,INDIANB,Q2-FY25,0.084,1,FY25,Q2
Yields,PSU BANK,INDIANB,Q3-FY25,0.0877,2,FY25,Q3
Yields,PSU BANK,INDIANB,Q4-FY25,0.0864,3,FY25,Q4
Yields,PSU BANK,INDIANB,Q1-FY26,0.0858,4,FY26,Q1
Yields,PSU BANK,INDIANB,Q2-FY26,0.084,5,FY26,Q2
Yields,PSU BANK,INDIANB,Q3-FY26,0.0839,6,FY26,Q3
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q1-FY25,390000.0,0,FY25,Q1
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q2-FY25,399500.0,1,FY25,Q2
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q3-FY25,413800.0,2,FY25,Q3
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q4-FY25,429600.0,3,FY25,Q4
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q1-FY26,444800.0,4,FY26,Q1
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q2-FY26,462600.0,5,FY26,Q2
Advances (INR Crs),PRIVATE BANK,KOTAKBANK,Q3-FY26,480673.0,6,FY26,Q3
CAR,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.224,0,FY25,Q1
CAR,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.226,1,FY25,Q2
CAR,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.228,2,FY25,Q3
CAR,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.222,3,FY25,Q4
CAR,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.226,4,FY26,Q1
CAR,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.228,5,FY26,Q2
CAR,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.226,6,FY26,Q3
CASA,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.434,0,FY25,Q1
CASA,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.436,1,FY25,Q2
CASA,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.423,2,FY25,Q3
CASA,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.43,3,FY25,Q4
CASA,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.409,4,FY26,Q1
CASA,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.423,5,FY26,Q2
CASA,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.413,6,FY26,Q3
CoFs,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.051,0,FY25,Q1
CoFs,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.052,1,FY25,Q2
CoFs,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.051,2,FY25,Q3
CoFs,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.051,3,FY25,Q4
CoFs,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.05,4,FY26,Q1
CoFs,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.047,5,FY26,Q2
CoFs,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.0454,6,FY26,Q3
Cost to Income,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.462,0,FY25,Q1
Cost to Income,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.475,1,FY25,Q2
Cost to Income,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.472,2,FY25,Q3
Cost to Income,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.477,3,FY25,Q4
Cost to Income,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.462,4,FY26,Q1
Cost to Income,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.468,5,FY26,Q2
Cost to Income,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.483,6,FY26,Q3
Credit Cost,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.0055,0,FY25,Q1
Credit Cost,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.007,1,FY25,Q2
Credit Cost,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.008,2,FY25,Q3
Credit Cost,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.009,3,FY25,Q4
Credit Cost,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.012,4,FY26,Q1
Credit Cost,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.009,5,FY26,Q2
Credit Cost,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.0063,6,FY26,Q3
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q1-FY25,447400.0,0,FY25,Q1
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q2-FY25,461500.0,1,FY25,Q2
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q3-FY25,473500.0,2,FY25,Q3
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q4-FY25,499100.0,3,FY25,Q4
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q1-FY26,512800.0,4,FY26,Q1
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q2-FY26,528800.0,5,FY26,Q2
Deposits (INR Crs),PRIVATE BANK,KOTAKBANK,Q3-FY26,542638.0,6,FY26,Q3
GNPA,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.0139,0,FY25,Q1
GNPA,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.015,1,FY25,Q2
GNPA,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.015,2,FY25,Q3
GNPA,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.0142,3,FY25,Q4
GNPA,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.0148,4,FY26,Q1
GNPA,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.0139,5,FY26,Q2
GNPA,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.013,6,FY26,Q3
Leverage,PRIVATE BANK,KOTAKBANK,Q1-FY25,4.49811320754717,0,FY25,Q1
Leverage,PRIVATE BANK,KOTAKBANK,Q2-FY25,,1,FY25,Q2
Leverage,PRIVATE BANK,KOTAKBANK,Q3-FY25,,2,FY25,Q3
Leverage,PRIVATE BANK,KOTAKBANK,Q4-FY25,4.67897435897436,3,FY25,Q4
Leverage,PRIVATE BANK,KOTAKBANK,Q1-FY26,4.327390599675851,4,FY26,Q1
Leverage,PRIVATE BANK,KOTAKBANK,Q2-FY26,,5,FY26,Q2
Leverage,PRIVATE BANK,KOTAKBANK,Q3-FY26,,6,FY26,Q3
NII,PRIVATE BANK,KOTAKBANK,Q1-FY25,6840.0,0,FY25,Q1
NII,PRIVATE BANK,KOTAKBANK,Q2-FY25,7020.0,1,FY25,Q2
NII,PRIVATE BANK,KOTAKBANK,Q3-FY25,7196.0,2,FY25,Q3
NII,PRIVATE BANK,KOTAKBANK,Q4-FY25,7280.0,3,FY25,Q4
NII,PRIVATE BANK,KOTAKBANK,Q1-FY26,7260.0,4,FY26,Q1
NII,PRIVATE BANK,KOTAKBANK,Q2-FY26,7311.0,5,FY26,Q2
NII,PRIVATE BANK,KOTAKBANK,Q3-FY26,7565.0,6,FY26,Q3
NIMs,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.0502,0,FY25,Q1
NIMs,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.0491,1,FY25,Q2
NIMs,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.0493,2,FY25,Q3
NIMs,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.0497,3,FY25,Q4
NIMs,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.0465,4,FY26,Q1
NIMs,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.0454,5,FY26,Q2
NIMs,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.0454,6,FY26,Q3
NNPA,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.0035,0,FY25,Q1
NNPA,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.004,1,FY25,Q2
NNPA,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.004,2,FY25,Q3
NNPA,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.0031,3,FY25,Q4
NNPA,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.0034,4,FY26,Q1
NNPA,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.003,5,FY26,Q2
NNPA,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.0031,6,FY26,Q3
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q1-FY25,,0,FY25,Q1
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q2-FY25,,1,FY25,Q2
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.0295,2,FY25,Q3
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q4-FY25,,3,FY25,Q4
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q1-FY26,,4,FY26,Q1
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.0267,5,FY26,Q2
Opex to AUM,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.0276,6,FY26,Q3
Other Income,PRIVATE BANK,KOTAKBANK,Q1-FY25,2930.0,0,FY25,Q1
Other Income,PRIVATE BANK,KOTAKBANK,Q2-FY25,2684.0,1,FY25,Q2
Other Income,PRIVATE BANK,KOTAKBANK,Q3-FY25,2623.0,2,FY25,Q3
Other Income,PRIVATE BANK,KOTAKBANK,Q4-FY25,3180.0,3,FY25,Q4
Other Income,PRIVATE BANK,KOTAKBANK,Q1-FY26,3080.0,4,FY26,Q1
Other Income,PRIVATE BANK,KOTAKBANK,Q2-FY26,2589.0,5,FY26,Q2
Other Income,PRIVATE BANK,KOTAKBANK,Q3-FY26,2838.0,6,FY26,Q3
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q1-FY25,3520.0,0,FY25,Q1
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q2-FY25,3344.0,1,FY25,Q2
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q3-FY25,3305.0,2,FY25,Q3
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q4-FY25,3552.0,3,FY25,Q4
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q1-FY26,3282.0,4,FY26,Q1
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q2-FY26,3253.0,5,FY26,Q2
PAT (INR Crs),PRIVATE BANK,KOTAKBANK,Q3-FY26,3446.0,6,FY26,Q3
PCR,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.75,0,FY25,Q1
PCR,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.714,1,FY25,Q2
PCR,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.732,2,FY25,Q3
PCR,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.78,3,FY25,Q4
PCR,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.77,4,FY26,Q1
PCR,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.77,5,FY26,Q2
PCR,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.76,6,FY26,Q3
RoA,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.024,0,FY25,Q1
RoA,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.026,1,FY25,Q2
RoA,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.021,2,FY25,Q3
RoA,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.028,3,FY25,Q4
RoA,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.024,4,FY26,Q1
RoA,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.021,5,FY26,Q2
RoA,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.0189,6,FY26,Q3
RoE,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.1391,0,FY25,Q1
RoE,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.1223,1,FY25,Q2
RoE,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.1219,2,FY25,Q3
RoE,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.1242,3,FY25,Q4
RoE,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.1094,4,FY26,Q1
RoE,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.1038,5,FY26,Q2
RoE,PRIVATE BANK,KOTAKBANK,Q3-FY26,0.1068,6,FY26,Q3
Yields,PRIVATE BANK,KOTAKBANK,Q1-FY25,0.109,0,FY25,Q1
Yields,PRIVATE BANK,KOTAKBANK,Q2-FY25,0.108,1,FY25,Q2
Yields,PRIVATE BANK,KOTAKBANK,Q3-FY25,0.107,2,FY25,Q3
Yields,PRIVATE BANK,KOTAKBANK,Q4-FY25,0.104,3,FY25,Q4
Yields,PRIVATE BANK,KOTAKBANK,Q1-FY26,0.102,4,FY26,Q1
Yields,PRIVATE BANK,KOTAKBANK,Q2-FY26,0.098,5,FY26,Q2
Yields,PRIVATE BANK,KOTAKBANK,Q3-FY26,,6,FY26,Q3
Advances (INR Crs),PSU BANK,PNB,Q1-FY25,983997.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,PNB,Q2-FY25,1061900.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,PNB,Q3-FY25,1110292.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,PNB,Q4-FY25,1077474.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,PNB,Q1-FY26,1091980.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,PNB,Q2-FY26,1170800.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,PNB,Q3-FY26,1231328.0,6,FY26,Q3
CAR,PSU BANK,PNB,Q1-FY25,0.1579,0,FY25,Q1
CAR,PSU BANK,PNB,Q2-FY25,0.1636,1,FY25,Q2
CAR,PSU BANK,PNB,Q3-FY25,0.1541,2,FY25,Q3
CAR,PSU BANK,PNB,Q4-FY25,0.1701,3,FY25,Q4
CAR,PSU BANK,PNB,Q1-FY26,0.175,4,FY26,Q1
CAR,PSU BANK,PNB,Q2-FY26,0.1719,5,FY26,Q2
CAR,PSU BANK,PNB,Q3-FY26,0.1677,6,FY26,Q3
CASA,PSU BANK,PNB,Q1-FY25,0.4008,0,FY25,Q1
CASA,PSU BANK,PNB,Q2-FY25,0.3931,1,FY25,Q2
CASA,PSU BANK,PNB,Q3-FY25,0.3812,2,FY25,Q3
CASA,PSU BANK,PNB,Q4-FY25,0.3795,3,FY25,Q4
CASA,PSU BANK,PNB,Q1-FY26,0.3699,4,FY26,Q1
CASA,PSU BANK,PNB,Q2-FY26,0.373,5,FY26,Q2
CASA,PSU BANK,PNB,Q3-FY26,0.371,6,FY26,Q3
CoFs,PSU BANK,PNB,Q1-FY25,0.0454,0,FY25,Q1
CoFs,PSU BANK,PNB,Q2-FY25,0.0457,1,FY25,Q2
CoFs,PSU BANK,PNB,Q3-FY25,0.0463,2,FY25,Q3
CoFs,PSU BANK,PNB,Q4-FY25,0.0476,3,FY25,Q4
CoFs,PSU BANK,PNB,Q1-FY26,0.047,4,FY26,Q1
CoFs,PSU BANK,PNB,Q2-FY26,0.0458,5,FY26,Q2
CoFs,PSU BANK,PNB,Q3-FY26,0.045,6,FY26,Q3
Cost to Income,PSU BANK,PNB,Q1-FY25,0.5328,0,FY25,Q1
Cost to Income,PSU BANK,PNB,Q2-FY25,0.5458,1,FY25,Q2
Cost to Income,PSU BANK,PNB,Q3-FY25,0.5416,2,FY25,Q3
Cost to Income,PSU BANK,PNB,Q4-FY25,0.5621,3,FY25,Q4
Cost to Income,PSU BANK,PNB,Q1-FY26,0.5531,4,FY26,Q1
Cost to Income,PSU BANK,PNB,Q2-FY26,0.5102,5,FY26,Q2
Cost to Income,PSU BANK,PNB,Q3-FY26,0.5191,6,FY26,Q3
Credit Cost,PSU BANK,PNB,Q1-FY25,0.0032,0,FY25,Q1
Credit Cost,PSU BANK,PNB,Q2-FY25,0.0008,1,FY25,Q2
Credit Cost,PSU BANK,PNB,Q3-FY25,0.0012,2,FY25,Q3
Credit Cost,PSU BANK,PNB,Q4-FY25,0.0021,3,FY25,Q4
Credit Cost,PSU BANK,PNB,Q1-FY26,0.0014,4,FY26,Q1
Credit Cost,PSU BANK,PNB,Q2-FY26,0.0,5,FY26,Q2
Credit Cost,PSU BANK,PNB,Q3-FY26,0.0046,6,FY26,Q3
Deposits (INR Crs),PSU BANK,PNB,Q1-FY25,1408247.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,PNB,Q2-FY25,1458300.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,PNB,Q3-FY25,1529699.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,PNB,Q4-FY25,1566623.28,3,FY25,Q4
Deposits (INR Crs),PSU BANK,PNB,Q1-FY26,1589378.55,4,FY26,Q1
Deposits (INR Crs),PSU BANK,PNB,Q2-FY26,1617000.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,PNB,Q3-FY26,1660290.0,6,FY26,Q3
GNPA,PSU BANK,PNB,Q1-FY25,0.0498,0,FY25,Q1
GNPA,PSU BANK,PNB,Q2-FY25,0.0448,1,FY25,Q2
GNPA,PSU BANK,PNB,Q3-FY25,0.0409,2,FY25,Q3
GNPA,PSU BANK,PNB,Q4-FY25,0.0395,3,FY25,Q4
GNPA,PSU BANK,PNB,Q1-FY26,0.0378,4,FY26,Q1
GNPA,PSU BANK,PNB,Q2-FY26,0.0345,5,FY26,Q2
GNPA,PSU BANK,PNB,Q3-FY26,0.0319,6,FY26,Q3
Leverage,PSU BANK,PNB,Q1-FY25,13.047316917662451,0,FY25,Q1
Leverage,PSU BANK,PNB,Q2-FY25,,1,FY25,Q2
Leverage,PSU BANK,PNB,Q3-FY25,12.741076397169886,2,FY25,Q3
Leverage,PSU BANK,PNB,Q4-FY25,12.958365963508957,3,FY25,Q4
Leverage,PSU BANK,PNB,Q1-FY26,12.583935134315915,4,FY26,Q1
Leverage,PSU BANK,PNB,Q2-FY26,12.531114220487517,5,FY26,Q2
Leverage,PSU BANK,PNB,Q3-FY26,12.32394366197183,6,FY26,Q3
NII,PSU BANK,PNB,Q1-FY25,10476.0,0,FY25,Q1
NII,PSU BANK,PNB,Q2-FY25,10517.0,1,FY25,Q2
NII,PSU BANK,PNB,Q3-FY25,11032.0,2,FY25,Q3
NII,PSU BANK,PNB,Q4-FY25,10757.0,3,FY25,Q4
NII,PSU BANK,PNB,Q1-FY26,10578.0,4,FY26,Q1
NII,PSU BANK,PNB,Q2-FY26,10469.0,5,FY26,Q2
NII,PSU BANK,PNB,Q3-FY26,10533.0,6,FY26,Q3
NIMs,PSU BANK,PNB,Q1-FY25,0.0307,0,FY25,Q1
NIMs,PSU BANK,PNB,Q2-FY25,0.0292,1,FY25,Q2
NIMs,PSU BANK,PNB,Q3-FY25,0.0292,2,FY25,Q3
NIMs,PSU BANK,PNB,Q4-FY25,0.0281,3,FY25,Q4
NIMs,PSU BANK,PNB,Q1-FY26,0.027,4,FY26,Q1
NIMs,PSU BANK,PNB,Q2-FY26,0.026,5,FY26,Q2
NIMs,PSU BANK,PNB,Q3-FY26,0.0252,6,FY26,Q3
NNPA,PSU BANK,PNB,Q1-FY25,0.006,0,FY25,Q1
NNPA,PSU BANK,PNB,Q2-FY25,0.0046,1,FY25,Q2
NNPA,PSU BANK,PNB,Q3-FY25,0.0041,2,FY25,Q3
NNPA,PSU BANK,PNB,Q4-FY25,0.004,3,FY25,Q4
NNPA,PSU BANK,PNB,Q1-FY26,0.0038,4,FY26,Q1
NNPA,PSU BANK,PNB,Q2-FY26,0.0036,5,FY26,Q2
NNPA,PSU BANK,PNB,Q3-FY26,0.0032,6,FY26,Q3
Opex to AUM,PSU BANK,PNB,Q1-FY25,,0,FY25,Q1
Opex to AUM,PSU BANK,PNB,Q2-FY25,,1,FY25,Q2
Opex to AUM,PSU BANK,PNB,Q3-FY25,0.018,2,FY25,Q3
Opex to AUM,PSU BANK,PNB,Q4-FY25,0.019,3,FY25,Q4
Opex to AUM,PSU BANK,PNB,Q1-FY26,0.019,4,FY26,Q1
Opex to AUM,PSU BANK,PNB,Q2-FY26,0.016,5,FY26,Q2
Opex to AUM,PSU BANK,PNB,Q3-FY26,0.017,6,FY26,Q3
Other Income,PSU BANK,PNB,Q1-FY25,3609.52,0,FY25,Q1
Other Income,PSU BANK,PNB,Q2-FY25,4572.0,1,FY25,Q2
Other Income,PSU BANK,PNB,Q3-FY25,3412.0,2,FY25,Q3
Other Income,PSU BANK,PNB,Q4-FY25,4716.0,3,FY25,Q4
Other Income,PSU BANK,PNB,Q1-FY26,5267.82,4,FY26,Q1
Other Income,PSU BANK,PNB,Q2-FY26,4342.0,5,FY26,Q2
Other Income,PSU BANK,PNB,Q3-FY26,5022.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,PNB,Q1-FY25,3251.53,0,FY25,Q1
PAT (INR Crs),PSU BANK,PNB,Q2-FY25,4303.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,PNB,Q3-FY25,4508.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,PNB,Q4-FY25,4567.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,PNB,Q1-FY26,1675.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,PNB,Q2-FY26,4904.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,PNB,Q3-FY26,5100.0,6,FY26,Q3
PCR,PSU BANK,PNB,Q1-FY25,0.959,0,FY25,Q1
PCR,PSU BANK,PNB,Q2-FY25,0.9667,1,FY25,Q2
PCR,PSU BANK,PNB,Q3-FY25,0.9677,2,FY25,Q3
PCR,PSU BANK,PNB,Q4-FY25,0.9682,3,FY25,Q4
PCR,PSU BANK,PNB,Q1-FY26,0.9688,4,FY26,Q1
PCR,PSU BANK,PNB,Q2-FY26,0.9691,5,FY26,Q2
PCR,PSU BANK,PNB,Q3-FY26,0.9699,6,FY26,Q3
RoA,PSU BANK,PNB,Q1-FY25,0.0082,0,FY25,Q1
RoA,PSU BANK,PNB,Q2-FY25,0.0102,1,FY25,Q2
RoA,PSU BANK,PNB,Q3-FY25,0.0103,2,FY25,Q3
RoA,PSU BANK,PNB,Q4-FY25,0.0102,3,FY25,Q4
RoA,PSU BANK,PNB,Q1-FY26,0.0037,4,FY26,Q1
RoA,PSU BANK,PNB,Q2-FY26,0.0105,5,FY26,Q2
RoA,PSU BANK,PNB,Q3-FY26,0.0106,6,FY26,Q3
RoE,PSU BANK,PNB,Q1-FY25,0.1682,0,FY25,Q1
RoE,PSU BANK,PNB,Q2-FY25,0.1991,1,FY25,Q2
RoE,PSU BANK,PNB,Q3-FY25,0.1922,2,FY25,Q3
RoE,PSU BANK,PNB,Q4-FY25,0.1923,3,FY25,Q4
RoE,PSU BANK,PNB,Q1-FY26,0.0659,4,FY26,Q1
RoE,PSU BANK,PNB,Q2-FY26,0.1795,5,FY26,Q2
RoE,PSU BANK,PNB,Q3-FY26,0.178,6,FY26,Q3
Yields,PSU BANK,PNB,Q1-FY25,0.0833,0,FY25,Q1
Yields,PSU BANK,PNB,Q2-FY25,0.0831,1,FY25,Q2
Yields,PSU BANK,PNB,Q3-FY25,0.0838,2,FY25,Q3
Yields,PSU BANK,PNB,Q4-FY25,0.0836,3,FY25,Q4
Yields,PSU BANK,PNB,Q1-FY26,0.0814,4,FY26,Q1
Yields,PSU BANK,PNB,Q2-FY26,0.079,5,FY26,Q2
Yields,PSU BANK,PNB,Q3-FY26,0.0769,6,FY26,Q3
Advances (INR Crs),PSU BANK,SBIN,Q1-FY25,3812087.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,SBIN,Q2-FY25,3920719.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,SBIN,Q3-FY25,4067752.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,SBIN,Q4-FY25,4220703.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,SBIN,Q1-FY26,4254516.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,SBIN,Q2-FY26,4419674.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,SBIN,Q3-FY26,4683508.0,6,FY26,Q3
CAR,PSU BANK,SBIN,Q1-FY25,0.1386,0,FY25,Q1
CAR,PSU BANK,SBIN,Q2-FY25,0.1376,1,FY25,Q2
CAR,PSU BANK,SBIN,Q3-FY25,0.1303,2,FY25,Q3
CAR,PSU BANK,SBIN,Q4-FY25,0.1425,3,FY25,Q4
CAR,PSU BANK,SBIN,Q1-FY26,0.1463,4,FY26,Q1
CAR,PSU BANK,SBIN,Q2-FY26,0.1463,5,FY26,Q2
CAR,PSU BANK,SBIN,Q3-FY26,0.1404,6,FY26,Q3
CASA,PSU BANK,SBIN,Q1-FY25,,0,FY25,Q1
CASA,PSU BANK,SBIN,Q2-FY25,,1,FY25,Q2
CASA,PSU BANK,SBIN,Q3-FY25,,2,FY25,Q3
CASA,PSU BANK,SBIN,Q4-FY25,,3,FY25,Q4
CASA,PSU BANK,SBIN,Q1-FY26,,4,FY26,Q1
CASA,PSU BANK,SBIN,Q2-FY26,,5,FY26,Q2
CASA,PSU BANK,SBIN,Q3-FY26,,6,FY26,Q3
CoFs,PSU BANK,SBIN,Q1-FY25,0.05,0,FY25,Q1
CoFs,PSU BANK,SBIN,Q2-FY25,0.0503,1,FY25,Q2
CoFs,PSU BANK,SBIN,Q3-FY25,0.0507,2,FY25,Q3
CoFs,PSU BANK,SBIN,Q4-FY25,0.0511,3,FY25,Q4
CoFs,PSU BANK,SBIN,Q1-FY26,0.0521,4,FY26,Q1
CoFs,PSU BANK,SBIN,Q2-FY26,0.0513,5,FY26,Q2
CoFs,PSU BANK,SBIN,Q3-FY26,0.0507,6,FY26,Q3
Cost to Income,PSU BANK,SBIN,Q1-FY25,0.4942,0,FY25,Q1
Cost to Income,PSU BANK,SBIN,Q2-FY25,0.4851,1,FY25,Q2
Cost to Income,PSU BANK,SBIN,Q3-FY25,0.5513,2,FY25,Q3
Cost to Income,PSU BANK,SBIN,Q4-FY25,0.5329,3,FY25,Q4
Cost to Income,PSU BANK,SBIN,Q1-FY26,0.474,4,FY26,Q1
Cost to Income,PSU BANK,SBIN,Q2-FY26,0.4928,5,FY26,Q2
Cost to Income,PSU BANK,SBIN,Q3-FY26,0.4829,6,FY26,Q3
Credit Cost,PSU BANK,SBIN,Q1-FY25,0.0048,0,FY25,Q1
Credit Cost,PSU BANK,SBIN,Q2-FY25,0.0043,1,FY25,Q2
Credit Cost,PSU BANK,SBIN,Q3-FY25,0.0037,2,FY25,Q3
Credit Cost,PSU BANK,SBIN,Q4-FY25,0.0038,3,FY25,Q4
Credit Cost,PSU BANK,SBIN,Q1-FY26,0.0047,4,FY26,Q1
Credit Cost,PSU BANK,SBIN,Q2-FY26,0.0043,5,FY26,Q2
Credit Cost,PSU BANK,SBIN,Q3-FY26,0.0029,6,FY26,Q3
Deposits (INR Crs),PSU BANK,SBIN,Q1-FY25,4901726.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,SBIN,Q2-FY25,5117285.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,SBIN,Q3-FY25,5229384.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,SBIN,Q4-FY25,5382190.0,3,FY25,Q4
Deposits (INR Crs),PSU BANK,SBIN,Q1-FY26,5473254.0,4,FY26,Q1
Deposits (INR Crs),PSU BANK,SBIN,Q2-FY26,5591700.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,SBIN,Q3-FY26,5701309.0,6,FY26,Q3
GNPA,PSU BANK,SBIN,Q1-FY25,0.0221,0,FY25,Q1
GNPA,PSU BANK,SBIN,Q2-FY25,0.0213,1,FY25,Q2
GNPA,PSU BANK,SBIN,Q3-FY25,0.0207,2,FY25,Q3
GNPA,PSU BANK,SBIN,Q4-FY25,0.0182,3,FY25,Q4
GNPA,PSU BANK,SBIN,Q1-FY26,0.0183,4,FY26,Q1
GNPA,PSU BANK,SBIN,Q2-FY26,0.0173,5,FY26,Q2
GNPA,PSU BANK,SBIN,Q3-FY26,0.0157,6,FY26,Q3
Leverage,PSU BANK,SBIN,Q1-FY25,,0,FY25,Q1
Leverage,PSU BANK,SBIN,Q2-FY25,,1,FY25,Q2
Leverage,PSU BANK,SBIN,Q3-FY25,,2,FY25,Q3
Leverage,PSU BANK,SBIN,Q4-FY25,,3,FY25,Q4
Leverage,PSU BANK,SBIN,Q1-FY26,,4,FY26,Q1
Leverage,PSU BANK,SBIN,Q2-FY26,,5,FY26,Q2
Leverage,PSU BANK,SBIN,Q3-FY26,,6,FY26,Q3
NII,PSU BANK,SBIN,Q1-FY25,41125.0,0,FY25,Q1
NII,PSU BANK,SBIN,Q2-FY25,41620.0,1,FY25,Q2
NII,PSU BANK,SBIN,Q3-FY25,41446.0,2,FY25,Q3
NII,PSU BANK,SBIN,Q4-FY25,42775.0,3,FY25,Q4
NII,PSU BANK,SBIN,Q1-FY26,41071.0,4,FY26,Q1
NII,PSU BANK,SBIN,Q2-FY26,42984.0,5,FY26,Q2
NII,PSU BANK,SBIN,Q3-FY26,45190.0,6,FY26,Q3
NIMs,PSU BANK,SBIN,Q1-FY25,0.0335,0,FY25,Q1
NIMs,PSU BANK,SBIN,Q2-FY25,0.0331,1,FY25,Q2
NIMs,PSU BANK,SBIN,Q3-FY25,0.0325,2,FY25,Q3
NIMs,PSU BANK,SBIN,Q4-FY25,0.0322,3,FY25,Q4
NIMs,PSU BANK,SBIN,Q1-FY26,0.0302,4,FY26,Q1
NIMs,PSU BANK,SBIN,Q2-FY26,0.0305,5,FY26,Q2
NIMs,PSU BANK,SBIN,Q3-FY26,0.0299,6,FY26,Q3
NNPA,PSU BANK,SBIN,Q1-FY25,0.0057,0,FY25,Q1
NNPA,PSU BANK,SBIN,Q2-FY25,0.0053,1,FY25,Q2
NNPA,PSU BANK,SBIN,Q3-FY25,0.0053,2,FY25,Q3
NNPA,PSU BANK,SBIN,Q4-FY25,0.0047,3,FY25,Q4
NNPA,PSU BANK,SBIN,Q1-FY26,0.0047,4,FY26,Q1
NNPA,PSU BANK,SBIN,Q2-FY26,0.0042,5,FY26,Q2
NNPA,PSU BANK,SBIN,Q3-FY26,0.0039,6,FY26,Q3
Opex to AUM,PSU BANK,SBIN,Q1-FY25,0.0167,0,FY25,Q1
Opex to AUM,PSU BANK,SBIN,Q2-FY25,0.0176,1,FY25,Q2
Opex to AUM,PSU BANK,SBIN,Q3-FY25,0.0179,2,FY25,Q3
Opex to AUM,PSU BANK,SBIN,Q4-FY25,0.0215,3,FY25,Q4
Opex to AUM,PSU BANK,SBIN,Q1-FY26,0.0166,4,FY26,Q1
Opex to AUM,PSU BANK,SBIN,Q2-FY26,0.018,5,FY26,Q2
Opex to AUM,PSU BANK,SBIN,Q3-FY26,0.018,6,FY26,Q3
Other Income,PSU BANK,SBIN,Q1-FY25,11162.0,0,FY25,Q1
Other Income,PSU BANK,SBIN,Q2-FY25,15271.0,1,FY25,Q2
Other Income,PSU BANK,SBIN,Q3-FY25,11041.0,2,FY25,Q3
Other Income,PSU BANK,SBIN,Q4-FY25,24210.0,3,FY25,Q4
Other Income,PSU BANK,SBIN,Q1-FY26,17346.0,4,FY26,Q1
Other Income,PSU BANK,SBIN,Q2-FY26,19919.0,5,FY26,Q2
Other Income,PSU BANK,SBIN,Q3-FY26,18359.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,SBIN,Q1-FY25,17035.0,0,FY25,Q1
PAT (INR Crs),PSU BANK,SBIN,Q2-FY25,18331.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,SBIN,Q3-FY25,16891.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,SBIN,Q4-FY25,18643.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,SBIN,Q1-FY26,19160.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,SBIN,Q2-FY26,20160.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,SBIN,Q3-FY26,21028.0,6,FY26,Q3
PCR,PSU BANK,SBIN,Q1-FY25,0.7441,0,FY25,Q1
PCR,PSU BANK,SBIN,Q2-FY25,0.9221,1,FY25,Q2
PCR,PSU BANK,SBIN,Q3-FY25,0.9174,2,FY25,Q3
PCR,PSU BANK,SBIN,Q4-FY25,0.9208,3,FY25,Q4
PCR,PSU BANK,SBIN,Q1-FY26,0.9171,4,FY26,Q1
PCR,PSU BANK,SBIN,Q2-FY26,0.9229,5,FY26,Q2
PCR,PSU BANK,SBIN,Q3-FY26,0.9237,6,FY26,Q3
RoA,PSU BANK,SBIN,Q1-FY25,0.011,0,FY25,Q1
RoA,PSU BANK,SBIN,Q2-FY25,0.0117,1,FY25,Q2
RoA,PSU BANK,SBIN,Q3-FY25,0.0109,2,FY25,Q3
RoA,PSU BANK,SBIN,Q4-FY25,0.011,3,FY25,Q4
RoA,PSU BANK,SBIN,Q1-FY26,0.0114,4,FY26,Q1
RoA,PSU BANK,SBIN,Q2-FY26,0.0117,5,FY26,Q2
RoA,PSU BANK,SBIN,Q3-FY26,0.0119,6,FY26,Q3
RoE,PSU BANK,SBIN,Q1-FY25,0.2098,0,FY25,Q1
RoE,PSU BANK,SBIN,Q2-FY25,0.2178,1,FY25,Q2
RoE,PSU BANK,SBIN,Q3-FY25,0.2146,2,FY25,Q3
RoE,PSU BANK,SBIN,Q4-FY25,0.1987,3,FY25,Q4
RoE,PSU BANK,SBIN,Q1-FY26,0.197,4,FY26,Q1
RoE,PSU BANK,SBIN,Q2-FY26,0.2021,5,FY26,Q2
RoE,PSU BANK,SBIN,Q3-FY26,0.2068,6,FY26,Q3
Yields,PSU BANK,SBIN,Q1-FY25,0.072,0,FY25,Q1
Yields,PSU BANK,SBIN,Q2-FY25,0.0893,1,FY25,Q2
Yields,PSU BANK,SBIN,Q3-FY25,0.0894,2,FY25,Q3
Yields,PSU BANK,SBIN,Q4-FY25,0.0898,3,FY25,Q4
Yields,PSU BANK,SBIN,Q1-FY26,0.0878,4,FY26,Q1
Yields,PSU BANK,SBIN,Q2-FY26,0.0868,5,FY26,Q2
Yields,PSU BANK,SBIN,Q3-FY26,0.0704,6,FY26,Q3
Advances (INR Crs),PSU BANK,UNIONBANK,Q1-FY25,912214.0,0,FY25,Q1
Advances (INR Crs),PSU BANK,UNIONBANK,Q2-FY25,928800.0,1,FY25,Q2
Advances (INR Crs),PSU BANK,UNIONBANK,Q3-FY25,949164.0,2,FY25,Q3
Advances (INR Crs),PSU BANK,UNIONBANK,Q4-FY25,982894.0,3,FY25,Q4
Advances (INR Crs),PSU BANK,UNIONBANK,Q1-FY26,974489.0,4,FY26,Q1
Advances (INR Crs),PSU BANK,UNIONBANK,Q2-FY26,975100.0,5,FY26,Q2
Advances (INR Crs),PSU BANK,UNIONBANK,Q3-FY26,1016805.0,6,FY26,Q3
CAR,PSU BANK,UNIONBANK,Q1-FY25,0.183,0,FY25,Q1
CAR,PSU BANK,UNIONBANK,Q2-FY25,0.1713,1,FY25,Q2
CAR,PSU BANK,UNIONBANK,Q3-FY25,0.1671,2,FY25,Q3
CAR,PSU BANK,UNIONBANK,Q4-FY25,0.1802,3,FY25,Q4
CAR,PSU BANK,UNIONBANK,Q1-FY26,0.183,4,FY26,Q1
CAR,PSU BANK,UNIONBANK,Q2-FY26,0.1707,5,FY26,Q2
CAR,PSU BANK,UNIONBANK,Q3-FY26,0.1649,6,FY26,Q3
CASA,PSU BANK,UNIONBANK,Q1-FY25,0.334,0,FY25,Q1
CASA,PSU BANK,UNIONBANK,Q2-FY25,0.3272,1,FY25,Q2
CASA,PSU BANK,UNIONBANK,Q3-FY25,0.3343,2,FY25,Q3
CASA,PSU BANK,UNIONBANK,Q4-FY25,0.3352,3,FY25,Q4
CASA,PSU BANK,UNIONBANK,Q1-FY26,0.3252,4,FY26,Q1
CASA,PSU BANK,UNIONBANK,Q2-FY26,0.3256,5,FY26,Q2
CASA,PSU BANK,UNIONBANK,Q3-FY26,0.3396,6,FY26,Q3
CoFs,PSU BANK,UNIONBANK,Q1-FY25,0.0489,0,FY25,Q1
CoFs,PSU BANK,UNIONBANK,Q2-FY25,0.0504,1,FY25,Q2
CoFs,PSU BANK,UNIONBANK,Q3-FY25,0.0489,2,FY25,Q3
CoFs,PSU BANK,UNIONBANK,Q4-FY25,0.048,3,FY25,Q4
CoFs,PSU BANK,UNIONBANK,Q1-FY26,0.0479,4,FY26,Q1
CoFs,PSU BANK,UNIONBANK,Q2-FY26,0.0474,5,FY26,Q2
CoFs,PSU BANK,UNIONBANK,Q3-FY26,0.046,6,FY26,Q3
Cost to Income,PSU BANK,UNIONBANK,Q1-FY25,0.4407729329789526,0,FY25,Q1
Cost to Income,PSU BANK,UNIONBANK,Q2-FY25,0.4356,1,FY25,Q2
Cost to Income,PSU BANK,UNIONBANK,Q3-FY25,0.4514,2,FY25,Q3
Cost to Income,PSU BANK,UNIONBANK,Q4-FY25,0.489,3,FY25,Q4
Cost to Income,PSU BANK,UNIONBANK,Q1-FY26,0.4919,4,FY26,Q1
Cost to Income,PSU BANK,UNIONBANK,Q2-FY26,0.5065,5,FY26,Q2
Cost to Income,PSU BANK,UNIONBANK,Q3-FY26,0.4995,6,FY26,Q3
Credit Cost,PSU BANK,UNIONBANK,Q1-FY25,0.0073,0,FY25,Q1
Credit Cost,PSU BANK,UNIONBANK,Q2-FY25,0.0109,1,FY25,Q2
Credit Cost,PSU BANK,UNIONBANK,Q3-FY25,0.0063,2,FY25,Q3
Credit Cost,PSU BANK,UNIONBANK,Q4-FY25,0.0069,3,FY25,Q4
Credit Cost,PSU BANK,UNIONBANK,Q1-FY26,0.0047,4,FY26,Q1
Credit Cost,PSU BANK,UNIONBANK,Q2-FY26,0.0022,5,FY26,Q2
Credit Cost,PSU BANK,UNIONBANK,Q3-FY26,0.0009,6,FY26,Q3
Deposits (INR Crs),PSU BANK,UNIONBANK,Q1-FY25,1196548.0,0,FY25,Q1
Deposits (INR Crs),PSU BANK,UNIONBANK,Q2-FY25,1211600.0,1,FY25,Q2
Deposits (INR Crs),PSU BANK,UNIONBANK,Q3-FY25,1182622.0,2,FY25,Q3
Deposits (INR Crs),PSU BANK,UNIONBANK,Q4-FY25,1272247.0,3,FY25,Q4
Deposits (INR Crs),PSU BANK,UNIONBANK,Q1-FY26,1239933.0,4,FY26,Q1
Deposits (INR Crs),PSU BANK,UNIONBANK,Q2-FY26,1234600.0,5,FY26,Q2
Deposits (INR Crs),PSU BANK,UNIONBANK,Q3-FY26,1222856.0,6,FY26,Q3
GNPA,PSU BANK,UNIONBANK,Q1-FY25,0.0454,0,FY25,Q1
GNPA,PSU BANK,UNIONBANK,Q2-FY25,0.0436,1,FY25,Q2
GNPA,PSU BANK,UNIONBANK,Q3-FY25,0.0385,2,FY25,Q3
GNPA,PSU BANK,UNIONBANK,Q4-FY25,0.036,3,FY25,Q4
GNPA,PSU BANK,UNIONBANK,Q1-FY26,0.0352,4,FY26,Q1
GNPA,PSU BANK,UNIONBANK,Q2-FY26,0.0329,5,FY26,Q2
GNPA,PSU BANK,UNIONBANK,Q3-FY26,0.0306,6,FY26,Q3
Leverage,PSU BANK,UNIONBANK,Q1-FY25,,0,FY25,Q1
Leverage,PSU BANK,UNIONBANK,Q2-FY25,,1,FY25,Q2
Leverage,PSU BANK,UNIONBANK,Q3-FY25,,2,FY25,Q3
Leverage,PSU BANK,UNIONBANK,Q4-FY25,,3,FY25,Q4
Leverage,PSU BANK,UNIONBANK,Q1-FY26,,4,FY26,Q1
Leverage,PSU BANK,UNIONBANK,Q2-FY26,,5,FY26,Q2
Leverage,PSU BANK,UNIONBANK,Q3-FY26,,6,FY26,Q3
NII,PSU BANK,UNIONBANK,Q1-FY25,9412.0,0,FY25,Q1
NII,PSU BANK,UNIONBANK,Q2-FY25,9047.0,1,FY25,Q2
NII,PSU BANK,UNIONBANK,Q3-FY25,9240.0,2,FY25,Q3
NII,PSU BANK,UNIONBANK,Q4-FY25,9514.0,3,FY25,Q4
NII,PSU BANK,UNIONBANK,Q1-FY26,9113.0,4,FY26,Q1
NII,PSU BANK,UNIONBANK,Q2-FY26,9328.0,5,FY26,Q2
NII,PSU BANK,UNIONBANK,Q3-FY26,9328.0,6,FY26,Q3
NIMs,PSU BANK,UNIONBANK,Q1-FY25,0.0305,0,FY25,Q1
NIMs,PSU BANK,UNIONBANK,Q2-FY25,0.029,1,FY25,Q2
NIMs,PSU BANK,UNIONBANK,Q3-FY25,0.0291,2,FY25,Q3
NIMs,PSU BANK,UNIONBANK,Q4-FY25,0.0287,3,FY25,Q4
NIMs,PSU BANK,UNIONBANK,Q1-FY26,0.0276,4,FY26,Q1
NIMs,PSU BANK,UNIONBANK,Q2-FY26,0.0267,5,FY26,Q2
NIMs,PSU BANK,UNIONBANK,Q3-FY26,0.0276,6,FY26,Q3
NNPA,PSU BANK,UNIONBANK,Q1-FY25,0.009,0,FY25,Q1
NNPA,PSU BANK,UNIONBANK,Q2-FY25,0.0098,1,FY25,Q2
NNPA,PSU BANK,UNIONBANK,Q3-FY25,0.0082,2,FY25,Q3
NNPA,PSU BANK,UNIONBANK,Q4-FY25,0.0063,3,FY25,Q4
NNPA,PSU BANK,UNIONBANK,Q1-FY26,0.0062,4,FY26,Q1
NNPA,PSU BANK,UNIONBANK,Q2-FY26,0.0055,5,FY26,Q2
NNPA,PSU BANK,UNIONBANK,Q3-FY26,0.0051,6,FY26,Q3
Opex to AUM,PSU BANK,UNIONBANK,Q1-FY25,,0,FY25,Q1
Opex to AUM,PSU BANK,UNIONBANK,Q2-FY25,,1,FY25,Q2
Opex to AUM,PSU BANK,UNIONBANK,Q3-FY25,,2,FY25,Q3
Opex to AUM,PSU BANK,UNIONBANK,Q4-FY25,,3,FY25,Q4
Opex to AUM,PSU BANK,UNIONBANK,Q1-FY26,,4,FY26,Q1
Opex to AUM,PSU BANK,UNIONBANK,Q2-FY26,,5,FY26,Q2
Opex to AUM,PSU BANK,UNIONBANK,Q3-FY26,,6,FY26,Q3
Other Income,PSU BANK,UNIONBANK,Q1-FY25,4509.0,0,FY25,Q1
Other Income,PSU BANK,UNIONBANK,Q2-FY25,5328.0,1,FY25,Q2
Other Income,PSU BANK,UNIONBANK,Q3-FY25,4417.0,2,FY25,Q3
Other Income,PSU BANK,UNIONBANK,Q4-FY25,5559.0,3,FY25,Q4
Other Income,PSU BANK,UNIONBANK,Q1-FY26,4486.0,4,FY26,Q1
Other Income,PSU BANK,UNIONBANK,Q2-FY26,4996.0,5,FY26,Q2
Other Income,PSU BANK,UNIONBANK,Q3-FY26,4541.0,6,FY26,Q3
PAT (INR Crs),PSU BANK,UNIONBANK,Q1-FY25,3679.0,0,FY25,Q1
PAT (INR Crs),PSU BANK,UNIONBANK,Q2-FY25,4720.0,1,FY25,Q2
PAT (INR Crs),PSU BANK,UNIONBANK,Q3-FY25,4604.0,2,FY25,Q3
PAT (INR Crs),PSU BANK,UNIONBANK,Q4-FY25,4985.0,3,FY25,Q4
PAT (INR Crs),PSU BANK,UNIONBANK,Q1-FY26,4116.0,4,FY26,Q1
PAT (INR Crs),PSU BANK,UNIONBANK,Q2-FY26,4249.0,5,FY26,Q2
PAT (INR Crs),PSU BANK,UNIONBANK,Q3-FY26,5017.0,6,FY26,Q3
PCR,PSU BANK,UNIONBANK,Q1-FY25,0.9349,0,FY25,Q1
PCR,PSU BANK,UNIONBANK,Q2-FY25,0.9279,1,FY25,Q2
PCR,PSU BANK,UNIONBANK,Q3-FY25,0.9342,2,FY25,Q3
PCR,PSU BANK,UNIONBANK,Q4-FY25,0.9461,3,FY25,Q4
PCR,PSU BANK,UNIONBANK,Q1-FY26,0.9465,4,FY26,Q1
PCR,PSU BANK,UNIONBANK,Q2-FY26,0.9513,5,FY26,Q2
PCR,PSU BANK,UNIONBANK,Q3-FY26,0.9513,6,FY26,Q3
RoA,PSU BANK,UNIONBANK,Q1-FY25,0.0106,0,FY25,Q1
RoA,PSU BANK,UNIONBANK,Q2-FY25,0.0135,1,FY25,Q2
RoA,PSU BANK,UNIONBANK,Q3-FY25,0.013,2,FY25,Q3
RoA,PSU BANK,UNIONBANK,Q4-FY25,0.0135,3,FY25,Q4
RoA,PSU BANK,UNIONBANK,Q1-FY26,0.0111,4,FY26,Q1
RoA,PSU BANK,UNIONBANK,Q2-FY26,0.0116,5,FY26,Q2
RoA,PSU BANK,UNIONBANK,Q3-FY26,0.0135,6,FY26,Q3
RoE,PSU BANK,UNIONBANK,Q1-FY25,0.157,0,FY25,Q1
RoE,PSU BANK,UNIONBANK,Q2-FY25,0.191,1,FY25,Q2
RoE,PSU BANK,UNIONBANK,Q3-FY25,0.1775,2,FY25,Q3
RoE,PSU BANK,UNIONBANK,Q4-FY25,0.1907,3,FY25,Q4
RoE,PSU BANK,UNIONBANK,Q1-FY26,0.1515,4,FY26,Q1
RoE,PSU BANK,UNIONBANK,Q2-FY26,0.1508,5,FY26,Q2
RoE,PSU BANK,UNIONBANK,Q3-FY26,0.1709,6,FY26,Q3
Yields,PSU BANK,UNIONBANK,Q1-FY25,0.076,0,FY25,Q1
Yields,PSU BANK,UNIONBANK,Q2-FY25,0.087,1,FY25,Q2
Yields,PSU BANK,UNIONBANK,Q3-FY25,0.0878,2,FY25,Q3
Yields,PSU BANK,UNIONBANK,Q4-FY25,0.0872,3,FY25,Q4
Yields,PSU BANK,UNIONBANK,Q1-FY26,0.085,4,FY26,Q1
Yields,PSU BANK,UNIONBANK,Q2-FY26,0.0834,5,FY26,Q2
Yields,PSU BANK,UNIONBANK,Q3-FY26,0.0827,6,FY26,Q3
