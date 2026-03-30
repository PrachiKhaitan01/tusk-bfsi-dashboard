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
