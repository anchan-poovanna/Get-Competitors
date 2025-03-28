import streamlit as st
import pandas as pd
import requests
import json
from urllib.parse import urlparse, quote_plus
from firecrawl import FirecrawlApp

# Set page config
st.set_page_config(
    page_title="SEO Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load API keys from secrets
firecrawl_api_key = st.secrets.get("FIRECRAWL_API_KEY")
serp_api_key = st.secrets.get("SERP_API_KEY")

# Initialize the FirecrawlApp
app = FirecrawlApp(api_key=firecrawl_api_key)

# Fixed CSS with dark theme styling
st.markdown("""
<style>
    /* Base styles for the app */
    .stApp {
        background-color: #1e1e1e;
    }
    
    /* Text color */
    body, p, h1, h2, h3, .stTextInput > label, .stSelectbox > label, .stTab > button {
        color: #ffffff !important;
    }
    
    div[data-testid="stVerticalBlock"] {
        color: #ffffff;
    }
    
    /* Input containers */
    .stTextInput > div > div {
        background-color: #2d2d2d;
        border-radius: 5px;
        border: 1px solid #444;
        color: white;
    }
    
    /* Make sure input text is visible */
    .stTextInput input {
        color: white !important;
    }
    
    /* Tabs styling */
    button[data-baseweb="tab"] {
        color: #ffffff !important;
    }
    
    div[data-testid="stTabContent"] {
        background-color: #1e1e1e;
    }
    
    /* Content sections */
    .content-section {
        background-color: #2d2d2d;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.5);
        color: #ffffff;
    }
    
    /* Your site highlight in tables */
    .your-site-row {
        background-color: #2c5282 !important;
        border-left: 3px solid #4299e1 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #4299e1;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        background-color: #3182ce;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
    }
    
    /* Console output styling */
    .console-output {
        font-family: monospace;
        background-color: #2d2d2d;
        color: #e2e8f0;
        padding: 15px;
        border-radius: 5px;
        white-space: pre-wrap;
        border: 1px solid #444;
    }
    
    /* JSON display */
    .json-view {
        font-family: monospace;
        background-color: #2d2d2d;
        color: #e2e8f0;
        padding: 20px;
        border-radius: 5px;
        white-space: pre-wrap;
        overflow-x: auto;
        border: 1px solid #444;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background-color: #38a169;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #4299e1 !important;
    }
    
    /* Status messages */
    div[data-baseweb="notification"] {
        background-color: #2d2d2d !important;
        border: 1px solid #444 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

def extract_focus_keyword(url):
    """Extract the focus keyword from a given URL using Firecrawl"""
    try:
        with st.spinner("Extracting focus keywords..."):
            data = app.extract(
                [url], 
                {
                    'prompt': '''
                    You are an SEO keyword specialist. Analyze this page and identify:
                    1. The primary focus keyword this page is targeting
                    
                    Base your analysis on:
                    - Page title
                    - Headings (H1, H2, etc.)
                    - Content and keyword density
                    - URL structure
                    - Image alt tags (if available)
                    
                    Provide only the focus keyword and do not include any explanations.
                    ''',
                    'schema': {
                        "type": "object",
                        "properties": {
                            "focus_keyword": {
                                "type": "string",
                                "description": "The primary SEO keyword or phrase that the page appears to be targeting"
                            }
                        },
                        "required": ["focus_keyword"]
                    }
                }
            )
            
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list) and len(data) > 0:
                return data[0]
            else:
                return data
            
    except Exception as e:
        st.error(f"Error extracting focus keyword: {str(e)}")
        return None

def extract_keyword_manually(url):
    """Manual fallback method to extract keywords from URL"""
    path = urlparse(url).path
    parts = path.strip('/').split('/')
    if parts:
        keyword = parts[-1].replace('-', ' ')
        return {"focus_keyword": keyword}
    return {"focus_keyword": "all purpose cleaner"}

def check_serp_rankings(keyword, target_url):
    """Query SERP API to check rankings for a keyword and identify competitors"""
    try:
        with st.spinner(f"Checking SERP rankings for '{keyword}'..."):
            # Make sure keyword is URL-friendly
            encoded_keyword = quote_plus(keyword)
            
            # Extract domain for partial matching
            target_domain = urlparse(target_url).netloc
            
            # Query SERP API
            api_url = f"https://serpapi.com/search.json?api_key={serp_api_key}&q={encoded_keyword}&num=100&gl=us&hl=en"
            
            response = requests.get(api_url)
            
            if response.status_code != 200:
                return {
                    'error': f"SERP API returned status code {response.status_code}",
                    'keyword': keyword,
                    'target_position': "N/A",
                    'competitors': []
                }
                
            data = response.json()
            
            # Extract organic search results
            organic_results = data.get('organic_results', [])
            
            # Find ranking position of target URL
            target_position = "N/A"
            competitors = []
            domain_positions = []
            
            for i, result in enumerate(organic_results):
                position = i + 1
                result_url = result.get('link', '')
                result_domain = urlparse(result_url).netloc
                result_title = result.get('title', 'No Title')
                
                # Check if the target domain appears in this result's domain
                if target_domain in result_domain:
                    domain_positions.append(position)
                
                # Add to competitors list
                competitors.append({
                    'position': position,
                    'title': result_title,
                    'url': result_url,
                    'domain': result_domain,
                    'is_your_site': target_domain in result_domain
                })
            
            # If we found the domain in any results, set the target position
            if domain_positions:
                target_position = domain_positions[0]  # Use the first occurrence
            
            return {
                'keyword': keyword,
                'target_position': target_position,
                'all_domain_positions': domain_positions,
                'competitors': competitors
            }
        
    except Exception as e:
        st.error(f"Error in SERP rankings check: {str(e)}")
        return {
            'error': str(e),
            'keyword': keyword,
            'target_position': "N/A",
            'competitors': []
        }

# Main application
def main():
    # App title
    st.markdown("<h1 style='text-align: center; color: #4299e1;'>SEO Analyzer</h1>", unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2 = st.tabs(["Analysis", "JSON Results"])
    
    with tab1:
        # URL input
        st.markdown("<div class='content-section'>", unsafe_allow_html=True)
        url = st.text_input("Enter URL to analyze:", placeholder="https://example.com/page")
        analyze_button = st.button("Analyze")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if not url and not analyze_button:
            st.markdown("<div class='content-section' style='text-align: center; padding: 40px;'>Enter a URL above to begin analysis.</div>", unsafe_allow_html=True)
            return
        
        # Make sure URL has proper protocol
        if url and not url.startswith("http"):
            url = "https://" + url.lstrip(":/")
        
        if analyze_button and url:
            # Step 1: Extract focus keyword
            with st.spinner("Analyzing URL..."):
                st.markdown(f"<div class='console-output'>Analyzing URL: {url}</div>", unsafe_allow_html=True)
                
                keyword_data = extract_focus_keyword(url)
                
                # Use fallback method if Firecrawl fails
                if not keyword_data or not isinstance(keyword_data, dict) or 'focus_keyword' not in keyword_data:
                    st.markdown("<div class='console-output'>Firecrawl extraction failed, using fallback method</div>", unsafe_allow_html=True)
                    keyword_data = extract_keyword_manually(url)
                
                # Extract focus keyword from the response
                focus_keyword = keyword_data.get('focus_keyword', '')
                if not focus_keyword:
                    focus_keyword = "all purpose cleaner"
                
                st.markdown(f"<div class='console-output'>The focus keyword is: {focus_keyword}</div>", unsafe_allow_html=True)
                
                # Step 2: Get SERP results
                st.markdown(f"<div class='console-output'>Checking SERP rankings for keyword: '{focus_keyword}'</div>", unsafe_allow_html=True)
                serp_results = check_serp_rankings(focus_keyword, url)
            
            # Display results in console-style format
            st.markdown("<div class='content-section'>", unsafe_allow_html=True)
            
            # Create console-style output
            console_output = f"""===== FOCUS KEYWORD & SERP ANALYSIS =====
URL: {url}
The focus keyword is: {focus_keyword}
"""
            
            if 'error' in serp_results:
                console_output += f"Error getting SERP results: {serp_results['error']}"
            else:
                # Display SERP position
                console_output += f"You are ranking in: {serp_results['target_position']}\n"
                
                # If domain appears in multiple positions, show them all
                if 'all_domain_positions' in serp_results and len(serp_results['all_domain_positions']) > 1:
                    all_positions = ", ".join(map(str, serp_results['all_domain_positions']))
                    console_output += f"Your domain appears at positions: {all_positions}\n\n"
                else:
                    console_output += "\n"
                
                # Display competitors
                console_output += "Your competitors are:\n"
                target_domain = urlparse(url).netloc
                
                for comp in serp_results['competitors'][:10]:  # Show top 10 competitors
                    if comp['domain'] == target_domain:
                        console_output += f"#{comp['position']} - {comp['title']} (YOUR SITE)\n"
                    else:
                        console_output += f"#{comp['position']} - {comp['title']}\n"
                    console_output += f"    URL: {comp['url']}\n\n"
            
            st.markdown(f"<div class='console-output'>{console_output}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Save results to session state for the JSON tab
            if 'error' not in serp_results:
                full_analysis = {
                    'url': url,
                    'focus_keyword': focus_keyword,
                    'serp_results': serp_results
                }
                st.session_state.analysis_json = json.dumps(full_analysis, indent=2)
            
    with tab2:
        if 'analysis_json' in st.session_state:
            st.markdown("<div class='content-section'>", unsafe_allow_html=True)
            st.markdown("<h3>SERP Analysis Results (JSON)</h3>", unsafe_allow_html=True)
            st.markdown(f"<div class='json-view'>{st.session_state.analysis_json}</div>", unsafe_allow_html=True)
            
            # Download button for JSON
            st.download_button(
                label="Download JSON",
                data=st.session_state.analysis_json,
                file_name="serp_analysis_results.json",
                mime="application/json"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='content-section' style='text-align: center; padding: 40px;'>Run an analysis to view JSON results.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()