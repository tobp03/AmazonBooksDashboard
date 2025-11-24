import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Books Dashboard", layout="wide")
st.title("Amazon Books Dashboard")

# Load data
@st.cache_data
def load_data():
    return {
        'scorecard': pd.read_csv('./dataset/scorecard_data.csv'),
        'genre': pd.read_csv('./dataset/genre_data.csv'),
        'books': pd.read_csv('./dataset/top_books_data.csv'),
        'authors': pd.read_csv('./dataset/top_authors_data.csv')
    }

data = load_data()
scorecard, genre_data, top_books_data, top_authors_data = data['scorecard'], data['genre'], data['books'], data['authors']

# Initialize session state
if 'selected_genre' not in st.session_state:
    st.session_state.selected_genre = "All Genres"

# Helper functions
def get_measure_cols(measure):
    return {
        'genre_col': 'total_sales' if measure == 'Sales' else 'review_count',
        'books_col': 'total_sales' if measure == 'Sales' else 'total_reviews',
        'label': measure,
        'axis_label': 'Sales ($)' if measure == 'Sales' else 'Reviews'
    }

def truncate_text(text, max_len=15):
    return (text[:max_len] + '...')[:max_len].ljust(max_len) if len(text) > max_len else text.ljust(max_len)

def create_sparkline_chart(data, y_col):
    fig = px.line(data, x='year', y=y_col)
    fig.update_layout(showlegend=False, xaxis={'visible': False}, yaxis={'visible': False},
                      margin=dict(l=0, r=0, t=0, b=0), height=80)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig

def filter_by_year(df, year_range):
    return (df['year'] >= year_range[0]) & (df['year'] <= year_range[1])

# Filters
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    year_range = st.slider("Published Year", int(scorecard['year'].min()), int(scorecard['year'].max()), 
                           (2000, int(scorecard['year'].max())))

with filter_col2:
    measure = st.selectbox("Measure for Top N Charts", ["Sales", "Reviews"], index=0)

with filter_col3:
    filtered_genre_for_options = genre_data[filter_by_year(genre_data, year_range)]
    all_genres = sorted([g for g in filtered_genre_for_options['genre'].unique() if pd.notna(g)])
    genre_options = ["All Genres"] + all_genres
    current_idx = genre_options.index(st.session_state.selected_genre) if st.session_state.selected_genre in genre_options else 0
    st.selectbox("Filter by Genre", genre_options, index=current_idx, key="genre_filter", 
                 on_change=lambda: st.session_state.update({'selected_genre': st.session_state.genre_filter}))
    st.session_state.selected_genre = st.session_state.get('genre_filter', "All Genres")

# Display key metrics
filtered_scorecard = scorecard[filter_by_year(scorecard, year_range)]
col1, col2, col3 = st.columns(3)

for idx, (col, label, value_col, fmt) in enumerate([(col1, "Total Books", "total_books", "{:,.0f}"),
                                                      (col2, "Total Reviews", "total_reviews", "{:,.0f}"),
                                                      (col3, "Total Sales", "total_sales", "${:,.2f}")]):
    with col:
        m_col, c_col = st.columns([1, 1])
        with m_col:
            val = filtered_scorecard[value_col].sum()
            st.metric(label, fmt.format(val))
        with c_col:
            st.plotly_chart(create_sparkline_chart(filtered_scorecard, value_col), config={'responsive': True})

# Load format analysis data
@st.cache_data
def load_format_data():
    return pd.read_csv('./dataset/format_data.csv')

format_data = load_format_data()

# Book Format Analysis Section
st.subheader("Book Format Analysis")
filtered_format = format_data[filter_by_year(format_data, year_range)]

col_format_comparison, col_format_trends = st.columns([0.3, 0.6])

with col_format_comparison:
    # Get measure columns for format analysis
    format_cols = get_measure_cols(measure)
    
    # Determine which column to use for waterfall chart based on measure
    waterfall_col = 'total_reviews' if measure == 'Reviews' else 'total_sales'
    
    # Waterfall chart: Measure by format (aggregated across all years)
    format_measure_agg = filtered_format[filtered_format['book_format'] != 'All Formats'].copy()
    format_measure_agg = format_measure_agg.groupby('book_format').agg({waterfall_col: 'sum'}).reset_index()
    format_measure_agg = format_measure_agg.sort_values(waterfall_col, ascending=False)
    
    def format_waterfall_value(val):
        return f'${val/1e6:.1f}M' if measure == 'Sales' else f'{val/1e3:.0f}K'
    
    # Create waterfall data with cumulative and total
    formats = format_measure_agg['book_format'].tolist()
    values = format_measure_agg[waterfall_col].tolist()
    
    # Prepare data for waterfall
    x_data = formats + ['Total']
    y_data = values + [sum(values)]
    measure_type = ['relative'] * len(formats) + ['total']
    
    # Default Plotly colors for consistency with line chart
    plotly_colors = px.colors.qualitative.Plotly
    
    fig_waterfall = go.Figure(go.Waterfall(
        x=x_data, 
        y=y_data, 
        measure=measure_type,
        increasing={"marker": {"color": "#83C8FE"}},
        decreasing={"marker": {"color": "#83C8FE"}},
        totals={"marker": {"color": "#003f87"}},
        connector={"line": {"color": "rgba(0, 0, 0, 0.2)"}}
    ))
    
    fig_waterfall.update_layout(
        title=f'{format_cols["label"]} by Format',
        height=380, margin=dict(l=20, r=20, t=40, b=80),
        title_font=dict(size=14), showlegend=False
    )
    
    # Extend y-axis to prevent label cutoff
    fig_waterfall.update_yaxes(automargin=True)
    
    # Add custom text labels with formatted values and percentages
    total_val = sum(values)
    text_labels = [f"{format_waterfall_value(v)}<br>({(v/total_val)*100:.1f}%)" for v in values]
    text_labels.append(f"{format_waterfall_value(total_val)}")
    
    fig_waterfall.data[0].text = text_labels
    fig_waterfall.data[0].textposition = 'inside'
    fig_waterfall.update_traces(textfont=dict(color='white'))
    
    st.plotly_chart(fig_waterfall, config={'responsive': True})
    
    # Scorecards for each format
    format_stats = filtered_format[filtered_format['book_format'] != 'All Formats'].copy()
    format_stats = format_stats.groupby('book_format').agg({'avg_price': 'mean'}).reset_index()
    format_stats = format_stats.sort_values('avg_price', ascending=False)
    
    score_col1, score_col2, score_col3 = st.columns(3)
    for idx, (score_col, row) in enumerate(zip([score_col1, score_col2, score_col3], format_stats.itertuples())):
        with score_col:
            st.metric(label=f"{row[1]} Format", value=f"${row[2]:.2f}")


with col_format_trends:
    st.write("**Pricing Trends by Format**")
    # Line chart 1: Average price by year (All Formats)
    format_measure_col = 'avg_price'
    format_axis_label = 'Average Price ($)'
    
    price_by_year = filtered_format[filtered_format['book_format'] == 'All Formats'].sort_values('year')
    fig_price = px.line(price_by_year, x='year', y=format_measure_col, 
                        title='All Formats', markers=True)
    fig_price.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20), 
                           title_font=dict(size=14), showlegend=False)
    fig_price.update_yaxes(title_text=format_axis_label)
    fig_price.update_xaxes(title_text='Year')
    fig_price.update_traces(hovertemplate='Year: %{x}<br>Avg Price: $%{y:.2f}<extra></extra>')
    st.plotly_chart(fig_price, config={'responsive': True}, use_container_width=True)
    
    # Line chart 2: Average price by year broken down by format
    format_lines = filtered_format[filtered_format['book_format'] != 'All Formats'].copy()
    format_lines = format_lines.sort_values(['year', 'book_format'])
    fig_format_lines = px.line(format_lines, x='year', y=format_measure_col, color='book_format',
                              title='By Format', markers=True)
    fig_format_lines.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20),
                                  title_font=dict(size=14), showlegend=False)
    fig_format_lines.update_yaxes(title_text=format_axis_label)
    fig_format_lines.update_xaxes(title_text='Year')
    fig_format_lines.update_traces(hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>Avg Price: $%{y:.2f}<extra></extra>')
    st.plotly_chart(fig_format_lines, config={'responsive': True}, use_container_width=True)

# Genre overview
st.subheader("Genre Analysis")
filtered_genre = genre_data[filter_by_year(genre_data, year_range)]
cols = get_measure_cols(measure)
genre_sums = filtered_genre.groupby('genre')[cols['genre_col']].sum().reset_index()
top_genres = genre_sums.nlargest(5, cols['genre_col'])['genre'].tolist()
color_palette = ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#c6dbef']

# Genre trends and top genres
col_pie, col_stacked = st.columns([0.3, 0.7])

with col_pie:
    genre_agg = filtered_genre.groupby('genre')[cols['genre_col']].sum().reset_index().nlargest(5, cols['genre_col'])
    pct = (genre_agg[cols['genre_col']].sum() / filtered_genre[cols['genre_col']].sum()) * 100
    fig = px.pie(genre_agg, values=cols['genre_col'], names='genre', 
                 title=f'Top 5 Genres by {cols["label"]}', hole=0.4, color_discrete_sequence=color_palette)
    def format_pie_value(val):
        return f'${val/1e6:.1f}M' if measure == 'Sales' else f'{val/1e3:.0f}K'
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), title_font=dict(size=25), showlegend=True)
    fig.add_annotation(text=f"Top 5 Share(%):<br>{pct:.1f}%", x=0.5, y=0.5, showarrow=False, font=dict(size=16, color='white'))
    fig.update_traces(textposition='auto', textfont=dict(size=11),
                      hovertemplate='<b>%{label}</b><br>' + cols['label'] + ': %{value:,.0f}<extra></extra>')
    total_genre_val = genre_agg[cols['genre_col']].sum()
    for trace in fig.data:
        trace.text = [f"{format_pie_value(v)}<br>({(v/total_genre_val)*100:.1f}%)" for v in trace.values]
        trace.textinfo = 'label+text'
    st.plotly_chart(fig, config={'responsive': True})

with col_stacked:
    genre_year = filtered_genre.groupby(['year', 'genre'])[cols['genre_col']].sum().reset_index()
    genre_year = genre_year[genre_year['genre'].isin(top_genres)]
    fig = px.bar(genre_year, x='year', y=cols['genre_col'], color='genre', 
                 labels={'year': 'Year', cols['genre_col']: cols['axis_label'], 'genre': 'Genre'},
                 title=f'Top 5 Genres Trends', color_discrete_sequence=color_palette, category_orders={'genre': top_genres})
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), title_font=dict(size=25), showlegend=False)
    fig.update_traces(textposition='outside', textfont=dict(size=9),
                      hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>' + cols['axis_label'] + ': %{y:,.0f}<extra></extra>')
    def format_stacked_value(val):
        return f'${val/1e6:.1f}M' if measure == 'Sales' else f'{val/1e3:.0f}K'
    for trace in fig.data:
        trace.text = [format_stacked_value(v) for v in trace.y]
    st.plotly_chart(fig, config={'responsive': True})

# Treemap below genre analysis
col_treemap = st.columns(1)[0]

with col_treemap:
    genre_treemap = top_books_data[filter_by_year(top_books_data, year_range)].groupby('genre')[cols['books_col']].sum().reset_index().dropna(subset=['genre'])
    genre_treemap = genre_treemap.sort_values(cols['books_col'], ascending=False)
    
    # Create color mapping: top 5 get blue palette, rest get light grey
    genre_colors = {}
    for i, genre in enumerate(genre_treemap['genre'].values):
        if i < 5:
            genre_colors[genre] = color_palette[i]
        else:
            genre_colors[genre] = "#a5aebf"  # light grey
    
    fig = px.treemap(genre_treemap, path=['genre'], values=cols['books_col'], 
                     title=f"All Genres by {cols['label']}")
    def format_treemap_value(val):
        return f'${val/1e6:.1f}M' if measure == 'Sales' else f'{val/1e3:.0f}K'
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), title_font=dict(size=25), showlegend=False)
    
    # Apply custom colors to each trace
    for trace in fig.data:
        trace.marker.colors = [genre_colors.get(label, '#d3d3d3') for label in trace.labels]
    
    fig.update_traces(textfont=dict(size=12), textinfo='text',
                      hovertemplate='<b>%{label}</b><br>' + cols['label'] + ': %{value:,.0f}<extra></extra>')
    for i, trace in enumerate(fig.data):
        trace.text = [f"<b>{label}</b><br>{format_treemap_value(val)}" for label, val in zip(trace.labels, trace.values)]
        trace.textposition = 'middle center'
    st.plotly_chart(fig, config={'responsive': True})

# Top 10 Books and Authors
def create_top_chart(data, group_cols, name_col, title):
    agg = data.groupby(group_cols)[cols['books_col']].sum().reset_index().nlargest(10, cols['books_col'])
    agg['short_name'] = agg[name_col].apply(truncate_text)
    fig = px.bar(agg, x=cols['books_col'], y='short_name', orientation='h',
                 labels={cols['books_col']: cols['axis_label'], 'short_name': name_col.title()},
                 title=f'{title} by {cols["label"]}')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=250, margin=dict(l=20, r=20, t=40, b=20),
                      title_font=dict(size=25), yaxis_tickfont=dict(family='monospace'))
    fig.update_traces(textposition='outside', textfont=dict(size=9),
                      hovertemplate='<b>%{y}</b><br>' + cols['axis_label'] + ': %{x:,.0f}<extra></extra>')
    def format_top_value(val):
        return f'${val/1e6:.1f}M' if measure == 'Sales' else f'{val/1e3:.0f}K'
    for trace in fig.data:
        trace.text = [format_top_value(v) for v in trace.x]
    return fig

selected_genre = st.session_state.selected_genre
filtered_books = top_books_data[filter_by_year(top_books_data, year_range)]
if selected_genre != "All Genres":
    filtered_books = filtered_books[filtered_books['genre'] == selected_genre]

filtered_authors = top_authors_data[filter_by_year(top_authors_data, year_range)]
if selected_genre != "All Genres":
    genre_authors = top_books_data[filter_by_year(top_books_data, year_range) & (top_books_data['genre'] == selected_genre)]['author_name'].unique()
    filtered_authors = filtered_authors[filtered_authors['author_name'].isin(genre_authors)]

# Top 10 side by side
col_top_books, col_top_authors = st.columns(2)
with col_top_books:
    st.plotly_chart(create_top_chart(filtered_books, ['title', 'author_name'], 'title', 'Top 10 Books'), config={'responsive': True})
with col_top_authors:
    st.plotly_chart(create_top_chart(filtered_authors, ['author_name'], 'author_name', 'Top 10 Authors'), config={'responsive': True})


