import streamlit as st
import requests
import time
from requests.exceptions import RequestException
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

# Configuration
from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    MAX_RETRIES: int = 5
    RETRY_DELAY: int = 2
    ALLOWED_FILE_TYPES: List[str] = field(default_factory=lambda: ["txt", "csv", "pdf"])
    MAX_FILE_SIZE_MB: int = 100
    DEFAULT_TEMPERATURE: float = 0.5
    DEFAULT_MAX_TOKENS: int = 2000
    DEFAULT_TOP_K: int = 10

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if response.status_code == 502 and attempt < Config.MAX_RETRIES - 1:
                    with st.spinner(f'Retrying... (Attempt {attempt + 1}/{Config.MAX_RETRIES})'):
                        time.sleep(Config.RETRY_DELAY)
                else:
                    raise e
            except RequestException as e:
                if attempt < Config.MAX_RETRIES - 1:
                    with st.spinner(f'Connection error. Retrying... (Attempt {attempt + 1}/{Config.MAX_RETRIES})'):
                        time.sleep(Config.RETRY_DELAY)
                else:
                    raise e

    def create_user(self, name: str) -> Dict[str, Any]:
        response = self._make_request("POST", "users", data={"name": name})
        return response.json()

    def create_chatbot(self, user_id: str, name: str, description: str) -> Dict[str, Any]:
        response = self._make_request(
            "POST", 
            "chatbots",
            data={"user_id": user_id, "name": name, "description": description}
        )
        return response.json()

    def create_knowledge_base(self, chatbot_id: str, name: str, description: str) -> Dict[str, Any]:
        response = self._make_request(
            "POST",
            "knowledge-bases",
            data={"chatbot_id": chatbot_id, "name": name, "description": description}
        )
        return response.json()

    def upload_document(self, kb_id: str, file) -> Dict[str, Any]:
        files = [("files", (file.name, file.getvalue(), file.type))]
        response = self._make_request(
            "POST",
            f"knowledge-bases/{kb_id}/documents",
            files=files
        )
        return response.json()

    def query_chatbot(self, chatbot_id: str, query: str, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Query the chatbot with enhanced metadata and chunk information
        
        Args:
            chatbot_id: The ID of the chatbot
            query: The user's query
            include_metadata: Whether to include document metadata in the response
            
        Returns:
            Dict containing the response with enhanced chunk information
        """
        response = self._make_request(
            "POST",
            "query",
            json={
                "query": query,
                "chatbot_id": chatbot_id,
                "include_metadata": include_metadata,
                "return_chunks": True  # Request chunk information
            }
        )
        return response.json()

class SessionState:
    """Manages application state and validation"""
    @staticmethod
    def initialize_session_state():
        if 'api_client' not in st.session_state:
            st.session_state.api_client = None
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

    @staticmethod
    def validate_state():
        if not st.session_state.server_url and st.session_state.current_step > 1:
            raise ValueError("Server URL not configured")
        if not st.session_state.user_id and st.session_state.current_step > 2:
            raise ValueError("User not configured")
        if not st.session_state.chatbot_id and st.session_state.current_step > 3:
            raise ValueError("Chatbot not configured")
        if not st.session_state.kb_id and st.session_state.current_step > 4:
            raise ValueError("Knowledge base not configured")

class UIComponents:
    """UI Component rendering"""
    @staticmethod
    def render_reference_chunk(doc: Dict[str, Any], index: int):
        """Renders a single reference chunk with detailed information"""
        with st.container():
            st.markdown(f"**📄 Document**: {doc['name']}")
            st.markdown(f"**📍 Chunk Index**: {index}")
            
            # Display chunk content with formatting
            st.markdown("**📝 Content:**")
            st.markdown(f"```\n{doc['preview']}\n```")
            
            # Display keywords if available
            if doc.get('keywords'):
                st.markdown("**🔑 Keywords:**")
                for keyword in doc['keywords']:
                    st.markdown(f"- {keyword}")
            
            # Display metadata if available
            if doc.get('metadata'):
                st.markdown("**ℹ️ Metadata:**")
                for key, value in doc['metadata'].items():
                    st.markdown(f"- **{key}**: {value}")
            
            st.markdown("---")  # Separator between chunks

    @staticmethod
    def render_chat_message(message: Dict[str, Any]):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "documents" in message and message["documents"]:
                with st.expander("📚 View Source Documents"):
                    st.markdown("### Retrieved Chunks")
                    for idx, doc in enumerate(message["documents"], 1):
                        UIComponents.render_reference_chunk(doc, idx)

    @staticmethod
    def render_sidebar_status():
        st.sidebar.header("Configuration Status")
        steps = {
            "Server Setup": bool(st.session_state.server_url),
            "User Setup": bool(st.session_state.user_id),
            "Chatbot Setup": bool(st.session_state.chatbot_id),
            "Knowledge Base": bool(st.session_state.kb_id),
        }
        for step, completed in steps.items():
            if completed:
                st.sidebar.success(f"✅ {step}")
            else:
                st.sidebar.warning(f"⏳ {step}")

def main():
    st.set_page_config(
        page_title="RAG System",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    SessionState.initialize_session_state()

    try:
        # Validate current state
        SessionState.validate_state()
        
        # Render sidebar status
        UIComponents.render_sidebar_status()

        # Main application logic...
        # [Rest of the application code would go here, broken down into smaller functions]

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        if st.button("Reset Application"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
