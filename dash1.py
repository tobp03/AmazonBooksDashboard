import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Books Dashboard", layout="wide")
st.title("Amazon Books Dashboard")

# Hide Streamlit sidebar page navigation
st.markdown("""
<style>
/* Hide the entire sidebar page navigation */
section[data-testid="stSidebarNav"] {
    display: none !important;
}

/* Optional: hide sidebar entirely */
section[data-testid="stSidebar"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


# Load data (cache busts when files change)
@st.cache_data
def load_data(cache_bust: tuple):
    return {
        'scorecard': pd.read_csv('./dataset/scorecard_data.csv'),
        'genre': pd.read_csv('./dataset/genre_data.csv'),
        'books': pd.read_csv('./dataset/top_books_data.csv'),
        'authors': pd.read_csv('./dataset/top_authors_data.csv'),
        'publishers': pd.read_csv('./dataset/top_publishers_data.csv')
    }

data = load_data((
    os.path.getmtime('./dataset/scorecard_data.csv'),
    os.path.getmtime('./dataset/genre_data.csv'),
    os.path.getmtime('./dataset/top_books_data.csv'),
    os.path.getmtime('./dataset/top_authors_data.csv'),
    os.path.getmtime('./dataset/top_publishers_data.csv')
))
scorecard, genre_data, top_books_data, top_authors_data, top_publishers_data = data['scorecard'], data['genre'], data['books'], data['authors'], data['publishers']

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
    if len(text) > max_len:
        return text[:max_len - 3] + '...'
    return text

def create_sparkline_chart(data, y_col):
    fig = px.area(data, x='year', y=y_col)
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

# Load format analysis data (cache busts when file changes)
@st.cache_data
def load_format_data(cache_bust: float):
    return pd.read_csv('./dataset/format_data.csv')

format_data = load_format_data(os.path.getmtime('./dataset/format_data.csv'))

# Book Format Analysis Section
st.subheader("Book Format Analysis")
filtered_format = format_data[filter_by_year(format_data, year_range)].copy()
selected_genre = st.session_state.get('selected_genre', "All Genres")
if selected_genre != "All Genres":
    filtered_format = filtered_format[filtered_format['genre'] == selected_genre]

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
        if measure == 'Sales':
            if val < 1000:
                return f'${val:.0f}'
            elif val < 1e6:
                return f'${val/1e3:.1f}K'
            else:
                return f'${val/1e6:.1f}M'
        else:
            if val < 1000:
                return f'{val:.0f}'
            else:
                return f'{val/1e3:.0f}K'
    
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
        increasing={"marker": {"color": "#3182BD"}},
        decreasing={"marker": {"color": "#3182BD"}},
        totals={"marker": {"color": "#003f87"}},
        connector={"line": {"color": "rgba(0, 0, 0, 0.2)"}}
    ))
    
    fig_waterfall.update_layout(
        title=f'{format_cols["label"]} by Format',
        height=380, margin=dict(l=20, r=20, t=40, b=80),
        title_font=dict(size=14), showlegend=False
    )
    
    # Extend y-axis to prevent label cutoff
    fig_waterfall.update_yaxes(automargin=True, showgrid=False)
    fig_waterfall.update_xaxes(showgrid=False)
    
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
    # Line chart 1: Average price by year (All Formats)
    format_measure_col = 'avg_price'
    format_axis_label = 'Average Price ($)'
    
    # Compute All Formats by year; if a genre is selected, derive it from formats via weighted avg
    if selected_genre == "All Genres":
        price_by_year = format_data[(format_data['book_format'] == 'All Formats') & filter_by_year(format_data, year_range)].sort_values('year')
        y_series = price_by_year[format_measure_col]
        x_series = price_by_year['year']
    else:
        tmp = filtered_format[filtered_format['book_format'] != 'All Formats']
        wsum = (tmp['avg_price'] * tmp['book_count']).groupby(tmp['year']).sum()
        wden = tmp.groupby('year')['book_count'].sum()
        price_by_year = pd.DataFrame({'year': wsum.index, 'avg_price': (wsum / wden).fillna(0)})
        y_series = price_by_year['avg_price']
        x_series = price_by_year['year']
    fig_price = px.line(x=x_series, y=y_series, 
                        title='All Formats', markers=True)
    fig_price.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20), 
                           title_font=dict(size=14), showlegend=True, 
                           legend=dict(orientation="h", yanchor="top", y=1.15, xanchor="left", x=0))
    fig_price.update_yaxes(title_text=format_axis_label, showgrid=False)
    fig_price.update_xaxes(title_text='Year', showgrid=False)
    fig_price.update_traces(hovertemplate='Year: %{x}<br>Avg Price: $%{y:.2f}<extra></extra>')
    st.plotly_chart(fig_price, config={'responsive': True}, use_container_width=True)
    
    # Line chart 2: Average price by year broken down by format
    format_lines = filtered_format[filtered_format['book_format'] != 'All Formats'].copy()
    format_lines = format_lines.sort_values(['year', 'book_format'])
    fig_format_lines = px.line(format_lines, x='year', y=format_measure_col, color='book_format',
                              title='By Format', markers=True)
    fig_format_lines.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20),
                                  title_font=dict(size=14), showlegend=True,
                                  legend=dict(orientation="h", yanchor="top", y=1.15, xanchor="left", x=0, title='Format'))
    fig_format_lines.update_yaxes(title_text=format_axis_label, showgrid=False)
    fig_format_lines.update_xaxes(title_text='Year', showgrid=False)
    fig_format_lines.update_traces(hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>Avg Price: $%{y:.2f}<extra></extra>')
    st.plotly_chart(fig_format_lines, config={'responsive': True}, use_container_width=True)

# Prepare data for both sections
filtered_genre = genre_data[filter_by_year(genre_data, year_range)]
cols = get_measure_cols(measure)
genre_sums = filtered_genre.groupby('genre')[cols['genre_col']].sum().reset_index()
top_genres = genre_sums.nlargest(5, cols['genre_col'])['genre'].tolist()
color_palette = ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#c6dbef']

# Top 20 Publishers
st.subheader(f"Top 20 Publishers by {cols['label']}")
filtered_publishers = top_publishers_data[filter_by_year(top_publishers_data, year_range)].copy()
if selected_genre != "All Genres":
    filtered_publishers = filtered_publishers[filtered_publishers['genre'] == selected_genre]
publisher_col = 'total_sales' if measure == 'Sales' else 'total_reviews'

# Compute weighted average rating across the selected period for each publisher
filtered_publishers['weighted_rating'] = filtered_publishers['avg_rating'] * filtered_publishers['total_reviews']
publisher_agg = filtered_publishers.groupby('publisher_name').agg({
    publisher_col: 'sum',
    'weighted_rating': 'sum',
    'total_reviews': 'sum'
}).reset_index()
publisher_agg['avg_rating'] = publisher_agg.apply(lambda r: (r['weighted_rating'] / r['total_reviews']) if r['total_reviews'] > 0 else 0, axis=1)

# Take top 20 by primary measure and preserve order
publisher_agg = publisher_agg.sort_values(publisher_col, ascending=False).head(20).reset_index(drop=True)

def format_publisher_value(val):
    if measure == 'Sales':
        if val < 1000:
            return f'${val:.0f}'
        elif val < 1e6:
            return f'${val/1e3:.1f}K'
        else:
            return f'${val/1e6:.1f}M'
    else:
        if val < 1000:
            return f'{val:.0f}'
        else:
            return f'{val/1e3:.0f}K'

# Create display names with ranking prefix (no truncation)
publisher_agg['display_name'] = publisher_agg.apply(lambda row: f"{row.name + 1}. {truncate_text(row['publisher_name'])}", axis=1)

# Create custom two-line labels: Avg. Rating: X.XX \n Total Measure
text_labels = []
for idx, row in publisher_agg.iterrows():
    rating_line = f"Avg. Rating: {row['avg_rating']:.2f}"
    measure_line = format_publisher_value(row[publisher_col])
    text_labels.append(f"{rating_line}<br>{measure_line}")

fig_publishers = px.bar(publisher_agg, x='display_name', y=publisher_col,
                        labels={'display_name': 'Publisher', publisher_col: cols['axis_label']},
                        color_discrete_sequence=['#3182BD'])
fig_publishers.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20),
                            xaxis={'categoryorder': 'total descending'},
                            xaxis_title='Publisher', yaxis_title=cols['axis_label'])
fig_publishers.update_xaxes(showgrid=False, tickangle=-45)
fig_publishers.update_yaxes(showgrid=False)
fig_publishers.update_traces(text=text_labels, textposition='outside', textfont=dict(size=9),
                            hovertemplate='<b>%{x}</b><br>' + cols['axis_label'] + ': %{y:,.0f}<extra></extra>')
st.plotly_chart(fig_publishers, config={'responsive': True}, use_container_width=True)

# Top 10 Books and Authors
def create_top_chart(data, group_cols, name_col, title):
    agg = data.groupby(group_cols)[cols['books_col']].sum().reset_index().nlargest(10, cols['books_col'])
    agg = agg.reset_index(drop=True)
    agg['short_name'] = agg.apply(lambda row: f"{row.name + 1}. {truncate_text(row[name_col])}", axis=1)
    fig = px.bar(agg, x=cols['books_col'], y='short_name', orientation='h',
                 labels={cols['books_col']: cols['axis_label'], 'short_name': name_col.title()},
                 title=f'{title} by {cols["label"]}', color_discrete_sequence=['#3182BD'])
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500, margin=dict(l=20, r=20, t=40, b=20),
                      title_font=dict(size=25), yaxis_tickfont=dict(family='monospace'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_traces(textposition='outside', textfont=dict(size=9),
                      hovertemplate='<b>%{y}</b><br>' + cols['axis_label'] + ': %{x:,.0f}<extra></extra>')
    def format_top_value(val):
        if measure == 'Sales':
            if val < 1000:
                return f'${val:.0f}'
            elif val < 1e6:
                return f'${val/1e3:.1f}K'
            else:
                return f'${val/1e6:.1f}M'
        else:
            if val < 1000:
                return f'{val:.0f}'
            else:
                return f'{val/1e3:.0f}K'
    for trace in fig.data:
        trace.text = [format_top_value(v) for v in trace.x]
    return fig

selected_genre = st.session_state.get('selected_genre', "All Genres")
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

# Genre overview
st.subheader("Genre Analysis")

# Genre trends and top genres
col_pie, col_stacked = st.columns([0.3, 0.7])

with col_pie:
    genre_agg = filtered_genre.groupby('genre')[cols['genre_col']].sum().reset_index().nlargest(5, cols['genre_col'])
    pct = (genre_agg[cols['genre_col']].sum() / filtered_genre[cols['genre_col']].sum()) * 100
    fig = px.pie(genre_agg, values=cols['genre_col'], names='genre', 
                 title=f'Top 5 Genres by {cols["label"]}', hole=0.4, color_discrete_sequence=color_palette)
    def format_pie_value(val):
        if measure == 'Sales':
            if val < 1000:
                return f'${val:.0f}'
            elif val < 1e6:
                return f'${val/1e3:.1f}K'
            else:
                return f'${val/1e6:.1f}M'
        else:
            if val < 1000:
                return f'{val:.0f}'
            else:
                return f'{val/1e3:.0f}K'
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20), title_font=dict(size=25), showlegend=True,
                      legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=0, xref = 'container'))
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
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_traces(textposition='outside', textfont=dict(size=9),
                      hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>' + cols['axis_label'] + ': %{y:,.0f}<extra></extra>')
    def format_stacked_value(val):
        if measure == 'Sales':
            if val < 1000:
                return f'${val:.0f}'
            elif val < 1e6:
                return f'${val/1e3:.1f}K'
            else:
                return f'${val/1e6:.1f}M'
        else:
            if val < 1000:
                return f'{val:.0f}'
            else:
                return f'{val/1e3:.0f}K'
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
        if measure == 'Sales':
            if val < 1000:
                return f'${val:.0f}'
            elif val < 1e6:
                return f'${val/1e3:.1f}K'
            else:
                return f'${val/1e6:.1f}M'
        else:
            if val < 1000:
                return f'{val:.0f}'
            else:
                return f'{val/1e3:.0f}K'
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


if st.button("Go to Author Insights Dashboard"):
    st.switch_page("pages/dash2.py")


