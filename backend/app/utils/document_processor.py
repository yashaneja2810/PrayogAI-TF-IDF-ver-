from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, BinaryIO
import os
from PyPDF2 import PdfReader
from docx import Document
import chardet

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]  # More granular splitting
        )
    
    def process_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        # Remove excessive whitespace and normalize line endings
        text = "\n".join(line.strip() for line in text.splitlines())
        return self.text_splitter.split_text(text)
    
    def detect_encoding(self, file_content: bytes) -> str:
        """Detect the encoding of file content"""
        result = chardet.detect(file_content)
        return result['encoding'] or 'utf-8'
    
    def process_pdf(self, file: BinaryIO) -> str:
        """Extract text from PDF file"""
        pdf = PdfReader(file)
        text_parts = []
        
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Clean and normalize the text
                text = " ".join(text.split())  # Normalize whitespace
                text_parts.append(text)
                
        return "\n\n".join(text_parts)  # Use double newline as page separator
    
    def process_docx(self, file: BinaryIO) -> str:
        """Extract text from DOCX file"""
        doc = Document(file)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:  # Only include non-empty paragraphs
                text_parts.append(text)
                
        return "\n\n".join(text_parts)  # Double newline between paragraphs
    
    def process_txt(self, file: BinaryIO) -> str:
        """Process text file with encoding detection"""
        content = file.read()
        if isinstance(content, str):
            return content
            
        encoding = self.detect_encoding(content)
        text = content.decode(encoding)
        
        # Normalize line endings and clean whitespace
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
    
    def process_file(self, filepath: str, filename: str) -> List[str]:
        """Process a file and return chunks based on file type"""
        text = ""
        file_ext = os.path.splitext(filename)[1].lower()
        
        try:
            with open(filepath, 'rb') as file:
                if file_ext == '.pdf':
                    text = self.process_pdf(file)
                elif file_ext == '.docx':
                    text = self.process_docx(file)
                elif file_ext == '.txt':
                    text = self.process_txt(file)
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                    
            # Split the extracted text into chunks
            return self.process_text(text)
        except Exception as e:
            raise ValueError(f"Error processing file {filename}: {str(e)}")

def generate_widget_code(bot_id: str, company_name: str) -> str:
    """Generate JavaScript widget code for the company"""
    return f"""
    <script>
        (function(w,d,s,o,f,js,fjs){{
            w['BotWidget']=o;w[o]=w[o]||function(){{(w[o].q=w[o].q||[]).push(arguments)}};
            js=d.createElement(s),fjs=d.getElementsByTagName(s)[0];
            js.id=o;js.src=f;js.async=1;fjs.parentNode.insertBefore(js,fjs);
        }}(window,document,'script','botw','https://your-backend-url/widget/{bot_id}.js'));
        
        botw('init', {{
            botId: '{bot_id}',
            company: '{company_name}'
        }});
    </script>
    """
