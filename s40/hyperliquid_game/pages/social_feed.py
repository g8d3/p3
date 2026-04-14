import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Social Feed - Hyperliquid Trading Game", layout="wide")

st.title("Social Feed - All Backtest Results")
st.markdown("See what others (and the AI) have been trading!")

# Load results
results_file = Path('backtest_results.json')
if results_file.exists():
    with open(results_file, 'r') as f:
        all_results = json.load(f)
    
    if all_results:
        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        
        # Sort by timestamp descending
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
        
        # Display summary metrics
        st.subheader("Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Backtests", len(df))
        with col2:
            if 'total_return_pct' in df.columns:
                avg_return = df['total_return_pct'].mean()
                st.metric("Avg Return", f"{avg_return:.2f}%")
        with col3:
            if 'user_id' in df.columns:
                unique_users = df['user_id'].nunique()
                st.metric("Unique Users", unique_users)
        
        # Display detailed table
        st.subheader("All Results")
        
        # Format columns for better readability
        display_df = df.copy()
        if 'timestamp' in display_df.columns:
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        if 'total_return_pct' in display_df.columns:
            display_df['total_return_pct'] = display_df['total_return_pct'].apply(lambda x: f"{x:.2f}%")
        if 'max_drawdown_pct' in display_df.columns:
            display_df['max_drawdown_pct'] = display_df['max_drawdown_pct'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No backtest results yet. Run some backtests to see them here!")
else:
    st.info("No results file found. Run your first backtest to start tracking results.")

# Add navigation back to main app
st.sidebar.title("Navigation")
if st.sidebar.button("← Back to Backtest"):
    st.switch_page("app.py")