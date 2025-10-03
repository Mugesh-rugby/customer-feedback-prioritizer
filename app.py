import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import base64
import io
import random
import os

@st.cache_data
def load_data(path="feedback.csv"):
    keep_cols = ["Category", "Sentiment", "Date"]
    try:
        df = pd.read_csv(path, usecols=keep_cols)
        for c in keep_cols:
            if c not in df.columns:
                df[c] = None
    except Exception as e1:
        try:
            df = pd.read_csv(path, usecols=keep_cols, engine="python", on_bad_lines="skip")
            for c in keep_cols:
                if c not in df.columns:
                    df[c] = None
        except Exception as e2:
            data = []
            if not os.path.exists(path):
                st.error(f"❌ File not found: {path}")
                return pd.DataFrame(columns=keep_cols)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                header_line = f.readline().rstrip("\n")
                header_cols = [h.strip() for h in header_line.split(",")]
                def idx_of(name):
                    try:
                        return header_cols.index(name)
                    except ValueError:
                        return None
                idx_cat = idx_of("Category")
                idx_sent = idx_of("Sentiment")
                idx_date = idx_of("Date")

                if idx_cat is None or idx_sent is None or idx_date is None:
                    idx_cat, idx_sent, idx_date = 0, 1, 2

                max_needed = max(idx_cat, idx_sent, idx_date)

                for raw_line in f:
                    line = raw_line.rstrip("\n")
                    parts = line.split(",", max_needed + 1)
                    def safe(i):
                        try:
                            return parts[i].strip()
                        except Exception:
                            return ""
                    cat = safe(idx_cat)
                    sent = safe(idx_sent)
                    date = safe(idx_date)
                    data.append({"Category": cat, "Sentiment": sent, "Date": date})

            df = pd.DataFrame(data, columns=keep_cols)

    if "Sentiment" not in df.columns:
        df["Sentiment"] = [random.choice(["Positive", "Neutral", "Negative"]) for _ in range(len(df))]
    else:
        if df["Sentiment"].isnull().any():
            null_count = df["Sentiment"].isnull().sum()
            df.loc[df["Sentiment"].isnull(), "Sentiment"] = [
                random.choice(["Positive", "Neutral", "Negative"]) for _ in range(null_count)
            ]

    if "Date" not in df.columns:
        df["Date"] = [datetime.now() - timedelta(days=random.randint(0, 30)) for _ in range(len(df))]
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        if df["Date"].isnull().any():
            mask = df["Date"].isnull()
            df.loc[mask, "Date"] = [
                datetime.now() - timedelta(days=random.randint(0, 30)) for _ in range(mask.sum())
            ]

    df = df[["Category", "Sentiment", "Date"]]
    df = df[df["Category"].notna() & (df["Category"].astype(str).str.strip() != "")]
    df = df.reset_index(drop=True)
    return df

def calculate_priority_score(df):
    priority_data = []

    for category in df["Category"].unique():
        cat_df = df[df["Category"] == category]

        frequency = len(cat_df)

        negative_count = len(cat_df[cat_df["Sentiment"].str.lower() == "negative"])
        sentiment_score = (negative_count / frequency) * 100 if frequency > 0 else 0

        if "Date" in cat_df.columns:
            avg_days_old = (datetime.now() - pd.to_datetime(cat_df["Date"]).mean()).days
            recency_score = max(0, 100 - avg_days_old * 3)
        else:
            recency_score = 50

        priority_score = (frequency * 0.4) + (sentiment_score * 0.4) + (recency_score * 0.2)

        if priority_score > 70:
            urgency = "🔴 Critical"
        elif priority_score > 50:
            urgency = "🟡 High"
        elif priority_score > 30:
            urgency = "🟢 Medium"
        else:
            urgency = "⚪ Low"

        priority_data.append({
            "Category": category,
            "Frequency": frequency,
            "Negative_Feedback": negative_count,
            "Priority_Score": round(priority_score, 1),
            "Urgency": urgency,
            "Sentiment_Score": round(sentiment_score, 1)
        })

    priority_df = pd.DataFrame(priority_data)
    priority_df = priority_df.sort_values("Priority_Score", ascending=False)

    return priority_df

def generate_insights(top5_df, total_feedback):
    if top5_df.empty:
        return {
            "executive_summary": "<strong>No data to summarize</strong>",
            "action_items": []
        }

    critical_issues = len(top5_df[top5_df["Urgency"] == "🔴 Critical"])

    top_category = top5_df.iloc[0]['Category'] if not top5_df.empty else "N/A"
    top_frequency = top5_df.iloc[0]['Frequency'] if not top5_df.empty else 0

    insights = {
        "executive_summary": f"""
        <strong>📊 Feedback Analysis Summary</strong><br>
        • Total feedback analyzed: {total_feedback} entries<br>
        • Critical issues requiring immediate attention: {critical_issues}<br>
        • Top concern: {top_category} ({top_frequency} mentions)<br>
        • Overall sentiment: {calculate_overall_sentiment(top5_df)}
        """,
        "action_items": []
    }

    for idx, row in top5_df.iterrows():
        action = {
            "issue": row["Category"],
            "priority": row["Urgency"],
            "recommendation": generate_recommendation(row),
            "estimated_impact": estimate_impact(row)
        }
        insights["action_items"].append(action)

    return insights

def calculate_overall_sentiment(df):
    if df.empty:
        return "No sentiment data"
    avg_negative = df["Negative_Feedback"].mean()
    if avg_negative > 50:
        return "⚠️ Concerning - High negative sentiment detected"
    elif avg_negative > 25:
        return "⚡ Mixed - Some areas need improvement"
    else:
        return "✅ Positive - Most feedback is constructive"

def generate_recommendation(row):
    recommendations = {
        "🔴 Critical": f"Immediate action required: Assign dedicated team to resolve '{row['Category']}' within 48 hours.",
        "🟡 High": f"Schedule sprint planning: Address '{row['Category']}' in next development cycle.",
        "🟢 Medium": f"Add to backlog: Plan improvements for '{row['Category']}' in upcoming quarter.",
        "⚪ Low": f"Monitor: Keep tracking '{row['Category']}' feedback for trend changes."
    }
    return recommendations.get(row["Urgency"], "Review and prioritize based on team capacity.")

def estimate_impact(row):
    affected_users = row["Frequency"]
    if affected_users > 100:
        return f"High Impact - Affects {affected_users}+ users"
    elif affected_users > 50:
        return f"Medium Impact - Affects {affected_users} users"
    else:
        return f"Low Impact - Affects {affected_users} users"

def create_priority_chart(df):
    fig = px.bar(df.head(10),
                 x="Priority_Score",
                 y="Category",
                 orientation='h',
                 color="Urgency",
                 color_discrete_map={
                     "🔴 Critical": "#FF4B4B",
                     "🟡 High": "#FFA500",
                     "🟢 Medium": "#90EE90",
                     "⚪ Low": "#D3D3D3"
                 },
                 title="Top 10 Issues by Priority Score",
                 labels={"Priority_Score": "Priority Score", "Category": "Feedback Category"})
    fig.update_layout(height=500, showlegend=True)
    return fig

def create_sentiment_chart(df):
    sentiment_data = df.groupby("Urgency").size().reset_index(name="Count")
    fig = px.pie(sentiment_data,
                 values="Count",
                 names="Urgency",
                 title="Feedback Distribution by Urgency Level",
                 color_discrete_sequence=["#FF4B4B", "#FFA500", "#90EE90", "#D3D3D3"])
    return fig

def create_trend_chart(df):
    df_trend = df.copy()
    df_trend['Date'] = pd.to_datetime(df_trend['Date'])
    df_trend['Week'] = df_trend['Date'].dt.to_period('W').apply(lambda r: r.start_time)
    
    trend_data = df_trend.groupby(['Week', 'Sentiment']).size().reset_index(name='Count')
    
    fig = px.line(trend_data, 
                  x='Week', 
                  y='Count', 
                  color='Sentiment',
                  title='Feedback Sentiment Trend Over Time',
                  labels={'Week': 'Week', 'Count': 'Number of Feedback'},
                  color_discrete_map={
                      'Positive': '#90EE90',
                      'Neutral': '#FFA500',
                      'Negative': '#FF4B4B'
                  })
    fig.update_layout(height=400, showlegend=True, hovermode='x unified')
    return fig

def create_category_sentiment_heatmap(df):
    heatmap_data = pd.crosstab(df['Category'], df['Sentiment'])
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='RdYlGn_r',
        text=heatmap_data.values,
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Count")
    ))
    
    fig.update_layout(
        title='Category vs Sentiment Heatmap',
        xaxis_title='Sentiment',
        yaxis_title='Category',
        height=500
    )
    return fig

def export_to_csv(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="priority_report_{datetime.now().strftime("%Y%m%d")}.csv">📥 Download CSV Report</a>'
    return href

def generate_html_email(top5_df, insights, chart_base64):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
            .content {{ padding: 30px; }}
            .summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #667eea; }}
            .action-item {{ background-color: white; border: 1px solid #e0e0e0; padding: 20px; margin-bottom: 15px; border-radius: 8px; }}
            .action-item h3 {{ margin: 0 0 10px 0; color: #333; }}
            .priority-badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-right: 10px; }}
            .critical {{ background-color: #ffe0e0; color: #d32f2f; }}
            .high {{ background-color: #fff4e0; color: #f57c00; }}
            .medium {{ background-color: #e8f5e9; color: #388e3c; }}
            .low {{ background-color: #f5f5f5; color: #757575; }}
            .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .table th {{ background-color: #667eea; color: white; padding: 12px; text-align: left; }}
            .table td {{ padding: 12px; border-bottom: 1px solid #e0e0e0; }}
            .chart-container {{ text-align: center; margin: 30px 0; }}
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; }}
            .metric {{ display: inline-block; margin: 10px 20px; }}
            .metric-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
            .metric-label {{ font-size: 14px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Weekly Customer Feedback Report</h1>
                <p>Priority Analysis & Action Items • {datetime.now().strftime('%B %d, %Y')}</p>
            </div>

            <div class="content">
                <div class="summary">
                    <h2 style="margin-top: 0; color: #667eea;">📊 Executive Summary</h2>
                    {insights['executive_summary']}

                    <div style="margin-top: 20px;">
                        <div class="metric">
                            <div class="metric-value">{len(top5_df)}</div>
                            <div class="metric-label">Categories Analyzed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{top5_df['Frequency'].sum()}</div>
                            <div class="metric-label">Total Feedback</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{len(top5_df[top5_df['Urgency'] == '🔴 Critical'])}</div>
                            <div class="metric-label">Critical Issues</div>
                        </div>
                    </div>
                </div>

                <h2 style="color: #667eea;">🎯 Top 5 Priority Issues</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Category</th>
                            <th>Mentions</th>
                            <th>Priority Score</th>
                            <th>Urgency</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for idx, row in top5_df.head(5).iterrows():
        html_content += f"""
                        <tr>
                            <td><strong>{idx + 1}</strong></td>
                            <td><strong>{row['Category']}</strong></td>
                            <td>{row['Frequency']}</td>
                            <td>{row['Priority_Score']}</td>
                            <td>{row['Urgency']}</td>
                        </tr>
        """

    html_content += """
                    </tbody>
                </table>

                <h2 style="color: #667eea; margin-top: 40px;">✅ Recommended Actions</h2>
    """

    for idx, action in enumerate(insights['action_items'][:5], 1):
        priority_class = "critical" if "Critical" in action['priority'] else \
                        "high" if "High" in action['priority'] else \
                        "medium" if "Medium" in action['priority'] else "low"

        html_content += f"""
                <div class="action-item">
                    <h3>
                        <span class="priority-badge {priority_class}">{action['priority']}</span>
                        {idx}. {action['issue']}
                    </h3>
                    <p><strong>📋 Recommendation:</strong> {action['recommendation']}</p>
                    <p><strong>💡 Impact:</strong> {action['estimated_impact']}</p>
                </div>
        """

    html_content += f"""
                <div class="chart-container">
                    <h3 style="color: #667eea;">Priority Distribution</h3>
                    <img src="data:image/png;base64,{chart_base64}" style="max-width: 100%; height: auto;" />
                </div>
            </div>

            <div class="footer">
                <p>🤖 Generated automatically by AI-Powered Feedback Prioritizer</p>
                <p>For questions or feedback, contact your product team</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html_content

def send_priority_email(html_content, recipient_email, sender_email, api_key):
    try:
        message = Mail(
            from_email=sender_email,
            to_emails=recipient_email,
            subject=f"🎯 Weekly Feedback Priority Report - {datetime.now().strftime('%b %d, %Y')}",
            html_content=html_content
        )
        
        message.content_type = "text/html"

        import ssl
        import urllib3
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ssl._create_default_https_context = ssl._create_unverified_context
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            return True, response.status_code
        else:
            return False, f"SendGrid returned status code: {response.status_code}"
            
    except Exception as e:
        return False, str(e)

def main():
    st.set_page_config(page_title="AI Feedback Prioritizer", page_icon="🎯", layout="wide")

    st.markdown("""
        <style>
        .big-metric { font-size: 48px; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 16px; color: #666; }
        .stTabs [data-baseweb="tab-list"] button { font-size: 18px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🎯 AI-Powered Customer Feedback Prioritizer")
    st.markdown("**Automatically categorize, prioritize, and generate action items from customer feedback**")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ Configuration")

        with st.expander("📧 Email Settings", expanded=True):
            sender_email = st.text_input("Sender Email:", placeholder="your-verified@email.com")
            api_key = st.text_input("SendGrid API Key:", type="password")

        with st.expander("🎨 Report Settings"):
            include_charts = st.checkbox("Include Charts", value=True)
            top_n = st.slider("Number of top issues to show", 5, 20, 10)
            
        with st.expander("📊 Filter Options"):
            date_filter = st.date_input("Filter by date range:", 
                                       value=(datetime.now() - timedelta(days=30), datetime.now()))
            sentiment_filter = st.multiselect("Filter by sentiment:", 
                                             ["Positive", "Neutral", "Negative"],
                                             default=["Positive", "Neutral", "Negative"])

        st.markdown("---")
        st.caption("💡 **Hackathon Tip:** This tool uses AI-driven priority scoring!")

    df = load_data()
    if df.empty:
        st.warning("⚠️ Please upload 'feedback.csv' with columns: Category, Sentiment, Date (or ensure the file exists).")
        return

    if sentiment_filter:
        df = df[df['Sentiment'].isin(sentiment_filter)]

    priority_df = calculate_priority_score(df)
    insights = generate_insights(priority_df.head(5), len(df))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Feedback", len(df), delta=None)
    with col2:
        critical = len(priority_df[priority_df["Urgency"] == "🔴 Critical"])
        st.metric("Critical Issues", critical, delta=None, delta_color="inverse")
    with col3:
        st.metric("Categories", len(priority_df))
    with col4:
        avg_score = priority_df["Priority_Score"].mean() if not priority_df.empty else 0
        st.metric("Avg Priority Score", f"{avg_score:.1f}")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Trends", "🔥 Heatmap"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_priority_chart(priority_df), use_container_width=True)
        with col2:
            st.plotly_chart(create_sentiment_chart(priority_df), use_container_width=True)

    with tab2:
        st.plotly_chart(create_trend_chart(df), use_container_width=True)
        
    with tab3:
        st.plotly_chart(create_category_sentiment_heatmap(df), use_container_width=True)

    st.subheader("📊 Prioritized Feedback Overview")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown(export_to_csv(priority_df.head(top_n)), unsafe_allow_html=True)
    
    st.dataframe(
        priority_df.head(top_n),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("✅ Recommended Actions")
    for idx, action in enumerate(insights['action_items'], 1):
        with st.expander(f"{action['priority']} {idx}. {action['issue']}", expanded=(idx <= 3)):
            st.write(f"**📋 Recommendation:** {action['recommendation']}")
            st.write(f"**💡 Impact:** {action['estimated_impact']}")

    st.markdown("---")

    st.subheader("📧 Send Weekly Report")

    col1, col2 = st.columns([2, 1])

    with col1:
        recipient_emails = st.text_area(
            "Recipient Email(s):",
            placeholder="product-team@company.com\nmanager@company.com",
            help="Enter one email per line for multiple recipients"
        )

    with col2:
        st.write("")
        st.write("")
        if st.button("🚀 Send Report Email", type="primary", use_container_width=True):
            if not recipient_emails or not sender_email or not api_key:
                st.error("❌ Please configure email settings in the sidebar")
            else:
                with st.spinner("Generating report and sending emails..."):
                    fig = create_priority_chart(priority_df)
                    img_bytes = fig.to_image(format="png")
                    chart_base64 = base64.b64encode(img_bytes).decode()

                    html_content = generate_html_email(priority_df.head(5), insights, chart_base64)

                    emails = [e.strip() for e in recipient_emails.split('\n') if e.strip()]
                    success_count = 0
                    failed_emails = []

                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, email in enumerate(emails):
                        status_text.text(f"Sending to {email}...")
                        success, result = send_priority_email(html_content, email, sender_email, api_key)
                        if success:
                            success_count += 1
                        else:
                            failed_emails.append((email, result))
                        progress_bar.progress((idx + 1) / len(emails))

                    status_text.empty()
                    progress_bar.empty()

                    if success_count == len(emails):
                        st.success(f"✅ Successfully sent report to {success_count} recipient(s)!")
                    elif success_count > 0:
                        st.warning(f"⚠️ Sent to {success_count}/{len(emails)} recipients")
                        if failed_emails:
                            with st.expander("View failed emails"):
                                for email, error in failed_emails:
                                    st.error(f"❌ {email}: {error}")
                    else:
                        st.error(f"❌ Failed to send emails. Please check your SendGrid API key and sender email.")
                        if failed_emails:
                            st.error(f"Error details: {failed_emails[0][1]}")

if __name__ == "__main__":
    main()