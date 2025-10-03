# 🎯 AI-Powered Customer Feedback Prioritizer

## 📌 Overview

The **AI-Powered Customer Feedback Prioritizer** helps organizations automatically analyze, categorize, and prioritize customer feedback. It provides actionable insights, visual dashboards, and automated weekly email reports for decision-makers.

This tool ensures that **critical customer issues are never overlooked**, saving time and helping teams focus on what matters most.

---

## 🚀 Features

* 📂 **Robust Data Handling**: Cleans and processes messy CSV feedback files.
* 📊 **Priority Scoring**: Calculates urgency using Frequency, Sentiment, and Recency.
* 🧠 **Insights Generation**: Produces executive summaries, recommended actions, and impact analysis.
* 📈 **Interactive Dashboards**:

  * Bar chart of top issues by priority.
  * Pie chart of urgency distribution.
  * Sentiment trends over time.
  * Heatmap of categories vs sentiment.
* 📧 **Automated Email Reporting**:

  * Professional HTML reports.
  * Top issues, action items, and charts embedded.
  * SendGrid integration for bulk recipients.

---

## 🛠 Tech Stack

* **Python** (Data processing + logic)
* **Streamlit** (Web dashboard)
* **Pandas** (Data cleaning & transformations)
* **Plotly** (Interactive visualizations)
* **SendGrid API** (Email automation)
* **HTML/CSS** (Report formatting)

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Mugesh-rugby/feedback-prioritizer.git
cd feedback-prioritizer
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Prepare Data

Create a `feedback.csv` file with columns:

```
Category, Sentiment, Date
```

* **Category** → Issue type (e.g., Payment, Login, Delivery)
* **Sentiment** → Positive / Neutral / Negative
* **Date** → Date of feedback (YYYY-MM-DD)

### 4️⃣ Run the App

```bash
streamlit run app.py
```

### 5️⃣ Configure Email (Optional)

* Get a **SendGrid API Key** from [SendGrid](https://sendgrid.com/).
* Verify your **sender email** in SendGrid.
* Enter these in the app sidebar.

---

## 📊 Usage Flow

1. **Upload/Use feedback.csv** → Data loads automatically.
2. **Filter feedback** → By date range and sentiment.
3. **View Dashboard** → Explore charts, trends, and heatmaps.
4. **Check Insights** → Executive summary and recommended actions.
5. **Export Reports** → Download CSV or send automated email.

---

## 📧 Email Report Example

The email report includes:

* Executive summary
* Top 5 priority issues
* Recommended actions
* Priority distribution chart

This ensures stakeholders **receive weekly insights directly in their inbox**.

---

## 📜 License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute it with attribution.

---

💡 *Developed to help businesses unlock the power of customer feedback.*
