import streamlit as st
import requests
import time
from requests.exceptions import RequestException

# Configuration
MAX_RETRIES = 5
RETRY_DELAY = 2
ALLOWED_FILE_TYPES = ["txt", "csv", "pdf"]

def make_request_with_retry(method, url, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            response = method(url, **kwargs)
            response.raise_for_status()  # Raise exception for non-200 status codes
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 502 and attempt < MAX_RETRIES - 1:
                with st.spinner(f'Retrying... (Attempt {attempt + 1}/{MAX_RETRIES})'):
                    time.sleep(RETRY_DELAY)
            else:
                raise e
        except RequestException as e:
            if attempt < MAX_RETRIES - 1:
                with st.spinner(f'Connection error. Retrying... (Attempt {attempt + 1}/{MAX_RETRIES})'):
                    time.sleep(RETRY_DELAY)
            else:
                raise e
    return response

def validate_url(url):
    """Validate the server URL format"""
    if not url:
        return False
    if not url.startswith(('http://', 'https://')):
        return False
    return True

def check_server_health(url):
    """Check if the server is accessible"""
    try:
        response = requests.get(f"{url}/docs")
        return response.status_code == 200
    except:
        return False

# Page configuration
st.set_page_config(
    page_title="RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add CSS for better UI
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .success-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session states
if 'server_url' not in st.session_state:
    st.session_state.server_url = ""
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'chatbot_id' not in st.session_state:
    st.session_state.chatbot_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'kb_id' not in st.session_state:
    st.session_state.kb_id = None

# Sidebar for configuration status
with st.sidebar:
    st.header("Configuration Status")
    steps = {
        "Server Setup": bool(st.session_state.server_url),
        "User Setup": bool(st.session_state.user_id),
        "Chatbot Setup": bool(st.session_state.chatbot_id),
        "Knowledge Base": bool(st.session_state.kb_id),
    }
    for step, completed in steps.items():
        if completed:
            st.success(f"✅ {step}")
        else:
            st.warning(f"⏳ {step}")

st.title("RAG System")

# Step 1: Server Configuration
st.header("1. Server Setup")
if st.session_state.current_step >= 1:
    input_url = st.text_input(
        "Server URL:", 
        value=st.session_state.server_url,
        help="Example: http://localhost:8000"
    )
    
    if input_url != st.session_state.server_url:
        if validate_url(input_url):
            if check_server_health(input_url):
                st.session_state.server_url = input_url
                st.success("✅ Server connected successfully")
                if st.session_state.current_step == 1:
                    st.session_state.current_step = 2
            else:
                st.error("❌ Unable to connect to server")
        else:
            st.error("❌ Invalid URL format")

# Step 2: User Setup
if st.session_state.current_step >= 2:
    st.header("2. User Setup")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Create New User")
        new_user_name = st.text_input("Enter username")
        create_user = st.button("Create User", disabled=not new_user_name)
        
        if create_user:
            try:
                response = make_request_with_retry(
                    requests.post,
                    f"{st.session_state.server_url}/users",
                    data={"name": new_user_name}
                )
                st.session_state.user_id = response.json()['id']
                st.success(f"User created! ID: {st.session_state.user_id}")
                if st.session_state.current_step == 2:
                    st.session_state.current_step = 3
            except Exception as e:
                st.error(f"Error creating user: {str(e)}")

    with col2:
        st.subheader("Existing User")
        user_id = st.text_input("Enter User ID", value=st.session_state.user_id or "")
        if user_id and user_id != st.session_state.user_id:
            st.session_state.user_id = user_id
            if st.session_state.current_step == 2:
                st.session_state.current_step = 3

# Step 3: Chatbot Setup
if st.session_state.current_step >= 3:
    st.header("3. Chatbot Setup")
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Create New Chatbot")
        new_bot_name = st.text_input("Chatbot Name")
        new_bot_desc = st.text_area("Description")
        create_bot = st.button("Create Chatbot", disabled=not new_bot_name)
        
        if create_bot:
            try:
                response = make_request_with_retry(
                    requests.post,
                    f"{st.session_state.server_url}/chatbots",
                    data={
                        "user_id": st.session_state.user_id,
                        "name": new_bot_name,
                        "description": new_bot_desc
                    }
                )
                st.session_state.chatbot_id = response.json()['id']
                st.success(f"Chatbot created! ID: {st.session_state.chatbot_id}")
                if st.session_state.current_step == 3:
                    st.session_state.current_step = 4
            except Exception as e:
                st.error(f"Error creating chatbot: {str(e)}")

    with col4:
        st.subheader("Existing Chatbot")
        chatbot_id = st.text_input("Enter Chatbot ID", value=st.session_state.chatbot_id or "")
        if chatbot_id and chatbot_id != st.session_state.chatbot_id:
            st.session_state.chatbot_id = chatbot_id
            if st.session_state.current_step == 3:
                st.session_state.current_step = 4

# Step 4: Knowledge Base and Configuration
if st.session_state.current_step >= 4:
    st.header("4. Knowledge Base Setup")
    
    with st.expander("Chatbot Settings", expanded=True):
        col5, col6, col7, col8 = st.columns(4)  # Changed to 4 columns
        with col5:
            temperature = st.slider("Temperature", 0.0, 1.0, 0.5, 0.1)
        with col6:
            max_tokens = st.slider("Max Tokens", 100, 4000, 2000, 100)
        with col7:
            k = st.slider("Top k Results", 1, 20, 10)
        with col8:
            rerank_type = st.selectbox(
                "Rerank Method",
                options=["similarity", "keywords"],
                help="similarity: Uses cosine similarity for reranking\nkeywords: Uses keyword overlap for reranking"
            )

        if st.button("Update Settings"):
            try:
                response = make_request_with_retry(
                    requests.post,
                    f"{st.session_state.server_url}/chatbots/{st.session_state.chatbot_id}/configure",
                    data={
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "k": k,
                        "rerank_type": rerank_type
                    }
                )
                st.success("Settings updated successfully!")
            except Exception as e:
                st.error(f"Error updating settings: {str(e)}")

    st.subheader("Knowledge Base")
    col8, col9 = st.columns(2)

    with col8:
        kb_name = st.text_input("Knowledge Base Name")
        kb_desc = st.text_area("Knowledge Base Description")
        create_kb = st.button("Create Knowledge Base", disabled=not kb_name)
        
        if create_kb:
            try:
                response = make_request_with_retry(
                    requests.post,
                    f"{st.session_state.server_url}/knowledge-bases",
                    data={
                        "chatbot_id": st.session_state.chatbot_id,
                        "name": kb_name,
                        "description": kb_desc
                    }
                )
                st.session_state.kb_id = response.json()['id']
                st.success(f"Knowledge base created! ID: {st.session_state.kb_id}")
                if st.session_state.current_step == 4:
                    st.session_state.current_step = 5
            except Exception as e:
                st.error(f"Error creating knowledge base: {str(e)}")

    with col9:
        kb_id = st.text_input("Or enter existing Knowledge Base ID", 
                             value=st.session_state.kb_id or '')
        if kb_id and kb_id != st.session_state.kb_id:
            st.session_state.kb_id = kb_id
            if st.session_state.current_step == 4:
                st.session_state.current_step = 5
                
# Step 5: Document Upload
if st.session_state.current_step >= 5:
    st.header("5. Document Upload")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=ALLOWED_FILE_TYPES,
        accept_multiple_files=True,
        help=f"Supported formats: {', '.join(ALLOWED_FILE_TYPES)}"
    )
    
    if uploaded_files:
        total_size = sum(file.size for file in uploaded_files)
        if total_size > 100 * 1024 * 1024:  # 100MB limit
            st.warning("⚠️ Total file size exceeds 100MB. Some files may fail to upload.")

        if st.button("Upload Documents"):
            with st.status("Processing documents...", expanded=True) as status:
                success_count = 0
                fail_count = 0
                
                for idx, file in enumerate(uploaded_files, 1):
                    progress_text = f"Processing file {idx}/{len(uploaded_files)}: {file.name}"
                    st.write(progress_text)
                    
                    # Initialize retry counter for each file
                    retry_count = 0
                    max_retries = 5
                    success = False

                    while retry_count < max_retries and not success:
                        try:
                            # Create files dictionary with single file
                            files = [("files", (file.name, file.getvalue(), file.type))]
                            
                            response = make_request_with_retry(
                                requests.post,
                                f"{st.session_state.server_url}/knowledge-bases/{st.session_state.kb_id}/documents",
                                files=files
                            )
                            
                            success = True
                            success_count += 1
                            st.success(f"✅ {file.name} processed successfully")

                        except Exception as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                st.warning(f"⚠️ Attempt {retry_count}/{max_retries} failed for {file.name}. Retrying...")
                                time.sleep(RETRY_DELAY)  # Use the same delay as make_request_with_retry
                            else:
                                fail_count += 1
                                st.error(f"❌ Error processing {file.name} after {max_retries} attempts: {str(e)}")
                
                # Final status update
                if fail_count == 0:
                    status.update(
                        label=f"Upload complete! All {success_count} files processed successfully.",
                        state="complete"
                    )
                    if st.session_state.current_step == 5:
                        st.session_state.current_step = 6
                else:
                    status.update(
                        label=f"Upload finished with issues. Success: {success_count}, Failed: {fail_count}",
                        state="error"
                    )
                    
# Step 6: Chat Interface
if st.session_state.current_step >= 6:
    st.header("6. Chat Interface")
    
    # Add a container for chat messages with fixed height and scrolling
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "documents" in message and message["documents"]:
                    with st.expander("View Sources"):
                        for doc in message["documents"]:
                            st.markdown("---")
                            st.markdown(f"**Chunk ID**: `{doc['id']}`")
                            st.markdown(f"**Document**: {doc['name']}")
                            
                            # Display scores in columns
                            col1, col2 = st.columns(2)
                            with col1:
                                if doc.get('similarity_score') is not None:
                                    st.markdown(f"**Similarity Score**: {doc['similarity_score']:.3f}")
                            with col2:
                                if doc.get('keyword_overlap_score') is not None:
                                    st.markdown(f"**Keyword Overlap**: {doc['keyword_overlap_score']:.3f}")
                            
                            if doc.get('chunk_index') is not None and doc.get('total_chunks') is not None:
                                st.markdown(f"**Chunk**: {doc['chunk_index'] + 1} of {doc['total_chunks']}")
                            if doc.get('created_at'):
                                created_time = datetime.strptime(doc['created_at'], '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
                                st.markdown(f"**Created**: {created_time}")
                            st.markdown(f"**Preview**: {doc['preview']}")
                            
                            # Display keywords with scores
                            if doc.get('keywords'):
                                st.markdown("**Keywords**:")
                                for kw, score in zip(doc.get('keywords', []), doc.get('keyword_scores', [])):
                                    st.markdown(f"- {kw} ({score:.2f})")

    # Chat input
    user_query = st.chat_input("Ask a question...")
    
    if user_query:
        # Add user message
        with st.chat_message("user"):
            st.write(user_query)
        
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_query
        })
        
        # Get bot response
        with st.chat_message("assistant"):
            try:
                with st.spinner('Thinking...'):
                    response = make_request_with_retry(
                        requests.post,
                        f"{st.session_state.server_url}/query",
                        data={
                            "query": user_query,
                            "chatbot_id": st.session_state.chatbot_id
                        }
                    )
                    
                    result = response.json()
                    st.write(result['answer'])
                    
                    # Add bot message to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result['answer'],
                        "documents": result.get('documents', [])
                    })
                    
                    # Show sources if available
                    if result.get('documents'):
                        with st.expander("View Sources"):
                            for doc in result['documents']:
                                st.markdown("---")
                                st.markdown(f"**Chunk ID**: `{doc['id']}`")
                                st.markdown(f"**Document**: {doc['name']}")
                                
                                # Display scores in columns
                                col1, col2 = st.columns(2)
                                with col1:
                                    if doc.get('similarity_score') is not None:
                                        st.markdown(f"**Similarity Score**: {doc['similarity_score']:.3f}")
                                with col2:
                                    if doc.get('keyword_overlap_score') is not None:
                                        st.markdown(f"**Keyword Overlap**: {doc['keyword_overlap_score']:.3f}")
                                
                                if doc.get('chunk_index') is not None and doc.get('total_chunks') is not None:
                                    st.markdown(f"**Chunk**: {doc['chunk_index'] + 1} of {doc['total_chunks']}")
                                if doc.get('created_at'):
                                    created_time = datetime.strptime(doc['created_at'], '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
                                    st.markdown(f"**Created**: {created_time}")
                                st.markdown(f"**Preview**: {doc['preview']}")
                                
                                # Display keywords with scores
                                if doc.get('keywords'):
                                    st.markdown("**Keywords**:")
                                    for kw, score in zip(doc.get('keywords', []), doc.get('keyword_scores', [])):
                                        st.markdown(f"- {kw} ({score:.2f})")

            except Exception as e:
                st.error(f"Error getting response: {str(e)}")

    # Add controls in a sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("Chat Controls")
        
        # Temperature control for real-time adjustment
        temp = st.slider(
            "Response Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Higher values make the output more random, lower values make it more focused and deterministic"
        )

        # Clear chat button
        if st.session_state.chat_history and st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

        # Session info
        st.markdown("---")
        st.subheader("Session Information")
        if st.session_state.user_id:
            st.info(f"User ID: {st.session_state.user_id}")
        if st.session_state.chatbot_id:
            st.info(f"Chatbot ID: {st.session_state.chatbot_id}")
        if st.session_state.kb_id:
            st.info(f"Knowledge Base ID: {st.session_state.kb_id}")

        # Reset button
        if st.button("Reset All Settings", type="primary"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

# Add error handling for the entire app
try:
    if not st.session_state.server_url and st.session_state.current_step > 1:
        st.error("Server URL not configured. Please set up the server first.")
        st.session_state.current_step = 1
    elif not st.session_state.user_id and st.session_state.current_step > 2:
        st.warning("User not configured. Please set up a user first.")
        st.session_state.current_step = 2
    elif not st.session_state.chatbot_id and st.session_state.current_step > 3:
        st.warning("Chatbot not configured. Please set up a chatbot first.")
        st.session_state.current_step = 3
    elif not st.session_state.kb_id and st.session_state.current_step > 4:
        st.warning("Knowledge base not configured. Please set up a knowledge base first.")
        st.session_state.current_step = 4
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")
    st.button("Reset Application", on_click=lambda: st.session_state.clear())
