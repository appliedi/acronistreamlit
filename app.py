import matplotlib.pyplot as plt

def generate_pdf_updated(data, tenant_name, bar_fig, pie_fig):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt="Acronis Billing Review", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Report for {tenant_name}", ln=True, align='C')
    
    
    bar_img_path = "bar_plot.png"
    pie_img_path = "pie_plot.png"
    bar_fig.write_image(bar_img_path)
    pie_fig.write_image(pie_img_path)
    
    pdf.image(bar_img_path, x=10, y=pdf.get_y(), w=190)
    pdf.ln(65)
    pdf.image(pie_img_path, x=10, y=pdf.get_y(), w=190)
    pdf.ln(65)
    
    col_widths = [25, 25, 20, 40, 20, 25, 20, 25]
    columns = ['Service name', 'Edition', 'SKU', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']
    
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

        # New section for product/SKU analysis
        st.subheader("Product/SKU Analysis")
        
        # Create selectboxes for product and SKU filtering
        col1, col2 = st.columns(2)
        
        with col1:
            # Get unique service names for selection
            service_options = ['All Services'] + list(merged_data['Service name'].unique())
            selected_service = st.selectbox("Select Service:", service_options)
        
        with col2:
            # Filter SKUs based on selected service and create formatted options
            if selected_service == 'All Services':
                sku_data_for_dropdown = merged_data[['Metric name', 'SKU']].drop_duplicates()
            else:
                sku_data_for_dropdown = merged_data[merged_data['Service name'] == selected_service][['Metric name', 'SKU']].drop_duplicates()
            
            # Create formatted SKU options with "Metric Name - SKU" format
            sku_options = ['All SKUs']
            sku_mapping = {'All SKUs': 'All SKUs'}
            
            for _, row in sku_data_for_dropdown.iterrows():
                formatted_option = f"{row['Metric name']} - {row['SKU']}"
                sku_options.append(formatted_option)
                sku_mapping[formatted_option] = row['SKU']
            
            selected_sku_display = st.selectbox("Select SKU:", sku_options)
            selected_sku = sku_mapping[selected_sku_display]
        
        # Filter data based on selections
        filtered_product_data = merged_data.copy()
        
        if selected_service != 'All Services':
            filtered_product_data = filtered_product_data[filtered_product_data['Service name'] == selected_service]
        
        if selected_sku != 'All SKUs':
            filtered_product_data = filtered_product_data[filtered_product_data['SKU'] == selected_sku]
        
        # Display filtered results
        if not filtered_product_data.empty:
            st.subheader(f"Customer Usage for {selected_service} - {selected_sku}")
            
            # Create summary table grouped by tenant
            product_summary = filtered_product_data.groupby(['Tenant name']).agg({
                'Total usage': 'sum',
                'total': 'sum',
                'perunit': 'first',  # Assuming same price per unit for same SKU
                'Edition': 'first',
                'Metric name': 'first',
                'Metric unit': 'first'
            }).reset_index()
            
            # Format the pricing columns
            product_summary['perunit_formatted'] = product_summary['perunit'].map("${:,.2f}".format)
            product_summary['total_formatted'] = product_summary['total'].map("${:,.2f}".format)
            
            # Sort by total cost descending
            product_summary = product_summary.sort_values('total', ascending=False)
            
            # Display the summary table
            display_columns = ['Tenant name', 'Edition', 'Metric name', 'Metric unit', 'Total usage', 'perunit_formatted', 'total_formatted']
            column_names = ['Customer', 'Edition', 'Metric Name', 'Metric Unit', 'Total Usage', 'Price per Unit', 'Total Cost']
            
            summary_display = product_summary[display_columns].copy()
            summary_display.columns = column_names
            
            st.write(summary_display)
            
            # Show summary statistics for this product/SKU
            total_customers = len(product_summary)
            total_usage_sum = product_summary['Total usage'].sum()
            total_revenue = product_summary['total'].sum()
            avg_usage_per_customer = total_usage_sum / total_customers if total_customers > 0 else 0
            
            # Get the metric unit for display
            metric_unit = product_summary['Metric unit'].iloc[0] if len(product_summary) > 0 else ""
            
            st.write(f"**Summary for {selected_service} - {selected_sku}:**")
            st.write(f"- Total Customers: {total_customers}")
            st.write(f"- Total Quantity: {total_usage_sum:,.2f} {metric_unit}")
            st.write(f"- Total Revenue: ${total_revenue:,.2f}")
            st.write(f"- Average Quantity per Customer: {avg_usage_per_customer:,.2f} {metric_unit}")
            
            # Create a bar chart showing top customers for this product/SKU
            if len(product_summary) > 1:
                top_customers_for_product = product_summary.head(10)  # Show top 10 customers
                fig_product = px.bar(
                    top_customers_for_product, 
                    x='Tenant name', 
                    y='total',
                    title=f"Top Customers by Revenue - {selected_service} ({selected_sku})",
                    labels={'total': 'Total Revenue ($)', 'Tenant name': 'Customer'}
                )
                fig_product.update_layout(xaxis_tickangle=45)
                st.plotly_chart(fig_product)
        else:
            st.write("No data found for the selected service/SKU combination.")

        tenant_name = st.selectbox("Select Tenant name:", merged_data['Tenant name'].unique())

        tenant_data = merged_data[merged_data['Tenant name'] == tenant_name][['Service name', 'Edition', 'SKU', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']]
        
        # Convert 'total' to float for plotting
        tenant_data['total_numeric'] = tenant_data['total'].astype(float)
        
        # Format 'perunit' and 'total' as US dollars for display
        tenant_data['perunit'] = tenant_data['perunit'].map("${:,.2f}".format)
        tenant_data['total'] = tenant_data['total'].map("${:,.2f}".format)
        st.write(tenant_data[['Service name', 'Edition', 'SKU', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']])
        
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
            pdf_data = generate_pdf_updated(tenant_data[['Service name', 'Edition', 'SKU', 'Metric name', 'Metric unit', 'Total usage', 'perunit', 'total']], tenant_name, bar_fig, pie_fig)
            st.download_button(
                label="Download PDF Report",
                data=pdf_data,
                file_name=f"Report_{tenant_name}.pdf",
                mime="application/pdf"
            )


def generate_pdf_updated_v2(data, tenant_name, bar_fig, pie_fig):
    # Use landscape page layout
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(0, 10, txt="Acronis Billing Review", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"Report for {tenant_name}", ln=True, align='C')
    
    # Reflect the sum of the total column for the selected tenant
    
    total_usage = data["total"].sum()
    pdf.cell(0, 10, txt=f"Total Usage Amount: {total_usage:,.2f}", ln=True, align='C')

    # Save figures as images
    bar_img_path = "bar_plot.png"
    pie_img_path = "pie_plot.png"
    bar_fig.write_image(bar_img_path)
    pie_fig.write_image(pie_img_path)
    
    # Add images to PDF
    pdf.image(bar_img_path, x=10, y=pdf.get_y(), w=260)
    pdf.ln(75)  # leave space for the image
    pdf.image(pie_img_path, x=10, y=pdf.get_y(), w=260)
    pdf.ln(75)  # leave space for the image
    
    # Table with adjusted column widths
    col_widths = [40, 40, 50, 30, 40, 30, 40]
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
