def render_ioc_view(feed_service: FeedService):
    """Render IOC view with flat layout."""
    st.header("🛡️ Indicators of Compromise")

    # Get all IOCs
    iocs = feed_service.get_all_iocs()

    if not iocs:
        st.info("No IOCs found")
        return

    # Display IOCs with filtering options
    ioc_types = list(set(ioc["type"] for ioc in iocs))
    selected_type = st.selectbox("Filter by type", ["All"] + ioc_types)

    filtered_iocs = iocs
    if selected_type != "All":
        filtered_iocs = [ioc for ioc in iocs if ioc["type"] == selected_type]

    # Display IOCs in a flat layout
    for ioc in filtered_iocs:
        st.markdown(f"""
        <div style="border: 1px solid #e2e8f0; padding: 1rem; margin-bottom: 1rem; border-radius: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                <strong style="color: #e53e3e;">🔍 {ioc['type']}: {ioc['value']}</strong>
                <span style="color: #718096; font-size: 0.875rem;">{ioc['discovered_date']}</span>
            </div>
            <p style="margin: 0.5rem 0; color: #4a5568;">Found in: {ioc['article_title']}</p>
            <div style="margin-top: 0.5rem;">
                <div style="font-weight: 500; color: #2d3748;">Context:</div>
                <div style="background: #f7fafc; padding: 0.75rem; border-radius: 0.25rem; margin-top: 0.25rem;">
                    {ioc['context'] if ioc['context'] else 'No context available'}
                </div>
            </div>
            <div style="margin-top: 0.5rem;">
                <div style="background: #ebf8ff; padding: 0.5rem; border-radius: 0.25rem;">
                    Confidence: {ioc['confidence_score']}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
