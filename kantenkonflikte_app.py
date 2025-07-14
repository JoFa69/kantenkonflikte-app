import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Seitenkonfiguration
st.set_page_config(
    page_title="Kantenkonflikte Erkennung - VBL",
    page_icon="🚌",
    layout="wide"
)

# Hilfsfunktionen
def create_sample_data():
    """Erstellt Beispieldaten für Demonstration"""
    sample_data = {
        'Liniennummer': ['1', '1', '2', '2', '3', '3', '4', '1', '2'],
        'Fahrt_ID': ['F001', 'F002', 'F003', 'F004', 'F005', 'F006', 'F007', 'F008', 'F009'],
        'Haltestelle': ['Bahnhof', 'Bahnhof', 'Bahnhof', 'Bahnhof', 'Bahnhof', 'Bahnhof', 'Bahnhof', 'Bahnhof', 'Bahnhof'],
        'Ankunft': ['08:00', '08:01', '08:02', '08:15', '08:30', '08:31', '08:45', '08:02', '08:03'],
        'Abfahrt': ['08:05', '08:06', '08:07', '08:20', '08:35', '08:36', '08:50', '08:07', '08:08'],
        'Haltekante': ['A', 'A', 'A', 'B', 'A', 'A', 'B', 'B', 'B'],
        'Fahrzeuglänge': [12, 12, 18, 12, 12, 18, 12, 12, 18],
        'Kantenlänge': [25, 25, 25, 30, 25, 25, 30, 30, 30]
    }
    return pd.DataFrame(sample_data)

def time_to_minutes(time_str):
    """Konvertiert Zeit-String zu Minuten seit Mitternacht"""
    try:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    except:
        return 0

def detect_conflicts(df, time_buffer=2):
    """Erkennt Kantenkonflikte basierend auf Zeitfenster und Fahrzeuglängen"""
    conflicts = []
    
    # Zeitkonvertierung
    df['Ankunft_min'] = df['Ankunft'].apply(time_to_minutes)
    df['Abfahrt_min'] = df['Abfahrt'].apply(time_to_minutes)
    
    # Gruppierung nach Haltekante
    for kante in df['Haltekante'].unique():
        kante_data = df[df['Haltekante'] == kante].copy()
        
        # Prüfung aller Zeitfenster
        for idx, row in kante_data.iterrows():
            ankunft = row['Ankunft_min']
            abfahrt = row['Abfahrt_min']
            
            # Finde überlappende Fahrten
            overlapping = kante_data[
                (kante_data['Ankunft_min'] <= abfahrt + time_buffer) &
                (kante_data['Abfahrt_min'] >= ankunft - time_buffer) &
                (kante_data.index != idx)
            ]
            
            if not overlapping.empty:
                # Berechne Gesamtlänge
                total_length = row['Fahrzeuglänge'] + overlapping['Fahrzeuglänge'].sum()
                available_length = row['Kantenlänge']
                
                if total_length > available_length:
                    conflicts.append({
                        'Haltekante': kante,
                        'Zeit': row['Ankunft'],
                        'Betroffene_Fahrten': [row['Fahrt_ID']] + overlapping['Fahrt_ID'].tolist(),
                        'Linien': [row['Liniennummer']] + overlapping['Liniennummer'].tolist(),
                        'Benötigte_Länge': total_length,
                        'Verfügbare_Länge': available_length,
                        'Überlänge': total_length - available_length
                    })
    
    return pd.DataFrame(conflicts)

def create_timeline_chart(df):
    """Erstellt Timeline-Visualisierung der Kantenbelegung"""
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set3
    
    for i, (idx, row) in enumerate(df.iterrows()):
        ankunft = time_to_minutes(row['Ankunft'])
        abfahrt = time_to_minutes(row['Abfahrt'])
        
        fig.add_trace(go.Scatter(
            x=[ankunft, abfahrt],
            y=[row['Haltekante'], row['Haltekante']],
            mode='lines+markers',
            name=f"Linie {row['Liniennummer']} ({row['Fahrt_ID']})",
            line=dict(width=8, color=colors[i % len(colors)]),
            hovertemplate=f"<b>Linie {row['Liniennummer']}</b><br>" +
                         f"Fahrt: {row['Fahrt_ID']}<br>" +
                         f"Ankunft: {row['Ankunft']}<br>" +
                         f"Abfahrt: {row['Abfahrt']}<br>" +
                         f"Länge: {row['Fahrzeuglänge']}m<extra></extra>"
        ))
    
    fig.update_layout(
        title="Kantenbelegung Timeline",
        xaxis_title="Uhrzeit (Minuten seit Mitternacht)",
        yaxis_title="Haltekante",
        height=400,
        hovermode='closest'
    )
    
    return fig

def create_conflict_chart(conflicts_df):
    """Erstellt Visualisierung der Konflikte"""
    if conflicts_df.empty:
        return None
    
    fig = px.bar(
        conflicts_df,
        x='Haltekante',
        y='Überlänge',
        color='Zeit',
        title="Konflikte nach Haltekante",
        labels={'Überlänge': 'Überlänge (Meter)', 'Haltekante': 'Haltekante'}
    )
    
    return fig

# Hauptanwendung
def main():
    st.title("🚌 Kantenkonflikte Erkennung")
    st.markdown("**Automatisierte Erkennung von Kantenkonflikten für Verkehrsbetriebe**")
    
    # Sidebar für Einstellungen
    st.sidebar.header("⚙️ Einstellungen")
    
    # Datenquelle wählen
    data_source = st.sidebar.radio(
        "Datenquelle wählen:",
        ["Beispieldaten verwenden", "Eigene Daten hochladen"]
    )
    
    # Zeitpuffer einstellen
    time_buffer = st.sidebar.slider(
        "Zeitpuffer (Minuten):",
        min_value=1,
        max_value=10,
        value=2,
        help="Zeitfenster für Konflikterkennung (± Minuten)"
    )
    
    # Daten laden
    if data_source == "Beispieldaten verwenden":
        df = create_sample_data()
        st.success("✅ Beispieldaten geladen")
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Fahrplan hochladen",
            type=['csv', 'xlsx'],
            help="CSV oder Excel-Datei mit Fahrplandaten"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.success("✅ Datei erfolgreich hochgeladen")
            except Exception as e:
                st.error(f"❌ Fehler beim Laden der Datei: {e}")
                return
        else:
            st.info("👆 Bitte eine Datei hochladen oder Beispieldaten verwenden")
            return
    
    # Datenvalidierung
    required_columns = ['Liniennummer', 'Fahrt_ID', 'Haltestelle', 'Ankunft', 'Abfahrt', 'Haltekante', 'Fahrzeuglänge', 'Kantenlänge']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"❌ Fehlende Spalten: {', '.join(missing_columns)}")
        st.info("📋 Erforderliche Spalten: " + ", ".join(required_columns))
        return
    
    # Hauptbereich mit Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Übersicht", "⚠️ Konflikte", "📈 Visualisierung", "📥 Export"])
    
    with tab1:
        st.header("Datenübersicht")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Anzahl Fahrten", len(df))
        with col2:
            st.metric("Haltestellen", df['Haltestelle'].nunique())
        with col3:
            st.metric("Haltekanten", df['Haltekante'].nunique())
        with col4:
            st.metric("Linien", df['Liniennummer'].nunique())
        
        # Filter
        st.subheader("🔍 Filter")
        col1, col2 = st.columns(2)
        
        with col1:
            selected_lines = st.multiselect(
                "Linien auswählen:",
                options=sorted(df['Liniennummer'].unique()),
                default=sorted(df['Liniennummer'].unique())
            )
        
        with col2:
            selected_stops = st.multiselect(
                "Haltestellen auswählen:",
                options=sorted(df['Haltestelle'].unique()),
                default=sorted(df['Haltestelle'].unique())
            )
        
        # Gefilterte Daten
        filtered_df = df[
            (df['Liniennummer'].isin(selected_lines)) &
            (df['Haltestelle'].isin(selected_stops))
        ]
        
        st.subheader("📋 Fahrplandaten")
        st.dataframe(filtered_df, use_container_width=True)
    
    with tab2:
        st.header("⚠️ Konflikterkennung")
        
        # Konflikte erkennen
        conflicts_df = detect_conflicts(filtered_df, time_buffer)
        
        if conflicts_df.empty:
            st.success("✅ Keine Konflikte erkannt!")
        else:
            st.error(f"❌ {len(conflicts_df)} Konflikte erkannt")
            
            # Konflikte anzeigen
            for idx, conflict in conflicts_df.iterrows():
                with st.expander(f"🚨 Konflikt an Kante {conflict['Haltekante']} um {conflict['Zeit']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Betroffene Fahrten:**")
                        for fahrt, linie in zip(conflict['Betroffene_Fahrten'], conflict['Linien']):
                            st.write(f"- {fahrt} (Linie {linie})")
                    
                    with col2:
                        st.metric("Benötigte Länge", f"{conflict['Benötigte_Länge']}m")
                        st.metric("Verfügbare Länge", f"{conflict['Verfügbare_Länge']}m")
                        st.metric("Überlänge", f"{conflict['Überlänge']}m", delta=f"{conflict['Überlänge']}m")
    
    with tab3:
        st.header("📈 Visualisierung")
        
        # Timeline Chart
        timeline_fig = create_timeline_chart(filtered_df)
        st.plotly_chart(timeline_fig, use_container_width=True)
        
        # Konflikt Chart
        if not conflicts_df.empty:
            conflict_fig = create_conflict_chart(conflicts_df)
            if conflict_fig:
                st.plotly_chart(conflict_fig, use_container_width=True)
    
    with tab4:
        st.header("📥 Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Konflikte als CSV exportieren"):
                if not conflicts_df.empty:
                    csv = conflicts_df.to_csv(index=False)
                    st.download_button(
                        label="💾 CSV herunterladen",
                        data=csv,
                        file_name=f"kantenkonflikte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Keine Konflikte zum Exportieren vorhanden")
        
        with col2:
            if st.button("📊 Fahrplandaten als CSV exportieren"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="💾 CSV herunterladen",
                    data=csv,
                    file_name=f"fahrplandaten_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
