
import streamlit as st
import pandas as pd
import numpy as np
import io
from fpdf import FPDF
import plotly.express as px

def filter_current_usage(data):
    data['SKU'] = data['SKU'].astype(str)
    filtered_data = data[~data['SKU'].isin(['nan']) & ~data['SKU'].str.startswith('C')]
    return filtered_data

def calculate_merged_data(usage_data, sku_data):
    merged_data = pd.merge(usage_data, sku_data, on="SKU", how="left")
    merged_data["perunit"] = merged_data["Commitment 4"]
    merged_data["total"] = merged_data["Total usage"] * merged_data["perunit"]
    merged_data.drop("Commitment 4", axis=1, inplace=True)
    return merged_data

def generate_pdf(data, tenant_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Report for {tenant_name}", ln=True, align='C')
    
    col_widths = [40, 40, 50, 20, 30, 30, 30]
    columns = ['Service name', 'Edition', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']
    
    for i, column in enumerate(columns):
        pdf.cell(col_widths[i], 10, txt=column, border=1)
    pdf.ln()
    
    for index, row in data.iterrows():
        for i, column in enumerate(columns):
            pdf.cell(col_widths[i], 10, txt=str(row[column]), border=1)
        pdf.ln()
    
    output = io.BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    return pdf_bytes

st.title("SKU Commitment Calculator 📊")

current_usage_file = st.file_uploader("Upload the 'current usage' spreadsheet:", type=['xlsx'])

if current_usage_file:
    current_usage_data = pd.read_excel(current_usage_file, header=7)
    filtered_data = filter_current_usage(current_usage_data)
    
    sku_file = st.file_uploader("Upload the 'SKU commitment' spreadsheet:", type=['xlsx'])

    if sku_file:
        sku_data = pd.read_excel(sku_file)
        merged_data = calculate_merged_data(filtered_data, sku_data)
        total_costs = merged_data.groupby('Tenant name')['total'].sum()

        # Displaying the top 30 customers based on total cost
        st.subheader("Top 30 Customers by Total Cost")
        top_customers = total_costs.sort_values(ascending=False).head(30)
        st.write(top_customers.reset_index(name='Total Cost'))

        tenant_name = st.selectbox("Select Tenant name:", merged_data['Tenant name'].unique())

        tenant_data = merged_data[merged_data['Tenant name'] == tenant_name][['Service name', 'Edition', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']]
        
        # Convert 'total' to float for plotting
        tenant_data['total_numeric'] = tenant_data['total'].astype(float)
        
        # Format 'perunit' and 'total' as US dollars for display
        tenant_data['perunit'] = tenant_data['perunit'].map("${:,.2f}".format)
        tenant_data['total'] = tenant_data['total'].map("${:,.2f}".format)
        st.write(tenant_data[['Service name', 'Edition', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']])
        
        # Display summary statistics
        st.subheader("Summary Statistics")
        total_cost = tenant_data['total_numeric'].sum()
        avg_cost_per_unit = total_cost / len(tenant_data)
        
        st.write(f"Total Cost for {tenant_name}: ${total_cost:,.2f}")
        st.write(f"Average Cost per Unit for {tenant_name}: ${avg_cost_per_unit:,.2f}")

        # Bar plot to compare total values for different services using Plotly
        st.subheader(f"Total cost by Service for {tenant_name}")
        bar_fig = px.bar(tenant_data, x='Service name', y='total_numeric', title=f"Total Cost by Service for {tenant_name}")
        st.plotly_chart(bar_fig)

        # Adjusting the pie chart creation code
        comparison_df = pd.DataFrame({
            'label': [tenant_name, "Largest Tenant"],
            'value': [total_cost, total_costs.max()]
        })
        pie_fig = px.pie(comparison_df, names='label', values='value', title=f"Total Cost Comparison of {tenant_name} with Largest Tenant", 
                         hover_data={'label': True, 'value': ':$.2f'}, hole=0.3)
        st.plotly_chart(pie_fig)

        # Download options
        st.subheader("Download Options 📥")

        if st.button("Download Merged Data as Excel"):
            towrite = io.BytesIO()
            merged_data.to_excel(towrite, index=False)
            towrite.seek(0)
            st.download_button(
                label="Download Excel File",
                data=towrite,
                file_name="MergedUsageWithCosts.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if st.button("Download Report as PDF"):
            pdf_data = generate_pdf(tenant_data[['Service name', 'Edition', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']], tenant_name)
            st.download_button(
                label="Download PDF Report",
                data=pdf_data,
                file_name=f"Report_{tenant_name}.pdf",
                mime="application/pdf"
            )
