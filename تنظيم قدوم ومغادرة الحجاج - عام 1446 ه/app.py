# File: app.py

from flask import Flask, render_template, url_for
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# مكتبات إضافية
import seaborn as sns
import matplotlib.pyplot as plt
import arabic_reshaper
from bidi.algorithm import get_display
import os

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# ────────────────────────────────────────────────
# 1) قراءة البيانات وتنظيفها
# ────────────────────────────────────────────────
df = pd.read_csv("Arrival_Report.csv")
df['Arrival date'] = pd.to_datetime(df['Arrival date'], dayfirst=True, errors='coerce')
df['Arrival type'] = df['Arrival type'].replace({"جوا": "جو", "برا": "بر"})
df['Arrival city'] = df['Arrival city'].astype(str).str.strip()
df["Num of pilgrims"] = pd.to_numeric(df["Num of pilgrims"], errors="coerce")
df["Num of pilgrims"].fillna(0, inplace=True)

# ────────────────────────────────────────────────
# 2) إنشاء رسوم Plotly الأساسية
# ────────────────────────────────────────────────

# --- الرسم 1: Stacked Bar لأعلى 15 دولة حسب وسيلة القدوم ---
total_by_country = (
    df.groupby("Countries")["Num of pilgrims"]
      .sum()
      .reset_index()
      .sort_values("Num of pilgrims", ascending=False)
)
top15_countries = total_by_country.head(15)["Countries"].tolist()

df_top15_country = df[df["Countries"].isin(top15_countries)].copy()
grouped_stack = (
    df_top15_country.groupby(["Countries", "Arrival type"])["Num of pilgrims"]
      .sum()
      .reset_index()
)

fig1 = px.bar(
    grouped_stack,
    x="Countries",
    y="Num of pilgrims",
    color="Arrival type",
    barmode="stack",
    labels={
        "Countries": "الدولة",
        "Num of pilgrims": "عدد الحجاج",
        "Arrival type": "وسيلة القدوم"
    },
    title="توزيع عدد الحجاج لأعلى 15 دولة حسب وسيلة القدوم",
    color_discrete_map={
        "جو": "#2E86C1",
        "بحر": "#0D47A1",
        "بر": "#5D4037"
    }
)
chart1_replaced = fig1.to_json()

# --- الرسم 2: Pie Chart لتوزيع الحجاج حسب وسيلة القدوم ---
grouped_type = (
    df.groupby("Arrival type")["Num of pilgrims"]
      .sum()
      .reset_index()
)
fig2 = px.pie(
    grouped_type,
    names="Arrival type",
    values="Num of pilgrims",
    title="توزيع الحجاج حسب وسيلة القدوم",
    labels={"Arrival type": "وسيلة القدوم", "Num of pilgrims": "عدد الحجاج"},
    color_discrete_map={
        "جو": "#2E86C1",
        "بحر": "#0D47A1",
        "بر": "#5D4037"
    }
)
chart2 = fig2.to_json()

# --- الرسم 3: Line Plot لعدد الحجاج حسب تاريخ الوصول بين 29/4 و1/6 ---
start_date = pd.to_datetime("2025-04-29")
end_date   = pd.to_datetime("2025-06-01")
df_date_filtered = df[
    (df["Arrival date"] >= start_date) & (df["Arrival date"] <= end_date)
].copy()

by_day = (
    df_date_filtered.groupby("Arrival date")["Num of pilgrims"]
      .sum()
      .reset_index()
)
fig3 = px.line(
    by_day,
    x="Arrival date",
    y="Num of pilgrims",
    markers=True,
    title="عدد الحجاج حسب تاريخ الوصول (29/4 – 1/6)",
    labels={"Arrival date": "تاريخ الوصول", "Num of pilgrims": "عدد الحجاج"}
)
chart3 = fig3.to_json()

# --- الرسم 4: Bar لتنظيم المدن إلى (جدة، المدينة المنورة، أخرى) ---
jeddah_count = df[df["Arrival city"] == "جدة"]["Num of pilgrims"].sum()
medina_count = df[df["Arrival city"] == "المدينة المنورة"]["Num of pilgrims"].sum()
others_count = df[~df["Arrival city"].isin(["جدة", "المدينة المنورة"])]["Num of pilgrims"].sum()

df_city_bar = pd.DataFrame({
    "Arrival city": ["جدة", "المدينة المنورة", "أخرى"],
    "Num of pilgrims": [jeddah_count, medina_count, others_count]
})
fig4 = px.bar(
    df_city_bar,
    x="Arrival city",
    y="Num of pilgrims",
    title="عدد الحجاج حسب المدينة (جدة، المدينة المنورة، أخرى)",
    labels={"Arrival city": "المدينة", "Num of pilgrims": "عدد الحجاج"},
    color="Arrival city",
    color_discrete_map={
        "جدة": "#D35400",
        "المدينة المنورة": "#8E44AD",
        "أخرى": "#95A5A6"
    }
)
chart4 = fig4.to_json()

# --- الرسم 5: Sankey Plot لتدفق الحجاج لأعلى 15 دولة ---
countries_sankey = top15_countries.copy()
arrival_types_list = df["Arrival type"].unique().tolist()

nodes = countries_sankey + arrival_types_list
country_to_index = {country: idx for idx, country in enumerate(countries_sankey)}
arrival_to_index = {
    arr: len(countries_sankey) + i for i, arr in enumerate(arrival_types_list)
}

grouped_sankey_full = (
    df[df["Countries"].isin(top15_countries)]
      .groupby(["Countries", "Arrival type"])["Num of pilgrims"]
      .sum()
      .reset_index()
)

sources = []
targets = []
values = []
link_colors = []

for _, row in grouped_sankey_full.iterrows():
    src_country = row["Countries"]
    trg_arrival = row["Arrival type"]
    pilgrims_count = row["Num of pilgrims"]

    sources.append(country_to_index[src_country])
    targets.append(arrival_to_index[trg_arrival])
    values.append(pilgrims_count)

    if trg_arrival == "جو":
        link_colors.append("#2E86C1")
    elif trg_arrival == "بحر":
        link_colors.append("#0D47A1")
    else:  # trg_arrival == "بر"
        link_colors.append("#5D4037")

fig5 = go.Figure(
    data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color="darkslategray"
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors
        )
    )]
)
fig5.update_layout(
    title_text="تدفق الحجاج لأعلى 15 دولة",
    font=dict(size=12, family='Tajawal, sans-serif')
)
chart5 = fig5.to_json()

# --- الرسم 7: Pie Summary باستخدام Plotly ---
def map_city_group_ar(city):
    if city == 'جدة':
        return 'جدة'
    elif city == 'المدينة المنورة':
        return 'المدينة المنورة'
    else:
        return 'أخرى'

df['City_Group'] = df['Arrival city'].apply(map_city_group_ar)
country_totals_ar = df.groupby('Countries')['Num of pilgrims'].sum().sort_values(ascending=False)
top10_countries_ar = country_totals_ar.head(10).index.tolist()

summary_data = []
for country in top10_countries_ar:
    total_p = df[df["Countries"] == country]["Num of pilgrims"].sum()
    top_method = (
        df[df["Countries"] == country]
        .groupby("Arrival type")["Num of pilgrims"]
        .sum()
        .idxmax()
    )
    top_city = (
        df[df["Countries"] == country]
        .groupby("Arrival city")["Num of pilgrims"]
        .sum()
        .idxmax()
    )
    summary_data.append({
        "country": country,
        "pilgrims": total_p,
        "top_method": top_method,
        "top_city": top_city
    })

df_summary = pd.DataFrame(summary_data)
fig7 = px.pie(
    df_summary,
    names="country",
    values="pilgrims",
    title="ملخص أعلى 10 دول: العدد – الوسيلة – المدينة",
    hover_data=["top_method", "top_city"],
    labels={
        "country": "الدولة",
        "pilgrims": "عدد الحجاج",
        "top_method": "وسيلة القدوم",
        "top_city": "أكثر مدينة وصول"
    }
)
fig7.update_traces(
    hovertemplate="<b>%{label}</b><br>عدد الحجاج: %{value:,}<br>"
                  "الوسيلة: %{customdata[0]}<br>أكثر مدينة: %{customdata[1]}<extra></extra>"
)
chart7 = fig7.to_json()

# --- خريطة حرارية (Heatmap) ---
pivot = df[df['Countries'].isin(top10_countries_ar)].pivot_table(
    values='Num of pilgrims',
    index='Countries',
    columns='City_Group',
    aggfunc='sum',
    fill_value=0
)
pivot = pivot[['جدة', 'المدينة المنورة', 'أخرى']]
pivot = pivot.loc[top10_countries_ar]

pivot.index = [get_display(arabic_reshaper.reshape(idx)) for idx in pivot.index]
pivot.columns = [get_display(arabic_reshaper.reshape(col)) for col in pivot.columns]

plt.figure(figsize=(8, 6))
sns.heatmap(
    pivot,
    cmap="YlGnBu",
    linewidths=0.5,
    annot=True,
    fmt=".0f",
    cbar_kws={'label': get_display(arabic_reshaper.reshape("عدد الحجاج"))}
)
plt.title(get_display(arabic_reshaper.reshape("خريطة حرارية: أعلى 10 دول × (جدة، المدينة المنورة، أخرى)")), fontsize=14, pad=10)
plt.xlabel(get_display(arabic_reshaper.reshape("مدن الوصول")), fontsize=12)
plt.ylabel(get_display(arabic_reshaper.reshape("الدولة")), fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()

os.makedirs("static", exist_ok=True)
plt.savefig("static/heatmap_top10.png")
plt.close()

# ────────────────────────────────────────────────
# 3) مسارات التطبيق
# ────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/charts')
def charts():
    return render_template(
        'charts.html',
        chart1_replaced=json.loads(chart1_replaced),
        chart2=json.loads(chart2),
        chart3=json.loads(chart3),
        chart4=json.loads(chart4),
        chart5=json.loads(chart5),
        chart7=json.loads(chart7),
        heatmap_url=url_for('static', filename='heatmap_top10.png')
    )

@app.route('/bar_chart_race')
def bar_chart_race():
    return render_template('bar_chart_race.html')

@app.route('/radial_chart')
def radial_chart():
    return render_template('radial_chart.html')

@app.route('/objectives')
def objectives():
    return render_template('objectives.html')

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/parking')
def parking():
    return render_template('parking.html')

@app.route('/departure_1446')
def departure():
    return render_template('departure_1446.html')

@app.route('/departure-stats')
def departure_stats():
    return render_template('departure-analysis-hajj1446.html')

@app.route('/future')
def future():
    return render_template('future.html')


# ────────────────────────────────────────────────
# 4) تشغيل التطبيق
# ────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
